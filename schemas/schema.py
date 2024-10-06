from pydantic import constr, BaseModel
from enum import Enum
from typing import Optional, Union
from datetime import date

class MoodEnum(int, Enum):
    SMILE = 1
    SAD = 2
    MEDIOCRE = 3
    ANGRY = 4
    EXCITED = 5
    HAPPY = 6

class WeatherEnum(int, Enum):
    SUNNY = 1
    RAINY = 2
    SNOWY = 3
    STORMY = 4
    CLOUDY = 5
    WINDY = 6

# 다이어리 기본 모델
class Diary(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    date: date
    mood: MoodEnum  # Enum으로 변경
    weather: WeatherEnum  # Enum으로 변경
    story: str
    title: str
    nickname: str
    like: bool = False  # 좋아요 상태 추가

    class Config:
        orm_mode = True  # SQLAlchemy 모델과의 호환을 위해 추가

# 다이어리 생성 시 사용하는 모델
class DiaryCreate(BaseModel):
    date: Optional[str] = None  # 날짜를 str로 받음, 나중에 변환할 것
    nickname: Optional[str] = None
    mood: MoodEnum  # Enum으로 변경
    weather: WeatherEnum  # Enum으로 변경
    title: str
    story: Optional[str] = None
    like: Optional[bool] = False  # 생성 시에도 좋아요 상태를 받을 수 있도록 추가

# 임시 다이어리
class TempDiarySchema(BaseModel):
    title: str
    weather: Optional[int] = None
    mood: Optional[int] = None
    date: date
    nickname: str
    story: str

    class Config:
        orm_mode = True

# 사용자 설정
class Settings(BaseModel):
    notification: Union[bool, None] = None
    dark_mode: Union[bool, None] = None

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

class NicknameUpdate(BaseModel):
    nickname: str = constr(min_length=1, max_length=100)  # 1자 이상, 100자 이하로 제한
    
    class Config:
        orm_mode = True  # ORM 호환 모드 활성화