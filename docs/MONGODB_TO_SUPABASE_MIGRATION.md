# MongoDB to Supabase Migration Guide

이 문서는 Garden5 프로젝트를 MongoDB에서 Supabase(PostgreSQL)로 마이그레이션한 과정을 정리한 것입니다.

## 1. 개요

### 1.1 마이그레이션 배경
- MongoDB에서 PostgreSQL 기반의 Supabase로 데이터베이스 전환
- Python 3.7.5에서 3.11로 업그레이드
- 더 나은 관계형 데이터 모델 활용 및 Supabase의 기능 활용

### 1.2 주요 변경사항
- 데이터베이스: MongoDB → PostgreSQL (Supabase)
- Python 버전: 3.7.5 → 3.11
- 데이터 저장 방식: BSON → JSONB
- 연결 드라이버: pymongo → psycopg2

## 2. 데이터베이스 스키마 설계

### 2.1 MongoDB 컬렉션 구조
```javascript
// MongoDB의 slack_messages 컬렉션
{
  "_id": ObjectId,
  "ts": "1234567890.123456",
  "type": "message",
  "text": "commit message",
  "user": "U1234567",
  "bot_id": "B1234567",
  "team": "T1234567",
  "bot_profile": {...},
  "attachments": [...]
}
```

### 2.2 PostgreSQL 테이블 구조
```sql
CREATE SCHEMA IF NOT EXISTS garden5;

CREATE TABLE garden5.slack_messages (
    ts VARCHAR(255) PRIMARY KEY,
    ts_for_db TIMESTAMP,
    bot_id VARCHAR(255),
    type VARCHAR(50),
    text TEXT,
    "user" VARCHAR(255),
    team VARCHAR(50),
    bot_profile JSONB,
    attachments JSONB
);

-- 인덱스 추가
CREATE INDEX idx_ts_for_db ON garden5.slack_messages(ts_for_db);
CREATE INDEX idx_user ON garden5.slack_messages("user");
CREATE INDEX idx_attachments_author ON garden5.slack_messages((attachments->0->>'author_name'));
```

### 2.3 주요 차이점
- PRIMARY KEY: MongoDB의 `_id` → PostgreSQL의 `ts` (Slack 타임스탬프)
- 날짜 처리: `ts_for_db` 컬럼 추가 (KST 시간대)
- JSON 데이터: MongoDB의 중첩 문서 → PostgreSQL의 JSONB 타입

## 3. 데이터 마이그레이션

### 3.1 마이그레이션 스크립트 (`migrate_to_supabase.py`)

```python
#!/usr/bin/env python3
import psycopg2
import bson
import json
from datetime import datetime
import getpass
from psycopg2.extras import execute_values

def get_db_config():
    """데이터베이스 연결 정보를 환경변수 또는 사용자 입력으로 가져오기"""
    db_password = getpass.getpass("DB Password: ")
    return {
        'database': 'postgres',
        'host': 'your-host.supabase.com',
        'port': 6543,
        'user': 'your-user',
        'password': db_password,
        'sslmode': 'require',
        'gssencmode': 'disable'
    }

def read_bson_file(file_path):
    """BSON 파일 읽기"""
    documents = []
    with open(file_path, 'rb') as f:
        while True:
            try:
                size_data = f.read(4)
                if not size_data:
                    break
                size = int.from_bytes(size_data, 'little')
                f.seek(-4, 1)
                doc_data = f.read(size)
                if doc_data:
                    doc = bson.decode(doc_data)
                    documents.append(doc)
            except Exception as e:
                break
    return documents

def migrate_data():
    """BSON 데이터를 Supabase로 마이그레이션"""
    # 배치 삽입으로 성능 최적화
    execute_values(cur, insert_query, batch)
```

### 3.2 마이그레이션 실행 과정
1. MongoDB 데이터를 BSON 파일로 덤프
2. Supabase에 스키마 및 테이블 생성
3. 마이그레이션 스크립트 실행
4. 데이터 검증

## 4. 애플리케이션 코드 변경

### 4.1 데이터베이스 연결 코드

**MongoDB (기존)**
```python
from pymongo import MongoClient

def connect_mongo(self):
    client = MongoClient(self.mongo_host, int(self.mongo_port))
    return client[self.mongo_database]
```

**PostgreSQL (변경후)**
```python
import psycopg2

def connect_db(self):
    conn = psycopg2.connect(
        host=self.pg_host,
        port=self.pg_port,
        database=self.pg_database,
        user=self.pg_user,
        password=self.pg_password,
        sslmode='require',
        gssencmode='disable'  # GSSAPI 오류 해결
    )
    return conn
```

### 4.2 데이터 조회 코드

**MongoDB (기존)**
```python
def find_attendance_by_user_mongo(self, user, date):
    start_date = datetime(date.year, date.month, date.day) - timedelta(hours=15)
    end_date = start_date + timedelta(days=1)
    
    docs = self.mongo_collection.find({
        "attachments.author_name": user,
        "ts_for_db": {"$gte": start_date, "$lt": end_date}
    })
    return list(docs)
```

**PostgreSQL (변경후)**
```python
def find_attendance_by_user(self, user, date):
    start_date = datetime(date.year, date.month, date.day) - timedelta(hours=15)
    end_date = start_date + timedelta(days=1)
    
    query = """
        SELECT ts, ts_for_db, attachments
        FROM garden5.slack_messages
        WHERE attachments->0->>'author_name' = %s
        AND ts_for_db >= %s
        AND ts_for_db < %s
        ORDER BY ts_for_db
    """
    cur.execute(query, (user, start_date, end_date))
    return cur.fetchall()
```

### 4.3 타임존 처리

**중요한 발견사항:**
- `ts` 컬럼: UTC epoch timestamp
- `ts_for_db` 컬럼: KST로 저장된 시간
- Garden4의 단순한 -9시간 방식을 참고하여 해결

```python
# 잘못된 방식 (복잡한 타임존 변환)
kst = pytz.timezone('Asia/Seoul')
ts_datetime = datetime.fromtimestamp(float(message['ts']))
ts_datetime = ts_datetime.replace(tzinfo=pytz.UTC).astimezone(kst)

# 올바른 방식 (이미 KST로 저장됨)
ts_datetime = message['ts_for_db']  # 변환 불필요
```

## 5. 의존성 변경

### 5.1 requirements.txt 업데이트

**제거된 패키지:**
- pymongo
- pytz (타임존 문제 해결 후 불필요)

**추가/변경된 패키지:**
- psycopg2-binary>=2.9
- supabase (선택사항)

### 5.2 최종 requirements.txt
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

# PostgreSQL database
psycopg2-binary>=2.9
```

## 6. 배포 설정

### 6.1 Dockerfile 생성
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

### 6.2 환경 변수 설정
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
```

## 7. 주요 이슈 및 해결 방법

### 7.1 GSSAPI 연결 오류
**문제:** `psycopg2.OperationalError: GSSAPI negotiation failed`

**해결:** 연결 설정에 `gssencmode='disable'` 추가

### 7.2 타임존 문제
**문제:** 커밋이 잘못된 날짜에 표시됨

**해결:** 
- `ts_for_db`가 이미 KST로 저장되어 있음을 확인
- 불필요한 타임존 변환 코드 제거

### 7.3 모듈 누락
**문제:** `ModuleNotFoundError: No module named 'pytz'`

**해결:** requirements.txt 업데이트 및 재설치

## 8. 검증 및 테스트

### 8.1 데이터 무결성 확인
```sql
-- 전체 레코드 수 확인
SELECT COUNT(*) FROM garden5.slack_messages;

-- 특정 사용자의 출석 기록 확인
SELECT ts_for_db, attachments->0->>'author_name' as author
FROM garden5.slack_messages
WHERE attachments->0->>'author_name' = 'junho85'
ORDER BY ts_for_db DESC
LIMIT 10;
```

### 8.2 애플리케이션 테스트
1. 출석 조회 기능 확인
2. 날짜별 조회 정확성 확인
3. 사용자별 통계 확인

## 9. 롤백 계획

만약 문제가 발생할 경우:
1. MongoDB 백업 데이터 보관
2. 이전 코드 버전 태그 유지
3. 환경 변수만 변경하여 빠른 전환 가능

## 10. 결론

MongoDB에서 Supabase(PostgreSQL)로의 마이그레이션은 다음과 같은 이점을 제공했습니다:
- 더 나은 쿼리 성능 (특히 날짜 범위 검색)
- JSONB를 활용한 유연한 스키마
- Supabase의 실시간 기능 활용 가능성
- 표준 SQL 사용으로 유지보수 용이

이 가이드가 다른 MongoDB to PostgreSQL 마이그레이션 프로젝트에 도움이 되기를 바랍니다.