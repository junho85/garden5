# 정원사들 시즌5 출석부 문서


## Slack Github Bot 연동
[Slack + GitHub](https://slack.github.com/) 에서 "Add to Slack" 눌러서 Slack 에 GitHub Bot 을 연동합니다.

## Slack API Token 발급
[Legacy tokens](https://api.slack.com/custom-integrations/legacy-tokens) 에서 Token 을 발급 받습니다.

## 01.mongodb
Slack API 이용해서 commit push 메시지들을 수집합니다. mongodb 를 이용합니다.  
자세한 내용은 [01.mongodb](01.mongodb.md) 을 참고합니다.

## 02.설정. config.ini, users.yaml
config.ini 에 slack api token, db 설정 등을 해줍니다.
users.yaml 에 slack 유저명에 github 유저명을 설정해 줍니다.
자세한 설정방법
[01.configuration](02.configuration.md)

## 02.Django 세팅
[02.Django](https://github.com/junho85/garden5/wiki/02.Django)

## 06.cron
[06.cron](https://github.com/junho85/garden5/wiki/06.cron)

## 09.배포
[09.deployment](https://github.com/junho85/garden5/wiki/09.deployment)

## 11.slack message
[11.slack message](https://github.com/junho85/garden5/wiki/11.slack-message)

## 12.API
[12.API](https://github.com/junho85/garden5/wiki/12.API)
