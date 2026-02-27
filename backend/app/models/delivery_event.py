import uuid
from typing import Optional
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import DeliveryEventType

class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id           = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    event_type         = Column(Enum(DeliveryEventType), nullable=False)
    previous_eta       = Column(Date, nullable=True)
    new_eta            = Column(Date, nullable=True)
    carrier_status_raw = Column(String(255), nullable=True)
    is_anomaly         = Column(Boolean, default=False, nullable=False)
    scraped_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes              = Column(Text, nullable=True)

    @property
    def eta_slippage_days(self) -> Optional[int]:
        if self.new_eta and self.previous_eta:
            return (self.new_eta - self.previous_eta).days
        return None

    order = relationship("Order", back_populates="delivery_events")
