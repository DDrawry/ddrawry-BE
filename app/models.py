from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    
    user_id = Column(Integer, primary_key=True)
    kakao_id = Column(String(255), nullable=True)
    nickname = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    last_login = Column(TIMESTAMP, nullable=True)

class Token(Base):
    __tablename__ = 'token'
    
    token_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    token = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)

class Diary(Base):
    __tablename__ = 'diary'
    
    diary_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    weather = Column(Integer, nullable=True)
    emotion = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    is_deleted = Column(Boolean, nullable=True)
    like = Column(Boolean, nullable=True)

class Image(Base):
    __tablename__ = 'image'
    
    image_id = Column(Integer, primary_key=True)
    diary_id = Column(Integer, ForeignKey('diary.diary_id'), nullable=False)
    image_url = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    is_temp = Column(Boolean, nullable=True)
    is_active = Column(Boolean, nullable=True)
    is_deleted = Column(Boolean, nullable=True)

class Notification(Base):
    __tablename__ = 'notification'
    
    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    type = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)

class Setting(Base):
    __tablename__ = 'setting'
    
    setting_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    dark_mode = Column(Boolean, nullable=True)
    notification = Column(Boolean, nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)

class TempDiary(Base):
    __tablename__ = 'temp_diary'
    
    temp_diary_id = Column(Integer, primary_key=True)
    diary_id = Column(Integer, ForeignKey('diary.diary_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    weather = Column(String(50), nullable=True)
    emotion = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, nullable=True)
    is_deleted = Column(Boolean, nullable=True)

class Prompt(Base):
    __tablename__ = 'prompt'
    
    prompt_id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_use = Column(Boolean, nullable=True)
