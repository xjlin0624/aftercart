from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.enums import ActionTaken

class OutcomeLogCreate(BaseModel):
    alert_id: UUID | None = None
    order_item_id: UUID | None = None
    action_taken: ActionTaken
    recovered_value: float | None = None
    was_successful: bool | None = None
    failure_reason: str | None = None
    notes: str | None = None

class OutcomeLogRead(BaseModel):
    id: UUID
    user_id: UUID
    alert_id: UUID | None
    order_item_id: UUID | None
    action_taken: ActionTaken
    recovered_value: float | None
    was_successful: bool | None
    failure_reason: str | None
    notes: str | None
    logged_at: datetime

    model_config = {"from_attributes": True}


class SavingsByAction(BaseModel):
    action_taken: ActionTaken
    count: int
    total_recovered: float


class SavingsSummary(BaseModel):
    total_recovered: float
    total_actions: int
    successful_actions: int
    by_action: list[SavingsByAction]
    history: list[OutcomeLogRead]
