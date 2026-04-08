from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from ..models.enums import MessageTone

class UserPreferencesUpdate(BaseModel):
    min_savings_threshold: float | None = None
    notify_price_drop: bool | None = None
    notify_delivery_anomaly: bool | None = None
    push_notifications_enabled: bool | None = None
    preferred_message_tone: MessageTone | None = None
    monitored_retailers: list[str] | None = None

class UserPreferencesRead(BaseModel):
    id: UUID
    user_id: UUID
    min_savings_threshold: float
    notify_price_drop: bool
    notify_delivery_anomaly: bool
    push_notifications_enabled: bool
    preferred_message_tone: MessageTone
    monitored_retailers: list[str]
    updated_at: datetime

    model_config = {"from_attributes": True}
