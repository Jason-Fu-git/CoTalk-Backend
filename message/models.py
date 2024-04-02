from django.db import models
from user.models import User
from chat.models import Chat
from utils.utils_require import MAX_MESSAGE_LENGTH
from utils.utils_time import get_timestamp


class Message(models.Model):
    """
    消息 model
    :var msg_id: 消息id
    :var sender: 发送者
    :var chat: 所属聊天（主要隶属关系）
    :var msg_text: 消息内容
    :var msg_file: （如果`msg_type`不是text的话）消息文件
    :var msg_type: 消息类型（从 'text', 'image', 'audio', 'video', 'others' 大写首字母中选择）
    :var create_time: 消息创建时间
    :var update_time: 消息状态更新时间
    """
    msg_id = models.BigAutoField(primary_key=True)

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_messages')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_messages')

    msg_text = models.CharField(max_length=MAX_MESSAGE_LENGTH)
    msg_file = models.FileField(upload_to='../assets/messages/', blank=True)
    msg_type = models.CharField(max_length=10, choices=(('T', 'text'),
                                                        ('I', 'image'), ('A', 'audio'), ('V', 'video'),
                                                        ('O', 'others')))
    create_time = models.FloatField(default=get_timestamp)
    update_time = models.FloatField(default=get_timestamp)

    read_users = models.ManyToManyField(User, related_name='read_messages')

    def __str__(self) -> str:
        return f"{self.msg_id}'s type is {self.msg_type}, content is {self.msg_text}"


class Notification(models.Model):
    """
    通知（主要隶属关系）
    :var receiver: 接收者
    :var sender: 发送者
    :var content: 通知内容
    :var create_time: 通知创建时间
    :var is_read: 是否已读
    """
    notification_id = models.BigAutoField(primary_key=True)

    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receiver_notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sender_notifications')

    content = models.CharField(max_length=MAX_MESSAGE_LENGTH)
    create_time = models.FloatField(default=get_timestamp)
    is_read = models.BooleanField(default=False)

    def serialize(self):
        return {
            'notification_id': self.notification_id,
            'receiver_id': self.receiver.user_id,
            'sender_id': self.sender.user_id,
            'content': self.content,
            'create_time': self.create_time,
            'is_read': self.is_read
        }

    def __str__(self):
        return f"{self.notification_id}'s content is {self.content}, the receiver is {self.receiver}"
