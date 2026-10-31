import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import (
    ACCESS_COOKIE,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    CSRF_COOKIE,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from .database import get_db
from .models import User

password_hasher = PasswordHasher()  # Argon2id, OWASP-recommended defaults

# Verified against when the email doesn't exist, so login takes the same time either way.
DUMMY_HASH = password_hasher.hash("dummy-password")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at). The jti identifies the token's row in the database."""
    now = utcnow()
    jti = uuid.uuid4().hex
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "jti": jti, "iat": now, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), jti, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["sub", "type", "iat", "exp"]}
    )
    # Stops a refresh token being used as an access token and vice versa.
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def verify_csrf(request: Request) -> None:
    """Double-submit check: unsafe requests must echo the csrf_token cookie in a header."""
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get("X-CSRF-Token")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token missing or invalid")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise unauthorized
    try:
        user_id = int(decode_token(token, "access")["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    verify_csrf(request)
    return user
