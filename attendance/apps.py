from django.apps import AppConfig
import configparser
import slack
import os
import yaml


class AttendanceConfig(AppConfig):
    name = 'attendance'
