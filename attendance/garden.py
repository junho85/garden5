import configparser
from datetime import date, timedelta, datetime
from slack_sdk import WebClient
import psycopg2
import psycopg2.extras
import json
import os
import yaml


class Garden:
    def __init__(self):
        config = configparser.ConfigParser()
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(BASE_DIR, 'config.ini')
        config.read(path)

        # Use environment variables if available, otherwise fallback to config file
        slack_api_token = os.getenv('SLACK_API_TOKEN', config['DEFAULT']['SLACK_API_TOKEN'])
        self.slack_client = WebClient(token=slack_api_token)

        self.channel_id = os.getenv('CHANNEL_ID', config['DEFAULT']['CHANNEL_ID'])

        # PostgreSQL settings - prioritize environment variables
        if 'POSTGRESQL' in config:
            self.pg_database = os.getenv('DB_NAME', config['POSTGRESQL']['DATABASE'])
            self.pg_host = os.getenv('DB_HOST', config['POSTGRESQL']['HOST'])
            self.pg_port = os.getenv('DB_PORT', config['POSTGRESQL']['PORT'])
            self.pg_user = os.getenv('DB_USER', config['POSTGRESQL']['USER'])
            self.pg_password = os.getenv('DB_PASSWORD', config['POSTGRESQL']['PASSWORD'])
            self.pg_schema = os.getenv('DB_SCHEMA', config['POSTGRESQL']['SCHEMA'])
        else:
            # Default values if POSTGRESQL section doesn't exist
            self.pg_database = os.getenv('DB_NAME', 'postgres')
            self.pg_host = os.getenv('DB_HOST', 'localhost')
            self.pg_port = os.getenv('DB_PORT', '5432')
            self.pg_user = os.getenv('DB_USER', 'postgres')
            self.pg_password = os.getenv('DB_PASSWORD', '')
            self.pg_schema = os.getenv('DB_SCHEMA', 'garden5')

        self.gardening_days = os.getenv('GARDENING_DAYS', config['DEFAULT']['GARDENING_DAYS'])

        # users list ['junho85', 'user2', 'user3']
        # self.users = config['GITHUB']['USERS'].split(',')

        # users_with_slackname
        path = os.path.join(BASE_DIR, 'users.yaml')

        with open(path) as file:
            self.users_with_slackname = yaml.safe_load(file)

        self.users = list(self.users_with_slackname.keys())

        self.start_date = datetime.strptime(config['DEFAULT']['START_DATE'],
                                            "%Y-%m-%d").date()  # start_date e.g.) 2020-03-02

    def connect_postgres(self):
        """PostgreSQL 연결 생성"""
        conn = psycopg2.connect(
            host=self.pg_host,
            port=self.pg_port,
            database=self.pg_database,
            user=self.pg_user,
            password=self.pg_password,
            sslmode='require',
            gssencmode='disable'
        )
        # 연결 후 스키마 설정
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {self.pg_schema}")
        cursor.close()
        return conn

    def get_database(self):
        return self.connect_postgres()

    def get_member(self):
        return self.users

    def get_gardening_days(self):
        return self.gardening_days

    '''
    github userid - slack username
    '''

    def get_members(self):
        return self.users_with_slackname

    # 특정 유저의 전체 출석부를 생성함
    # TODO 출석부를 DB에 넣고 마지막 생성된 출석부 이후의 데이터로 추가 출석부 만들도록 하자
    def find_attendance_by_user(self, user):
        return self._find_attendance_by_user_postgres(user)

    def _find_attendance_by_user_postgres(self, user):
        """PostgreSQL을 사용한 출석부 조회"""
        conn = self.connect_postgres()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        result = {}
        start_date = self.start_date

        try:
            # PostgreSQL JSONB 쿼리: 사용자별 첨부파일이 있는 메시지 조회
            query = """
                SELECT ts, ts_for_db, attachments
                FROM slack_messages 
                WHERE attachments @> %s
                ORDER BY ts
            """
            
            # JSONB 쿼리 파라미터
            param = json.dumps([{"author_name": user}])
            cursor.execute(query, (param,))
            
            for message in cursor.fetchall():
                # make attend
                commits = []
                attachments = message['attachments']
                if attachments:
                    for attachment in attachments:
                        if attachment.get('author_name') == user and attachment.get('text'):
                            commits.append(attachment.get('text', ''))

                # skip - if there is no commits
                if len(commits) == 0:
                    continue

                # DB의 ts_for_db는 이미 KST로 저장되어 있음
                # 추가 타임존 변환 불필요
                ts_datetime = message['ts_for_db']
                attend = {"ts": ts_datetime, "message": commits}

                # current date and date before day1
                date = ts_datetime.date()
                date_before_day1 = date - timedelta(days=1)
                hour = ts_datetime.hour

                if date_before_day1 >= start_date and hour < 4 and date_before_day1 not in result:
                    # check before day1. if exists, before day1 is already done.
                    result[date_before_day1] = []
                    result[date_before_day1].append(attend)
                else:
                    # create date commits array
                    if date not in result:
                        result[date] = []

                    result[date].append(attend)

        except Exception as e:
            print(f"Error in _find_attendance_by_user_postgres: {e}")
        finally:
            cursor.close()
            conn.close()

        return result


    # github 봇으로 모은 slack message 들을 DB에 저장
    def collect_slack_messages(self, oldest, latest):
        return self._collect_slack_messages_postgres(oldest, latest)

    def _collect_slack_messages_postgres(self, oldest, latest):
        """PostgreSQL에 Slack 메시지 저장"""
        response = self.slack_client.conversations_history(
            channel=self.channel_id,
            latest=str(latest),
            oldest=str(oldest),
            limit=1000
        )

        conn = self.connect_postgres()
        cursor = conn.cursor()

        for message in response["messages"]:
            # Slack 타임스탬프를 datetime으로 변환하고 KST로 저장
            utc_time = datetime.fromtimestamp(float(message["ts"]))
            ts_for_db = utc_time + timedelta(hours=9)  # UTC → KST
            
            # PostgreSQL INSERT 쿼리
            insert_query = """
                INSERT INTO slack_messages (
                    ts, ts_for_db, bot_id, type, text, "user", team, 
                    bot_profile, attachments
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (ts) DO NOTHING
            """
            
            try:
                cursor.execute(insert_query, (
                    message.get("ts"),
                    ts_for_db,
                    message.get("bot_id"),
                    message.get("type"),
                    message.get("text"),
                    message.get("user"),
                    message.get("team"),
                    json.dumps(message.get("bot_profile")) if message.get("bot_profile") else None,
                    json.dumps(message.get("attachments")) if message.get("attachments") else None
                ))
            except Exception as err:
                print(f"Error inserting message: {err}")
                continue

        conn.commit()
        cursor.close()
        conn.close()


    """
    db 에 수집한 slack 메시지 삭제
    """
    def remove_all_slack_messages(self):
        conn = self.connect_postgres()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM slack_messages")
        conn.commit()
        cursor.close()
        conn.close()

    """
    특정일의 출석 데이터 불러오기
    @param selected_date
    """
    def get_attendance(self, selected_date):
        attend_dict = {}

        # get all users attendance info
        for user in self.users:
            attends = self.find_attendance_by_user(user)
            attend_dict[user] = attends

        result = {}
        result_attendance = []

        # make users - dates - first_ts
        for user in attend_dict:
            if user not in result:
                result[user] = {}

            result[user][selected_date] = None

            if selected_date in attend_dict[user]:
                result[user][selected_date] = attend_dict[user][selected_date][0]["ts"]

            result_attendance.append({"user": user, "first_ts": result[user][selected_date]})

        return result_attendance

    def send_no_show_message(self):
        members = self.get_members()
        today = datetime.today().date()

        message = "[미출석자 알람]\n"
        results = self.get_attendance(today)
        for result in results:
            if result["first_ts"] is None:
                message += "@%s " % members[result["user"]]["slack"]

        self.slack_client.chat_postMessage(
            channel='#gardening-for-100days',
            text=message,
            link_names=1
        )

    def test_slack(self):
        # self.slack_client.chat_postMessage(
        #     channel='#junekim', # temp
        #     text='@junho85 test',
        #     link_names=1
        # )
        response = self.slack_client.users_list()
        print(response)
