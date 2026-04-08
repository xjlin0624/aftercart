from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.enums import AlertType, AlertStatus, AlertPriority, RecommendedAction, EffortLevel


class RecommendationFactor(BaseModel):
    """A single decision factor that influenced the recommendation."""
    factor: str       # machine-readable key, e.g. "price_match_eligible"
    label: str        # human-readable label
    result: bool      # True if this factor was satisfied
    explanation: str  # why this factor matters / what it means in context


class ActionStep(BaseModel):
    """One numbered step in the recommended action plan."""
    step: int
    instruction: str


class ExplainedRecommendation(BaseModel):
    """
    Structured, explainable payload describing why an action was recommended
    and how the user can act on it.
    """
    alert_id: UUID
    recommended_action: RecommendedAction
    estimated_savings: float
    estimated_effort: EffortLevel
    effort_steps_estimate: int
    rationale: str
    decision_factors: list[RecommendationFactor]
    action_steps: list[ActionStep]
    days_remaining_return: int | None
    action_deadline: date | None
    evidence: dict

class GeneratedMessage(BaseModel):
    """Response for a generated customer support message."""
    alert_id: UUID
    tone: str
    message: str
    cached: bool


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
