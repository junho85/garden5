# garden5
* 정원사들 시즌5 출석부입니다.
* slack #commit 채널에 올라온 메시지들을 수집해서 출석부를 작성합니다.
* [시즌 5 출석부 바로가기 gogo](http://garden5.junho85.pe.kr/)
* [github](https://github.com/junho85/garden5)
* [wiki](https://github.com/junho85/garden5/wiki)

## 개발 환경 설정

### 필요 사항
- Python 3.11.11+
- Django 4.2+

### 설치 및 실행 방법

1. **Python 가상환경 생성 및 활성화**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # 또는
   .venv\Scripts\activate     # Windows
   ```

2. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

3. **설정 파일 생성**
   ```bash
   # config.ini 설정
   cp attendance/config.ini.sample attendance/config.ini
   
   # users.yaml 설정
   cp attendance/users.yaml.sample attendance/users.yaml
   ```

4. **설정 파일 수정**
   - `attendance/config.ini`: Slack API 토큰, 채널 ID 등 설정
   - `attendance/users.yaml`: GitHub 사용자명과 Slack 사용자명 매핑

5. **Django 마이그레이션**
   ```bash
   python manage.py migrate
   ```

6. **개발 서버 실행**
   ```bash
   python manage.py runserver
   ```

7. **브라우저에서 확인**
   - http://localhost:8000 접속

### 설정 파일 상세 설명

#### config.ini 설정
```ini
[DEFAULT]
SLACK_API_TOKEN = xoxb-your-slack-bot-token-here  # Slack Bot Token
CHANNEL_ID = CXXXXXXXXX                           # GitHub 커밋 채널 ID
START_DATE = 2020-03-02                          # 출석 시작 날짜
GARDENING_DAYS = 100                             # 활동 기간(일)

[MONGO]
DATABASE = garden5
HOST = localhost
PORT = 27017

[POSTGRESQL]  # Supabase 마이그레이션용 (선택사항)
DATABASE = postgres
HOST = your-supabase-host.pooler.supabase.com
PORT = 6543
USER = postgres.your-project-id
PASSWORD = your-password
SCHEMA = garden5
```

#### users.yaml 설정
```yaml
# GitHub 사용자명과 Slack 사용자명 매핑
junho85:
  slack: junho85

genie-youn:
  slack: yjs930915

chloeeekim:
  slack: chloe.kim
```

#### Slack API 토큰 발급 방법
1. [Slack API 페이지](https://api.slack.com/apps) 방문
2. "Create New App" > "From scratch" 선택
3. OAuth & Permissions에서 다음 권한 추가:
   - `channels:history` (채널 메시지 읽기)
   - `chat:write` (메시지 보내기)
   - `users:read` (사용자 정보 읽기)
4. "Bot User OAuth Token" 복사하여 config.ini에 설정

### 주요 변경사항 (Python 3.11 업그레이드)
- Python 3.7.5 → 3.11.11
- Django 3.0 → 4.2
- slack → slack_sdk
- python-markdown-slack → 커스텀 Slack 마크다운 확장

## 참고
* [github](https://github.com/junho85/garden5)