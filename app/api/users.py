from fastapi import APIRouter, Request
from pydantic import BaseModel
from schemas.schema import Mood, Weather, Diary, TempDiary, Settings

router = APIRouter(prefix="/users")


# /users/settings


@router.patch("/settings")
async def settings(settings: Settings):
    return {"settings": settings}

# /users/nickname
@router.put("/nickname")
async def nickname(request: Request):
    json = await request.json()
    # request body(json)가 업는 경우
    if not json:
        return {"status": 409, "message": "데이터가 없습니다."}

    nickname = json.get("nickname")
    if not nickname:
        # json에 nickname 데이터가 없는 경우
        return {"status": 409, "message": "닉네임 데이터 없음", "request": json}

    # 닉네임 중복을 테스트 하기 위해 'admin', 'test' 인 경우 중복으로 판정
    if nickname in ["admin", "test"]:
        return {"status": 409, "message": "닉네임 중복"}
    # 그 외에는 닉네임 변경 성공 return
    return {"status": 200, "message": "닉네임 변경 성공"}
