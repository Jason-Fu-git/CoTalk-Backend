from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login),
    path('search', views.search),
    path('private/<user_id>', views.user_management),
    path('private/<user_id>/friends', views.friend_management),
    path('private/<user_id>/chats', views.user_chats_management),
    path('private/<user_id>/avatar', views.get_user_avatar),
    path('private/<user_id>/notifications', views.get_notification_list),
    path('private/<user_id>/notification/<notification_id>', views.notification_detail_or_delete_or_read),
    path('private/<user_id>/verification', views.user_verification),
    path('rsa', views.default_rsa_key)
]
