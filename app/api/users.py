from fastapi import APIRouter, HTTPException, Cookie, Response, Depends, Request, Query
from ..utils import get_current_user_id
from schemas.schema import Settings, NicknameUpdate
from ..models import Setting, User
from app.database import get_db  # DB 세션을 가져오는 함수를 import합니다.
from sqlalchemy.orm import Session
from datetime import datetime



router = APIRouter(prefix="/users")


# /users/settings


@router.patch("/settings")
async def update_settings(
    settings: Settings, 
    user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)):
    # 사용자 설정 정보를 가져옵니다.
    user_settings = db.query(Setting).filter(Setting.user_id == user_id).first()

    if settings.dark_mode is not None:  # dark_mode가 요청에 포함되어 있을 경우
        user_settings.dark_mode = settings.dark_mode  # 다크 모드 업데이트
    if settings.notification is not None:  # notification이 요청에 포함되어 있을 경우
        user_settings.notification = settings.notification  # 알림 업데이트
    user_settings.updated_at = datetime.now()  # 업데이트 시간 기록
    db.commit()  # 변경 사항 저장

    return {"message": "설정이 성공적으로 업데이트되었습니다."}


@router.put("/nickname")
async def update_nickname(
    nickname_data: NicknameUpdate,  # Pydantic 스키마를 통해 요청 데이터 검증
    user_id: int = Depends(get_current_user_id),  # 현재 사용자의 ID를 가져옵니다
    db: Session = Depends(get_db)):  # DB 세션을 가져옵니다

    # DB에서 현재 사용자를 조회합니다
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # 유저가 없을 경우 에러를 반환합니다
        raise HTTPException(status_code=404, detail="User not found")

    # 닉네임 중복 확인 (admin, test 제외하고 DB 내 중복 확인)
    existing_user = db.query(User).filter(User.nickname == nickname_data.nickname).first()
    if existing_user and existing_user.id != user_id:
        raise HTTPException(status_code=409, detail="Nickname already in use")

    # 닉네임 업데이트
    user.nickname = nickname_data.nickname
    user.updated_at = datetime.now()  # 업데이트 시간을 기록합니다
    db.commit()  # DB에 변경 사항을 저장합니다
    db.refresh(user)  # 업데이트된 사용자 데이터를 다시 불러옵니다

    return {"status": 200, "message": "닉네임 변경 성공", "nickname": user.nickname}
