# Operations

## Health Endpoints
- `GET /api/health`
  - Liveness probe for process-level uptime.
- `GET /api/health/ready`
  - Readiness probe for API + Postgres + Redis.
  - Returns `503` when database or Redis is unavailable.

## Production Configuration Matrix

### Render backend services

Required for a real production deployment:

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `JWT_SECRET`
- `ALLOWED_ORIGINS`
- `RENDER_EXTERNAL_URL`

Optional, but required for the related feature to be truly validated:

- `SENTRY_DSN`
- `SENTRY_RELEASE`
- `GEMINI_API_KEY`
- `FCM_ENABLED`
- `FCM_SERVICE_ACCOUNT_JSON` or `FCM_SERVICE_ACCOUNT_FILE`

Render blueprint notes:

- `render.yaml` now declares the managed Postgres/Redis links plus the manual production values that must be entered in Render.
- `ALLOWED_ORIGINS` must include the deployed Vercel dashboard origin or browser requests will fail CORS in production.
- `JWT_SECRET` must be set explicitly. The code falls back to an insecure default only for local development.
- `RENDER_EXTERNAL_URL` should be the public Render API URL.

### Vercel frontend

Required for a real production deployment:

- `VITE_API_BASE_URL`

Optional, but required for the related feature to be truly validated:

- `VITE_SENTRY_DSN`
- `VITE_SENTRY_ENVIRONMENT`
- `VITE_SENTRY_RELEASE`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_VAPID_KEY`

Vercel notes:

- This repo uses a separate Render backend, so `VITE_API_BASE_URL` must point to the deployed Render `/api` base.
- Browser push is not release-validated until the full Firebase web config and VAPID key are present in Vercel.

### GitHub deploy hooks

Optional:

- `RENDER_DEPLOY_HOOK_URL`
- `VERCEL_DEPLOY_HOOK_URL`

The deploy workflow only triggers those hooks when the GitHub secrets exist.

## Uptime Monitoring
- Configure Render health checks against `/api/health/ready`.
- Add an external synthetic monitor if desired for the public frontend and API base URL.
- Keep frontend monitoring focused on Vercel deployment health and dashboard route availability.

## Sentry Triage Flow
1. Confirm environment and release tags on the event.
2. Check whether the failure came from `api`, `celery`, or `frontend`.
3. Group by retailer when scraper-related.
4. Determine whether the issue is:
   - secret or config missing
   - transient retailer or layout drift
   - code regression
5. If scraper drift is retailer-specific, verify whether the circuit is open and inspect recent task logs.

## Common Failure Modes
- Missing Firebase credentials: push task reports `disabled` and does not mark `alerts.push_sent_at`.
- Missing retailer session state: delivery scraper returns `scraper_not_ready`.
- Redis unavailable: readiness fails and cache and rate-limit features degrade.
- Retailer markup drift: scraper retries, then circuit-breaks after the configured threshold.
- Missing `ALLOWED_ORIGINS`: frontend can load but browser API calls fail due to CORS in production.
- Missing `JWT_SECRET`: the service boots with the insecure default and should not be treated as production-ready.

## Redis Coordination Keys
- Scraper rate limit: `ratelimit:scraper:<retailer>`
- Scraper circuit open flag: `circuit:scraper:<retailer>`
- Scraper failure counter: `circuit:failures:scraper:<retailer>`
- LLM cache: `llm:cache:<sha256>`
- LLM dedupe lock: `llm:dedupe:<sha256>`
- LLM rate limit: `llm:rate:global`

## Verification Commands
```powershell
docker compose config
.\.venv313\Scripts\python -m pytest backend/tests/test_health_push_and_guidance.py -q
.\.venv313\Scripts\python backend/scripts/validate_price_check_performance.py --items 100 --target-seconds 300
cd frontend; npm run lint; npm run build
```
