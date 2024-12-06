from fastapi import FastAPI, Request
from .database import engine, Base
from .models import *  # 모델을 임포트하여 테이블을 생성하도록 함
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# DB 테이블을 생성
Base.metadata.create_all(bind=engine) 

from .api.v1 import V1

app = FastAPI()
app.include_router(V1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",  # 로컬 개발 환경
        "https://localhost:5173",  # 로컬 개발 환경 (프론트엔드)
        "https://ddrawry.site",  # 프로덕션 환경
        "https://kauth.kakao.com/",
        "https://kapi.kakao.com/" 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server!!!!"}


@app.exception_handler(Exception)
async def universal_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "An error occurred", "details": str(exc)},
    )