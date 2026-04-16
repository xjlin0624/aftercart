# Scraper Reliability

## Reliability Controls
- Retailer adapters run through a shared reliability guard before Playwright navigation.
- Redis-backed rate limiting uses `ratelimit:scraper:<retailer>` keys to cap scrape volume per minute.
- Redis-backed circuit state uses:
  - `circuit:scraper:<retailer>`
  - `circuit:failures:scraper:<retailer>`
- Transient scraper failures retry with exponential backoff plus jitter.
- Auth/session-dependent delivery scrapes fail as structured `scraper_not_ready` results instead of crashing the worker.

## Failure Isolation
- One retailer failure returns a safe task status and does not abort other queued retailer work.
- The circuit breaker opens after `SCRAPER_CIRCUIT_FAILURE_THRESHOLD` consecutive failures for the cooldown window.
- Successful scrapes reset the retailer circuit state.

## Logging and Debugging
- Task logs include retailer, order/order-item ID, status, and error detail.
- Normalized scrape payloads carry `raw_payload` metadata for later inspection.
- Missing authenticated Playwright storage state is treated as an expected operational gap, not an unhandled exception.

## Operational Notes
- Product price pages are public-path friendly.
- Nike and Sephora delivery polling works best with authenticated Playwright storage state files in `PLAYWRIGHT_STORAGE_STATE_DIR`.
- Render deployment does not magically create those storage-state files. Real cloud delivery polling remains blocked until `nike.json` and/or `sephora.json` are provisioned at `PLAYWRIGHT_STORAGE_STATE_DIR` on the worker host.
- Amazon is implemented as a price adapter only in this repository.

## Phase 4 Validation Status
- Authenticated delivery polling was not revalidated in the current Phase 4 environment because no Playwright storage-state directory or retailer session files were present.
- Graceful fallback behavior without storage state remains covered by automated tests and by the `scraper_not_ready` return path in delivery polling.

## Validation Commands
```powershell
.\.venv313\Scripts\python -m pytest backend/tests/test_scrapers.py
.\.venv313\Scripts\python backend/scripts/validate_price_check_performance.py --items 100
```
