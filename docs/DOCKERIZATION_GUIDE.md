# Django 프로젝트 도커라이징 가이드

이 문서는 Garden5 프로젝트를 Docker로 컨테이너화한 과정을 정리한 것입니다. Garden6 등 향후 프로젝트에서 활용할 수 있도록 작성되었습니다.

## 1. 개요

### 1.1 도커라이징 목표
- Django 애플리케이션의 컨테이너화
- 개발/배포 환경의 일관성 확보
- 멀티 플랫폼 지원 (linux/amd64, linux/arm64)
- 자동화된 빌드 및 배포 프로세스

### 1.2 환경 정보
- Base Image: `python:3.11-slim`
- Framework: Django 4.x
- Database: PostgreSQL (Supabase)
- Python Version: 3.11

## 2. Dockerfile 작성

### 2.1 완성된 Dockerfile

```dockerfile
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
```

### 2.2 Dockerfile 주요 구성 요소 설명

#### 2.2.1 Base Image 선택
```dockerfile
FROM python:3.11-slim
```
- `slim` 버전 사용으로 이미지 크기 최적화
- Python 3.11 공식 이미지 사용

#### 2.2.2 시스템 의존성 설치
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```
- `gcc`: C 컴파일러 (psycopg2 컴파일용)
- `python3-dev`: Python 개발 헤더
- `libpq-dev`: PostgreSQL 클라이언트 라이브러리
- 패키지 캐시 정리로 이미지 크기 감소

#### 2.2.3 Python 패키지 설치
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- Docker 레이어 캐싱 최적화를 위해 requirements.txt 먼저 복사
- `--no-cache-dir`: pip 캐시 비활성화로 이미지 크기 감소

#### 2.2.4 환경변수 설정
```dockerfile
ENV PYTHONUNBUFFERED=1
ENV STATIC_ROOT=/app/staticfiles
```
- `PYTHONUNBUFFERED=1`: Python 출력 버퍼링 비활성화 (로그 실시간 확인)
- `STATIC_ROOT`: Django 정적 파일 경로 설정

## 3. .dockerignore 작성

### 3.1 완성된 .dockerignore

```dockerignore
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.pytest_cache
.mypy_cache
.hypothesis

# Virtual environments
venv/
.venv/
ENV/
env/

# Django
*.sqlite3
local_settings.py
db.sqlite3
media/
staticfiles/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.pydevproject

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
ehthumbs.db

# Project specific
archive/
docs/
debug_*.py
test_*.py
analyze_*.py
verify_*.py
check_*.py
compare_*.py
create_*.py
python_upgrade_analysis.md
*.bson

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Scripts
build-and-push.sh

# Configuration samples
*.sample
attendance/config.ini
attendance/users.yaml

# Temporary files
tmp/
temp/
```

### 3.2 .dockerignore 주요 카테고리

1. **개발 환경 파일**: 가상환경, IDE 설정, 캐시 파일
2. **테스트 및 분석 파일**: 테스트 스크립트, 분석 도구
3. **민감한 설정 파일**: 실제 설정 파일 제외 (샘플만 포함)
4. **불필요한 파일**: 문서, 아카이브, 임시 파일

## 4. 빌드 및 배포 스크립트

### 4.1 build-and-push.sh

```bash
#!/bin/bash

# Docker Hub 사용자명
DOCKER_USER="junho85"
IMAGE_NAME="garden5"

# 스크립트가 있는 디렉토리를 기준으로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 현재 날짜/시간으로 태그 생성
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Docker Hub 로그인 확인
echo "Checking Docker Hub authentication..."
if ! docker pull hello-world:latest > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Not logged in to Docker Hub or network issue${NC}"
    echo "Please run 'docker login' first"
    exit 1
fi
echo -e "${GREEN}✓ Docker Hub authentication OK${NC}"

echo ""
echo "Building multi-platform Docker image for Garden5..."
echo "Build directory: $SCRIPT_DIR"
echo "Platforms: linux/amd64, linux/arm64"
echo "Tags: latest, $TIMESTAMP"
echo ""

# buildx 빌더 생성 (이미 있으면 무시)
docker buildx create --name multiplatform --use 2>/dev/null || true

# 멀티 플랫폼 빌드 및 푸시
if docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $DOCKER_USER/$IMAGE_NAME:latest \
  --tag $DOCKER_USER/$IMAGE_NAME:$TIMESTAMP \
  --push \
  "$SCRIPT_DIR"; then
    
    echo ""
    echo -e "${GREEN}✓ Build and push completed successfully!${NC}"
    echo "Images pushed:"
    echo "  $DOCKER_USER/$IMAGE_NAME:latest"
    echo "  $DOCKER_USER/$IMAGE_NAME:$TIMESTAMP"
    echo ""
    echo "To run the container:"
    echo "  docker run -d \\"
    echo "    --name garden5 \\"
    echo "    -p 8000:8000 \\"
    echo "    -e SLACK_API_TOKEN=your_token \\"
    echo "    -e CHANNEL_ID=your_channel \\"
    echo "    -e DB_HOST=your_host \\"
    echo "    -e DB_NAME=your_database \\"
    echo "    -e DB_USER=your_user \\"
    echo "    -e DB_PASSWORD=your_password \\"
    echo "    $DOCKER_USER/$IMAGE_NAME:latest"
else
    echo ""
    echo -e "${RED}✗ Build or push failed!${NC}"
    echo "Please check the error message above."
    echo ""
    echo "Common issues:"
    echo "1. Not logged in to Docker Hub: run 'docker login'"
    echo "2. Repository doesn't exist: create it at https://hub.docker.com/"
    echo "3. No push permissions: check your Docker Hub access"
    exit 1
fi
```

### 4.2 스크립트 실행 권한 설정

```bash
chmod +x build-and-push.sh
```

### 4.3 스크립트 주요 기능

1. **멀티 플랫폼 빌드**: linux/amd64, linux/arm64 지원
2. **자동 태깅**: latest + 타임스탬프 태그
3. **인증 확인**: Docker Hub 로그인 상태 체크
4. **에러 처리**: 빌드 실패시 상세한 에러 메시지
5. **사용법 안내**: 컨테이너 실행 명령어 제공

## 5. 환경변수 설정

### 5.1 필수 환경변수

```bash
# Slack 설정
SLACK_API_TOKEN=xoxb-your-slack-token
CHANNEL_ID=your-channel-id

# 데이터베이스 설정
DB_HOST=your-host.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=your-user
DB_PASSWORD=your-password
DB_SCHEMA=garden5

# Django 설정
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,localhost
```

### 5.2 Docker 실행시 환경변수 전달

```bash
# 직접 전달
docker run -d \
  --name garden5 \
  -p 8000:8000 \
  -e SLACK_API_TOKEN=your_token \
  -e DB_HOST=your_host \
  junho85/garden5:latest

# .env 파일 사용
docker run -d \
  --name garden5 \
  -p 8000:8000 \
  --env-file .env \
  junho85/garden5:latest
```

## 6. Docker Compose (선택사항)

### 6.1 docker-compose.yml 예시

```yaml
version: '3.8'

services:
  garden5:
    image: junho85/garden5:latest
    container_name: garden5
    ports:
      - "8000:8000"
    environment:
      - SLACK_API_TOKEN=${SLACK_API_TOKEN}
      - CHANNEL_ID=${CHANNEL_ID}
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_SCHEMA=${DB_SCHEMA}
      - DEBUG=False
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/attendance/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 7. 최적화 팁

### 7.1 이미지 크기 최적화

1. **Multi-stage 빌드 (고급)**
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
```

2. **Alpine 이미지 사용 (대안)**
```dockerfile
FROM python:3.11-alpine
RUN apk add --no-cache gcc musl-dev postgresql-dev
```

### 7.2 보안 강화

1. **Non-root 사용자**
```dockerfile
RUN adduser --disabled-password --gecos '' appuser
USER appuser
```

2. **민감한 파일 제외**
```dockerignore
*.env
*.key
*.pem
config.ini
users.yaml
```

## 8. 프로덕션 고려사항

### 8.1 웹서버 변경 (권장)

```dockerfile
# 프로덕션용 - Gunicorn 사용
RUN pip install gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "garden5.wsgi:application"]
```

### 8.2 정적 파일 처리

```dockerfile
# 정적 파일 수집
RUN python manage.py collectstatic --noinput
```

### 8.3 헬스체크 추가

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/attendance/ || exit 1
```

## 9. 문제 해결

### 9.1 일반적인 이슈

1. **권한 문제**
```bash
# 스크립트 실행 권한
chmod +x build-and-push.sh

# Docker 소켓 권한
sudo usermod -aG docker $USER
```

2. **포트 충돌**
```bash
# 다른 포트 사용
docker run -p 8080:8000 image_name
```

3. **메모리 부족**
```bash
# 메모리 제한 설정
docker run -m 512m image_name
```

### 9.2 디버깅

```bash
# 컨테이너 로그 확인
docker logs garden5

# 컨테이너 내부 접근
docker exec -it garden5 /bin/bash

# 이미지 레이어 확인
docker history junho85/garden5:latest
```

## 10. Garden6 적용시 체크리스트

### 10.1 파일 수정
- [ ] Dockerfile의 IMAGE_NAME 변경
- [ ] build-and-push.sh의 IMAGE_NAME 변경
- [ ] requirements.txt 업데이트
- [ ] .dockerignore 프로젝트별 설정 추가

### 10.2 환경변수 업데이트
- [ ] 새로운 서비스별 환경변수 추가
- [ ] 데이터베이스 스키마명 변경
- [ ] 도메인/포트 설정 확인

### 10.3 테스트
- [ ] 로컬 Docker 빌드 테스트
- [ ] 멀티 플랫폼 빌드 테스트
- [ ] 컨테이너 실행 및 기능 테스트
- [ ] 환경변수 전달 확인

## 11. 결론

이 도커라이징 가이드는 다음과 같은 이점을 제공합니다:

1. **일관된 환경**: 개발/스테이징/프로덕션 환경 통일
2. **쉬운 배포**: 단일 명령어로 배포 가능
3. **확장성**: 멀티 플랫폼 지원으로 다양한 환경 대응
4. **자동화**: CI/CD 파이프라인 구축 기반

Garden6 등 향후 프로젝트에서는 이 가이드를 기반으로 프로젝트별 특성에 맞게 조정하여 사용하시기 바랍니다.