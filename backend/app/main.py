from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth
from .config import FRONTEND_ORIGIN
from .models import User
from .security import get_current_user

# Schema is managed by Alembic: run `alembic upgrade head` before starting the app.
app = FastAPI(title="Sample Auth API")

# Only needed if the frontend is served from a different origin than the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(auth.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    """Example protected endpoint."""
    return {
        "message": f"Welcome back, {current_user.full_name}!",
        "stats": {"projects": 3, "tasks_open": 7, "tasks_done": 12},
    }
