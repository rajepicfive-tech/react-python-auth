# Sample Auth App — React + Python (FastAPI) + PostgreSQL

Full-stack authentication with backend-issued JWTs stored in httpOnly cookies, 15-minute access tokens and automatic, rotating refresh tokens.

```
backend/   FastAPI + SQLAlchemy + PostgreSQL + Alembic + Argon2 + PyJWT
frontend/  React 18 + Vite + React Router
```

## Run it

```bash
# 1. PostgreSQL (Docker)
docker compose up -d

# 2. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # set a real SECRET_KEY
alembic upgrade head              # create / update tables
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the backend, so the app and API share one origin.
API docs: http://localhost:8000/docs

## API

| Method | Path               | Auth          | Description                                   |
|--------|--------------------|---------------|-----------------------------------------------|
| POST   | /api/auth/register | –             | Create user, set auth cookies                 |
| POST   | /api/auth/login    | –             | Log in, set auth cookies                      |
| POST   | /api/auth/refresh  | refresh cookie| Rotate refresh token, issue new access token  |
| POST   | /api/auth/logout   | refresh cookie| Revoke the session, clear cookies             |
| GET    | /api/auth/me       | access cookie | Current user                                  |
| GET    | /api/dashboard     | access cookie | Example protected endpoint                    |
| GET    | /api/health        | –             | Health check                                  |

## How auth works

1. Login/register sets three cookies:

   | Cookie          | Contents                     | Lifetime | Flags                                  |
   |-----------------|------------------------------|----------|----------------------------------------|
   | `access_token`  | JWT (`type: access`)         | 15 min   | HttpOnly, SameSite=Lax, Path=/api       |
   | `refresh_token` | JWT (`type: refresh`, `jti`) | 7 days   | HttpOnly, SameSite=Strict, Path=/api/auth |
   | `csrf_token`    | random string                | 7 days   | readable by JS, SameSite=Strict        |

   All are `Secure` when `COOKIE_SECURE=true` (production, HTTPS).
2. The browser sends the access cookie on every `/api` request; JavaScript never sees the tokens.
3. When the access token expires the API returns 401; the frontend calls `/api/auth/refresh` once (shared across parallel requests) and retries.
4. Every refresh **rotates** the refresh token: the old one is revoked in the `refresh_tokens` table. Reusing a revoked token revokes the whole session (**reuse detection**), with a 10 s grace window for tabs refreshing at the same time.
5. Logout revokes the session in the database and clears the cookies.

## Security best practices applied

- **Passwords**: Argon2id hashing, transparent rehash on parameter change, equal-time response for unknown emails.
- **JWT**: short-lived access token, `type` claim checked so tokens can't be swapped, required `exp`/`iat`, secret must be ≥ 32 chars or the app refuses to start.
- **Refresh tokens**: stored server-side by `jti`, single-use (rotation), revocable, reuse detection, row lock against concurrent refreshes.
- **Cookies**: HttpOnly (no XSS token theft), SameSite, narrow `Path` for the refresh token, `Secure` in production.
- **CSRF**: SameSite cookies plus double-submit token (`X-CSRF-Token` header) on every authenticated POST/PUT/PATCH/DELETE.
- **Database**: PostgreSQL with Alembic migrations, `pool_pre_ping`, cascade delete of tokens with the user.

## Production checklist

- Set `COOKIE_SECURE=true`, serve everything over HTTPS behind one domain (reverse proxy for `/api`).
- Use a long random `SECRET_KEY` from a secret manager; rotating it logs everyone out.
- Add rate limiting on `/api/auth/login` and `/api/auth/register` (e.g. `slowapi` or at the proxy).
- Periodically delete expired rows from `refresh_tokens`.
