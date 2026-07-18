from fastapi import APIRouter

from app.api.v1 import system
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.financial_health.router import router as health_router
from app.modules.receipts.router import router as receipts_router

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth_router)
api_router.include_router(receipts_router)
api_router.include_router(categories_router)
api_router.include_router(analytics_router)
api_router.include_router(health_router)
