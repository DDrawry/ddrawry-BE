# app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"DDRAWRY": "This is ddrawry's API server"}
