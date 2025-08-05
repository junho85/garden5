# Python 버전 업그레이드 가이드

이 문서는 Garden5 프로젝트의 Python 3.7.5에서 3.11로 업그레이드한 과정을 정리한 것입니다.

## 1. 업그레이드 배경
- Python 3.7.5에서 3.11로 업그레이드
- 최신 패키지 지원 및 성능 향상
- 보안 업데이트 및 장기 지원

## 2. 의존성 변경

### 2.1 주요 패키지 업데이트
- Django 버전 업그레이드 (4.1 이상)
- slack-sdk로 마이그레이션 (기존 slackclient에서 변경)

### 2.2 requirements.txt 업데이트
```
# Garden5 - Python 3.11 requirements
# Core framework
Django>=4.1,<5.0

# Configuration and data formats
pyyaml>=6.0
python-dotenv>=1.0.0

# Slack integration
slack-sdk>=3.0

# Markdown processing
markdown>=3.4

# Database driver (MongoDB)
pymongo>=4.0
```

## 3. 주요 변경사항

### 3.1 문법 및 기능 개선
- Type hints 향상
- Pattern matching 지원 (match-case)
- 성능 최적화

### 3.2 호환성 이슈
- 일부 deprecated 함수 제거
- asyncio 개선사항

## 4. 업그레이드 절차
1. Python 3.11 설치
2. 가상환경 재생성
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # Linux/Mac
   ```
3. requirements.txt로 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```
4. 호환성 테스트 실행
5. 애플리케이션 동작 확인

## 5. 테스트 및 검증
- 단위 테스트 실행
- 통합 테스트 수행
- 성능 벤치마크 비교