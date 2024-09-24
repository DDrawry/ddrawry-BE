from fastapi import APIRouter, HTTPException, Cookie, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import httpx
import os
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, Token  # User와 Token 모델 import
from app.database import get_db  # DB 세션을 가져오는 함수를 import합니다.

router = APIRouter(prefix="/auth")

load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")  # JWT 비밀키
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60  # JWT 토큰 유효 시간

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
async def kakao_callback(code: str, db: Session = Depends(get_db)):
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

        # 사용자 정보 요청
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.get(user_info_url, headers=user_headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail="Failed to get user info")
        
        user_info = user_response.json()
        kakao_id = user_info.get("id")
        nickname = user_info.get("properties", {}).get("nickname")

        # DB에 사용자 정보 저장
        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        if user:
            # 기존 사용자라면 액세스 토큰 업데이트
            token_entry = db.query(Token).filter(Token.user_id == user.user_id).first()
            if token_entry:
                if await is_token_valid(token_entry.token):
                    access_token = token_entry.token  # 유효한 토큰 사용
                else:
                    access_token = await refresh_access_token(token_entry.token)  # 새로운 토큰 요청
                    token_entry.token = access_token  # DB에서 업데이트
            else:
                new_token = Token(user_id=user.user_id, token=access_token, created_at=datetime.now())
                db.add(new_token)
        else:
            # 신규 사용자 등록
            user = User(kakao_id=kakao_id, nickname=nickname, created_at=datetime.now())
            db.add(user)
            db.commit()
            db.refresh(user)

            # 신규 사용자에 대한 액세스 토큰 저장
            new_token = Token(user_id=user.user_id, token=access_token, created_at=datetime.now())
            db.add(new_token)

        db.commit()  # 모든 변경 사항 저장

        # JWT 토큰 생성
        jwt_payload = {
            "user_id": user.user_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES),
        }
        jwt_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = JSONResponse(content={"message": "Login successful"})
        response.set_cookie(key="jwt_token", value=jwt_token, httponly=True, max_age=3600)  # JWT 토큰 쿠키에 저장
        return response

@router.get("/kakao/logout")
async def kakao_logout(response: Response, jwt_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not jwt_token:
        raise HTTPException(status_code=401, detail="JWT 토큰이 없습니다.")

    # JWT 토큰 검증
    try:
        payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.user_id == user_id).first()
    except (jwt.ExpiredSignatureError, jwt.JWTError):
        raise HTTPException(status_code=401, detail="Invalid JWT token")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Token 테이블에서 Kakao 액세스 토큰 가져오기
    token_entry = db.query(Token).filter(Token.user_id == user.user_id).first()
    if not token_entry:
        raise HTTPException(status_code=404, detail="Token not found")

    # 카카오 로그아웃 요청
    kakao_logout_url = "https://kapi.kakao.com/v1/user/unlink"
    headers = {"Authorization": f"Bearer {token_entry.token}"}  # DB에서 Kakao 액세스 토큰 가져오기

    async with httpx.AsyncClient() as client:
        logout_response = await client.post(kakao_logout_url, headers=headers)

        if logout_response.status_code != 200:
            raise HTTPException(status_code=logout_response.status_code, detail="Kakao 로그아웃에 실패했습니다.")

        # JWT 토큰 쿠키 삭제
        response.delete_cookie(key="jwt_token")

        # Token 테이블에서 해당 사용자의 액세스 토큰 삭제 (선택적)
        db.delete(token_entry)
        db.commit()

        return {"message": "Kakao에서 성공적으로 로그아웃되었습니다."}

async def is_token_valid(token: str) -> bool:
    token_info_url = "https://kapi.kakao.com/v1/user/access_token_info"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(token_info_url, headers=headers)
        return response.status_code == 200
    
async def refresh_access_token(refresh_token: str) -> str:
    kakao_refresh_url = "https://kauth.kakao.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_CLIENT_ID,
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(kakao_refresh_url, headers=headers, data=data)
        if response.status_code == 200:
            token_json = response.json()
            return token_json.get("access_token")
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to refresh access token")

