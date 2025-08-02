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

3. **Django 마이그레이션**
   ```bash
   python manage.py migrate
   ```

4. **개발 서버 실행**
   ```bash
   python manage.py runserver
   ```

5. **브라우저에서 확인**
   - http://localhost:8000 접속

### 주요 변경사항 (Python 3.11 업그레이드)
- Python 3.7.5 → 3.11.11
- Django 3.0 → 4.2
- slack → slack_sdk
- python-markdown-slack → 커스텀 Slack 마크다운 확장

## 참고
* [github](https://github.com/junho85/garden4)