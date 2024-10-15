#!/bin/sh
set -e

# 현재 디렉토리 확인
echo "Current Directory: $(pwd)"
echo "Contents:"
ls -la

# 데이터베이스 마이그레이션 (Alembic을 사용하는 경우)
alembic upgrade head

# FastAPI 애플리케이션을 Gunicorn + Uvicorn worker로 실행
exec gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 app.main:app
