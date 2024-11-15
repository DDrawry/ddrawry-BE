FROM python:3.12-slim

# 빌드 의존성 설치
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean

# 의존성 파일만 복사
COPY pyproject.toml poetry.lock /ddrawry/

# 작업 디렉토리 설정
WORKDIR /ddrawry

# Poetry 설치 및 의존성 설치
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

# 나머지 애플리케이션 파일 복사
COPY . /ddrawry/

# 스크립트 복사 및 권한 부여
COPY ./scripts /scripts
RUN chmod +x /scripts/run.sh

# 애플리케이션 시작
CMD ["/scripts/run.sh"]
