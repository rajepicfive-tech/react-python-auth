import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import FIREBASE_CREDENTIALS, FIREBASE_PROJECT_ID
from .database import get_db
from .models import User

bearer_scheme = HTTPBearer(auto_error=False)


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(FIREBASE_CREDENTIALS) if FIREBASE_CREDENTIALS else None
    options = {"projectId": FIREBASE_PROJECT_ID} if FIREBASE_PROJECT_ID else None
    firebase_admin.initialize_app(cred, options)


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token (an RS256 JWT): signature, expiry, audience and issuer."""
    return firebase_auth.verify_id_token(token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = verify_firebase_token(credentials.credentials)
    except (ValueError, firebase_auth.InvalidIdTokenError, firebase_auth.CertificateFetchError):
        raise unauthorized
    return sync_user(db, claims)


def sync_user(db: Session, claims: dict) -> User:
    """Create the local profile on first sight, and keep it in sync with Firebase."""
    email = claims.get("email", "")
    name = (claims.get("name") or "").strip() or email.split("@")[0]
    user = db.scalar(select(User).where(User.firebase_uid == claims["uid"]))
    if user is None:
        user = User(firebase_uid=claims["uid"], email=email, full_name=name)
        db.add(user)
    else:
        user.email, user.full_name = email, name
    db.commit()
    db.refresh(user)
    return user
