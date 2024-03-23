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
