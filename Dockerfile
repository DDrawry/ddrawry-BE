# 베이스 이미지
FROM python:3.12-slim

# 빌드 의존성 설치
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean

# 종속성 파일 복사
COPY pyproject.toml poetry.lock /ddrawry/  

# 작업 디렉토리 설정
WORKDIR /ddrawry 

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install
RUN poetry add gunicorn


# 데이터베이스 마이그레이션
RUN poetry run alembic upgrade head

COPY ./scripts /scripts
RUN chmod +x /scripts/run.sh
CMD ["/scripts/run.sh"]

# 베이스 이미지
FROM python:3.12-slim

# 종속성 파일 복사
COPY ./poetry.lock /ndd/
COPY ./pyproject.toml /ndd/

# 작업 디렉토리 설정
WORKDIR /ndd

# 종속성 설치
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install
RUN poetry add gunicorn

# 애플리케이션 코드 복사
# COPY ./app /ndd/app
WORKDIR /ndd/app

COPY ./scripts /scripts
RUN chmod +x /scripts/run.sh
CMD ["/scripts/run.sh"]