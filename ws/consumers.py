import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import WebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
import urllib.parse
from .models import Client
from user.models import User
from message.models import Message
from utils.utils_jwt import verify_a_user
from utils.utils_require import require
from django.utils import timezone


class WSConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("hello there!")
        try:

            # 获取 'auth' 参数的值
            jwt_token = self.scope['url_route']['kwargs']['token']

            # 获取 'user_id' 的值
            user_id = int(self.scope['url_route']['kwargs']['user_id'])

            self.user: User = await self.get_user(user_id=user_id)

            exists = await self.client_exists(user_id=user_id)

            # 检查用户身份
            verify_a_user(salt=self.user.jwt_token_salt, user_id=user_id, req=None, token=jwt_token)

            # 如果不存在连接，则建立
            if not exists:
                print(f'Channel {self.channel_name} connected, user id: {user_id}')
                # 从数据库中提取群聊
                chat_ids = await self.get_chat_ids(user=self.user)
                if chat_ids is not None:
                    # 加入群组
                    for chat_id in chat_ids:
                        await self.channel_layer.group_add(
                            f'chat_{chat_id}',
                            self.channel_name)

                await self.accept()
                await self.create_client(user_id=user_id)
            else:
                # 否则，关闭连接
                print('User already connected')
                await self.close()

        except Exception as e:
            if isinstance(e, ValueError) and str(e).startswith('Unauthorized'):
                print('Authentication failed')
            print(f'Error: {str(e)}')
            await self.close()

    async def disconnect(self, close_code):
        try:
            # 从数据库中提取群聊
            chat_ids = await self.get_chat_ids(user=self.user)
            # 退出群组
            if chat_ids is not None:
                for chat_id in chat_ids:
                    await self.channel_layer.group_discard(
                        f'chat_{chat_id}',
                        self.channel_name)
            await self.delete_client()
            print(f'Channel {self.channel_name} disconnected, user_id:{self.user.user_id}')
        except Exception as e:
            print(e)

    # === 后端client之间通信处理 ===
    async def user_friend_request(self, event):
        """
        后端处理 `type` == `user.friend.request` 的事件
        :param event: 事件数据
        """
        print(f'Channel {self.user.user_id} received:', event)
        friend_id = require(event, 'user_id', 'int')
        status = require(event, 'status', 'string')
        is_approved = require(event, 'is_approved', 'bool')
        # 向前端发送消息
        await self.send(text_data=json.dumps(
            {
                'type': 'user.friend.request',
                'status': status,
                'user_id': friend_id,
                'is_approved': is_approved
            })
        )

    async def chat_message(self, event):
        """
        后端处理 `type` == `chat.message` 的事件
        :param event: 事件数据
        """
        print(f'Channel {self.user.user_id} received:', event)
        user_id = require(event, 'user_id', 'int')
        chat_id = require(event, 'chat_id', 'int')
        msg_id = require(event, 'msg_id', 'int')
        status = require(event, 'status', 'string')
        update_time = require(event, 'update_time', 'float')
        # 向前端发送消息
        await self.send(text_data=json.dumps(
            {
                'type': 'chat.message',
                'status': status,
                'user_id': user_id,
                'chat_id': chat_id,
                'msg_id': msg_id,
                'update_time': update_time
            }))

    async def chat_management(self, event):
        """
        后端处理 `type` == `chat.management` 的事件
        :param event: 事件数据
        """
        print(f'Channel {self.user.user_id} received:', event)
        user_id = require(event, 'user_id', 'int')
        chat_id = require(event, 'chat_id', 'int')
        status = require(event, 'status', 'string')
        is_approved = require(event, 'is_approved', 'bool')
        # 向前端发送消息
        await self.send(text_data=json.dumps(
            {
                'type': 'user.friend.request',
                'status': status,
                'user_id': user_id,
                'chat_id': chat_id,
                'is_approved': is_approved
            })
        )

    # === 后端client之间通信处理 ===

    # === DJANGO ORM I/O ===
    @database_sync_to_async
    def create_client(self, user_id):
        Client.objects.create(user_id=user_id, channel_name=self.channel_name)

    @database_sync_to_async
    def delete_client(self):
        Client.objects.filter(user_id=self.user.user_id).delete()

    @database_sync_to_async
    def get_client(self, user_id):
        return Client.objects.get(user_id=user_id)

    @database_sync_to_async
    def client_exists(self, user_id):
        return Client.objects.filter(user_id=user_id).exists()

    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(user_id=user_id)

    @database_sync_to_async
    def get_chat_ids(self, user):
        chats = self.user.get_chats()
        if len(chats) == 0:
            return None
        else:
            return [item['chat'] for item in chats]

    @database_sync_to_async
    def create_msg(self, chat_id, msg_text, msg_type):
        msg = Message.objects.create(sender=self.user, chat_id=chat_id,
                                     msg_text=msg_text, msg_type=msg_type)
        msg.read_users.add(self.user)
        msg.save()
        return msg

    # === DJANGO ORM I/O ===


# 公开论坛
class PiazzaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "piazza"
        # 加入群组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 离开群组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_id = text_data_json['sender_id']
        sender_name = text_data_json['sender_name']
        now = timezone.now()
        # 将消息发到群组
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'datetime': now.isoformat(),
                'sender_id': sender_id,
                'sender_name': sender_name,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))


# 聊天连接
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 利用路由变量确定聊天群组
        self.id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.id}'
        # TODO: 身份验证
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 离开群组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 从WebSocket获得消息
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_id = text_data_json['sender_id']
        sender_name = text_data_json['sender_name']
        now = timezone.now()
        # 将消息发到群组
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'datetime': now.isoformat(),
                'sender_id': sender_id,
                'sender_name': sender_name,
            }
        )

    # 从群组获得消息
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
