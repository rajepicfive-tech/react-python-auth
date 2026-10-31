import secrets

from fastapi import Response

from .config import (
    ACCESS_COOKIE,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SECURE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

# The refresh cookie is only sent to /api/auth/*, never to ordinary API calls.
ACCESS_PATH = "/api"
REFRESH_PATH = "/api/auth"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=ACCESS_PATH,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=REFRESH_PATH,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
    )
    # Readable by JavaScript on purpose: the frontend echoes it in the X-CSRF-Token header.
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
        httponly=False,
        secure=COOKIE_SECURE,
        samesite="strict",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path=ACCESS_PATH, secure=COOKIE_SECURE, httponly=True, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, secure=COOKIE_SECURE, httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=COOKIE_SECURE, samesite="strict")
