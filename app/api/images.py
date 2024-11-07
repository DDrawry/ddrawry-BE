from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from openai import OpenAI
from ..utils import get_current_user_id, generate_and_upload_image_to_s3
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
async def generate_and_upload_image(request: ImageRequest, db: Session = Depends(get_db), ): #user_id: int = Depends(get_current_user_id)):
    story_cleaned = request.story.strip()

    # temp_id로 tempdiary에서 date 값을 조회
    tempdiary = get_tempdiary_by_id(db, request.temp_id)
    if not tempdiary:
        raise HTTPException(status_code=404, detail="TempDiary not found")
    
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
        s3_image_response = await generate_and_upload_image_to_s3(image_url, user_id=1, date=date)

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
                "image_url": S3_BASE_URL + relative_image_url
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during image generation or upload: {str(e)}")


class CopyRequest(BaseModel):
    date: str  # YYYY-MM-DD 형식으로 날짜 입력
