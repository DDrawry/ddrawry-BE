from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import openai

router = APIRouter(prefix="/images")

load_dotenv()

api_key = os.getenv("OPENAI_TEST_KEY")
openai.api_key = api_key  # api_key를 openai 모듈에 직접 설정

class ImageRequest(BaseModel):
    story: str  # 프론트에서 전달받을 다이어리 내용

@router.post("")
async def generate_image_and_translate(request: ImageRequest):
    # 다이어리 내용을 프롬프트에 삽입하여 번역 요청
    story_cleaned = request.story.strip()

    try:
        # OpenAI API로 번역 요청
        translation_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Translate the following text to English: {story_cleaned}"}]
        )
        translated_text = translation_response['choices'][0]['message']['content'].strip()

        # 번역된 텍스트를 사용하여 이미지 생성 요청
        # 다이어리 내용을 프롬프트에 삽입
        prompt = f"Draw a simple, playful drawing in the style of a young child. The picture shows: {translated_text}. The lines should be wobbly and imperfect, with bright colors and minimal details, giving it a carefree, childlike feel."

        # 여기에서 await를 사용하지 않고 create 호출
        image_response = openai.Image.create(  # OpenAI API 호출
            prompt=prompt,
            n=1,
            model="dall-e-2",
            size="1024x1024",
        )
        image_url = image_response['data'][0]['url']
        return {"status": 200, 
                "message": "Image generated successfully", 
                "data": {
                   "image": image_url
                   }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during translation or image generation: {str(e)}")
    


@router.post("/trans")
async def generate_image_and_translate(request: ImageRequest):
    # 다이어리 내용을 프롬프트에 삽입하여 번역 요청
    story_cleaned = request.story.strip()
    # OpenAI API로 번역 요청
    translation_response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Translate the following text to English: {story_cleaned}"}]
    )
    translated_text = translation_response['choices'][0]['message']['content'].strip()

    return {translated_text}