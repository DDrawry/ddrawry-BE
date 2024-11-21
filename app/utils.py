import jwt
from fastapi import HTTPException, Header, Request
from dotenv import load_dotenv

from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import TempDiary, Image as ImageModel

from PIL import Image

import io
import requests
import boto3
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
            raise HTTPException(status_code=401, detail="유효하지 않은 인증 형식입니다.")

        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id")
    except ValueError:
        raise HTTPException(status_code=401, detail="잘못된 Authorization 헤더 형식입니다.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT 토큰이 만료되었습니다.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 JWT 토큰입니다.")


# utils.py
def replace_null_with_empty_str(data: dict) -> dict:
    """Dict에서 None 값을 빈 문자열로 변환하는 함수"""
    return {key: (value if value is not None else "") for key, value in data.items()}


def get_dev_from_request(request: Request):
    dev = request.query_params.get("dev")
    if dev is not None and dev in ["0", "1"]:
        return int(dev)
    return 1  # 기본값은 1




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
    

from datetime import datetime
# 하루 최대 이미지 생성 횟수
MAX_DAILY_IMAGE_COUNT = 100

def get_daily_image_count(db: Session, user_id: int) -> int:
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    used_count = db.query(func.count(ImageModel.id)).join(
        TempDiary, ImageModel.temp_diary_id == TempDiary.id
    ).filter(
        TempDiary.user_id == user_id,
        ImageModel.created_at >= start_of_day,
        ImageModel.created_at <= end_of_day,
        ImageModel.is_deleted == False,
        ImageModel.is_active == True
    ).scalar()

    remaining_count = MAX_DAILY_IMAGE_COUNT - used_count
    return max(0, remaining_count)

def get_image_count_for_date(db: Session, user_id: int, target_date: date) -> int:
    # TempDiary와 관련된 Image를 날짜별로 카운트하는 쿼리 작성
    count = db.query(func.count(ImageModel.id))\
              .join(TempDiary, TempDiary.id == ImageModel.temp_diary_id)\
              .filter(TempDiary.user_id == user_id)\
              .filter(TempDiary.date == target_date)\
              .filter(ImageModel.is_deleted == False)\
              .scalar()  # 실제 값 반환
    
    return count or 0  # 없으면 0을 반환



import uuid

def upload_image_to_s3(image_data: bytes, user_id: int) -> str:
    """
    이미지 데이터를 S3 버킷에 업로드하는 함수

    :param image_data: Base64 디코딩된 이미지 바이트 데이터
    :param user_id: 사용자 ID
    :return: 업로드된 이미지의 S3 URL
    """
    # 파일 이름 생성
    filename = f"share/{user_id}/{uuid.uuid4()}.jpg"
    
    # S3에 이미지 업로드
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=image_data,
        ContentType='image/jpeg'
    )
    
    # 이미지 URL 생성 및 반환
    s3_url = filename
    return s3_url