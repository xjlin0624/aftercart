import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import ActionTaken

class OutcomeLog(Base):
    __tablename__ = "outcome_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    alert_id        = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    order_item_id   = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True)
    action_taken    = Column(Enum(ActionTaken), nullable=False)
    recovered_value = Column(Float, nullable=True)
    was_successful  = Column(Boolean, nullable=True)
    failure_reason  = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)
    logged_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user       = relationship("User", back_populates="outcome_logs")
    alert      = relationship("Alert", back_populates="outcome_log")
    order_item = relationship("OrderItem")
