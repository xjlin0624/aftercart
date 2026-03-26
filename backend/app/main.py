from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.alerts import router as alerts_router
from .api.auth import router as auth_router
from .api.orders import router as orders_router
from .api.preferences import router as preferences_router
from .api.prices import router as prices_router
from .api.users import router as users_router

app = FastAPI(title="AfterCart API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(preferences_router, prefix="/api")
app.include_router(prices_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
