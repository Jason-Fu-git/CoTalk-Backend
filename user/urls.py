from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login),
    path('<user_id>', views.update_or_delete),
    path('<user_id>/friends', views.friend_management),
]
