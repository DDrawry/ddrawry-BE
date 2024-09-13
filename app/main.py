from fastapi import FastAPI
# from .database import engine, Base
# Base.metadata.create_all(bind=engine) # DB연결 아직 안할거니까

from .api.v1 import V1

app = FastAPI()
app.include_router(V1)


@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server"}


