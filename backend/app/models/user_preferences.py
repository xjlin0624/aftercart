import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import MessageTone

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                    = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    min_savings_threshold      = Column(Float, default=10.00, nullable=False)
    notify_price_drop          = Column(Boolean, default=True, nullable=False)
    notify_delivery_anomaly    = Column(Boolean, default=True, nullable=False)
    notify_subscription        = Column(Boolean, default=True, nullable=False)
    push_notifications_enabled = Column(Boolean, default=False, nullable=False)
    preferred_message_tone     = Column(Enum(MessageTone), default=MessageTone.polite, nullable=False)
    monitored_retailers        = Column(ARRAY(String), default=list, nullable=False)
    updated_at                 = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="preferences")