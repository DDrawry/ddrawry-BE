import jwt
from fastapi import HTTPException, Cookie
from dotenv import load_dotenv

import os 

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")  # JWT 비밀키
JWT_ALGORITHM = "HS256"

def get_current_user_id(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="JWT 토큰이 없습니다.")
    
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT 토큰이 만료되었습니다.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 JWT 토큰입니다.")


# utils.py
def replace_null_with_empty_str(data: dict) -> dict:
    """Dict에서 None 값을 빈 문자열로 변환하는 함수"""
    return {key: (value if value is not None else "") for key, value in data.items()}
