from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    price_changes_enabled: bool
    budget_alerts_enabled: bool
    goal_alerts_enabled: bool
    ai_insights_enabled: bool
    unusual_spending_enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    price_changes_enabled: bool | None = None
    budget_alerts_enabled: bool | None = None
    goal_alerts_enabled: bool | None = None
    ai_insights_enabled: bool | None = None
    unusual_spending_enabled: bool | None = None
