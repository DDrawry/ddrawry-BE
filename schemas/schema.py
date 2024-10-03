from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import date

class Mood(Enum):
    NORMAL = 1
    SAD = 2
    SOSO = 3
    ANGRY = 4
    FUNNY = 5
    HAPPY = 6


class Weather(Enum):
    SUN = 1
    RAIN = 2
    SNOW = 3
    STORM = 4
    CLOUD = 5
    WIND = 6

class Diary(BaseModel):
    id: Optional[int] = None
    user_id: int
    date: date
    mood: int
    story: str
    title: str
    weather: int
    nickname: str

    class Config:
        orm_mode = True  


class TempDiary(BaseModel):
    id: int | None = None
    date: str | None = None
    mood: Mood | str | None = None
    weather: Weather | str | None = None
    title: str | None = None
    image: str | None = None
    story: str | None = None

class Settings(BaseModel):
    alram: bool | None = False
    darkmode: bool | None = False

class DiaryCreate(BaseModel):
    date: Optional[str] = None  # 선택적 필드
    nickname: Optional[str] = None  # 선택적 필드
    mood: int  # 필수 필드
    weather: int  # 필수 필드
    title: str  # 필수 필드
    image: Optional[str] = None  # 선택적 필드
    story: Optional[str] = None  # 선택적 필드

    class Config:
        orm_mode = True    