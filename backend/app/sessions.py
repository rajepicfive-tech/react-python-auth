from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .config import ACCESS_COOKIE, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_COOKIE
from .cookies import ACCESS_PATH, clear_auth_cookies
from .database import get_db
from .models import RefreshToken, User
from .security import decode_token, get_current_user, utcnow

# Lets a logged-in user inspect their own tokens and sessions, and end them early.
router = APIRouter(prefix="/api/auth", tags=["sessions"])


def _token_info(claims: dict, now: datetime) -> dict:
    expires_at = datetime.fromtimestamp(claims["exp"], timezone.utc)
    return {
        "jti": claims.get("jti"),
        "issued_at": datetime.fromtimestamp(claims["iat"], timezone.utc),
        "expires_at": expires_at,
        "expires_in": max(0, int((expires_at - now).total_seconds())),
    }


def _current_family(request: Request, db: Session) -> str | None:
    try:
        jti = decode_token(request.cookies.get(REFRESH_COOKIE, ""), "refresh")["jti"]
    except (jwt.PyJWTError, KeyError):
        return None
    return db.scalar(select(RefreshToken.family_id).where(RefreshToken.jti == jti))


@router.get("/session")
def session_info(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = utcnow()
    access = _token_info(decode_token(request.cookies[ACCESS_COOKIE], "access"), now)
    try:
        refresh = _token_info(decode_token(request.cookies.get(REFRESH_COOKIE, ""), "refresh"), now)
    except jwt.PyJWTError:
        refresh = None
    current = _current_family(request, db)

    # One session per token family that still has an active (unrevoked, unexpired) refresh token.
    families = db.execute(
        select(
            RefreshToken.family_id,
            func.min(RefreshToken.created_at),
            func.max(RefreshToken.created_at),
            func.count(),
        )
        .where(RefreshToken.user_id == user.id)
        .group_by(RefreshToken.family_id)
    ).all()
    active = {
        t.family_id: t
        for t in db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
    }
    sessions = [
        {
            "id": family_id,
            "device": active[family_id].user_agent,
            "started_at": started,
            "last_refreshed_at": last,
            "expires_at": active[family_id].expires_at,
            "refreshes": count - 1,
            "current": family_id == current,
        }
        for family_id, started, last, count in families
        if family_id in active
    ]
    sessions.sort(key=lambda s: (not s["current"], s["started_at"]))

    return {
        "server_time": now,
        "access_token_lifetime": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "access_token": access,
        "refresh_token": refresh,
        "sessions": sessions,
    }


@router.post("/expire-access", status_code=status.HTTP_204_NO_CONTENT)
def expire_access(response: Response, _: User = Depends(get_current_user)):
    """Drop the access cookie now, exactly as the browser does when its 15 minutes run out."""
    response.delete_cookie(ACCESS_COOKIE, path=ACCESS_PATH)


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == session_id,
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=utcnow())
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found or already ended")
    db.commit()
    if session_id == _current_family(request, db):
        clear_auth_cookies(response)
