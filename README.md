# CS5500 Final Project: AfterCart

*Group 1: Yingchao Cai, Bo Hu, Xuelan Lin, Weiyi Sun*

AfterCart is a post-purchase assistant that aggregates orders, monitors price and delivery risks, and helps users decide whether to wait, contact support, cancel, return, or rebuy.

## Stack

- Backend: `FastAPI`, `SQLAlchemy`, `Alembic`, `Celery`, `Redis`, `Postgres`
- Frontend: `React`, `Vite`
- Scraping: `Playwright` retailer adapters for Nike, Sephora, and Amazon price checks
- Notifications/observability: `Firebase Cloud Messaging`, `Sentry`
- Deployment targets: `Render` for backend services and `Vercel` for the dashboard

## Repository Guides

- Architecture: [docs/architecture.md](docs/architecture.md)
- Engineering workflow: [docs/engineering-workflow.md](docs/engineering-workflow.md)
- Operations and uptime: [docs/operations.md](docs/operations.md)
- Scraper reliability: [docs/scraper-reliability.md](docs/scraper-reliability.md)
- Student B execution plan: [docs/student-b-execution-plan.md](docs/student-b-execution-plan.md)
- Student B checklist: [docs/student-b-checklist.md](docs/student-b-checklist.md)
- Student B handoff: [docs/student-b-handoff.md](docs/student-b-handoff.md)
- Demo walkthrough: [docs/student-b-demo.md](docs/student-b-demo.md)

## Functional Scope

### MVP

1. Cross-retailer order aggregation
2. Price drop and better-deal monitoring
3. Delivery anomaly detection and Plan B recommendations
4. Decision-confidence visualization
5. Customer-support message assistance

### Stretch Goals

6. Personalized recommendation tuning
7. Amazon retailer integration

## Local Development

### Prerequisites

- Docker Desktop
- Python `3.13` recommended for local backend tooling
- Node.js `20+`

### Initial Setup

```bash
cp .env.example .env
```

Review `.env` and add secrets only if you need those integrations locally:

- `GEMINI_API_KEY` for message generation
- `SENTRY_DSN` / `VITE_SENTRY_DSN` for Sentry
- Firebase credentials for browser push
- Playwright storage-state files for authenticated retailer pages

### Start the Local Platform

```bash
docker compose up --build postgres redis api worker beat
```

This brings up:

- Postgres on `localhost:5432`
- Redis on `localhost:6379`
- FastAPI on `http://localhost:8000`
- Celery worker
- Celery Beat scheduler

The API container runs Alembic migrations automatically at startup.

### Seed Demo Data

In a separate terminal:

```bash
py -3.13 backend/seed.py
```

To reset and reseed:

```bash
py -3.13 backend/seed.py --reset
```

### Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Chrome Extension

Load the `extension/` folder in Chrome Developer Mode. The popup sign-in screen lets you set the backend API base URL, so local (`http://localhost:8000/api`) and deployed environments can be used without code edits. Chrome will request host access for the configured API origin the first time you save a new backend target.

Current extension retailer support:

- Nike: order-page and product-page capture
- Sephora: order-page and product-page capture
- Target: intentionally unsupported in this build; the content script exits without attempting extraction

## Manual Backend Commands

If you want to run backend tools outside Docker:

```bash
py -3.13 -m venv .venv313
.\.venv313\Scripts\pip install -r backend/requirements.txt
.\.venv313\Scripts\python -m playwright install chromium
.\.venv313\Scripts\python -m pytest backend/tests
.\.venv313\Scripts\python -m ruff check backend
```

Useful Celery entrypoints:

```bash
celery -A backend.app.workers.celery_app.celery_app worker --loglevel=INFO
celery -A backend.app.workers.celery_app.celery_app beat --loglevel=INFO
```

## Health and Verification

- API health: `GET /api/health`
- API readiness: `GET /api/health/ready`
- Swagger UI: `http://localhost:8000/api/docs` in development

Recommended verification commands:

```bash
docker compose config
.\.venv313\Scripts\python -m pytest backend/tests
.\.venv313\Scripts\python -m ruff check backend
.\.venv313\Scripts\python backend/scripts/validate_price_check_performance.py --items 100 --target-seconds 300
.\.venv313\Scripts\python backend/scripts/measure_dashboard_load.py --url http://localhost:5173/dashboard --target-ms 2000 --headless
cd frontend && npm run lint && npm run build
```

## Environment Variables

The canonical variable reference lives in [.env.example](.env.example). Key groups:

- platform/database/cache
- auth
- Celery schedules
- Sentry
- Playwright/scraper reliability
- Gemini cache/rate limits
- Firebase/FCM
- Render/Vercel deployment URLs
- frontend `VITE_*` build-time config

## Deployment

- Backend services and managed data stores are described in [render.yaml](render.yaml)
- Frontend deployment assumptions live in [vercel.json](vercel.json)
- CI and deploy automation live under `.github/workflows/`

## Notes

- Browser push no-ops safely until Firebase credentials are configured.
- Delivery polling for Nike/Sephora uses Playwright storage-state files when authenticated retailer pages are required.
- Amazon is implemented as a price-only adapter in this pass.
