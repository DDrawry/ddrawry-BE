from fastapi import APIRouter, HTTPException, Cookie, Response, Depends, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import os
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, Token, Setting  # User와 Token 모델 import
from app.database import get_db  # DB 세션을 가져오는 함수를 import합니다.
from app.utils import get_current_user_id

router = APIRouter(prefix="/auth")

load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")  # JWT 비밀키
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30  # JWT 토큰 유효 시간 30분
JWT_REFRESH_EXPIRATION_MINUTES = 60  # JWT 리프레시 토큰 유효 시간 60분
LOCAL_REDIRECT_URI = os.getenv("LOCAL_REDIRECT_URI")
PROD_REDIRECT_URI = os.getenv("PROD_REDIRECT_URI")

@router.get("/kakao/callback")
async def kakao_callback(code: str, request: Request, response: Response, db: Session = Depends(get_db)):
    kakao_token_url = "https://kauth.kakao.com/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    redirect_uri = LOCAL_REDIRECT_URI if "dev" in request.query_params else PROD_REDIRECT_URI

    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        token_response = await client.post(kakao_token_url, headers=headers, data=data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Kakao 토큰 요청 실패")

        token_json = token_response.json()
        kakao_access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")  # 리프레시 토큰 저장

        user_info_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {kakao_access_token}"}
        user_response = await client.get(user_info_url, headers=user_headers)

        if user_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Kakao 사용자 정보 요청 실패")

        user_info = user_response.json()
        kakao_id = user_info.get("id")
        nickname = user_info.get("properties", {}).get("nickname")

        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        if user:
            # 기존 사용자인 경우 설정 확인
            setting = db.query(Setting).filter(Setting.user_id == user.id).first()
            if not setting:
                setting = Setting(user_id=user.id, dark_mode=False, notification=True, created_at=datetime.now())
                db.add(setting)

            existing_tokens = db.query(Token).filter(
                Token.user_id == user.id, 
                Token.expires_at.is_(None)
            ).all()
            
            for token in existing_tokens:
                token.expires_at = datetime.now()  # 만료 시간 기록
        else:
            user = User(kakao_id=kakao_id, nickname=nickname, created_at=datetime.now())
            db.add(user)
            db.commit()
            db.refresh(user)

            setting = Setting(user_id=user.id, dark_mode=False, notification=True, created_at=datetime.now())
            db.add(setting)

        # 새로운 액세스 토큰과 리프레시 토큰 저장
        new_token = Token(
            user_id=user.id,
            token=kakao_access_token,  # 엑세스 토큰 저장
            refresh_token=refresh_token,  # 리프레시 토큰 저장
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=6)  # 6시간 후 만료
        )
        db.add(new_token)
        db.commit()

        # JWT 토큰 생성
        jwt_access_payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES),
        }
        access_token = jwt.encode(jwt_access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        jwt_refresh_payload = {
            "user_id": user.id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_REFRESH_EXPIRATION_MINUTES),  # 1시간으로 설정
        }
        refresh_token = jwt.encode(jwt_refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=24 * 60 * 60,
            samesite="none",
            secure=True
        )

        return {
            "status": 200,
            "message": "토큰 발급 성공",
            "data": {
                "access_token": access_token,
            }
        }

@router.get("/kakao/logout")
async def kakao_logout(
    request: Request, 
    response: Response, 
    user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        refresh_payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = refresh_payload.get("user_id")

        token_entry = db.query(Token).filter(Token.user_id == user_id).order_by(Token.created_at.desc()).first()
        if not token_entry:
            raise HTTPException(status_code=404, detail="Access token not found")

        kakao_access_token = token_entry.token

        kakao_logout_url = "https://kapi.kakao.com/v1/user/unlink"
        headers = {"Authorization": f"Bearer {kakao_access_token}"}

        async with httpx.AsyncClient() as client:
            logout_response = await client.post(kakao_logout_url, headers=headers)

            if logout_response.status_code != 200:
                raise HTTPException(status_code=401, detail="KaKao 액세스 토큰 만료되었습니다.")

        response.delete_cookie(key="refresh_token")
        db.commit()

        return {"message": "Kakao에서 성공적으로 로그아웃되었습니다."} 
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/kakao/refresh")
async def kakao_refresh_token(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # 1. DB에서 특정 사용자의 카카오 리프레시 토큰 조회
    token_entry = db.query(Token).filter(Token.user_id == user_id).first()
    if not token_entry or not token_entry.refresh_token:
        raise HTTPException(status_code=404, detail="Token not found for the user")

    refresh_token = token_entry.refresh_token

    try:
        # 2. 카카오 리프레시 토큰을 사용하여 새로운 카카오 액세스 토큰 요청
        kakao_token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": KAKAO_CLIENT_ID,
            "refresh_token": refresh_token,  # DB에서 가져온 리프레시 토큰 사용
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(kakao_token_url, data=data)
            if token_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Kakao refresh token request failed")

            # 3. 새로운 액세스 토큰과 만료 시간 계산
            token_json = token_response.json()
            new_access_token = token_json.get("access_token")
            expires_in = token_json.get("expires_in")  # 만료 시간 (초 단위)

            # 4. DB에 새로운 액세스 토큰 및 만료 시간 갱신
            token_entry.token = new_access_token
            token_entry.expires_at = datetime.now() + timedelta(seconds=expires_in)
            db.commit()

        return {
            "status": 200,
            "message": "토큰 갱신 성공",
            "data": {
                "access_token": new_access_token
            }
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Kakao API request error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES),  # 30분으로 설정
        }
        new_access_token = jwt.encode(new_access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # JSON 형태로 토큰 및 만료 시간 반환
        return {
            "status": 200,
            "message": "토큰 갱신 성공",
            "data": {
                "access_token": new_access_token
            }
        }
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