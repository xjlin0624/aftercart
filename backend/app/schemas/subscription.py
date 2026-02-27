from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.enums import SubscriptionStatus, DetectionMethod

class SubscriptionCreate(BaseModel):
    retailer: str
    product_name: str
    product_url: str | None = None
    detection_method: DetectionMethod
    recurrence_interval_days: int | None = None
    estimated_monthly_cost: float | None = None
    last_charged_at: date | None = None
    next_expected_charge: date | None = None
    cancellation_url: str | None = None
    cancellation_steps: str | None = None
    source_order_ids: list[UUID] | None = None

class SubscriptionUpdate(BaseModel):
    status: SubscriptionStatus | None = None
    recurrence_interval_days: int | None = None
    estimated_monthly_cost: float | None = None
    next_expected_charge: date | None = None
    cancellation_url: str | None = None
    cancellation_steps: str | None = None

class SubscriptionRead(BaseModel):
    id: UUID
    user_id: UUID
    retailer: str
    product_name: str
    product_url: str | None
    detection_method: DetectionMethod
    recurrence_interval_days: int | None
    estimated_monthly_cost: float | None
    last_charged_at: date | None
    next_expected_charge: date | None
    status: SubscriptionStatus
    cancellation_url: str | None
    cancellation_steps: str | None
    source_order_ids: list[UUID] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}