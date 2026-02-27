import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import SnapshotSource

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id       = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False)
    scraped_price       = Column(Float, nullable=False)
    original_paid_price = Column(Float, nullable=False)
    currency            = Column(String(3), default="USD", nullable=False)
    is_available        = Column(Boolean, default=True, nullable=False)
    snapshot_source     = Column(Enum(SnapshotSource), nullable=False)
    scraped_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def price_delta(self) -> float:
        return round(self.original_paid_price - self.scraped_price, 2)

    order_item = relationship("OrderItem", back_populates="price_snapshots")
