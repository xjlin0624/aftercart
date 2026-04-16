# Student B Demo

## Demo Flow
1. Start the stack:
   - `docker compose up --build postgres redis api worker beat`
   - `cd frontend && npm run dev`
2. Show the architecture diagram and explain where Playwright, Redis, and Celery fit.
3. Open the dashboard Settings page:
   - show notification preferences
   - show browser push enablement path
4. Trigger or inspect a price-drop flow:
   - explain the shared adapter interface
   - highlight high-priority alert push delivery
5. Show delivery monitoring:
   - Nike/Sephora order URLs
   - graceful `scraper_not_ready` behavior when session state is missing
   - call out that Amazon is price-only in the current build
6. Show monitoring and operations:
   - `/api/health`
   - `/api/health/ready`
   - Sentry setup and triage notes
7. Close with deployment:
   - `render.yaml`
   - `vercel.json`
   - GitHub Actions CI and deploy-hook workflow

## Demo Talking Points
- Redis is doing double duty: Celery transport plus coordination store for reliability and LLM protections.
- Scraper failures are retailer-scoped, not global.
- Push notifications are optional and secret-gated, so local/dev remains safe.
- Performance validation is reproducible through repo scripts, not only manual observation.
