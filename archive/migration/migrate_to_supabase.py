#!/usr/bin/env python3
"""
Garden5 MongoDB to Supabase Migration Script
Enhanced version based on garden4 migration experience
"""
import psycopg2
import bson
import json
from datetime import datetime, timedelta
import os
import logging
import getpass
from psycopg2.extras import execute_values, RealDictCursor
from typing import List, Dict, Any, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_config():
    """데이터베이스 연결 정보를 환경변수 또는 사용자 입력으로 가져오기"""
    
    print("=== Supabase PostgreSQL 연결 설정 ===")
    
    # 환경변수에서 먼저 확인
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER') 
    db_password = os.getenv('DB_PASSWORD')
    
    # 환경변수가 없으면 사용자 입력 받기
    if not db_host:
        db_host = input("DB Host [aws-0-ap-northeast-2.pooler.supabase.com]: ").strip()
        if not db_host:
            db_host = 'aws-0-ap-northeast-2.pooler.supabase.com'
    
    if not db_user:
        db_user = input("DB User [postgres.schejihwxwsvaduhpkbe]: ").strip()
        if not db_user:
            db_user = 'postgres.schejihwxwsvaduhpkbe'
    
    if not db_password:
        db_password = getpass.getpass("DB Password: ")
        if not db_password:
            print("❌ 비밀번호는 필수입니다!")
            exit(1)
    
    print(f"✅ 연결 설정: {db_user}@{db_host}")
    
    return {
        'database': os.getenv('DB_NAME', 'postgres'),
        'host': db_host,
        'port': int(os.getenv('DB_PORT', 6543)),
        'user': db_user,
        'password': db_password,
        'sslmode': 'require',
        'gssencmode': 'disable'
    }

SCHEMA_NAME = os.getenv('DB_SCHEMA', 'garden5')

def create_connection(db_config):
    """PostgreSQL 연결 생성"""
    try:
        conn = psycopg2.connect(**db_config)
        # 스키마 설정
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {SCHEMA_NAME}")
        cursor.close()
        logger.info(f"PostgreSQL 연결 성공: {db_config['host']}")
        return conn
    except Exception as e:
        logger.error(f"연결 오류: {e}")
        return None

def read_bson_file(file_path):
    """BSON 파일 읽기"""
    documents = []
    with open(file_path, 'rb') as f:
        while True:
            try:
                # BSON 문서 크기 읽기 (4 bytes)
                size_data = f.read(4)
                if not size_data:
                    break
                
                # 크기 정보를 포함한 전체 문서 읽기
                size = int.from_bytes(size_data, 'little')
                f.seek(-4, 1)  # 4바이트 뒤로
                doc_data = f.read(size)
                
                if doc_data:
                    doc = bson.decode(doc_data)
                    documents.append(doc)
            except Exception as e:
                print(f"문서 읽기 오류: {e}")
                break
    return documents

def format_timestamp(ts_string):
    """Slack 타임스탬프를 PostgreSQL TIMESTAMP로 변환"""
    try:
        ts_float = float(ts_string)
        return datetime.fromtimestamp(ts_float)
    except:
        return None

def prepare_document_for_insert(doc):
    """MongoDB 문서를 PostgreSQL 삽입용으로 변환"""
    ts = doc.get('ts')
    ts_for_db = format_timestamp(ts) if ts else None
    
    if not ts or not ts_for_db:
        return None
    
    return (
        ts,
        ts_for_db,
        doc.get('bot_id'),
        doc.get('type'),
        doc.get('text'),
        doc.get('user'),
        doc.get('team'),
        json.dumps(doc.get('bot_profile')) if doc.get('bot_profile') else None,
        json.dumps(doc.get('attachments')) if doc.get('attachments') else None
    )

def migrate_data():
    """BSON 데이터를 Supabase로 마이그레이션"""
    bson_file = "/Users/junho85/PycharmProjects/garden5/archive/20250802_mongodb_dump/slack_messages.bson"
    
    # DB 연결 설정 가져오기
    db_config = get_db_config()
    
    print("\n1. BSON 파일 읽기 시작...")
    documents = read_bson_file(bson_file)
    print(f"   - {len(documents)}개의 문서를 읽었습니다.")
    
    print("\n2. PostgreSQL 연결...")
    conn = create_connection(db_config)
    if not conn:
        print("   - 연결 실패!")
        return
    
    cur = conn.cursor()
    
    try:
        # garden5 스키마가 존재하는지 확인
        print("\n3. garden5 스키마 확인...")
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'garden5'")
        if not cur.fetchone():
            print("   - garden5 스키마가 없습니다. supabase_schema.sql을 먼저 실행해주세요.")
            return
        
        # 기존 데이터 개수 확인
        cur.execute("SELECT COUNT(*) FROM garden5.slack_messages")
        existing_count = cur.fetchone()[0]
        print(f"   - 기존 데이터: {existing_count}개")
        
        # 데이터 변환 및 준비
        print("\n4. 데이터 변환 중...")
        insert_data = []
        skipped = 0
        
        for doc in documents:
            prepared = prepare_document_for_insert(doc)
            if prepared:
                insert_data.append(prepared)
            else:
                skipped += 1
        
        print(f"   - 변환 완료: {len(insert_data)}개 (스킵: {skipped}개)")
        
        if insert_data:
            print("\n5. 데이터 삽입 중...")
            
            # 배치 삽입 (성능 최적화)
            insert_query = """
                INSERT INTO garden5.slack_messages 
                (ts, ts_for_db, bot_id, type, text, "user", team, bot_profile, attachments)
                VALUES %s
                ON CONFLICT (ts) DO NOTHING
            """
            
            # 1000개씩 배치 처리
            batch_size = 1000
            inserted_total = 0
            
            for i in range(0, len(insert_data), batch_size):
                batch = insert_data[i:i+batch_size]
                execute_values(cur, insert_query, batch)
                conn.commit()
                inserted_total += cur.rowcount
                print(f"   - 진행률: {i+len(batch)}/{len(insert_data)} ({inserted_total}개 삽입됨)")
            
            print(f"\n6. 마이그레이션 완료!")
            print(f"   - 총 {inserted_total}개의 레코드가 삽입되었습니다.")
            
            # 최종 데이터 개수 확인
            cur.execute("SELECT COUNT(*) FROM garden5.slack_messages")
            final_count = cur.fetchone()[0]
            print(f"   - 최종 데이터 개수: {final_count}개")
            
            # 샘플 데이터 확인
            cur.execute("""
                SELECT ts, ts_for_db, text, attachments->0->>'author_name' as author
                FROM garden5.slack_messages 
                WHERE attachments IS NOT NULL 
                LIMIT 5
            """)
            
            print("\n7. 샘플 데이터:")
            for row in cur.fetchall():
                print(f"   - {row[1]}: {row[3]} - {row[2][:50]}...")
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("=== Garden5 MongoDB to Supabase 마이그레이션 ===\n")
    migrate_data()