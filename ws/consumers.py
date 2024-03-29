import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.utils import timezone
import urllib.parse
from user.models import User
from utils.utils_jwt import verify_a_user


# todo : this is a sync consumer, need to be async
class WSConsumer(WebsocketConsumer):
    def connect(self):
        # 解析 URL 查询参数
        query_params = urllib.parse.parse_qs(self.scope['query_string'].decode('utf-8'))

        # 获取 'auth' 参数的值
        jwt_token = query_params.get('Authorization', [''])[0]

        # 获取 'user_id' 的值
        user_id = query_params.get('user_id', [''])[0]

        # 如果登录认证通过
        if verify_a_user(user_id=user_id, req=None, token=jwt_token):
            self.user: User = User.objects.get(user_id=user_id)
            self.channel_name = f'user_{self.user.user_id}'
            # 从数据库中提取群聊
            chat_ids = [item['chat'] for item in self.user.get_chats()]
            # 加入群组
            for chat_id in chat_ids:
                async_to_sync(self.channel_layer.group_add)(
                    f'chat_{chat_id}',
                    self.channel_name
                )
            self.accept()
        else:
            self.close()

    def disconnect(self, close_code):
        # 从数据库中提取群聊
        chat_ids = [item['chat'] for item in self.user.get_chats()]
        # 退出群组
        for chat_id in chat_ids:
            async_to_sync(self.channel_layer.group_discard)(
                f'chat_{chat_id}',
                self.channel_name
            )

    def receive(self, text_data):
        print("Backend ChatConsumer receive: " + text_data)
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        now = timezone.now()
        # 从数据库中提取群聊
        # todo : maybe inefficient
        chat_ids = [item['chat'] for item in self.user.get_chats()]
        # 将消息发到群组
        for chat_id in chat_ids:
            async_to_sync(self.channel_layer.group_send)(
                f'chat_{chat_id}',
                {
                    'type': 'chat_message',
                    'message': message,
                    'datetime': now.isoformat(),
                    'user': self.user.user_name,
                }
            )
        self.send(text_data=json.dumps({'message': message}))
