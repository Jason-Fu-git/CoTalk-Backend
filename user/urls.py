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
    path('private/<user_id>/notification/', views.get_notification_list),
    path('private/<user_id>/notifications', views.all_notifications),
    path('private/<user_id>/notification/<notification_id>/detail', views.notification_detail_or_delete),
    path('private/<user_id>/notification/<notification_id>/read', views.read_notification),
]
