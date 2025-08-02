# Python 3.11 slim image 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 PostgreSQL 클라이언트 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 디렉토리 생성
RUN mkdir -p /app/staticfiles

# 환경변수 설정
ENV PYTHONUNBUFFERED=1
ENV STATIC_ROOT=/app/staticfiles

# 포트 설정
EXPOSE 8000

# Django 개발 서버 실행 (프로덕션에서는 gunicorn 사용 권장)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]