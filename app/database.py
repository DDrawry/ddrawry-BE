# 데이터베이스 연결 엔진을 생성하는 함수
from sqlalchemy import create_engine 

# 테이블과 모델을 정의하기 위한 기본 클래스를 생성
from sqlalchemy.ext.declarative import declarative_base

# 데이터베이스 세션을 생성하기 위한 팩토리 함수를 생성
# Sesstion : 데이터베이스 트랜잭션을 관리
from sqlalchemy.orm import sessionmaker, Session

#  제너레이터 함수의 반환 타입을 정의하는 타입 힌트
from typing import Generator

# 의존성 주입 도구
from fastapi import Depends

# 데이터베이스 URL 설정
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost/ddrawry"


# 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 데이터베이스 베이스 클래스 생성
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
