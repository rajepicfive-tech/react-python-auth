from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from . import firebase_client
from .database import get_db
from .models import User
from .schemas import AuthResponse, RefreshRequest, Token, UserCreate, UserLogin, UserOut
from .security import get_current_user, sync_user, verify_firebase_token

# The frontend only talks to these endpoints; the backend talks to Firebase.
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(tokens: dict, db: Session) -> AuthResponse:
    user = sync_user(db, verify_firebase_token(tokens["id_token"]))
    return AuthResponse(
        access_token=tokens["id_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        user=user,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    tokens = firebase_client.sign_up(data.email.lower(), data.password, data.full_name.strip())
    return _auth_response(tokens, db)


@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    tokens = firebase_client.sign_in(data.email.lower(), data.password)
    return _auth_response(tokens, db)


@router.post("/refresh", response_model=Token)
def refresh(data: RefreshRequest):
    tokens = firebase_client.refresh(data.refresh_token)
    return Token(access_token=tokens["id_token"], refresh_token=tokens["refresh_token"], expires_in=tokens["expires_in"])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
