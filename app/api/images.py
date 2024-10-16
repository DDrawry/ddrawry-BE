from dotenv import load_dotenv
from fastapi import APIRouter

import os
import openai

router = APIRouter(prefix="/images")

load_dotenv()

api_key = os.getenv("OPENAI_TEST_KEY")
client = openai.OpenAI(api_key=api_key)


@router.get("/")
async def get_images():
    response = client.images.generate(
        prompt='Draw a simple, playful drawing in the style of a young child. The picture shows a day at the park with family. The trees are beautifully colored in red and yellow. We laid down a picnic blanket and enjoyed delicious food. The sun was shining warmly, and the breeze was refreshing. We saw butterflies flying around, and we picked up acorns under the trees. It was such a fun day! The lines should be wobbly and imperfect, with bright colors and minimal details, giving it a carefree, childlike feel.',
        n=1,
        model="dall-e-2",
        size="1024x1024",
    )
    image_url = response.data[0].url
    return {"message": api_key, "image": image_url}
