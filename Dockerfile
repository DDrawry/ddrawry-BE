# 베이스 이미지
FROM python:3.12-slim

# 빌드 의존성 설치
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 및 의존성 파일 복사
COPY pyproject.toml poetry.lock ./

# Poetry 설치
RUN pip install poetry

# 의존성 설치
RUN poetry install --no-root

# 나머지 애플리케이션 파일 복사
COPY . .

# 애플리케이션 시작
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
