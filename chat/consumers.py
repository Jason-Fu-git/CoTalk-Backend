import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.utils import timezone
import urllib.parse
from user.models import User
from utils.utils_jwt import verify_a_user


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        # 解析 URL 查询参数
        query_params = urllib.parse.parse_qs(self.scope['query_string'].decode('utf-8'))

        # 获取 'auth' 参数的值
        jwt_token = query_params.get('Authorization', [''])[0]

        # 获取 'user_id' 的值
        user_id = query_params.get('user_id', [''])[0]

        if verify_a_user(user_id=user_id, req=None, token=jwt_token):
            self.user = User.objects.get(user_id=user_id)
            self.room_group_name = f'chat_simple'
            # 加入群组
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )
            self.accept()
        else:
            self.close()

    def disconnect(self, close_code):
        # 离开群组
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        print("Backend ChatConsumer receive: " + text_data)
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        now = timezone.now()
        # 将消息发到群组
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'datetime': now.isoformat(),
                'user': self.user.user_name,
            }
        )
        self.send(text_data=json.dumps({'message': message}))

    def chat_message(self, event):
        self.send(text_data=json.dumps(event))
