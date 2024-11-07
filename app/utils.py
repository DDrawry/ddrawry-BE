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
        token_type, access_token = authorization.split()
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=403, detail="유효하지 않은 인증 형식입니다.")

        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 Authorization 헤더 형식입니다.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=419, detail="JWT 토큰이 만료되었습니다.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="유효하지 않은 JWT 토큰입니다.")


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


import io
import requests
from PIL import Image
import boto3


AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY_ID=os.getenv("AWS_SECRET_KEY_ID")
AWS_REGION_NAME=os.getenv("AWS_REGION_NAME")

# Boto3 클라이언트 생성
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_KEY_ID,
    region_name=AWS_REGION_NAME
)

bucket_name = 'ddrawry-bucket-test-1'

async def generate_and_upload_image_to_s3(image_url: str, user_id: int, date: str):
    try:
        # 이미지 다운로드
        response = requests.get(image_url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch image")

        # 이미지 파일 열기
        img = Image.open(io.BytesIO(response.content))

        # 이미지 JPEG로 변환
        img = img.convert("RGB")  # PNG나 다른 형식에서 RGB로 변환

        # 파일명 생성 (user_id, date, 카운트 번호 등 포함)
        # 디렉토리가 없다면 생성
        directory_path = os.path.join(str(user_id), date)
        os.makedirs(directory_path, exist_ok=True)  # 디렉토리 생성, 이미 있으면 무시

        # S3에서 해당 디렉토리 내 파일 목록을 가져와서 count 계산
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=directory_path)
        count = 0
        if 'Contents' in response:
            # 파일 이름에 .jpg 또는 .jpeg가 포함된 파일만 카운팅
            count = len([f for f in response['Contents'] if f['Key'].endswith('.jpg') or f['Key'].endswith('.jpeg')])

        # 새로운 파일 이름 생성
        file_name = f"{user_id}/{date}/{count + 1}.jpg"

        # S3에 저장
        with io.BytesIO() as output:
            img.save(output, format="JPEG")
            output.seek(0)  # 파일 포인터를 처음으로 이동
            s3_client.put_object(Bucket=bucket_name, Key=file_name, Body=output, ContentType="image/jpeg")

        return {
            "status": 200,
            "message": "Image generated and uploaded successfully",
            "data": {"image_url": f"s3://your-s3-bucket/{file_name}"}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during image processing or upload: {str(e)}")