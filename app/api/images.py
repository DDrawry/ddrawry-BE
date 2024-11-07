from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from openai import OpenAI
from ..utils import get_current_user_id, generate_and_upload_image_to_s3


router = APIRouter(prefix="/images")

load_dotenv()

api_key = os.getenv("OPENAI_TEST_KEY")
client = OpenAI(api_key=api_key)



class ImageRequest(BaseModel):
    story: str  # 프론트에서 전달받을 다이어리 내용
    date: str  # 예시: '2024-11-07'


@router.post("")
async def generate_and_upload_image(request: ImageRequest): #user_id: int = Depends(get_current_user_id)):
    story_cleaned = request.story.strip()

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
        return await generate_and_upload_image_to_s3(image_url, user_id=1, date=request.date)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during image generation or upload: {str(e)}")


class CopyRequest(BaseModel):
    date: str  # YYYY-MM-DD 형식으로 날짜 입력
