"""Import all ORM models here so Alembic sees them."""

from app.db.base import Base
from app.modules.auth.models import (
    AuditLog,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)
from app.modules.banks.models import BankConnection, Transaction
from app.modules.categories.models import Category, CategoryRule
from app.modules.families.models import Family, FamilyMember, FamilyPermission
from app.modules.financial_health.models import FinancialScore
from app.modules.receipts.models import Receipt, ReceiptItem
from app.modules.users.models import User

__all__ = [
    "AuditLog",
    "BankConnection",
    "Base",
    "Category",
    "CategoryRule",
    "EmailVerificationToken",
    "Family",
    "FamilyMember",
    "FamilyPermission",
    "FinancialScore",
    "PasswordResetToken",
    "Receipt",
    "ReceiptItem",
    "RefreshToken",
    "Transaction",
    "User",
]
