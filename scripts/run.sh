#!/bin/sh
set -e

# 현재 디렉토리 확인
echo "Current Directory: $(pwd)"
echo "Contents:"
ls -la

# FastAPI 애플리케이션을 Gunicorn + Uvicorn worker로 실행
exec gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 app.main:app
