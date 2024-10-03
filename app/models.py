from sqlalchemy import Column, Integer, Date, String, ForeignKey, TIMESTAMP, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    kakao_id = Column(String(255), nullable=True)
    nickname = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    last_login = Column(TIMESTAMP, nullable=True)


class Token(Base):
    __tablename__ = 'token'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    token = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)


class Diary(Base):
    __tablename__ = 'diary'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    weather = Column(Integer, nullable=True)  # 날씨 값
    mood = Column(Integer, nullable=True)  # 기분 값
    date = Column(Date, nullable=True)  # 날짜
    nickname = Column(String(100), nullable=True)  # 닉네임
    story = Column(Text, nullable=True)  # 스토리
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    like = Column(Boolean, nullable=False, default=False)  # 좋아요 상태 추가


class Image(Base):
    __tablename__ = 'image'
    
    id = Column(Integer, primary_key=True)
    diary_id = Column(Integer, ForeignKey('diary.id'), nullable=False)
    image_url = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    is_temp = Column(Boolean, nullable=True, default=False)
    is_active = Column(Boolean, nullable=True, default=True)
    is_deleted = Column(Boolean, nullable=True, default=False)


class Notification(Base):
    __tablename__ = 'notification'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    type = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, nullable=True, default=False)
    created_at = Column(TIMESTAMP, nullable=True)


class Setting(Base):
    __tablename__ = 'setting'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    dark_mode = Column(Boolean, nullable=True, default=False)
    notification = Column(Boolean, nullable=True, default=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)


class TempDiary(Base):
    __tablename__ = 'temp_diary'
    
    id = Column(Integer, primary_key=True)
    diary_id = Column(Integer, ForeignKey('diary.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    weather = Column(String(50), nullable=True)
    mood = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    is_deleted = Column(Boolean, nullable=True, default=False)


class Prompt(Base):
    __tablename__ = 'prompt'
    
    id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_use = Column(Boolean, nullable=True, default=True)
