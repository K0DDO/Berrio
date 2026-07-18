"""User / auth domain events."""

from app.modules.events.base import DomainEvent


class UserRegisteredEvent(DomainEvent):
    event_type: str = "user.registered"


class UserLoggedInEvent(DomainEvent):
    event_type: str = "user.logged_in"
