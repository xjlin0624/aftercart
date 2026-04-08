# CS5500 Final Project: AfterCart

*group 1: Yingchao Cai, Bo Hu, Xuelan Lin, Weiyi Sun*

This project builds a "Post-Purchase Uncertainty Reducer" that helps shoppers feel confident after checkout by aggregating orders across retailers, monitoring price and delivery risks, and providing clear, actionable recommendations (price match, return/rebuy, replacement, or no action).

## Objectives

### MVP

1. Cross-retailer Order Aggregation
2. Price Drop and Better-Deal Monitoring
3. Delivery Anomaly Detection and Plan B Recommendations
4. Decision-Confidence Visualization
5. Customer Support Message Assistance

### Stretch Goals
6. Personalized Recommendation Tuning
7. Amazon Retailer Integration

## Functional Requirements

### Authentication & User Settings

- **FR-1 (MUST)** User Authentication

- **FR-2 (MUST)** User Preferences

### Order Capture & Aggregation

- **FR-3 (MUST)** Order Capture via Extension

- **FR-4 (MUST)** Order De-duplication

- **FR-5 (MUST)** Centralized Order View

### Price Monitoring & Price History

- **FR-6 (MUST)** Price History Storage

- **FR-7 (MUST)** Price Drop Detection

- ***FR-8 (SHOULD)** Same-Retailer Alternative Product Detection*

### Recommendation Engine

- **FR-9 (MUST)** Action Recommendation

- **FR-10 (MUST)** Explainable Recommendation Output

### Alerts & Notifications

- **FR-11 (MUST)** Alert Management

- **FR-12 (MUST)** Notification Delivery

### Delivery Monitoring

- **FR-13 (MUST)** Delivery ETA Monitoring

- ***FR-14 (SHOULD)** Plan-B Suggestions for Delays*

### Customer Support Message Assistance & Evidence

- **FR-15 (MUST)** Message Templates

- **FR-16 (MUST)** Evidence Bundling

### Outcome Tracking & Savings

- **FR-17 (MUST)** User Outcome Logging

- **FR-18 (MUST)** Savings Dashboard

---

## Running the Demo

### Prerequisites
- Docker Desktop running
- Python 3.12 with dependencies: `pip install -r backend/requirements.txt`
- Node.js: `cd frontend && npm install`

### Start

```bash
# 1. Copy env file and fill in DATABASE_URL with the shared Neon connection string (first time only)
cp .env.example .env

# 2. Start redis
docker compose up redis -d

# 3. Run migrations (first time only)
cd backend && alembic upgrade head && cd ..

# 4. Seed development data (first time only, requires APP_ENV=development)
python backend/seed.py
# To wipe and re-seed: python backend/seed.py --reset

# 5. Start API server (keep this terminal open)
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. In a new terminal — start frontend (keep this terminal open)
cd frontend && npm run dev

```

Open **http://localhost:5173** in your browser.

To log in via the Chrome extension, load the `extension/` folder in Chrome (developer mode) and use the same credentials.

### Stop

```bash
# Ctrl+C in the API and frontend terminals, then:
docker compose down
```

---

## Environment Variables

| Variable | Dev | Production |
|---|---|---|
| `APP_ENV` | `development` | `production` |
| `DATABASE_URL` | Shared Neon dev connection string | Neon prod branch connection string |
| `JWT_SECRET` | Anything | Strong random secret (required) |
| `ALLOWED_ORIGINS` | Leave empty (localhost auto-allowed) | Comma-separated frontend URLs |
| `GEMINI_API_KEY` | Free key from [aistudio.google.com](https://aistudio.google.com/apikey) | Same — each dev gets their own key |
| `LOG_LEVEL` | `INFO` or `DEBUG` | `INFO` or `WARNING` |

Swagger UI (`/api/docs`) is only enabled when `APP_ENV=development`.
The seed script (`seed.py`) refuses to run unless `APP_ENV=development`.

---

## Local Scheduler Dev

Copy `.env.example` to `.env` (with the shared Neon `DATABASE_URL`), then start the scheduler stack with:

```bash
docker compose up --build worker beat redis
```

Useful Celery entrypoints:

```bash
celery -A backend.app.workers.celery_app.celery_app worker --loglevel=INFO
celery -A backend.app.workers.celery_app.celery_app beat --loglevel=INFO
```
