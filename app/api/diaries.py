from typing import List, Optional
from schemas.schema import MoodEnum, WeatherEnum, DiaryCreate, StatusUpdateRequest, ShareImageRequest
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Diary as DiaryModel, Image, User, TempDiary
from ..utils import get_current_user_id, get_daily_image_count, get_image_count_for_date, upload_image_to_s3
from ..database import get_db
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from dateutil.relativedelta import relativedelta
import os
from fastapi.responses import JSONResponse
import base64
from calendar import monthrange

router = APIRouter(prefix="/diaries")
load_dotenv()
S3_BASE_URL= os.getenv("S3_BASE_URL")

@router.post("")
async def new_diary(
    diary: DiaryCreate, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_current_user_id)
):
    # 다이어리 생성
    new_diary = DiaryModel(
        user_id=user_id,
        title=diary.title,
        story=diary.story if diary.story else "",
        weather=diary.weather,
        mood=diary.mood,
        date=diary.date,  # 변환된 날짜 사용
        nickname=diary.nickname,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(new_diary)
    db.commit()
    db.refresh(new_diary)

    # 이미지 URL에서 S3 경로 부분 제거 (image가 None이 아닌 경우)
    relative_image_url = ""
    if diary.image:
        relative_image_url = diary.image.replace(S3_BASE_URL, "")
    
    # diary.date를 datetime 객체로 변환
    try:
        diary_date = datetime.strptime(diary.date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
    
    # 같은 경로의 기존 이미지의 is_temp 상태를 False로 업데이트
    date_path = f"{user_id}/{diary_date.strftime('%Y-%m-%d')}/"
    db.query(Image).filter(
        Image.image_url.startswith(date_path),
        Image.is_temp == True
    ).update({"is_temp": False})

    # 새로운 이미지의 is_temp 상태를 True로 설정 (image가 None이 아닌 경우에만)
    if diary.image:
        image = db.query(Image).filter(
            Image.image_url == relative_image_url,
            Image.is_temp == False
        ).first()
        if image:
            image.is_temp = True
            image.diary_id = new_diary.id  # 다이어리 ID 연결
            db.commit()
            db.refresh(image)

    # 같은 날짜의 다른 다이어리의 is_deleted를 True로 업데이트
    db.query(DiaryModel).filter(
        DiaryModel.user_id == user_id,
        DiaryModel.date == diary.date,
        DiaryModel.id != new_diary.id  # 새로 생성된 다이어리는 제외
    ).update({"is_deleted": True})

    # 새로 생성된 다이어리와 같은 날짜의 temp_diary 상태를 1로 업데이트
    db.query(TempDiary).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == diary.date,  # 변환된 날짜와 일치하는 조건 추가
        TempDiary.status != 1  # 상태가 1이 아닌 경우
    ).update({"status": 1})
    
    db.commit()
    
    # 생성된 TempDiary의 ID 가져오기
    last_temp_diary_id = db.query(TempDiary.id).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == diary.date
    ).order_by(TempDiary.id.desc()).first()

    return {
        "status": 201,
        "message": "다이어리 저장 성공",
        "data": {
            "id": new_diary.id,
            "temp_id": last_temp_diary_id[0] if last_temp_diary_id else None  # Last TempDiary id
        }
    }


@router.put("/{diary_id}")
async def edit_diary(
    diary_id: int, 
    diary: DiaryCreate, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_current_user_id)
):
    existing_diary = db.query(DiaryModel).filter(DiaryModel.id == diary_id).first()
    if not existing_diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    if existing_diary.user_id != user_id:  # 소유자 검증 로직 추가
        raise HTTPException(status_code=403, detail="You do not have permission to edit this diary")
    
    # 다이어리 업데이트
    existing_diary.title = diary.title
    existing_diary.story = diary.story or ""  # story가 없으면 빈 문자열
    existing_diary.mood = diary.mood  # 이미 Enum으로 변환됨
    existing_diary.weather = diary.weather  # 이미 Enum으로 변환됨
    existing_diary.date = diary.date
    existing_diary.nickname = diary.nickname
    existing_diary.updated_at = datetime.now(timezone.utc)  

    db.query(TempDiary).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == diary.date,  # 변환된 날짜와 일치하는 조건 추가
        TempDiary.status != 1  # 상태가 1이 아닌 경우
    ).update({"status": 1})
    
    # image_url에서 S3 URL 부분 제거 (image가 None이 아닌 경우에만)
    relative_image_url = ""
    if diary.image:
        relative_image_url = diary.image.replace(S3_BASE_URL, "")
    
    # diary.date를 datetime 객체로 변환
    try:
        diary_date = datetime.strptime(diary.date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    # image 필드가 비어 있으면 연결된 이미지의 is_temp 값을 모두 0으로 설정
    if diary.image == "":
        db.query(Image).filter(
            Image.diary_id == existing_diary.id
        ).update({"is_temp": False})
    else:
        # 같은 경로의 기존 이미지의 is_temp 상태를 False로 업데이트
        date_path = f"{user_id}/{diary_date.strftime('%Y-%m-%d')}/"
        db.query(Image).filter(
            Image.image_url.startswith(date_path),
            Image.is_temp == True
        ).update({"is_temp": False})

    # 새로운 이미지의 is_temp 상태를 True로 설정 (image가 None이 아닌 경우에만)
    if diary.image:
        image = db.query(Image).filter(
            Image.image_url == relative_image_url,
            Image.is_temp == False
        ).first()
        if image:
            image.is_temp = True
            image.diary_id = existing_diary.id  # 기존 다이어리 ID로 설정
            db.commit()
            db.refresh(image)

    # 새로 생성된 다이어리와 같은 날짜의 temp_diary 상태를 1로 업데이트
    db.query(TempDiary).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == diary.date,  # 변환된 날짜와 일치하는 조건 추가
        TempDiary.status != 1  # 상태가 1이 아닌 경우
    ).update({"status": 1})
    
    db.commit()

    last_temp_diary_id = db.query(TempDiary.id).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == diary.date
    ).order_by(TempDiary.id.desc()).first()

    return {
        "status": 200,
        "message": "다이어리 수정 성공",
        "data": {
            "id": existing_diary.id,
            "temp_id": last_temp_diary_id[0] if last_temp_diary_id else None  # Last TempDiary id
        }
    }

@router.put("/temp/{temp_id}")
async def save_temp(
    temp_id: int,
    diary: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    existing_temp_diary = db.query(TempDiary).filter(TempDiary.id == temp_id).first()
    if not existing_temp_diary:
        raise HTTPException(status_code=404, detail="임시 다이어리를 찾을 수 없습니다.")
    if existing_temp_diary.user_id != user_id:
        raise HTTPException(status_code=403, detail="해당 사용자가 아닙니다.")
    
    # 필요한 경우에만 필드를 업데이트
    if "title" in diary:
        existing_temp_diary.title = diary["title"] if diary["title"] != "" else None
    if "story" in diary:
        existing_temp_diary.story = diary["story"] if diary["story"] != "" else None
    if "weather" in diary:
        existing_temp_diary.weather = WeatherEnum[diary["weather"].lower()].value if diary["weather"] != "" else None
    if "mood" in diary:
        existing_temp_diary.mood = MoodEnum[diary["mood"].lower()].value if diary["mood"] != "" else None
    if "date" in diary:
        existing_temp_diary.date = diary["date"] if diary["date"] != "" else None
    if "nickname" in diary:
        existing_temp_diary.nickname = diary["nickname"] if diary["nickname"] != "" else None
    if "image" in diary:
        # 링크 형식일 경우 필요한 경로만 추출
        image_url = diary["image"]
        if image_url:
            parsed_image_url = image_url.split("s3.ap-northeast-2.amazonaws.com/")[-1]
            existing_temp_diary.image = parsed_image_url if parsed_image_url else None
        else:
            existing_temp_diary.image = None

    # 수정된 시간 기록
    existing_temp_diary.updated_at = datetime.now(timezone.utc)

    # 변경사항을 DB에 커밋
    db.commit()

    return {
        "status": 200,
        "message": "다이어리 임시 저장 성공",
        "data": {
            "temp_id": existing_temp_diary.id
        }
    }

@router.get("/temp/{temp_id}")
async def get_temp_diary(
    temp_id: int, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_current_user_id)
):
    # 현재 로그인한 유저 정보를 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    
    # temp_diary 정보 조회
    temp_diary = db.query(TempDiary).filter(
        TempDiary.id == temp_id,
        TempDiary.user_id == user_id,
        TempDiary.status == 0
    ).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="임시 다이어리를 찾을 수 없습니다.")

    # temp_diary와 관련된 가장 최근의 이미지 가져오기
    recent_image = db.query(Image).filter(
        Image.temp_diary_id == temp_id,
        Image.is_temp == 1,
        Image.is_deleted == False
    ).order_by(Image.created_at.desc()).first()

    # 필요한 데이터 반환 (NULL 값은 포함하지 않음)
    response_data = {}
    if temp_diary.id is not None:
        response_data["temp_id"] = temp_diary.id
    if temp_diary.date is not None:
        response_data["date"] = temp_diary.date
        target_date = temp_diary.date
    if user.nickname is not None:
        response_data["nickname"] = user.nickname
    if temp_diary.title is not None:
        response_data["title"] = temp_diary.title
    if temp_diary.mood is not None:
        response_data["mood"] = MoodEnum(temp_diary.mood).name.lower()
    if temp_diary.weather is not None:
        response_data["weather"] = WeatherEnum(temp_diary.weather).name.lower()
    if temp_diary.story is not None:
        response_data["story"] = temp_diary.story
    if temp_diary.image is not None:
        response_data["image"] = S3_BASE_URL + temp_diary.image
    

    # 기타 정보 추가
    daily_image_count = get_daily_image_count(db, user_id)
    image_count = get_image_count_for_date(db, user_id, target_date)
    response_data["remain_count"] = daily_image_count
    response_data["image_count"] = image_count

    return {
        "status": 200,
        "message": "임시 다이어리를 조회 완료.",
        "data": response_data
    }

@router.post("/cancel")
async def update_temp_diary_status(
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    try:
        formatted_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")

    user = db.query(User).filter(User.id == user_id).first()
    # user_id와 date가 일치하는 temp_diary 찾기
    temp_diary = db.query(TempDiary).filter(
        TempDiary.user_id == user_id,
        TempDiary.date == formatted_date,
        TempDiary.status == 0
    ).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="해당 날짜에 temp_diary가 존재하지 않습니다.")

    type = request.type
    if type == "write":
        # 상태를 True로 업데이트
        temp_diary.status = True
        temp_diary.updated_at = datetime.now()
        db.commit()
        return {
            "status": 200,
            "message": "상태가 업데이트되었습니다.",
            "data": {"temp_id": temp_diary.id}
        }
    elif type == "main":
        # 기존 temp_diary 상태를 True로 업데이트
        temp_diary.status = True
        temp_diary.updated_at = datetime.now()
        db.commit()

        # 새로운 TempDiary 생성
        new_temp_diary = TempDiary(
            user_id=user_id,
            date=formatted_date,
            title=None,
            weather=None,
            mood=None,
            nickname=user.nickname,
            image=None,
            status=False  # status를 False로 설정
        )
        db.add(new_temp_diary)
        db.commit()
        db.refresh(new_temp_diary)

        # 기존 temp_diary와 연결된 image들의 temp_diary_id를 새로운 new_temp_diary.id로 변경
        db.query(Image).filter(
            Image.temp_diary_id == temp_diary.id
        ).update({"temp_diary_id": new_temp_diary.id})
        db.commit()

        return {
            "status": 201,
            "message": "새로운 임시 다이어리가 생성되었습니다.",
            "data": {"temp_id": new_temp_diary.id}
        }

# /diaries?date=20240813
@router.get("")
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
            "data": {
                "temp_id": temp_diary.id,
                "is_temp_exist": True
            }
        }

    # 다이어리가 존재할 경우 다이어리의 내용을 바탕으로 임시 다이어리 생성
    if diary:
        new_temp_diary = TempDiary(
            user_id=user_id,
            diary_id=diary.id,  # 기존 다이어리 ID 추가
            date=formatted_date,
            title=diary.title,
            weather=diary.weather,
            mood=diary.mood,
            nickname=diary.nickname,
            story=diary.story
        )
        message = "기존 다이어리 내용을 기반으로 새 임시 다이어리가 생성되었습니다."
    else:
        # 다이어리가 없을 경우 빈 임시 다이어리 생성
        new_temp_diary = TempDiary(
            user_id=user_id,
            date=formatted_date,
            title=None,
            weather=None,
            mood=None,
            nickname=user.nickname,
            story=None
        )
        message = "임시 다이어리가 존재하지 않아 새로 생성되었습니다."
    
    db.add(new_temp_diary)
    db.commit()
    db.refresh(new_temp_diary)

    temp_diaries = db.query(TempDiary).filter(
        TempDiary.date == formatted_date,
        TempDiary.user_id == user_id
    ).all()

    # 각 TempDiary에 연결된 모든 이미지에 대해 temp_diary_id 업데이트
    for temp_diary in temp_diaries:
        images = db.query(Image).filter(Image.temp_diary_id == temp_diary.id).all()
        for image in images:
            image.temp_diary_id = new_temp_diary.id
            db.commit()

    return {
        "status": 200,
        "message": message,
        "data": {
            "temp_id": new_temp_diary.id,
            "is_temp_exist": False
        }
    }


import re

# /diaries/{id}
@router.delete("/{diary_id}")
async def delete_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 삭제할 다이어리 조회
    
    diary_to_delete = db.query(DiaryModel).filter(
        DiaryModel.id == diary_id,
        DiaryModel.is_deleted.is_(False)
    ).first()
    if not diary_to_delete:
        raise HTTPException(status_code=404, detail="Diary not found or already deleted")
    
    # 다이어리 소유자 확인
    if diary_to_delete.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this diary")
    first_image = db.query(Image).filter(
        Image.diary_id == diary_id,
        Image.is_deleted.is_(False)
    ).first()
    
    # 이미지가 없는 경우 바로 종료
    if not first_image or not first_image.image_url:
        raise HTTPException(status_code=404, detail="No associated images found for this diary")
    
    # {user_id}/{date} 추출
    match = re.search(r"^(\d+)/(\d{4}-\d{2}-\d{2})", first_image.image_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid image format")

    extracted_user_id = match.group(1)
    extracted_date = match.group(2)

    # 정확한 매칭을 위해 정규 표현식 사용
    images_to_delete = db.query(Image).filter(
        Image.image_url.op('REGEXP')(fr'^{extracted_user_id}/\d{{4}}-\d{{2}}-\d{{2}}/'),
        Image.is_deleted.is_(False)
    ).all()
    
    for image in images_to_delete:
        image.is_deleted = True

    # diary의 is_deleted 필드를 True로 설정 (논리적 삭제)
    diary_to_delete.is_deleted = True

    # 모든 변경 사항 커밋
    db.commit()

    return {
        "status": 200,
        "message": "다이어리 삭제 성공",
        "data": {
            "id": diary_id
        }
    }


@router.get("/search")
async def search_diary(
    keyword: str, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_current_user_id)
):
    if keyword == "":
        # 빈 키워드일 경우 모든 다이어리 조회
        diaries = db.query(DiaryModel).filter(
            DiaryModel.is_deleted == False,
            DiaryModel.user_id == user_id
        ).all()

        # 데이터 가공
        results = []
        for diary in diaries:
            image = db.query(Image).filter(
                Image.diary_id == diary.id,
                Image.is_active == True
            ).first()
            image_url = image.image_url if image else None
            results.append({
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),
                "title": diary.title,
                "image": S3_BASE_URL + image_url if image_url else None,
                "bookmark": diary.like,
            })

        return {
            "status": 200,
            "message": "모든 다이어리 조회 완료",
            "data": results,
        }

    # 키워드 검색
    diaries = db.query(DiaryModel).filter(
        (DiaryModel.title.like(f"%{keyword}%")) | 
        (DiaryModel.story.like(f"%{keyword}%")),
        DiaryModel.is_deleted == False,
        DiaryModel.user_id == user_id
    ).all()

    if not diaries:
        return {
            "status": 200,
            "message": f"'{keyword}'에 대한 검색 결과가 없습니다.",
            "data": []
        }

    # 데이터 가공
    results = []
    for diary in diaries:
        image = db.query(Image).filter(
            Image.diary_id == diary.id,
            Image.is_active == True,
            Image.is_temp == True
        ).first()
        image_url = image.image_url if image else None
        results.append({
            "id": diary.id,
            "date": diary.date.strftime("%Y-%m-%d"),
            "title": diary.title,
            "image": S3_BASE_URL + image_url if image_url else None,
            "bookmark": diary.like,
        })

    return {
        "status": 200,
        "message": f"'{keyword}'에 관한 다이어리 조회 완료",
        "data": results,
    }

def get_datetime_by_date(date):
    return datetime.strptime(date, "%Y%m%d")

@router.get("/main")
async def get_diaries(
    type: str,
    date: str = None,
    start: str = None,
    end: str = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # type이 'list'일 때 'date' 파라미터 확인
    if type == "list":
        if not date:
            raise HTTPException(
                status_code=400,
                detail="type이 'list'일 때는 'date' 파라미터가 필요합니다."
            )
        try:
            start_date = datetime.strptime(date, "%Y%m")
            end_date = start_date + relativedelta(months=1, days=-1)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="잘못된 date 형식입니다. 'YYYYMM' 형식을 사용하세요."
            )

    # type이 'calendar'일 때 'start'와 'end' 파라미터 확인
    elif type == "calendar":
        if not start or not end:
            raise HTTPException(
                status_code=400,
                detail="type이 'calendar'일 때는 'start'와 'end' 파라미터가 필요합니다."
            )
        try:
            start_date = datetime.strptime(start, "%Y%m%d")
            end_date = datetime.strptime(end, "%Y%m%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="잘못된 날짜 형식입니다. 'YYYYMMDD' 형식을 사용하세요."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="잘못된 type 값입니다. 'list' 또는 'calendar'를 사용하세요."
        )

    # 다이어리 조회 쿼리 (LEFT JOIN 사용하여 이미지가 없을 때도 포함)
    diaries_query = (
        db.query(DiaryModel)
        .filter(
            DiaryModel.date.between(start_date, end_date),
            DiaryModel.is_deleted == False,
            DiaryModel.user_id == user_id,
        ).options(joinedload(DiaryModel.images))  # 이미지 로드
    )

    # type에 따른 정렬
    if type == "calendar":
        diaries_query = diaries_query.order_by(DiaryModel.date.asc())
    elif type == "list":
        diaries_query = diaries_query.order_by(DiaryModel.date.desc())

    # 쿼리 실행
    diaries = diaries_query.all()

    result = []
    for diary in diaries:
        # 이미지 필터링
        images = [img for img in diary.images if img.is_temp == 1]  # is_temp가 1인 이미지만 포함
        image_url = S3_BASE_URL + images[0].image_url if images else None  # 첫 번째 이미지 URL

        diary_data = {
            "id": diary.id,
            "date": diary.date.strftime("%Y-%m-%d"),
            "title": diary.title,
            "image": image_url,
            "bookmark": diary.like,
        }
        result.append(diary_data)

    return {
        "status": 200,
        "message": f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} 기간에 대한 메인 페이지 조회 완료",
        "data": result,
    }



# 전체/월별
# /diaries/like 
# 좋아요를 누른 다이어리들 조회 API
@router.get("/like")
async def get_like_diaries(type: str, date: str = None, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)): 
    if type == "month" and date and len(date) == 6:
        year = int(date[:4])
        month = int(date[4:])
        last_day = monthrange(year, month)[1]
        
        # Query liked diaries for the specified month and year, ordered by date in descending order
        liked_diaries = db.query(DiaryModel).filter(
            DiaryModel.like == True,
            DiaryModel.user_id == user_id,  # user_id matches
            DiaryModel.is_deleted == False,  # only non-deleted diaries
            DiaryModel.date.between(f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}")  # correct date range
        ).order_by(DiaryModel.date.desc()).all()  # order by date descending
        
        if not liked_diaries:            
            return {
                "status": 200,
                "message": "해당 월에 좋아요를 누른 다이어리가 없습니다.",
                "data": []
            }

        # Prepare the response in the desired format
        result = []
        for diary in liked_diaries:
            # Fetch image URL (get only the first one)
            image = db.query(Image).filter(
                Image.diary_id == diary.id,
                Image.is_active == True,
                Image.is_deleted == False,
                Image.is_temp == True
            ).first()  # get the first image
            image_url = image.image_url if image else None
            result.append({
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),
                "title": diary.title,
                "image": S3_BASE_URL + image_url if image_url else None,  # single image URL or None
                "bookmark": 1 if diary.like else 0  # bookmark as 1 or 0
            })
        
        return {
            "status": 200,
            "message": f"{year}년 {month}월 좋아요 누른 일기 조회 완료",
            "data": result,
        }

    elif type == "all":
        # Query all liked diaries, ordered by date in descending order
        liked_diaries = db.query(DiaryModel).filter(
            DiaryModel.like == True,
            DiaryModel.is_deleted == False,  # only non-deleted diaries
            DiaryModel.user_id == user_id,  # user_id matches
        ).order_by(DiaryModel.date.desc()).all()  # order by date descending
    
        if not liked_diaries:            
            return {
                "status": 200,
                "message": "좋아요를 누른 다이어리가 없습니다.",
                "data": []
            }
        
        # Prepare the response
        result = []
        for diary in liked_diaries:
            # Fetch image URL (get only the first one)
            image = db.query(Image).filter(
                Image.diary_id == diary.id,
                Image.is_active == True,
                Image.is_deleted == False,
                Image.is_temp == True
            ).first()  # get the first image
            image_url = image.image_url if image else None
            result.append({
                "id": diary.id,
                "date": diary.date.strftime("%Y-%m-%d"),
                "title": diary.title,
                "image": S3_BASE_URL + image_url if image_url else None,  # single image URL or None
                "bookmark": True if diary.like else False  # bookmark as True or False
            })
        
        return {
            "status": 200,
            "message": "모든 좋아요를 누른 일기 조회 완료",
            "data": result,
        }

@router.get("/{id}")
async def get_diary(id: int, edit: Optional[bool] = None, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # 1. 다이어리를 조회
    diary = db.query(DiaryModel).filter(DiaryModel.id == id, DiaryModel.is_deleted == False).first()
    user = db.query(User).filter(User.id == user_id).first()

    if not diary:
        raise HTTPException(status_code=404, detail=f"{id}번 다이어리를 찾을 수 없습니다.")
    
    # edit 파라미터에 따라 이미지를 조회하는 방법이 달라집니다.
    if not edit:
        # edit=False일 때는 is_temp가 True인 이미지를 가져옵니다.
        image = db.query(Image).filter(
            Image.diary_id == diary.id,
            Image.is_temp == True,
            Image.is_deleted == False
        ).first()  # 첫 번째 결과만 가져오기
    else:
        # edit=True일 때는 기존 temp_diary와 연결된 모든 이미지들을 가져옵니다.
        temp_diary_images = db.query(Image).filter(
            Image.temp_diary_id == diary.id,
            Image.is_temp == True,
            Image.is_deleted == False
        ).all()  # 모든 관련 이미지를 가져오기

    try:
        # mood와 weather 값을 Enum을 통해 문자열로 변환하여 반환
        mood = MoodEnum(diary.mood).name
        weather = WeatherEnum(diary.weather).name
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mood or weather value")
    
    # 이미지 URL이 없으면 None으로 설정
    image_url = image.image_url if not edit and image else None

    # 2. edit 파라미터가 없거나 false일 때는 다이어리만 반환
    if not edit:
        return {
            "status": 200,
            "message": f"{id}번 다이어리 조회 완료",
            "data": {
                "id": diary.id,
                "date": diary.date,
                "nickname": diary.nickname,
                "mood": mood,
                "weather": weather,
                "title": diary.title,
                "image": S3_BASE_URL + image_url if image_url else None,  # single image URL or None
                "story": diary.story,
                "bookmark": diary.like
            }
        }
    
    # 3. edit=true일 경우, 기존 temp_diary 상태를 업데이트하고 새로운 임시 다이어리 생성
    db.query(TempDiary).filter(
        TempDiary.date == diary.date,
        TempDiary.user_id == user.id
    ).update({"status": 1})
    db.commit()

    temp_diary_image = db.query(Image).filter(
        Image.diary_id == diary.id,
        Image.is_temp == True,
        Image.is_deleted == False
    ).first()

    # 만약 is_temp 이미지가 있으면 그 image_url을 temp_diary에 저장
    temp_diary_image_url = temp_diary_image.image_url if temp_diary_image else None

    temp_diary = TempDiary(
        diary_id=diary.id,
        user_id=user.id,
        date=diary.date,
        nickname=user.nickname,
        mood=diary.mood,
        weather=diary.weather,
        title=diary.title,
        image=temp_diary_image_url,
        story=diary.story,
        like=diary.like
    )
    db.add(temp_diary)
    db.commit()
    db.refresh(temp_diary)

    # 4. 기존 temp_diary와 연결된 모든 이미지들의 temp_diary_id를 새로운 temp_diary로 업데이트
    temp_diaries = db.query(TempDiary).filter(TempDiary.diary_id == diary.id).all()
    for temp in temp_diaries:
        temp_images = db.query(Image).filter(
            Image.temp_diary_id == temp.id,
            Image.is_deleted == False
        ).all()  # 해당 temp_diary와 연결된 모든 이미지들을 가져옵니다.
        for img in temp_images:
            img.temp_diary_id = temp_diary.id  # 새로 생성된 temp_diary_id로 업데이트
        db.commit()

    # 5. 임시 다이어리의 temp_id와 함께 응답
    return {
        "status": 200,
        "message": f"{id}번 다이어리 수정 준비 완료",
        "data": {
            "temp_id": temp_diary.id  # 새로 생성된 temp_id 반환
        },
    }

@router.put("/like/{diary_id}")
async def like_diary(diary_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    diary = db.query(DiaryModel).filter(DiaryModel.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")
    
    if diary.user_id != user_id:
        raise HTTPException(status_code=403, detail="해당 사용자가 아닙니다.")
    
    # 좋아요 상태를 토글
    diary.like = not diary.like
    db.commit()
    
    # 좋아요 상태에 따라 메시지 변경
    if diary.like:
        return {
            "status": 200,
            "message": "좋아요 등록이 성공하였습니다.",
            "data": {
                "id": diary.id,
                "bookmark": diary.like
            }
        }
    else:
        return {
            "status": 200,
            "message": "좋아요 등록이 취소되었습니다.",
            "data": {
                "id": diary.id,
                "bookmark": diary.like
            }
        }

@router.post("/share")
async def share_diary_image(
    request: ShareImageRequest,  # 요청 본문으로 받기
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    
    if "," in request.image:
        image_data = request.image.split(",")[1]
    else:
        image_data = request.image
        
    try:
        image_data = base64.b64decode(image_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data")
    
    # S3에 이미지 업로드
    s3_url = upload_image_to_s3(image_data, user_id)
    
    # 이미지 URL과 정보를 데이터베이스에 저장
    new_image = Image(
        diary_id=request.diary_id,
        temp_diary_id=None,  # 필요 시 temp_diary_id를 설정
        image_url=s3_url,
        created_at=datetime.utcnow(),
        is_temp=False,
        is_active=True,
        is_deleted=False
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)  # 새로 추가된 이미지 정보를 새로고침하여 얻음

    return {
        "status": "success",
        "message": "Image uploaded and saved successfully",
        "data": {
            "image_url": S3_BASE_URL + s3_url
        }
    }