# MongoDB to Supabase Migration Guide

이 문서는 Garden5 프로젝트를 MongoDB에서 Supabase(PostgreSQL)로 마이그레이션한 과정을 정리한 것입니다.

## 1. 개요

### 1.1 마이그레이션 배경
- MongoDB에서 PostgreSQL 기반의 Supabase로 데이터베이스 전환
- 더 나은 관계형 데이터 모델 활용 및 Supabase의 기능 활용

### 1.2 주요 변경사항
- 데이터베이스: MongoDB → PostgreSQL (Supabase)
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

## 3. 애플리케이션 코드 변경

### 3.1 데이터베이스 연결 코드

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

### 3.2 데이터 조회 코드

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

### 3.3 타임존 처리

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

## 4. 주요 이슈 및 해결 방법

### 4.1 GSSAPI 연결 오류
**문제:** `psycopg2.OperationalError: GSSAPI negotiation failed`

**해결:** 연결 설정에 `gssencmode='disable'` 추가

### 4.2 타임존 문제
**문제:** 커밋이 잘못된 날짜에 표시됨

**해결:** 
- `ts_for_db`가 이미 KST로 저장되어 있음을 확인
- 불필요한 타임존 변환 코드 제거

## 5. 검증 및 테스트

### 5.1 데이터 무결성 확인
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

### 5.2 애플리케이션 테스트
1. 출석 조회 기능 확인
2. 날짜별 조회 정확성 확인
3. 사용자별 통계 확인

## 6. 결론

MongoDB에서 Supabase(PostgreSQL)로의 마이그레이션은 다음과 같은 이점을 제공했습니다:
- 더 나은 쿼리 성능 (특히 날짜 범위 검색)
- JSONB를 활용한 유연한 스키마
- Supabase의 실시간 기능 활용 가능성
- 표준 SQL 사용으로 유지보수 용이

## 관련 문서
- [Python 버전 업그레이드 가이드](./PYTHON_VERSION_UPGRADE.md)
- [데이터 마이그레이션 스크립트 가이드](./DATA_MIGRATION_SCRIPT.md)
- [Docker 배포 가이드](./DOCKER_DEPLOYMENT.md)