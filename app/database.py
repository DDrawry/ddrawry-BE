# 데이터베이스 연결 엔진을 생성하는 함수
from sqlalchemy import create_engine 
from sqlalchemy.exc import OperationalError 
import time
# 테이블과 모델을 정의하기 위한 기본 클래스를 생성
from sqlalchemy.ext.declarative import declarative_base

# 데이터베이스 세션을 생성하기 위한 팩토리 함수를 생성
# Sesstion : 데이터베이스 트랜잭션을 관리
from sqlalchemy.orm import sessionmaker, Session

#  제너레이터 함수의 반환 타입을 정의하는 타입 힌트
from typing import Generator

# 의존성 주입 도구
from fastapi import Depends
from dotenv import load_dotenv
import os

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")


# 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
    )

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Retry connection
def connect_with_retry(engine, retries=3, delay=5):
    for i in range(retries):
        try:
            connection = engine.connect()
            return connection
        except OperationalError:
            if i < retries - 1:
                time.sleep(delay)
            else:
                raise

try:
    connection = connect_with_retry(engine)
    print("Database connected successfully!")
except OperationalError:
    print("Failed to connect to the database after retries.")

# 데이터베이스 베이스 클래스 생성
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
