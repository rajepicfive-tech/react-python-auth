"""Thin client for the Firebase Auth REST API (sign-up, login, token refresh)."""

import httpx
from fastapi import HTTPException, status

from .config import FIREBASE_API_KEY

IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
TOKEN_URL = "https://securetoken.googleapis.com/v1/token"

# Firebase error codes → (HTTP status, message shown to the user)
ERRORS = {
    "EMAIL_EXISTS": (status.HTTP_400_BAD_REQUEST, "Email is already registered"),
    "INVALID_LOGIN_CREDENTIALS": (status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"),
    "INVALID_PASSWORD": (status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"),
    "EMAIL_NOT_FOUND": (status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"),
    "USER_DISABLED": (status.HTTP_403_FORBIDDEN, "This account has been disabled"),
    "WEAK_PASSWORD": (status.HTTP_400_BAD_REQUEST, "Password must be at least 6 characters"),
    "INVALID_EMAIL": (status.HTTP_400_BAD_REQUEST, "Invalid email address"),
    "TOO_MANY_ATTEMPTS_TRY_LATER": (status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try again later"),
    "INVALID_REFRESH_TOKEN": (status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again"),
    "TOKEN_EXPIRED": (status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again"),
}


def _post(url: str, **kwargs) -> dict:
    res = httpx.post(url, params={"key": FIREBASE_API_KEY}, timeout=10, **kwargs)
    if res.is_success:
        return res.json()
    # e.g. "WEAK_PASSWORD : Password should be at least 6 characters"
    code = res.json().get("error", {}).get("message", "").split(" ")[0]
    status_code, message = ERRORS.get(code, (status.HTTP_400_BAD_REQUEST, "Authentication failed"))
    raise HTTPException(status_code, message)


def sign_up(email: str, password: str, display_name: str) -> dict:
    """Create the user, set their name, and return tokens whose JWT carries the `name` claim."""
    data = _post(f"{IDENTITY_URL}:signUp", json={"email": email, "password": password, "returnSecureToken": True})
    updated = _post(
        f"{IDENTITY_URL}:update",
        json={"idToken": data["idToken"], "displayName": display_name, "returnSecureToken": True},
    )
    return {"id_token": updated["idToken"], "refresh_token": updated["refreshToken"], "expires_in": int(updated["expiresIn"])}


def sign_in(email: str, password: str) -> dict:
    data = _post(
        f"{IDENTITY_URL}:signInWithPassword",
        json={"email": email, "password": password, "returnSecureToken": True},
    )
    return {"id_token": data["idToken"], "refresh_token": data["refreshToken"], "expires_in": int(data["expiresIn"])}


def refresh(refresh_token: str) -> dict:
    data = _post(TOKEN_URL, data={"grant_type": "refresh_token", "refresh_token": refresh_token})
    return {"id_token": data["id_token"], "refresh_token": data["refresh_token"], "expires_in": int(data["expires_in"])}
