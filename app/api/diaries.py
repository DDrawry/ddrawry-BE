from fastapi import APIRouter, Request, Query, HTTPException, Depends
from typing import List, Optional
from fastapi.responses import JSONResponse
from schemas.schema import MoodEnum, WeatherEnum, Diary, TempDiarySchema, Settings, DiaryCreate
from sqlalchemy.orm import Session
from app.models import Diary as DiaryModel, Image, User, TempDiary
from ..database import get_db
from datetime import datetime, timezone


router = APIRouter(prefix="/diaries")


# /diaries
@router.post("/")
async def new_diary(diary: DiaryCreate, db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    new_diary = DiaryModel(
        user_id=user.id,
        title=diary.title,
        story=diary.story if diary.story else "",
        weather=diary.weather,
        mood=diary.mood,
        date=diary.date,  # date가 없으면 None
        nickname=diary.nickname,  # nickname이 없으면 None
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(new_diary)
    new_image = Image(
        diary_id=new_diary.id
    )
    db.commit()
    db.refresh(new_diary)
    
    return {"status": 201, "message": "다이어리 저장 성공", "id": new_diary.id}

@router.get("/diary/{diary_id}")
async def get_diary(diary_id: int, db: Session = Depends(get_db)):
    # 다이어리 ID로 조회
    diary = db.query(DiaryModel).filter(DiaryModel.id == diary_id).first()
    
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    # mood와 weather 값을 Enum을 통해 문자열로 변환하여 반환
    return {
        "id": diary.id,
        "user_id": diary.user_id,
        "title": diary.title,
        "story": diary.story,
        "mood": MoodEnum(diary.mood).name,  # 정수를 문자열로 변환
        "weather": WeatherEnum(diary.weather).name,  # 정수를 문자열로 변환
        "date": diary.date,
        "nickname": diary.nickname,
        "created_at": diary.created_at,
        "updated_at": diary.updated_at
    }

# /diaries/{id}
@router.put("/{id}")  # 이렇게 수정할 수 있음
async def edit_diary(id: int, diary: Diary, db: Session = Depends(get_db)):
    # 기존 다이어리 조회
    existing_diary = db.query(DiaryModel).filter(DiaryModel.id == id).first()

    if not existing_diary:
        raise HTTPException(status_code=404, detail="Diary not found")

    # 다이어리 수정
    existing_diary.title = diary.title
    existing_diary.story = diary.story
    existing_diary.mood = diary.mood
    existing_diary.weather = diary.weather
    existing_diary.date = diary.date
    existing_diary.nickname = diary.nickname
    existing_diary.updated_at = datetime.now(timezone.utc)# 수정된 시간 업데이트

    # 변경사항을 DB에 커밋
    db.commit()
    db.refresh(existing_diary)

    return {
        "status": 200,
        "message": "다이어리 수정 성공",
        "id": existing_diary.id,
        "diary": {
            "title": existing_diary.title,
            "story": existing_diary.story,
            "mood": MoodEnum(existing_diary.mood).name,  # 숫자를 문자열로 변환
            "weather": WeatherEnum(existing_diary.weather).name,  # 숫자를 문자열로 변환
            "date": existing_diary.date,
            "nickname": existing_diary.nickname,
            "updated_at": existing_diary.updated_at
        }
    }

# /diaries/{id}
@router.delete("/{id}")
async def delete_diary(id: int, db: Session = Depends(get_db)):
    # 다이어리 ID로 조회
    diary_to_delete = db.query(DiaryModel).filter(DiaryModel.id == id).first()
    
    if not diary_to_delete:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    # 다이어리 삭제
    db.delete(diary_to_delete)
    db.commit()  # 변경사항 커밋
    
    # 삭제된 다이어리 정보를 응답으로 반환
    return {
        "status": 200,
        "message": "다이어리 삭제 성공",
        "id": id
    }

# /diaries?date
@router.get("/")
async def search_diary_exist(date: int, db: Session = Depends(get_db)):
    # 쿼리 파라미터로 받은 date를 'YYYYMMDD' 형식에서 'YYYY-MM-DD' 형식으로 변환
    try:
        formatted_date = datetime.strptime(str(date), "%Y%m%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYYMMDD 형식을 사용하세요.")
    
    # 해당 날짜에 작성된 다이어리 조회
    diary = db.query(DiaryModel).filter(DiaryModel.date == formatted_date).first()
    
    if diary:
        return {
            "status": 200,
            "message": "작성한 다이어리가 존재합니다.",
            "data": {"date": formatted_date, "is_exist": True, "id": diary.id},
        }
    
    return {
        "status": 200,
        "message": "작성한 다이어리가 존재하지 않습니다.",
        "data": {"date": formatted_date, "is_exist": False, "id": None},
    }

# /diaries/temp
@router.post("/temp")
async def create_temp_diary(diary: TempDiarySchema, user_id: int, db: Session = Depends(get_db)):
    new_temp_diary = TempDiary(**diary.dict(), user_id=user_id)
    db.add(new_temp_diary)
    db.commit()
    db.refresh(new_temp_diary)
    return new_temp_diary

# /diaries/temp/{id}
@router.get("/temp/{id}")
async def get_temp_diary(id: int, db: Session = Depends(get_db)):
    temp_diary = db.query(TempDiary).filter(TempDiary.id == id).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="임시 다이어리를 찾을 수 없습니다.")
    return temp_diary

# /diaries/temp/{id}
@router.put("/temp/{id}")
async def save_temp(id: int, diary: TempDiarySchema, db: Session = Depends(get_db)):
    # 이미 존재하는 temp_diary가 있는지 확인
    existing_temp_diary = db.query(TempDiary).filter(TempDiary.id == id).first()

    # 존재하지 않는다면 404 에러를 발생시킴
    if not existing_temp_diary:
        raise HTTPException(status_code=404, detail="임시 다이어리를 찾을 수 없습니다.")
    
    # 임시 다이어리 수정
    existing_temp_diary.title = diary.title
    existing_temp_diary.story = diary.story
    existing_temp_diary.weather = diary.weather
    existing_temp_diary.mood = diary.mood
    existing_temp_diary.date = diary.date
    existing_temp_diary.nickname = diary.nickname
    existing_temp_diary.updated_at = datetime.now(timezone.utc)  # 수정된 시간 기록

    # 변경사항을 DB에 커밋
    db.commit()

    return {
        "status": 200,
        "message": "다이어리 임시 저장 성공",
        "temp_id": existing_temp_diary.id
    }


# /diaries/{id}?edit={bool}
# edit 생략 가능
@router.get("/{id}")
async def get_diary(id: int, edit: bool = None):
    # id가 999인 경우 존재하지 않는 다이어리
    if id == 999:
        return {
            "status": 404,
            "message": f"id가 {id}인 다이어리가 존재하지 않음",
        }

    # edit 이 True 경우 수정 중인 것으로 리턴
    if edit:
        return {
            "status": 200,
            "message": f"{id}번 다이어리 수정 준비 완료",
            "data": {
                "id": 1,
                "date": "2024-08-13",
                "nickname": "팡팡이",
                "mood": 1,
                "weather": 3,
                "title": "신나는 산책을 했따",
                "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...AYH/",
                "story": "아침에 쿨쿨자고 ,,,,",
            },
            "temp_id": 55,
        }
    return {
        "status": 200,
        "message": f"{id}번 다이어리 조회 완료",
        "data": {
            "id": 1,
            "date": 20240813,
            "nickname": "팡팡이",
            "mood": 1,
            "weather": 3,
            "title": "신나는 산책을 했따",
            "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...AYH/",
            "story": "아침에 쿨쿨자고 ,,,,",
        },
    }

# /diaries/like/{id}
@router.put("/like/{id}")
async def like_diary(id: int, db: Session = Depends(get_db)):
    diary = db.query(DiaryModel).filter(DiaryModel.id == id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    # 좋아요 상태를 토글
    diary.like = not diary.like
    db.commit()
    
    return {
        "status": 200,
        "id": id,
        "bookmark": diary.like
    }
# 전체/월별
# /diaries/like 
# 좋아요를 누른 다이어리들 조회 API
# @router.get("/like")
# async def get_like_diaries(db: Session = Depends(get_db)): 
#     # 좋아요를 누른 다이어리 조회
#     liked_diaries = db.query(DiaryModel).filter(DiaryModel.like == True).all()
    
#     if not liked_diaries:
#         raise HTTPException(status_code=404, detail="좋아요를 누른 다이어리가 없습니다.")
    
#     # 다이어리 정보를 반환
#     result = []
#     for diary in liked_diaries:
#         result.append({
#             "id": diary.id,
#             "date": diary.date.strftime("%Y-%m-%d"),  # 날짜 형식 변환
#             "title": diary.title,
#             "image": diary.image,  # 이미지 URL 또는 데이터
#             "bookmark": 1 if diary.like else 0  # 좋아요 상태를 int(1 또는 0)로 반환
#         })
    
#     return {
#         "status": 200,
#         "message": "좋아요 누른 일기 조회 완료",
#         "data": result,
#     }


# /diaries/search/{keyword}
@router.get("/search/{keyword}")
async def search_diary(keyword: str = ""):
    if keyword == "":
        return {"status": 200, "message": "모든 다이어리 조회"}

    if keyword == "999":
        return {"status": 404, "message": "해당 키워드로 검색이 되지 않았습니다."}

    return {
        "status": 200,
        "message": f"{keyword}에 관한 일기 조회 완료",
        "data": [
            {
                "id": 1,
                "date": "2024-08-13",
                "title": f"신나는 {keyword}을 했따",
                "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...AYH/",
                "bookmark": 1,
            },
            {
                "id": 3,
                "date": "2024-08-20",
                "title": f"{keyword} 가기 싫다",
                "image": "띠로리_로고.jpg",
                "bookmark": 0,
            },
        ],
    }

# /diaries/main?type=calender&date=202406
@router.get("/main")
async def get_main_diaries(type: str = Query(..., description="조회 유형 (list 또는 calender)"),
                           date: str = Query(..., description="조회할 년월 (예: 202408)")):
    calendar_data = [
        {
            "id": diary["id"],
            "date": diary["date"],
            "image": diary["image"],
            "bookmark": diary["bookmark"]
        }
        for diary in diaries_list
    ]

    return JSONResponse(content={
        "status": 200,
        "message": "다이어리 목록형 조회 완료",
        "data": calendar_data
    })

# 더미
diaries_list = [
    {
        "id": 1,
        "date": "2024-08-13",
        "title": "신나는 산책을 했따",
        "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...AYH/",
        "bookmark": True
    },
    {
        "id": 2,
        "date": "2024-08-19",
        "title": "냠냠 맛있는거 먹기",
        "image": None,  # 이미지가 없는 경우
        "bookmark": False
    }
]