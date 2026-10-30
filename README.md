# Sample Auth App — React + Python (FastAPI) + Firebase Auth

A minimal full-stack app with Firebase Authentication (email/password and Google), JWT-protected API endpoints and a protected dashboard.

```
backend/   FastAPI + SQLAlchemy (SQLite) + Firebase Admin SDK (verifies Firebase JWTs)
frontend/  React 18 + Vite + React Router + Firebase JS SDK
```

## Firebase setup (one time)

1. Create a project at https://console.firebase.google.com
2. **Authentication → Sign-in method**: enable **Email/Password** and (optionally) **Google**.
3. **Project settings → General → Your apps**: add a **Web app** and copy its config values.
4. Put the web config in `frontend/.env` and the project ID in `backend/.env`.

## Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set FIREBASE_PROJECT_ID
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env          # fill in the VITE_FIREBASE_* values
npm run dev
```

Open http://localhost:5173

## API

| Method | Path            | Auth   | Description                                  |
|--------|-----------------|--------|----------------------------------------------|
| GET    | /api/auth/me    | Bearer | Current user (created locally on first call) |
| GET    | /api/dashboard  | Bearer | Example protected endpoint                   |
| GET    | /api/health     | –      | Health check                                 |

## How auth works

1. The user signs up / logs in with Firebase in the browser (email/password or Google).
2. Firebase issues an **ID token** — an RS256-signed JWT (valid 1 hour, auto-refreshed by the SDK).
3. The frontend sends it as `Authorization: Bearer <token>` on every API call.
4. The backend verifies it with `firebase_admin.auth.verify_id_token` (signature, expiry, audience, issuer) and creates/updates a local `users` row keyed by the Firebase UID.
5. `ProtectedRoute` redirects to `/login` when there is no user; a 401 from the API logs the user out.
