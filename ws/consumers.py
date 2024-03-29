import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import urllib.parse
from user.models import User
from message.models import Message
from utils.utils_jwt import verify_a_user
from utils.utils_require import require


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

    def chat_message_received(self, chat_id, msg_text, msg_type):
        """
        处理从聊天接收的消息
        :param chat_id: 聊天ID
        :param msg_text: 消息文本
        :param msg_type: 消息类型
        """
        # todo : demo version, 需通知前端从数据库中提取消息以保证同步

        # 将消息保存到数据库
        msg = Message.objects.create(sender=self.user, chat_id=chat_id,
                                     msg_text=msg_text, msg_type=msg_type)
        msg.read_users.add(self.user)
        msg.save()

        # 通知给所有在线用户
        async_to_sync(self.channel_layer.group_send)(
            f'chat_{chat_id}',
            {
                'type': 'chat.message',
                'status': 'sent',
                'message': msg_text,
                'datetime': msg.create_time.isoformat(),
                'user': self.user.user_name,
            }
        )

        # 将成功消息通知给前端
        self.send(text_data=json.dumps({
            'type': 'chat.message',
            'status': 'success',
            'msg_id': msg.msg_id,
            'create_time': msg.create_time.isoformat(),
        }))

    def friend_request_received(self, friend_id, is_approved=True):
        """
        处理从好友请求接收的消息
        :param friend_id: 好友ID
        :param is_approved: 是否同意
        """
        # 通知好友
        async_to_sync(self.channel_layer.send)(
            f'user_{friend_id}',
            {
                'type': 'user.friend_request',
                'status': 'sent',
                'user_id': self.user.user_id,
                'is_approved': is_approved
            }
        )

        # 将成功消息通知给前端
        self.send(text_data=json.dumps({
            'type': 'user.friend_request',
            'status': 'success',
        }))

    def receive(self, text_data):
        print("Backend ChatConsumer receive: " + text_data)
        text_data_json = json.loads(text_data)
        _type = ''
        try:
            _type = require(text_data_json, 'type', 'string')
            if _type == 'chat.message':
                chat_id = require(text_data_json, 'chat_id', 'int')
                msg_type = require(text_data_json, 'msg_type', 'string')
                if msg_type == 'T':  # 纯文本
                    msg_text = require(text_data_json, 'msg_text', 'string')
                    self.chat_message_received(chat_id, msg_text, msg_type)
            elif _type == 'user.friend_request':
                friend_id = require(text_data_json, 'friend_id', 'int')
                is_approved = require(text_data_json, 'is_approved', 'bool')
                self.friend_request_received(friend_id, is_approved)
        except Exception as e:
            if _type == '':
                self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid or missing message type'
                }))
            else:
                self.send(text_data=json.dumps({
                    'type': _type,
                    'status': 'error',
                    'info': str(e)
                }))
