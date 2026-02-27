import uuid
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import AlertType, AlertStatus, AlertPriority, RecommendedAction, EffortLevel

class Alert(Base):
    __tablename__ = "alerts"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    order_id      = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True)
    alert_type    = Column(Enum(AlertType), nullable=False)
    status        = Column(Enum(AlertStatus), default=AlertStatus.new, nullable=False)
    priority      = Column(Enum(AlertPriority), default=AlertPriority.medium, nullable=False)
    title         = Column(String(255), nullable=False)
    body          = Column(Text, nullable=False)

    # Recommendation (flat for queryability)
    recommended_action        = Column(Enum(RecommendedAction), nullable=True)
    estimated_savings         = Column(Float, nullable=True)
    estimated_effort          = Column(Enum(EffortLevel), nullable=True)
    effort_steps_estimate     = Column(Integer, nullable=True)
    recommendation_rationale  = Column(Text, nullable=True)
    days_remaining_return     = Column(Integer, nullable=True)
    action_deadline           = Column(Date, nullable=True)
    alternative_product_url   = Column(Text, nullable=True)
    alternative_product_price = Column(Float, nullable=True)

    # JSONB blobs
    evidence           = Column(JSONB, nullable=True)
    generated_messages = Column(JSONB, nullable=True)

    push_sent_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user        = relationship("User", back_populates="alerts")
    order       = relationship("Order", back_populates="alerts")
    order_item  = relationship("OrderItem", back_populates="alerts")
    outcome_log = relationship("OutcomeLog", back_populates="alert", uselist=False)
