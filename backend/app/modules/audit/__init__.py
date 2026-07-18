"""Audit domain — append-only audit_logs."""

from app.modules.audit.service import AuditService

__all__ = ["AuditService"]
