import configparser
from datetime import date, timedelta, datetime
import slack
import pymongo
import pprint
import os
import yaml


class Garden:
    def __init__(self):
        config = configparser.ConfigParser()
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(BASE_DIR, 'config.ini')
        config.read(path)

        slack_api_token = config['DEFAULT']['SLACK_API_TOKEN']
        self.slack_client = slack.WebClient(token=slack_api_token)

        self.channel_id = config['DEFAULT']['CHANNEL_ID']

        self.mongo_database = config['MONGO']['DATABASE']
        self.mongo_host = config['MONGO']['HOST']
        self.mongo_port = config['MONGO']['PORT']

        self.gardening_days = config['DEFAULT']['GARDENING_DAYS']

        # mongodb collections
        self.mongo_collection_slack_message = "slack_messages"

        # users list ['junho85', 'user2', 'user3']
        # self.users = config['GITHUB']['USERS'].split(',')

        # users_with_slackname
        path = os.path.join(BASE_DIR, 'users.yaml')

        with open(path) as file:
            self.users_with_slackname = yaml.full_load(file)

        self.users = list(self.users_with_slackname.keys())

        self.start_date = datetime.strptime(config['DEFAULT']['START_DATE'],
                                            "%Y-%m-%d").date()  # start_date e.g.) 2020-03-02

    def connect_mongo(self):
        return pymongo.MongoClient("mongodb://%s:%s" % (self.mongo_host, self.mongo_port))

    def get_member(self):
        return self.users

    def get_gardening_days(self):
        return self.gardening_days

    '''
    github userid - slack username
    '''

    def get_members(self):
        return self.users_with_slackname

    def find_attend(self, oldest, latest):
        print("find_attend")
        print(oldest)
        print(datetime.fromtimestamp(oldest))
        print(latest)
        print(datetime.fromtimestamp(latest))

        conn = self.connect_mongo()

        db = conn.get_database(self.mongo_database)
        mongo_collection = db.get_collection(self.mongo_collection_slack_message)

        for message in mongo_collection.find(
                {"ts_for_db": {"$gte": datetime.fromtimestamp(oldest), "$lt": datetime.fromtimestamp(latest)}}):
            print(message["ts"])
            print(message)

    # 특정 유저의 전체 출석부를 생성함
    # TODO 출석부를 DB에 넣고 마지막 생성된 출석부 이후의 데이터로 추가 출석부 만들도록 하자
    def find_attendance_by_user(self, user):
        conn = self.connect_mongo()

        db = conn.get_database(self.mongo_database)
        mongo_collection = db.get_collection(self.mongo_collection_slack_message)

        result = {}

        start_date = self.start_date
        for message in mongo_collection.find({"attachments.author_name": user}).sort("ts", 1):
            # make attend
            commits = []
            for attachment in message["attachments"]:
                try:
                    # commit has text field
                    # there is no text field in pull request, etc...
                    commits.append(attachment["text"])
                except Exception as err:
                    print(message["attachments"])
                    print(err)
                    continue

            # skip - if there is no commits
            if len(commits) == 0:
                continue

            # ts_datetime = datetime.fromtimestamp(float(message["ts"]))
            ts_datetime = message["ts_for_db"]
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

        return result

    # github 봇으로 모은 slack message 들을 slack_messages collection 에 저장
    def collect_slack_messages(self, oldest, latest):

        response = self.slack_client.channels_history(
            channel=self.channel_id,
            latest=str(latest),
            oldest=str(oldest),
            count=1000
        )

        conn = self.connect_mongo()

        db = conn.get_database(self.mongo_database)
        mongo_collection = db.get_collection(self.mongo_collection_slack_message)

        for message in response["messages"]:
            message["ts_for_db"] = datetime.fromtimestamp(float(message["ts"]))
            # pprint.pprint(message)

            try:
                mongo_collection.insert_one(message)
            except pymongo.errors.DuplicateKeyError as err:
                print(err)
                continue

    """
    db 에 수집한 slack 메시지 삭제
    """
    def remove_all_slack_messages(self):
        conn = self.connect_mongo()

        mongo_database = self.mongo_database

        db = conn.get_database(mongo_database)

        mongo_collection = db.get_collection(self.mongo_collection_slack_message)
        mongo_collection.remove()

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
