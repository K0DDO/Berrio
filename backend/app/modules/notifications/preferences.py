from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_notification_preferences_user"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_changes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    budget_alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    goal_alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_insights_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unusual_spending_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
