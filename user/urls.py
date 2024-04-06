from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login),
    path('<user_id>', views.user_management),
    path('<user_id>/friends', views.friend_management),
    path('', views.search_for_users),
    path('<user_id>/chats', views.user_chats_management)
]
