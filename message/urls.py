from django.urls import path
from . import views

urlpatterns = [
     path('<message_id>/management', views.message_management),
     path('send', views.post_message)
]