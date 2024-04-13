from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/', consumers.WSConsumer.as_asgi()),
    path('ws/piazza', consumers.PiazzaConsumer.as_asgi()),
    path('ws/chat/<user_id>/<chat_id>', consumers.ChatConsumer.as_asgi()),
]