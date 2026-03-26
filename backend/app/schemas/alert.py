from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.enums import AlertType, AlertStatus, AlertPriority, RecommendedAction, EffortLevel

class AlertCreate(BaseModel):
    order_id: UUID | None = None
    order_item_id: UUID | None = None
    alert_type: AlertType
    priority: AlertPriority = AlertPriority.medium
    title: str
    body: str
    recommended_action: RecommendedAction | None = None
    estimated_savings: float | None = None
    estimated_effort: EffortLevel | None = None
    effort_steps_estimate: int | None = None
    recommendation_rationale: str | None = None
    days_remaining_return: int | None = None
    action_deadline: date | None = None
    alternative_product_url: str | None = None
    alternative_product_price: float | None = None
    evidence: dict | None = None
    generated_messages: dict | None = None

class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    generated_messages: dict | None = None

class AlertRead(BaseModel):
    id: UUID
    user_id: UUID
    order_id: UUID | None
    order_item_id: UUID | None
    alert_type: AlertType
    status: AlertStatus
    priority: AlertPriority
    title: str
    body: str
    recommended_action: RecommendedAction | None
    estimated_savings: float | None
    estimated_effort: EffortLevel | None
    effort_steps_estimate: int | None
    recommendation_rationale: str | None
    days_remaining_return: int | None
    action_deadline: date | None
    alternative_product_url: str | None
    alternative_product_price: float | None
    evidence: dict | None
    generated_messages: dict | None
    push_sent_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
