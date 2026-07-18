"""Explainable financial notifications — InApp MVP, Push/Email interfaces ready."""

from app.modules.notifications.channels import (
    EmailChannel,
    InAppChannel,
    PushChannel,
    StubEmailChannel,
    StubPushChannel,
)
from app.modules.notifications.models import Notification, NotificationSeverity, NotificationType
from app.modules.notifications.router import router
from app.modules.notifications.rules import NotificationRulesEngine
from app.modules.notifications.service import NotificationService

__all__ = [
    "EmailChannel",
    "InAppChannel",
    "Notification",
    "NotificationRulesEngine",
    "NotificationService",
    "NotificationSeverity",
    "NotificationType",
    "PushChannel",
    "StubEmailChannel",
    "StubPushChannel",
    "router",
]
