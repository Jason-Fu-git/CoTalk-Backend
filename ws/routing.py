from django.urls import path, re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/main/(?P<user_id>\d+)/$', consumers.WSConsumer.as_asgi()),
    # path('ws/piazza', consumers.PiazzaConsumer.as_asgi()),
    # re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
