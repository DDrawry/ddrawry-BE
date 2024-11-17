#!/bin/sh
set -e

# 현재 디렉토리 확인
echo "Current Directory: $(pwd)"
echo "Contents:"
ls -la

# 데이터베이스 마이그레이션 실행
echo "Running database migrations..."
poetry run alembic upgrade head

# PYTHONPATH 설정
export PYTHONPATH=/ddrawry

# FastAPI 애플리케이션을 Gunicorn + Uvicorn worker로 실행
echo "Starting FastAPI application..."
# 로그 레벨을 debug로 설정
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --log-level debug app.main:app
