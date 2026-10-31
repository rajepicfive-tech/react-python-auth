import uuid
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .config import REFRESH_COOKIE
from .cookies import clear_auth_cookies, set_auth_cookies
from .database import get_db
from .models import RefreshToken, User
from .schemas import UserCreate, UserLogin, UserOut
from .security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    password_hasher,
    utcnow,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Two tabs refreshing at the same moment both send the same refresh token.
# Within this window the second use is treated as a race, not as theft.
REUSE_GRACE = timedelta(seconds=10)


def issue_tokens(response: Response, db: Session, user: User, request: Request, family_id: str | None = None) -> None:
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            family_id=family_id or uuid.uuid4().hex,
            expires_at=expires_at,
            user_agent=(request.headers.get("user-agent") or "")[:255],
        )
    )
    db.commit()
    set_auth_cookies(response, create_access_token(user.id), refresh_token)


def session_ended(detail: str) -> JSONResponse:
    response = JSONResponse({"detail": detail}, status_code=status.HTTP_401_UNAUTHORIZED)
    clear_auth_cookies(response)
    return response


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, request: Request, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email is already registered")

    user = User(email=email, full_name=data.full_name.strip(), hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    issue_tokens(response, db, user, request)
    return user


@router.post("/login", response_model=UserOut)
def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None:
        verify_password(data.password, DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")

    # Upgrade old hashes transparently when Argon2 parameters change.
    if password_hasher.check_needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(data.password)

    issue_tokens(response, db, user, request)
    return user


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        return session_ended("Not logged in")
    try:
        jti = decode_token(token, "refresh")["jti"]
    except (jwt.PyJWTError, KeyError):
        return session_ended("Session expired, please log in again")

    # Lock the row so concurrent refreshes with the same token are serialised.
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti).with_for_update())
    if row is None:
        return session_ended("Session expired, please log in again")

    now = utcnow()
    # A concurrent refresh only counts as a race if the family is still alive (not logged out or revoked).
    family_alive = db.scalar(
        select(RefreshToken.id).where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
    )
    if row.revoked_at is not None and (now - row.revoked_at > REUSE_GRACE or not family_alive):
        # A rotated-out token was used again: assume it was stolen and end every session in this family.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        return session_ended("Session expired, please log in again")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return session_ended("Session expired, please log in again")

    # Rotation: every refresh token is single-use.
    if row.revoked_at is None:
        row.revoked_at = now
    issue_tokens(response, db, user, request, family_id=row.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        try:
            jti = decode_token(token, "refresh")["jti"]
        except (jwt.PyJWTError, KeyError):
            jti = None
        family_id = jti and db.scalar(select(RefreshToken.family_id).where(RefreshToken.jti == jti))
        if family_id:
            # End this login session: revoke every token issued from it.
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=utcnow())
            )
            db.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
