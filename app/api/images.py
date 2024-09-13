from fastapi import APIRouter

router = APIRouter(prefix="/images")


@router.get("/images")
async def get_images():
    return {"message": "Images route"}
