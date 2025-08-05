# 데이터 마이그레이션 스크립트 가이드

이 문서는 MongoDB에서 Supabase로 데이터를 마이그레이션하는 스크립트에 대한 상세 설명입니다.

## 1. 마이그레이션 스크립트 (`migrate_to_supabase.py`)

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

## 2. 마이그레이션 실행 과정

### 2.1 사전 준비
1. MongoDB 데이터를 BSON 파일로 덤프
   ```bash
   mongodump --db=your_db --collection=slack_messages --out=backup
   ```

2. Supabase에 스키마 및 테이블 생성
   - PostgreSQL 테이블 구조는 메인 마이그레이션 문서 참조

### 2.2 스크립트 실행
```bash
python migrate_to_supabase.py
```

### 2.3 데이터 검증
```sql
-- 전체 레코드 수 확인
SELECT COUNT(*) FROM garden5.slack_messages;

-- 샘플 데이터 확인
SELECT * FROM garden5.slack_messages LIMIT 10;
```

## 3. 성능 최적화

### 3.1 배치 삽입
- `execute_values` 사용으로 삽입 성능 향상
- 1000개씩 배치 처리

### 3.2 인덱스 생성
- 마이그레이션 완료 후 인덱스 생성으로 시간 단축

## 4. 에러 처리

### 4.1 BSON 파싱 에러
- 손상된 문서는 스킵하고 로그 기록
- 전체 프로세스는 계속 진행

### 4.2 데이터 타입 변환
- MongoDB의 ObjectId는 문자열로 변환
- Date 객체는 PostgreSQL timestamp로 변환

## 5. 롤백 계획
- 마이그레이션 전 전체 백업 필수
- 실패 시 테이블 DROP 후 재실행