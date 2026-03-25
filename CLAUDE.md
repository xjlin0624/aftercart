# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Install dependencies (from repo root)
pip install -r backend/requirements.txt

# Run all tests
pytest backend/tests

# Run a single test file
pytest backend/tests/test_price_monitoring.py

# Run a single test by name
pytest backend/tests/test_price_monitoring.py::test_process_order_item_price_check_creates_snapshot_and_updates_current_price

# Start the API server
cd backend && uvicorn app.main:app --reload

# Run the full scheduler stack (postgres + redis + celery worker + beat)
docker compose up --build worker beat postgres redis

# Run Celery manually (from repo root, with services running)
celery -A backend.app.workers.celery_app.celery_app worker --loglevel=INFO
celery -A backend.app.workers.celery_app.celery_app beat --loglevel=INFO

# Run database migrations
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini downgrade -1
```

### Frontend

```bash
cd frontend && npm install
npm run dev   # starts Vite dev server
```

### Environment

```bash
cp .env.example .env  # required before running anything locally
```

## Architecture

This is a multi-component project built by different authors. The three components are largely independent:

### Backend (`backend/`)
Python 3.12 / FastAPI / SQLAlchemy 2.0 / Celery / PostgreSQL 16 / Redis 7.

Two distinct subsystems share the same codebase:

1. **FastAPI HTTP server** (`app/main.py`) — serves the REST API. Currently only auth endpoints exist (`app/api/v1/auth.py`). The FastAPI dependency `get_db()` in `app/api/deps.py` yields a `Session`; this is separate from the `session_scope()` context manager used by Celery tasks.

2. **Celery worker** (`app/workers/celery_app.py`) — runs two periodic beat tasks: `price_check_cycle` and `subscription_flag_refresh_cycle`. Each follows a two-level pattern: a *cycle* task queries the DB and dispatches individual *item* tasks via `.delay()`. The item-level logic functions (`process_order_item_price_check`, etc.) accept an injected `session` and optional `adapter_lookup`, making them testable without a real DB. Tests use `FakeSession` / `FakeAdapter` from `backend/tests/conftest.py` — there is no test database.

3. **Scraper adapters** (`app/scrapers/`) — `RetailerPriceAdapter` ABC; concrete adapters registered by retailer slug in `registry.py`. Currently only `"nike"` and `"sephora"` are registered (both are stubs that raise `NotImplementedError`). Amazon and Target are not implemented despite the extension supporting them.

**Auth** (`app/core/security.py`, `app/api/v1/auth.py`): HS256 JWT, two-token pattern. Access tokens are stateless; refresh tokens are bcrypt-hashed into `users.refresh_token_hash` with rotation on every `/refresh` call. See `docs/auth.md` for full design rationale.

**Migrations** (`backend/alembic/`): Alembic with `env.py` wired to pull `DATABASE_URL` from Pydantic settings. Currently one migration: `0001_create_users_table`. When adding models, import them in `alembic/env.py` alongside the existing `import app.models.user` line so Alembic sees them during autogenerate.

### Chrome Extension (`extension/`)
Manifest V3, vanilla JS. `BaseExtractor` in `content/retailers/base.js` defines the interface; `AmazonExtractor` is fully implemented, `TargetExtractor` is a stub. `api-client.js` defines `API_BASE` (hardcoded `localhost:8000`) and the `api` object used by `service-worker.js` — load order matters since there are no ES module imports in MV3 content scripts.

### Frontend (`frontend/`)
React 18 / Vite / Recharts. All data is currently mocked via `src/mockData.js`. `src/api.js` is empty — no real API calls are wired. The brand name in `Sidebar.jsx` says "P.U.R." while the rest of the project uses "AfterCart".

## Key Known Gaps

- `dashboard/` and `extensions/` (plural) directories at the repo root are empty scaffolding — ignore them.
- The frontend `api.js` is blank; connecting it to the backend is unstarted work.
- Scraper adapters for Amazon and Target do not exist despite the extension capturing data from those retailers.
- `target.js` content script is a stub and silently does nothing on Target pages.
