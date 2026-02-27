
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.enums import OrderStatus

class OrderCreate(BaseModel):
    retailer: str
    retailer_order_id: str
    order_status: OrderStatus
    order_date: datetime
    subtotal: float
    currency: str = "USD"
    return_window_days: int | None = None
    return_deadline: date | None = None
    price_match_eligible: bool = False
    tracking_number: str | None = None
    carrier: str | None = None
    estimated_delivery: date | None = None
    order_url: str | None = None
    raw_capture: dict | None = None

class OrderUpdate(BaseModel):
    order_status: OrderStatus | None = None
    tracking_number: str | None = None
    carrier: str | None = None
    estimated_delivery: date | None = None
    delivered_at: datetime | None = None
    return_deadline: date | None = None
    price_match_eligible: bool | None = None

class OrderRead(BaseModel):
    id: UUID
    user_id: UUID
    retailer: str
    retailer_order_id: str
    order_status: OrderStatus
    order_date: datetime
    subtotal: float
    currency: str
    return_window_days: int | None
    return_deadline: date | None
    price_match_eligible: bool
    tracking_number: str | None
    carrier: str | None
    estimated_delivery: date | None
    delivered_at: datetime | None
    order_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}