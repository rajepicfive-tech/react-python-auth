from fastapi import APIRouter, Depends

from .models import User
from .schemas import UserOut
from .security import get_current_user

# Sign-up and login happen in Firebase on the frontend; the backend only verifies tokens.
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
