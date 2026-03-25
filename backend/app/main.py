from fastapi import FastAPI

from .api.v1.auth import router as auth_router

app = FastAPI(title="AfterCart API", version="0.1.0")

app.include_router(auth_router, prefix="/api/v1")
