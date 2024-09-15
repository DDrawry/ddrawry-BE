from fastapi import FastAPI
from .database import engine, Base
from .models import *  # 모델을 임포트하여 테이블을 생성하도록 함

# DB 테이블을 생성
Base.metadata.create_all(bind=engine) 

from .api.v1 import V1

app = FastAPI()
app.include_router(V1)

@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server"}
