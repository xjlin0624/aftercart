import uuid
from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import SubscriptionStatus, DetectionMethod

class Subscription(Base):
    __tablename__ = "subscriptions"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    retailer                 = Column(String(50), nullable=False)
    product_name             = Column(String(500), nullable=False)
    product_url              = Column(Text, nullable=True)
    detection_method         = Column(Enum(DetectionMethod), nullable=False)
    recurrence_interval_days = Column(Integer, nullable=True)
    estimated_monthly_cost   = Column(Float, nullable=True)
    last_charged_at          = Column(Date, nullable=True)
    next_expected_charge     = Column(Date, nullable=True)
    status                   = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.monitoring, nullable=False)
    cancellation_url         = Column(Text, nullable=True)
    cancellation_steps       = Column(Text, nullable=True)
    source_order_ids         = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at               = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="subscriptions")