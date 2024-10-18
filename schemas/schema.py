from pydantic import constr, BaseModel, validator
from enum import Enum
from typing import Optional, Union
from datetime import date

class MoodEnum(int, Enum):
    smile = 1
    sad = 2
    mediocre = 3
    angry = 4
    excited = 5
    happy = 6

class WeatherEnum(int, Enum):
    sunny = 1
    rainy = 2
    snowy = 3
    stormy = 4
    cloudy = 5
    windy = 6

# 다이어리 기본 모델
class Diary(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    date: date
    mood: MoodEnum
    weather: WeatherEnum
    title: str
    story: str
    nickname: str
    like: bool = False
    image_url: Optional[str] = None  

    class Config:
        orm_mode = True

# 다이어리 생성 시 사용하는 모델
class DiaryCreate(BaseModel):
    date: Optional[str] = None  
    nickname: Optional[str] = None
    mood: MoodEnum  # Enum으로 변경
    weather: WeatherEnum  # Enum으로 변경
    title: str
    story: Optional[str] = None
    like: Optional[bool] = False  

class TempDiarySchema(BaseModel):
    date: str
    nickname: str
    mood: MoodEnum
    weather: WeatherEnum
    image: str = None
    story: str

    @validator("mood", pre=True)
    def parse_mood(cls, value):
        if isinstance(value, str):
            return MoodEnum[value.upper()]  # 문자열을 대문자로 변환하여 Enum으로 매핑
        return MoodEnum(value)

    @validator("weather", pre=True)
    def parse_weather(cls, value):
        if isinstance(value, str):
            return WeatherEnum[value.upper()]  # 문자열을 대문자로 변환하여 Enum으로 매핑
        return WeatherEnum(value)

# 사용자 설정
class Settings(BaseModel):
    notification: Union[bool, None] = None
    dark_mode: Union[bool, None] = None

class DiaryCreate(BaseModel):
    date: Optional[str] = None  
    nickname: Optional[str] = None  
    mood: int  
    weather: int  
    title: str  
    image: Optional[str] = None  
    story: Optional[str] = None  

    class Config:
        orm_mode = True    

class NicknameUpdate(BaseModel):
    nickname: str = constr(min_length=1, max_length=100)  # 1자 이상, 100자 이하로 제한
    
    class Config:
        orm_mode = True  # ORM 호환 모드 활성화


class StatusUpdateRequest(BaseModel):
    date: str  # YYYY-MM-DD 형식으로 날짜 받음
    type: str  # "main" 또는 "write"를 받는 필드