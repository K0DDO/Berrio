"""IMAP mailbox sync architecture (credentials required for live use)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MailMessage:
    subject: str
    body: str
    message_id: str


class ImapMailbox(Protocol):
    """
    Future live sync:

    1. Decrypt connection imap_meta_enc
    2. Fetch UNSEEN since last_synced_at
    3. Route body → BankParser by bank_code
    4. BankService.ingest_email
    5. Update last_synced_at
    """

    async def fetch_unseen(self, *, folder: str = "INBOX", limit: int = 50) -> list[MailMessage]: ...


class NotConfiguredImapMailbox:
    """Placeholder until IMAP credentials are provided."""

    async def fetch_unseen(self, *, folder: str = "INBOX", limit: int = 50) -> list[MailMessage]:
        raise RuntimeError(
            "IMAP not configured. Set encrypted mailbox credentials on bank_connections "
            "and implement a real ImapMailbox adapter."
        )
