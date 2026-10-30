from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth
from .config import FRONTEND_ORIGIN
from .database import Base, engine
from .models import User
from .security import get_current_user, init_firebase

Base.metadata.create_all(bind=engine)
init_firebase()

app = FastAPI(title="Sample Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
