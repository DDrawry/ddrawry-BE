from fastapi import APIRouter, Request, Query, HTTPException, Depends
from typing import List, Optional
from fastapi.responses import JSONResponse
from schemas.schema import MoodEnum, WeatherEnum, Diary, TempDiarySchema, Settings, DiaryCreate, StatusUpdateRequest
from sqlalchemy.orm import Session
from app.models import Diary as DiaryModel, Image, User, TempDiary
from ..utils import get_current_user_id
from ..database import get_db
from datetime import datetime, timezone
from sqlalchemy import func

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
    
    return {"status": 201,
            "message": "다이어리 저장 성공",
            "data": {"id": new_diary.id}
        }

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


@router.get("/")
async def search_diary_exist(date: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # 'YYYYMMDD' 형식을 'YYYY-MM-DD' 형식으로 변환
    try:
        formatted_date = datetime.strptime(str(date), "%Y%m%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYYMMDD 형식을 사용하세요.")
    
    # diary에서 해당 날짜와 user_id로 조회
    diary = db.query(DiaryModel).filter(
        DiaryModel.date == formatted_date,
        DiaryModel.user_id == user_id,
        DiaryModel.is_deleted == False
    ).first()

    # user_id로 사용자 nickname 조회
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # diary가 존재할 경우
    if diary:
        return {
            "status": 200,
            "message": "작성한 다이어리가 존재합니다.",
            "is_exist": True,
            "data": {
                "date": formatted_date,
                "diary_id": diary.id
            },
        }

    # temp_diary에서 해당 날짜와 user_id로 조회
    temp_diary = db.query(TempDiary).filter(
        TempDiary.date == formatted_date,
        TempDiary.user_id == user_id,
        TempDiary.status == 0
    ).first()

    # temp_diary가 존재할 경우
    if temp_diary:
        return {
            "status": 200,
            "message": "임시 다이어리가 이미 존재합니다.",
            "is_exist": False,
            "is_temp_exist": True,
            "temp_data": {
                "date": formatted_date,
                "temp_id": temp_diary.id,
            }
        }

    # 다이어리와 temp_diary 모두 존재하지 않을 경우 새로운 temp_diary 생성
    new_temp_diary = TempDiary(
        user_id=user_id,
        date=formatted_date,
        title=None,
        weather=None,
        mood=None,
        nickname=user.nickname,
        story=None
    )
    
    db.add(new_temp_diary)
    db.commit()
    db.refresh(new_temp_diary)

    # 임시 다이어리 생성 시 temp_id만 반환
    return {
        "status": 200,
        "message": "임시 다이어리가 존재하지 않아 새로 생성되었습니다.",
        "is_exist": False,
        "is_temp_exist": False,
        "data": {
            "date": formatted_date,
            "temp_id": new_temp_diary.id
        }
    }

# # /diaries/temp
# @router.post("/temp")
# async def create_temp_diary(diary: TempDiarySchema, user_id: int, db: Session = Depends(get_db)):
#     new_temp_diary = TempDiary(**diary.dict(), user_id=user_id)
#     db.add(new_temp_diary)
#     db.commit()
#     db.refresh(new_temp_diary)
#     return new_temp_diary

@router.get("/temp/{id}")
async def get_temp_diary(
    id: int, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_current_user_id)
):
    # 현재 로그인한 유저 정보를 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    
    # temp_diary 정보 조회
    temp_diary = db.query(TempDiary).filter(TempDiary.id == id, TempDiary.user_id == user_id, TempDiary.status == 0).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="임시 다이어리를 찾을 수 없습니다.")

    # 필요한 데이터 반환
    return {
        "status": 200,
        "message": "임시 다이어리를 조회 완료.",
        "data": {
            "id": temp_diary.id,
            "user_id": temp_diary.user_id,
            "date": temp_diary.date,
            "nickname": user.nickname,  # 유저의 닉네임을 가져와서 포함
            "title": temp_diary.title,
            "weather": temp_diary.weather,
            "mood": temp_diary.mood,
            "story": temp_diary.story,
        }
    }


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
        "data": {
            "temp_id": existing_temp_diary.id
        }
    }



@router.put("/like/{id}")
async def like_diary(id: int, db: Session = Depends(get_db)):
    diary = db.query(DiaryModel).filter(DiaryModel.id == id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    # 좋아요 상태를 토글
    diary.like = not diary.like
    db.commit()
    
    # 좋아요 상태에 따라 메시지 변경
    if diary.like:
        return {
            "status": 200,
            "message": "좋아요 등록이 성공하였습니다.",
            "data": {
                "id": id,
                "bookmark": diary.like
            }
        }
    else:
        return {
            "status": 200,
            "message": "좋아요 등록이 실패하였습니다.",
            "data": {
                "id": id,
                "bookmark": diary.like
            }
        }



# 전체/월별
# /diaries/like 
# 좋아요를 누른 다이어리들 조회 API
@router.get("/like")
async def get_like_diaries(type: str, date: str = None, db: Session = Depends(get_db)): 
    if type == "month" and date and len(date) == 6:
        year = int(date[:4])
        month = int(date[4:])
        
        # 로그 추가
        print(f"Querying for year: {year}, month: {month}")

        # 해당 연도와 월에 해당하는 좋아요 누른 다이어리를 조회
        liked_diaries = db.query(DiaryModel).filter(
            DiaryModel.like == True,
            DiaryModel.date.between(f"{year}-{month:02d}-01", f"{year}-{month:02d}-30")  # 30일까지 확인
        ).all()
    
        if not liked_diaries:
            raise HTTPException(status_code=404, detail="해당 월에 좋아요를 누른 다이어리가 없습니다.")
    
        # 다이어리 정보를 반환할 형식으로 변환
        result = []
        for diary in liked_diaries:
            # 이미지 URL 가져오기 (하나만 가져오기)
            image = db.query(Image).filter(
                Image.diary_id == diary.id,
                Image.is_active == True,
                Image.is_deleted == False
            ).first()  # 첫 번째 결과만 가져오기

            # 이미지 URL이 없으면 None으로 설정
            image_url = image.image_url if image else None

            result.append({
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),  # 날짜 형식 변환
                "title": diary.title,
                "image": image_url,  # 단일 이미지 URL 또는 None
                "bookmark": 1 if diary.like else 0  # 좋아요 상태를 int(1 또는 0)로 반환
            })
        
        return {
            "status": 200,
            "message": f"{year}년 {month}월 좋아요 누른 일기 조회 완료",
            "data": result,
        }
    elif type == "all":
        # 모든 좋아요를 누른 다이어리를 날짜순으로 조회
        liked_diaries = db.query(DiaryModel).filter(DiaryModel.like == True).order_by(DiaryModel.date).all()

        if not liked_diaries:
            raise HTTPException(status_code=404, detail="좋아요를 누른 다이어리가 없습니다.")
        
        result = []
        for diary in liked_diaries:
            # 이미지 URL 가져오기 (하나만 가져오기)
            image = db.query(Image).filter(
                Image.diary_id == diary.id,
                Image.is_active == True,
                Image.is_deleted == False
            ).first()  # 첫 번째 결과만 가져오기

            # 이미지 URL이 없으면 None으로 설정
            image_url = image.image_url if image else None

            result.append({
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),  # 날짜 형식 변환
                "title": diary.title,
                "image": image_url,  # 단일 이미지 URL 또는 None
                "bookmark": 1 if diary.like else 0  # 좋아요 상태를 int(1 또는 0)로 반환
            })
        
        return {
            "status": 200,
            "message": "모든 좋아요를 누른 일기 조회 완료",
            "data": result,
    }



@router.get("/{id}")
async def get_diary(id: int, edit: Optional[bool] = None, db: Session = Depends(get_db)):
    # 1. 다이어리를 조회
    diary = db.query(DiaryModel).filter(DiaryModel.id == id).first()
    
    if not diary:
        raise HTTPException(status_code=404, detail=f"{id}번 다이어리를 찾을 수 없습니다.")
    
    image = db.query(Image).filter(
        Image.diary_id == diary.id,
        Image.is_active == True,
        Image.is_deleted == False
    ).first()  # 첫 번째 결과만 가져오기

    # 이미지 URL이 없으면 None으로 설정
    image_url = image.image_url if image else None

    # 2. edit 파라미터가 없거나 false일 때는 다이어리만 반환
    if not edit:
        return {
            "status": 200,
            "message": f"{id}번 다이어리 조회 완료",
            "data": {
                "id": diary.id,
                "date": diary.date,
                "nickname": diary.nickname,
                "mood": diary.mood,
                "weather": diary.weather,
                "title": diary.title,
                "image": image_url,
                "story": diary.story
            }
        }
    
    # 3. edit=true일 경우, 임시 다이어리 생성
    temp_diary = TempDiary(
        diary_id=diary.id,
        date=diary.date,
        nickname=diary.nickname,
        mood=diary.mood,
        weather=diary.weather,
        title=diary.title,
        image=image_url,
        story=diary.story
    )
    db.add(temp_diary)
    db.commit()
    db.refresh(temp_diary)

    # 4. 임시 다이어리의 temp_id와 함께 응답
    return {
        "status": 200,
        "message": f"{id}번 다이어리 수정 준비 완료",
        "data": {
            "id": diary.id,
            "date": diary.date,
            "nickname": diary.nickname,
            "mood": diary.mood,
            "weather": diary.weather,
            "title": diary.title,
            "image": image_url,
            "story": diary.story
        },
        "temp_id": temp_diary.id  # 새로 생성된 temp_id 반환
    }

# /diaries/search/{keyword}
@router.get("/search/{keyword}")
async def search_diary(keyword: str, db: Session = Depends(get_db)):
    if keyword == "":
        diaries = db.query(DiaryModel).all()
        return {
            "status": 200,
            "message": "모든 다이어리 조회 완료",
            "data": diaries,
        }
    
    # 키워드
    diaries = db.query(DiaryModel).filter(
        (DiaryModel.title.like(f"%{keyword}%")) |  
        (DiaryModel.story.like(f"%{keyword}%")) &  
        (DiaryModel.is_deleted == False)           # 삭제되지 않은 항목만
    ).all()
    
    if not diaries:
        return {
            "status": 404,
            "message": f"'{keyword}'에 대한 검색 결과가 없습니다."
        }
    
    results = []
    for diary in diaries:
        # diary에 연결된 이미지 가져오기
        image = db.query(Image).filter(Image.diary_id == diary.id, Image.is_active == True).first()
        image_url = image.image_url if image else None  # 이미지가 있으면 URL, 없으면 None

        results.append({
            "id": diary.id,
            "date": diary.date.strftime("%Y-%m-%d"),  # 날짜 포맷
            "title": diary.title,
            "image": image_url,
            "bookmark": diary.like,
        })
    
    return {
        "status": 200,
        "message": f"'{keyword}'에 관한 다이어리 조회 완료",
        "data": results,
    }

# /diaries/main?type=calender&date=202406
@router.get("/main")
async def get_diaries(type: str, date: str, db: Session = Depends(get_db)):
    year = date[:4]
    month = date[4:]

    # 해당 연도와 월의 다이어리 조회
    diaries = db.query(DiaryModel).filter(
        func.strftime("%Y", DiaryModel.date) == year,
        func.strftime("%m", DiaryModel.date) == month,
        DiaryModel.is_deleted == False
    ).all()

    # 다이어리가 없는 경우
    if not diaries:
        return {
            "status": 404,
            "message": f"{year}-{month}에 해당하는 다이어리가 없습니다."
        }

    # 캘린더형 조회 (title 없이)
    if type == "calender":
        result = [
            {
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),
                "image": diary.image_path if diary.image_path else "띠로리로고",  # 이미지가 없으면 기본 이미지 사용
                "bookmark": diary.like
            }
            for diary in diaries
        ]

    # 목록형 조회 (title 포함)
    elif type == "list":
        result = [
            {
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),
                "title": diary.title,
                "image": diary.image_path if diary.image_path else "띠로리로고",  # 이미지가 없으면 기본 이미지 사용
                "bookmark": diary.like
            }
            for diary in diaries
        ]

    else:
        return {
            "status": 400,
            "message": "잘못된 type 값입니다. 'list' 또는 'calender'를 사용하세요."
        }

    return {
        "status": 200,
        "message": f"{year}-{month}에 대한 메인 페이지 조회 완료",
        "data": result
    }



@router.post("/cancel")
async def update_temp_diary_status(
    request: StatusUpdateRequest,  # 요청 바디로 StatusUpdateRequest 사용
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)  # 현재 사용자의 user_id 가져오기
):
    # date 값을 'YYYY-MM-DD' 형식으로 변환
    try:
        formatted_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")

    user = db.query(User).filter(User.id == user_id).first()
    # user_id와 date가 일치하는 temp_diary 찾기
    temp_diary = db.query(TempDiary).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == formatted_date
    ).first()

    if not temp_diary:
        raise HTTPException(status_code=404, detail="해당 날짜에 temp_diary가 존재하지 않습니다.")

    type = request.type  # 요청 바디에서 type 필드 가져오기

    if type == "write":
        # 상태를 True로 업데이트
        temp_diary.status = True
        temp_diary.updated_at = datetime.now()  # updated_at 필드 업데이트
        db.commit()
        
        return {
            "status": 200,
            "message": "상태가 업데이트되었습니다.",
            "data": {"temp_id": temp_diary.id}
        }

    elif type == "main":
        
        temp_diary.status = True
        temp_diary.updated_at = datetime.now()  # updated_at 필드 업데이트
        db.commit()  # 변경 사항 저장

        # 새로운 TempDiary 생성
        new_temp_diary = TempDiary(
            user_id=user_id,
            date=formatted_date,
            title=None,
            weather=None,
            mood=None,
            nickname=user.nickname,  # 여기에 적절한 nickname을 추가하세요
            story=None,
            status=False  # status를 True로 설정
        )
        
        db.add(new_temp_diary)
        db.commit()
        db.refresh(new_temp_diary)  # 새로 생성된 diary의 id를 가져옴
        
        return {
            "status": 201,
            "message": "새로운 임시 다이어리가 생성되었습니다.",
            "data": {"temp_id": new_temp_diary.id}
        }