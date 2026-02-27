import uuid
from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = "users"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email              = Column(String(255), unique=True, nullable=False)
    password_hash      = Column(String(255), nullable=False)
    display_name       = Column(String(100), nullable=True)
    is_active          = Column(Boolean, default=True, nullable=False)
    is_verified        = Column(Boolean, default=False, nullable=False)
    refresh_token_hash = Column(String(255), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    preferences   = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders        = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    alerts        = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    outcome_logs  = relationship("OutcomeLog", back_populates="user", cascade="all, delete-orphan")