import jwt
from fastapi import HTTPException, Header
from dotenv import load_dotenv

import os 

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")  # JWT 비밀키
JWT_ALGORITHM = "HS256"

def get_current_user_id(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="JWT 토큰이 없습니다.")
    
    try:
        # "Bearer <token>" 형식에서 토큰 부분만 추출
        token_type, access_token = authorization.split()
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401, detail="유효하지 않은 인증 형식입니다.")

        # 토큰 디코딩
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except ValueError:
        raise HTTPException(status_code=401, detail="잘못된 Authorization 헤더 형식입니다.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT 토큰이 만료되었습니다.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 JWT 토큰입니다.")


# utils.py
def replace_null_with_empty_str(data: dict) -> dict:
    """Dict에서 None 값을 빈 문자열로 변환하는 함수"""
    return {key: (value if value is not None else "") for key, value in data.items()}


from fastapi import Request

def get_dev_from_request(request: Request):
    dev = request.query_params.get("dev")
    if dev is not None and dev in ["0", "1"]:
        return int(dev)
    return 1  # 기본값은 1
