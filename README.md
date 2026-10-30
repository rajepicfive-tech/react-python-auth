# Sample Auth App — React + Python (FastAPI)

A minimal full-stack app with user registration, login, JWT authentication and a protected dashboard.

```
backend/   FastAPI + SQLAlchemy (SQLite) + bcrypt + JWT
frontend/  React 18 + Vite + React Router
```

## Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set a real SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173

## API

| Method | Path                 | Auth   | Description                    |
|--------|----------------------|--------|--------------------------------|
| POST   | /api/auth/register   | –      | Create user, returns JWT       |
| POST   | /api/auth/login      | –      | Log in, returns JWT            |
| GET    | /api/auth/me         | Bearer | Current user                   |
| GET    | /api/dashboard       | Bearer | Example protected endpoint     |
| GET    | /api/health          | –      | Health check                   |

## How auth works

1. Register/login returns `{ access_token, user }`.
2. The frontend stores the token in `localStorage` and sends it as `Authorization: Bearer <token>`.
3. On page reload, `AuthContext` calls `/api/auth/me` to restore the session.
4. `ProtectedRoute` redirects to `/login` when there is no user; a 401 from the API logs the user out.

> For production: use a strong `SECRET_KEY`, HTTPS, and consider httpOnly cookies + refresh tokens instead of `localStorage`.
