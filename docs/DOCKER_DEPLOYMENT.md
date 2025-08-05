# Docker 배포 가이드

이 문서는 Garden5 프로젝트의 Docker 컨테이너화 및 배포 설정을 정리한 것입니다.

## 1. Dockerfile 구성

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc python3-dev libpq-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
ENV STATIC_ROOT=/app/staticfiles
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 2. 환경 변수 설정

### 2.1 .env 파일 예시
```bash
# PostgreSQL/Supabase 연결
DB_HOST=your-host.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=your-user
DB_PASSWORD=your-password
DB_SCHEMA=garden5

# Slack
SLACK_API_TOKEN=xoxb-your-token
CHANNEL_ID=your-channel-id

# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost
```

## 3. Docker 빌드 및 실행

### 3.1 이미지 빌드
```bash
docker build -t garden5:latest .
```

### 3.2 컨테이너 실행
```bash
docker run -d \
  --name garden5 \
  -p 8000:8000 \
  --env-file .env \
  garden5:latest
```

## 4. Docker Compose 설정 (선택사항)

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./staticfiles:/app/staticfiles
    restart: always
```

## 5. 프로덕션 고려사항

### 5.1 정적 파일 처리
- Nginx를 리버스 프록시로 사용
- 정적 파일은 Nginx에서 직접 서빙

### 5.2 보안
- 환경 변수는 절대 이미지에 포함시키지 않음
- 시크릿은 Docker Secrets 또는 환경 변수로 관리

### 5.3 헬스체크
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```

## 6. CI/CD 통합

### 6.1 GitHub Actions 예시
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push Docker image
        run: |
          docker build -t garden5:${{ github.sha }} .
          docker push garden5:${{ github.sha }}
```

## 7. 모니터링
- Docker 로그: `docker logs garden5`
- 컨테이너 상태: `docker stats garden5`
- 애플리케이션 로그는 볼륨 마운트로 영구 보관