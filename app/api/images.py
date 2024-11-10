from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from openai import OpenAI
from ..utils import get_current_user_id, generate_and_upload_image_to_s3, get_daily_image_count, get_image_count_for_date
from ..database import get_db
from app.models import TempDiary, Image
from datetime import datetime


from sqlalchemy.orm import Session



router = APIRouter(prefix="/images")

load_dotenv()

S3_BASE_URL= os.getenv("S3_BASE_URL")
api_key = os.getenv("OPENAI_TEST_KEY")
client = OpenAI(api_key=api_key)



class ImageRequest(BaseModel):
    temp_id: int
    story: str  # 프론트에서 전달받을 다이어리 내용

def get_tempdiary_by_id(db: Session, temp_id: int):
    return db.query(TempDiary).filter(TempDiary.id == temp_id).first()


@router.post("")
async def generate_and_upload_image(request: ImageRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    story_cleaned = request.story.strip()
    remaining_count = get_daily_image_count(db, user_id)

    if remaining_count == 0:
        raise HTTPException(status_code=400, detail="Daily image creation limit reached. Please try again tomorrow.")

    # temp_id로 tempdiary에서 date 값을 조회
    tempdiary = get_tempdiary_by_id(db, request.temp_id)
    if not tempdiary:
        raise HTTPException(status_code=404, detail="TempDiary not found")
    
    # temp_diary의 status가 1인 경우 오류 발생
    if tempdiary.status == 1:
        raise HTTPException(status_code=400, detail="임시다이어리가 존재하지 않습니다.")
    
    # date를 "YYYY-MM-DD" 형식으로 변환
    date = tempdiary.date.strftime("%Y-%m-%d")

    try:
        # OpenAI API로 번역 및 이미지 생성 요청 (이미지 URL 받기)
        translation_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Translate the following text to English: {story_cleaned}"}]
        )
        translated_text = translation_response.choices[0].message.content.strip()
        
        # 이미지를 생성하는 요청 (DALL-E 등 사용)
        image_response = client.images.generate(
            model="dall-e-2",
            prompt=f"Create a playful, childlike illustration based on the following story: '{translated_text}'.",
            n=1,
            size="1024x1024",
        )

        # 이미지 URL을 받아서 S3에 업로드
        image_url = image_response.data[0].url
        s3_image_response = await generate_and_upload_image_to_s3(image_url, user_id=user_id, date=date)

        # S3 URL에서 경로만 추출 (예: /1/2024-11-17/1.jpg)
        relative_image_url = s3_image_response["data"]["image_url"].replace("s3://your-s3-bucket/", "")

        # 생성된 이미지 정보를 Image 모델에 저장
        new_image = Image(
            temp_diary_id=request.temp_id,  # temp_id로 해당 temp_diary와 연결
            image_url=relative_image_url,  # 경로만 저장
            created_at=datetime.utcnow(),  # 생성 시간
            is_temp=False  # 임시 이미지로 설정 (필요시 수정)
        )
        db.add(new_image)
        db.commit()  # DB에 저장

        return {
            "status": 200,
            "message": "Image generated and uploaded successfully, saved to database",
            "data": {
                "image_url": S3_BASE_URL + relative_image_url,
                "remain_count": remaining_count
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during image generation or upload: {str(e)}")
    
@router.get("/{temp_id}")
async def get_images_by_temp_id(temp_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # temp_diary 정보를 찾기
    temp_diary = db.query(TempDiary).filter(TempDiary.id == temp_id).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="TempDiary not found")

    # temp_diary에서 user_id와 date를 가져옴
    date = temp_diary.date.strftime("%Y-%m-%d")  # date를 "YYYY-MM-DD" 형식으로 변환

    # 해당 user_id와 date에 해당하는 이미지 URL들을 찾음
    images = db.query(Image).filter(
        Image.temp_diary_id == temp_id,
        Image.image_url.like(f"{user_id}/{date}%"),  # image_url이 {user_id}/{date}로 시작하는 이미지만 찾기
        Image.is_active == True,  # 활성화된 이미지만 찾기
        Image.is_deleted == False  # 삭제되지 않은 이미지만 찾기
    ).all()

    # 이미지가 없으면 빈 배열 반환
    if not images:
        return {
            "status": 200,
            "message": "그림 목록 조회 성공",
            "data": []
        }

    # 기본 데이터 구조
    response_data = []
    main_image_info = None  # main_image 정보를 저장할 변수

    for index, image in enumerate(images):
        image_url = S3_BASE_URL + image.image_url  # 이미지 URL을 합침

        # main_image를 가장 먼저 추가
        if image.is_temp:
            main_image_info = {"id": image.id, "image": image_url}  # main_image로 설정
        else:
            response_data.append({"id": image.id, "image": image_url})  # temp_image로 설정

    # main_image가 존재하면 response_data의 앞에 추가
    if main_image_info:
        response_data.insert(0, main_image_info)  # main_image 정보를 리스트의 첫 번째에 추가

    return {
        "status": 200,
        "message": "그림 목록 조회 성공",
        "data": response_data
    }


@router.delete("/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    # 삭제할 이미지 찾기
    image = db.query(Image).filter(Image.id == image_id, Image.is_deleted == False).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found or already deleted")

    # 이미지 삭제 표시
    image.is_deleted = True
    db.commit()

    # 해당 이미지의 TempDiary와 날짜 조회
    temp_diary = db.query(TempDiary).filter(TempDiary.id == image.temp_diary_id).first()
    if not temp_diary:
        raise HTTPException(status_code=404, detail="Associated TempDiary not found")

    # 날짜별 남아있는 이미지 수 조회
    image_count = get_image_count_for_date(db, user_id, temp_diary.date)

    return {
        "status": 200,
        "message": "Image deleted successfully",
        "data": {
            "image_count": image_count
        }
    }

