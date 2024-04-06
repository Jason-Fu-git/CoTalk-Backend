from django.urls import path
from . import views

url_patterns = [
    path('', views.create_a_chat),
    path('<chat_id>/members', views.chat_members),
    path('<chat_id>/management', views.chat_management),
]
