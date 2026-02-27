from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, computed_field
from app.models.enums import SnapshotSource

class PriceSnapshotCreate(BaseModel):
    order_item_id: UUID
    scraped_price: float
    original_paid_price: float
    currency: str = "USD"
    is_available: bool = True
    snapshot_source: SnapshotSource

class PriceSnapshotRead(BaseModel):
    id: UUID
    order_item_id: UUID
    scraped_price: float
    original_paid_price: float
    currency: str
    is_available: bool
    snapshot_source: SnapshotSource
    scraped_at: datetime

    @computed_field
    @property
    def price_delta(self) -> float:
        return round(self.original_paid_price - self.scraped_price, 2)

    model_config = {"from_attributes": True}