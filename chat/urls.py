from django.urls import path
from . import views

urlpatterns = [
    path('create', views.create_a_chat),
    path('<chat_id>/members', views.chat_members),
    path('<chat_id>/detail', views.get_chat_detail),
    path('<chat_id>/management', views.chat_management),
    path('<chat_id>/messages', views.get_messages),
]
