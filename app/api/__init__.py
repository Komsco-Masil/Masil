from fastapi import APIRouter
from app.api.endpoints import auth, stores, employees, promotions, community

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(stores.router, prefix="/stores", tags=["stores"])
api_router.include_router(employees.router, prefix="/stores", tags=["employees"])
api_router.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
