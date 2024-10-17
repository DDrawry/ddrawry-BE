from fastapi import APIRouter, HTTPException, Cookie, Response, Depends, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import httpx
import os
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, Token  # User와 Token 모델 import
from app.database import get_db  # DB 세션을 가져오는 함수를 import합니다.
from app.utils import get_current_user_id

router = APIRouter(prefix="/auth")

load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")  # JWT 비밀키
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 300  # JWT 토큰 유효 시간 1분으로 설정 (테스트용)
JWT_REFRESH_EXPIRATION_MINUTES = 60  # JWT 리프레시 토큰 유효 시간 60분


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
    # Kakao API 토큰 요청 URL
    kakao_token_url = "https://kauth.kakao.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }

    # Kakao 토큰 요청
    async with httpx.AsyncClient() as client:
        token_response = await client.post(kakao_token_url, headers=headers, data=data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=token_response.status_code, detail="Failed to get Kakao token")

        token_json = token_response.json()
        kakao_access_token = token_json.get("access_token")
        print("Token Response:", token_response.status_code, token_response.text)

        # 사용자 정보 요청
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {kakao_access_token}"}
        user_response = await client.get(user_info_url, headers=user_headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=user_response.status_code, detail="Failed to get user info")

        user_info = user_response.json()
        kakao_id = user_info.get("id")
        nickname = user_info.get("properties", {}).get("nickname")

        print("User ID:", user.id)
        print("Kakao ID:", kakao_id)
        print("Nickname:", nickname)

        # DB에 사용자 정보 저장
        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        if user:
            # 기존 토큰을 삭제하지 않고 새로 추가
            new_token = Token(user_id=user.id, token=kakao_access_token, created_at=datetime.now())
            db.add(new_token)
        else:
            # 새로운 사용자 생성
            user = User(kakao_id=kakao_id, nickname=nickname, created_at=datetime.now())
            db.add(user)
            db.commit()  # 사용자 정보를 DB에 저장
            db.refresh(user)  # 방금 추가한 사용자 정보를 새로고침

            new_token = Token(user_id=user.id, token=kakao_access_token, created_at=datetime.now())
            db.add(new_token)

        db.commit()  # 모든 변경 사항 저장

        # JWT 액세스 토큰 생성
        jwt_access_payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES),
        }
        access_token = jwt.encode(jwt_access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # JWT 리프레시 토큰 생성
        jwt_refresh_payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_REFRESH_EXPIRATION_MINUTES),
        }
        refresh_token = jwt.encode(jwt_refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # 쿠키에 JWT 저장
        response = JSONResponse(content={"message": "Login successful"})
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=60)  # JWT 액세스 토큰 쿠키에 저장
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, max_age=3600 * 24 * 30)  # JWT 리프레시 토큰을 쿠키에 저장
        return response
    

@router.get("/kakao/logout")
async def kakao_logout(response: Response, access_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not access_token:
        raise HTTPException(status_code=401, detail="JWT 토큰이 없습니다.")

    # JWT 토큰 검증
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()  # 변경된 부분
    except (jwt.ExpiredSignatureError, jwt.JWTError):
        raise HTTPException(status_code=401, detail="Invalid JWT token")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Token 테이블에서 Kakao 액세스 토큰 가져오기 (가장 최근의 유효한 토큰)
    token_entry = db.query(Token).filter(Token.user_id == user.id, Token.expires_at.is_(None)).order_by(Token.created_at.desc()).first()  # 변경된 부분
    if not token_entry:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # 카카오 로그아웃 요청
    kakao_logout_url = "https://kapi.kakao.com/v1/user/unlink"
    headers = {"Authorization": f"Bearer {token_entry.token}"}

    async with httpx.AsyncClient() as client:
        logout_response = await client.post(kakao_logout_url, headers=headers)

        if logout_response.status_code != 200:
            raise HTTPException(status_code=logout_response.status_code, detail="Kakao 로그아웃에 실패했습니다.")

        # JWT 토큰 쿠키 삭제
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")

        # Token 테이블에서 해당 사용자의 액세스 토큰 만료 시간 기록
        token_entry.expires_at = datetime.now()  # 로그아웃 시간을 expires_at에 설정
        db.commit()

        return {"message": "Kakao에서 성공적으로 로그아웃되었습니다."}    

from jwt import PyJWTError  # PyJWTError를 import
@router.get("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        # 리프레시 토큰 디코드
        refresh_payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = refresh_payload.get("user_id")

        # 새로운 액세스 토큰 생성
        new_access_payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES),
        }
        new_access_token = jwt.encode(new_access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # 새로운 액세스 토큰을 쿠키에 저장
        response = JSONResponse(content={"access_token": new_access_token})  # JSON 응답 생성
        response.set_cookie(key="access_token", value=new_access_token, httponly=True, max_age=60)

        return response  # 쿠키와 JSON 응답을 함께 반환
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")



@router.delete("/", response_model=dict)
async def delete_user(
    user_id: int = Depends(get_current_user_id),  # 현재 사용자의 user_id 가져오기
    db: Session = Depends(get_db)
):
    # 1. User 찾기
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. delete_at 필드를 현재 시각으로 업데이트
    user.delete_at = datetime.now()
    
    # 3. 해당 유저와 연결된 Token의 expire_at 업데이트 (예: 1시간 후로 설정)
    tokens = db.query(Token).filter(Token.user_id == user_id).all()
    for token in tokens:
        token.expires_at = datetime.now()  # expire_at을 1시간 후로 설정
    
    # 4. 변경 사항 저장
    db.commit()
    
    return {"status": 200, 
            "message": "유저 데이터가 삭제되었습니다.", 
            "data": {
                "id": user_id,        
        }}



def is_valid_token(token: str) -> bool:
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True  # 유효한 토큰
    except (jwt.ExpiredSignatureError, PyJWTError):  # 여기서 PyJWTError로 변경
        return False  # 유효하지 않은 토큰