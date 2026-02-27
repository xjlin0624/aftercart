from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None

class UserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}