from django.urls import path
from . import views

app_name = 'attendance'
urlpatterns = [
    path('', views.index, name='index'), # 출석부 첫화면
    path('api/users/', views.users, name='users'), # 정원사들 리스트
    path('api/gets', views.gets, name='get'), # 전체 출석부 조회. 리스트. 유저별.
    path('collect/', views.collect, name='collect'), # slack_messages 수집
    path('get/<date>', views.get, name='get'), # 특정일의 출석부 조회. 날짜기준

    path('users/<user>/', views.user, name='user'), # 유저별 출석부 데이터 페이지
    path('api/users/<user>/', views.user_api, name='user'), # 특정 유저의 출석 데이터
]
