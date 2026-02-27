from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.enums import MonitoringStoppedReason

class OrderItemCreate(BaseModel):
    product_name: str
    variant: str | None = None
    sku: str | None = None
    product_url: str
    image_url: str | None = None
    quantity: int = 1
    paid_price: float

class OrderItemUpdate(BaseModel):
    current_price: float | None = None
    is_monitoring_active: bool | None = None
    monitoring_stopped_reason: MonitoringStoppedReason | None = None

class OrderItemRead(BaseModel):
    id: UUID
    order_id: UUID
    user_id: UUID
    product_name: str
    variant: str | None
    sku: str | None
    product_url: str
    image_url: str | None
    quantity: int
    paid_price: float
    current_price: float | None
    is_monitoring_active: bool
    monitoring_stopped_reason: MonitoringStoppedReason | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}