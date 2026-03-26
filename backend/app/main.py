from fastapi import FastAPI

from .api.alerts import router as alerts_router
from .api.auth import router as auth_router
from .api.orders import router as orders_router
from .api.preferences import router as preferences_router
from .api.prices import router as prices_router

app = FastAPI(title="AfterCart API", version="0.1.0")

app.include_router(auth_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(preferences_router, prefix="/api")
app.include_router(prices_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
