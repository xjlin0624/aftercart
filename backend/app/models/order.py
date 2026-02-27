import uuid
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from .base import Base
from .enums import OrderStatus

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint(
            "user_id", "retailer", "retailer_order_id",
            name="uq_order_per_user_retailer"
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id              = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    retailer             = Column(String(50), nullable=False)
    retailer_order_id    = Column(String(255), nullable=False)
    order_status         = Column(Enum(OrderStatus), nullable=False)
    order_date           = Column(DateTime(timezone=True), nullable=False)
    subtotal             = Column(Float, nullable=False)
    currency             = Column(String(3), default="USD", nullable=False)
    return_window_days   = Column(Integer, nullable=True)
    return_deadline      = Column(Date, nullable=True)
    price_match_eligible = Column(Boolean, default=False, nullable=False)
    tracking_number      = Column(String(100), nullable=True)
    carrier              = Column(String(50), nullable=True)
    estimated_delivery   = Column(Date, nullable=True)
    delivered_at         = Column(DateTime(timezone=True), nullable=True)
    order_url            = Column(Text, nullable=True)
    raw_capture          = Column(JSONB, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user            = relationship("User", back_populates="orders")
    items           = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    delivery_events = relationship("DeliveryEvent", back_populates="order", cascade="all, delete-orphan")
    alerts          = relationship("Alert", back_populates="order")

