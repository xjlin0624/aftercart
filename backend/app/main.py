import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.alerts import router as alerts_router
from .api.auth import router as auth_router
from .api.orders import router as orders_router
from .api.preferences import router as preferences_router
from .api.prices import router as prices_router
from .api.users import router as users_router
from .core.settings import get_settings

settings = get_settings()

if settings.app_env == "production" and settings.jwt_secret == "change-me-in-production":
    logging.warning("JWT_SECRET is not set — using insecure default. Set JWT_SECRET in your environment.")

_DEV_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

app = FastAPI(
    title="AfterCart API",
    version="0.1.0",
    docs_url="/api/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEV_ORIGINS if settings.app_env == "development" else [o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(preferences_router, prefix="/api")
app.include_router(prices_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
