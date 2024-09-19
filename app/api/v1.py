from fastapi import APIRouter

from .users import router as users_router
from .diaries import router as diaries_router
from .auth import router as auth_router

V1 = APIRouter(prefix="/api/v1")

# /api/v1/users
V1.include_router(users_router)

# /api/v1/diaries
V1.include_router(diaries_router)

# /api/v1/auth
V1.include_router(auth_router)


@V1.get("/", tags=["v1"])
async def start_v1():
    return {"msg": "DDrawry's API version 1"}
