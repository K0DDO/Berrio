from fastapi import APIRouter

from app.api.v1 import system
from app.modules.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth_router)
