from fastapi import FastAPI, Request
from .database import engine, Base
from .models import *  # 모델을 임포트하여 테이블을 생성하도록 함
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# DB 테이블을 생성
Base.metadata.create_all(bind=engine) 

from .api.v1 import V1

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(V1)



@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server!!!!"}


@app.exception_handler(Exception)
async def universal_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "An error occurred", "details": str(exc)},
    )