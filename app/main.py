# app/main.py
from fastapi import FastAPI

from api.v1 import V1


app = FastAPI()
app.include_router(V1)


@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server"}

