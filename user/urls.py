from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login),
    path('search', views.all_users),
    path('search/<search_text>', views.search),
    path('private/<user_id>', views.user_management),
    path('private/<user_id>/friends', views.friend_management),
    path('private/<user_id>/chats', views.user_chats_management),

]
