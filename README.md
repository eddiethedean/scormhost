# scormhost

Turn [FastAPI](https://fastapi.tiangolo.com/) into a **SCORM 1.2 / 2004 hosting app** with user accounts, JWT auth, and an admin UI — deployable to [FastAPI Cloud](https://fastapicloud.com/).

Works with packages built by [LXPack](https://github.com/eddiethedean/lxpack) (`lxpack build --target scorm12` / `scorm2004`) and other compliant SCORM ZIPs.

## Features

- **User management** — SQLite database, [Alembic](https://alembic.sqlalchemy.org/) migrations, bcrypt passwords
- **JWT auth** — access + refresh tokens (httpOnly cookies for the browser UI, `Authorization: Bearer` for API clients)
- **Public learning** — anyone can browse and launch courses without logging in
- **Optional login for learners** — progress saved to your account when signed in
- **Anonymous progress** — guests get a browser cookie so progress persists on that device
- **Staff login** — upload/delete courses and manage users (instructor/admin)
- **Roles** — `learner`, `instructor`, `admin` (first registered user becomes `admin`)

## Quick start

```bash
git clone https://github.com/eddiethedean/scormhost.git
cd scormhost
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# optional: run migrations manually (also runs on startup by default)
alembic upgrade head

fastapi dev
```

1. Open http://127.0.0.1:8000 — launch any course without an account.
2. Register at `/register` (first user = **admin**) to upload SCORM ZIPs or save progress to your account.

Or use the factory:

```python
from scormhost import create_scorm_app

app = create_scorm_app(
    data_dir="./data",
    title="My SCORM Host",
    secret_key="change-me-in-production",
)
```

Set `require_auth=True` only if you want to force login before taking courses (not the default).

## Database & migrations

Default database: `sqlite:///<data_dir>/scormhost.db` (override with `SCORMHOST_DATABASE_URL`).

```bash
alembic upgrade head    # apply migrations
alembic revision -m "describe change" --autogenerate  # new revision
```

On app startup, migrations run automatically when `SCORMHOST_AUTO_MIGRATE=true` (default).

## Roles

| Role | Capabilities |
|------|----------------|
| `learner` | Launch courses (no login required); signed-in progress tied to account |
| `instructor` | Upload packages, delete own uploads (login required) |
| `admin` | User management, delete any package (login required) |

**Without login:** launch courses; progress stored under a guest cookie on this browser.

**With login:** same, but SCORM progress is keyed to your user id (works across browsers/devices).

## Auth API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Create account (sets cookies) |
| `POST` | `/api/auth/login` | Login (sets cookies) |
| `POST` | `/api/auth/refresh` | Rotate refresh token |
| `POST` | `/api/auth/logout` | Revoke refresh token, clear cookies |
| `GET` | `/api/auth/me` | Current user (Bearer or cookie) |
| `PATCH` | `/api/auth/me/password` | Change password |
| `GET` | `/api/users` | List users (admin) |
| `PATCH` | `/api/users/{id}` | Update role / active flag (admin) |
| `DELETE` | `/api/users/{id}` | Delete user (admin) |

HTML: `/login`, `/register`, `/admin/users`

## SCORM API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Package catalog (requires login when auth enabled) |
| `GET` | `/launch/{package_id}` | SCORM player |
| `GET` | `/content/{package_id}/{path}` | Package static files |
| `POST` | `/api/packages` | Upload ZIP (instructor/admin) |
| `DELETE` | `/api/packages/{id}` | Delete package |
| `GET/PUT` | `/api/scorm/{id}/cmi` | CMI for authenticated user |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCORMHOST_DATA_DIR` | `./data` | Packages, sessions, SQLite DB |
| `SCORMHOST_SECRET_KEY` | random per start | **Set in production** — JWT signing |
| `SCORMHOST_DATABASE_URL` | `sqlite:///<data>/scormhost.db` | SQLAlchemy URL |
| `SCORMHOST_REQUIRE_AUTH` | `false` | If `true`, login required to take courses (not just manage) |
| `SCORMHOST_ALLOW_REGISTRATION` | `true` | Public sign-up |
| `SCORMHOST_BOOTSTRAP_ADMIN_EMAIL` | — | Force admin role for matching email on register |
| `SCORMHOST_ACCESS_TOKEN_MINUTES` | `30` | JWT access TTL |
| `SCORMHOST_REFRESH_TOKEN_DAYS` | `7` | Refresh token TTL |
| `SCORMHOST_COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `SCORMHOST_AUTO_MIGRATE` | `true` | Run `alembic upgrade head` on startup |
| `SCORMHOST_ALLOW_UPLOAD` | `true` | Global upload toggle |
| `SCORMHOST_TITLE` | `SCORM Host` | Site title |

## Deploy to FastAPI Cloud

```bash
cd examples/cloud
pip install -r requirements.txt
fastapi login
fastapi deploy
```

Set `SCORMHOST_DATA_DIR`, `SCORMHOST_SECRET_KEY`, and `SCORMHOST_COOKIE_SECURE=true` in the dashboard.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use `require_auth=False` for SCORM flows and a separate DB for auth tests.

## Limits (v0.1)

- SQLite by default (swap `SCORMHOST_DATABASE_URL` for Postgres in production)
- Package files remain on disk (not in the DB)
- cmi5 / xAPI launch not supported
- SCORM 2004 sequencing not enforced server-side

## License

Apache-2.0 — see [LICENSE](LICENSE).
