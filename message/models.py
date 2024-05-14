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
    :var msg_type: 消息类型（从 'text', 'group_notice', 'image', 'audio', 'video', 'others' 大写首字母中选择）
    :var create_time: 消息创建时间
    :var update_time: 消息状态更新时间
    :var read_users: 已经读取消息的用户
    :var unable_to_see_users: 不可视该消息的用户 （用户在前端标记删除）
    :var reply_to : 回复某消息，默认为-1，表示没有指定回复
    :var is_system: 是否为系统消息
    """
    msg_id = models.BigAutoField(primary_key=True)

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_messages')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_messages')

    msg_text = models.CharField(max_length=MAX_MESSAGE_LENGTH)
    msg_file = models.FileField(upload_to=f'assets/message/', blank=True)
    msg_type = models.CharField(max_length=10, choices=(('T', 'text'), ('G', 'group_notice'),
                                                        ('I', 'image'), ('A', 'audio'), ('V', 'video'),
                                                        ('O', 'others')), default='T')
    create_time = models.FloatField(default=get_timestamp)
    update_time = models.FloatField(default=get_timestamp)

    read_users = models.ManyToManyField(User, related_name='read_messages')
    unable_to_see_users = models.ManyToManyField(User, related_name='unable_to_see_messages')

    reply_to = models.IntegerField(default=-1)

    is_system = models.BooleanField(default=False)

    def serialize(self):
        return {
            'msg_id': self.msg_id,
            'sender_id': self.sender.user_id,
            'chat_id': self.chat.chat_id,

            'msg_text': self.msg_text,
            'msg_file_url': "",
            'msg_type': self.msg_type,

            'create_time': self.create_time,
            'update_time': self.update_time,

            'read_users': [user.user_id for user in self.read_users.all()],
            'unable_to_see_users': [user.user_id for user in self.unable_to_see_users.all()],

            'reply_to': self.reply_to,
            'is_system': self.is_system
        }

    def __str__(self) -> str:
        if self.is_system:
            return f"system information {self.msg_text}"
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

    content = models.CharField(max_length=MAX_MESSAGE_LENGTH, blank=False)
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


def withdraw_a_message(user_id, chat_id):
    """
    为“撤回”事件创建系统通知
    :param user_id: 用户id
    :param chat_id: 聊天id
    """
    system_user = User.objects.get(user_name='system')
    user = User.objects.get(user_id=user_id)
    chat = Chat.objects.get(chat_id=chat_id)
    message = Message.objects.create(sender=system_user, chat_id=chat_id, is_system=True,
                                     msg_text=f'{user.user_name} withdrawn a message.')
    message.read_users.add(user)
    message.save()


def kick_a_person(admin_id, member_id, chat_id):
    """
    为“踢出”事件创建系统通知
    :param admin_id: 管理员id
    :param member_id: 被踢者id
    :param chat_id: 聊天id
    """
    system_user = User.objects.get(user_name='system')
    admin = User.objects.get(user_id=admin_id)
    member = User.objects.get(user_id=member_id)
    message = Message.objects.create(sender=system_user, chat_id=chat_id, is_system=True,
                                     msg_text=f'{admin.user_name} kicked {member.user_name} out of the chat.')
    message.read_users.add(admin)
    message.save()


def join_a_chat(user_id, chat_id):
    """
    为“加入”事件创建系统通知
    :param user_id: 用户id
    :param chat_id: 聊天id
    """
    system_user = User.objects.get(user_name='system')
    user = User.objects.get(user_id=user_id)
    message = Message.objects.create(sender=system_user, chat_id=chat_id, is_system=True,
                                     msg_text=f'{user.user_name} joined the chat.')
    message.read_users.add(user)
    message.save()


def change_privilege(admin_id, member_id, chat_id, privilege):
    """
    为“更改权限”事件创建系统通知
    :param admin_id: 管理员id
    :param member_id: 被更改权限者id
    :param chat_id: 聊天id
    :param privilege: 更改权限的消息
    """
    system_user = User.objects.get(user_name='system')
    admin = User.objects.get(user_id=admin_id)
    member = User.objects.get(user_id=member_id)
    message = Message.objects.create(sender=system_user, chat_id=chat_id, is_system=True,
                                     msg_text=f'{admin.user_name} changed {member.user_name}\'s privilege to {privilege}.')
    message.read_users.add(admin)
    message.save()


def leave_chat(user_id, chat_id):
    """
    为“离开”事件创建系统通知
    :param user_id: 用户id
    :param chat_id: 聊天id
    """
    system_user = User.objects.get(user_name='system')
    user = User.objects.get(user_id=user_id)
    message = Message.objects.create(sender=system_user, chat_id=chat_id, is_system=True,
                                     msg_text=f'{user.user_name} left the chat.')
    message.save()
