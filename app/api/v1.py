from fastapi import APIRouter

from .users import router as users_router
from .diaries import router as diaries_router
from .auth import router as auth_router
from .images import router as image_router
from .auth import is_valid_token
from fastapi import APIRouter, HTTPException, Request

V1 = APIRouter(prefix="/api/v1")

# /api/v1/users
V1.include_router(users_router)

# /api/v1/diaries
V1.include_router(diaries_router)

# /api/v1/auth
V1.include_router(auth_router)

# /api/v1/images
V1.include_router(image_router)


@V1.get("/", tags=["v1"])
async def start_v1(request: Request):
    access_token = request.cookies.get("access_token")

    if not access_token or not is_valid_token(access_token):
        raise HTTPException(status_code=401, detail="Invalid or missing access token")

    return {"msg": "DDrawry's API version 1"}
