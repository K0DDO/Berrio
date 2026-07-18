"""Import all ORM models here so Alembic sees them."""

from app.db.base import Base
from app.modules.ai.models import AiInsight
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
from app.modules.products.models import Product, ProductPriceHistory, ProductVariant
from app.modules.receipts.models import Receipt, ReceiptItem
from app.modules.users.models import User

__all__ = [
    "AiInsight",
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
    "Product",
    "ProductPriceHistory",
    "ProductVariant",
    "Receipt",
    "ReceiptItem",
    "RefreshToken",
    "Transaction",
    "User",
]
