# Sample Auth App — React + Python (FastAPI) + Firebase Auth

A minimal full-stack app where the **backend owns sign-up and login**. The React frontend only talks to the FastAPI backend; the backend uses Firebase Authentication to create users, sign them in and issue JWTs.

```
backend/   FastAPI + SQLAlchemy (SQLite) + Firebase Auth REST API + Firebase Admin SDK
frontend/  React 18 + Vite + React Router (no Firebase SDK)
```

## Firebase setup (one time)

1. Create a project at https://console.firebase.google.com
2. **Authentication → Sign-in method**: enable **Email/Password**.
3. **Project settings → General**: copy the **Project ID** and **Web API key** into `backend/.env`.

## Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set FIREBASE_PROJECT_ID and FIREBASE_API_KEY
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

| Method | Path                | Auth   | Description                                         |
|--------|---------------------|--------|-----------------------------------------------------|
| POST   | /api/auth/register  | –      | Create Firebase user, returns tokens + user         |
| POST   | /api/auth/login     | –      | Sign in, returns tokens + user                      |
| POST   | /api/auth/refresh   | –      | Exchange a refresh token for a new access token     |
| GET    | /api/auth/me        | Bearer | Current user                                        |
| GET    | /api/dashboard      | Bearer | Example protected endpoint                          |
| GET    | /api/health         | –      | Health check                                        |

## How auth works

1. The frontend posts email/password to `/api/auth/register` or `/api/auth/login`.
2. The backend calls the Firebase Auth REST API, which returns an **ID token** (RS256-signed JWT, valid 1 hour) and a **refresh token**.
3. The backend verifies the ID token with `firebase_admin.auth.verify_id_token`, syncs a local `users` row keyed by the Firebase UID, and returns `{ access_token, refresh_token, expires_in, user }`.
4. The frontend stores the tokens in `localStorage` and sends `Authorization: Bearer <access_token>` on API calls.
5. When an API call returns 401, the frontend calls `/api/auth/refresh` once and retries; if that fails, the user is logged out.
