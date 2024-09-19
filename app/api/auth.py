from fastapi import APIRouter, HTTPException, Cookie, Response
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv


import httpx
import os

router = APIRouter(prefix="/auth")

load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

@router.get("/kakao/login")
def kakao_login():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={KAKAO_CLIENT_ID}&"
        f"redirect_uri={KAKAO_REDIRECT_URI}&"
        f"response_type=code"
    )
    return RedirectResponse(url=kakao_auth_url)

@router.get("/kakao/callback")
async def kakao_callback(code: str):
    kakao_token_url = "https://kauth.kakao.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(kakao_token_url, headers=headers, data=data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=token_response.status_code, detail="Failed to get Kakao token")
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        response = JSONResponse(content={"message": "Login successful"})
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=3600)  # Set cookie with token
        return response



@router.get("/kakao/logout")
async def kakao_logout(response: Response, access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Access token이 없습니다.")

    print(f"Access Token: {access_token}")  # 액세스 토큰 출력

    kakao_logout_url = "https://kapi.kakao.com/v1/user/logout"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        logout_response = await client.post(kakao_logout_url, headers=headers)
        
        if logout_response.status_code != 200:
            raise HTTPException(status_code=logout_response.status_code, detail="Kakao 로그아웃에 실패했습니다.")
        
        # 쿠키에서 액세스 토큰 삭제
        response.delete_cookie(key="access_token")

        return {"message": "Kakao에서 성공적으로 로그아웃되었습니다."}
