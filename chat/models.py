from django.db import models
from user.models import User
from utils.utils_require import MAX_NAME_LENGTH
from utils.utils_time import get_timestamp


# Create your models here.
class Chat(models.Model):
    """
    聊天 model
    :var chat_id: 聊天id
    :var chat_name: 聊天名称
    :var create_time: 聊天创建时间
    :var is_private: 是否为私聊
    """
    chat_id = models.BigAutoField(primary_key=True)
    chat_name = models.CharField(max_length=MAX_NAME_LENGTH)
    create_time = models.FloatField(default=get_timestamp)
    is_private = models.BooleanField(default=True)

    class Meta:
        unique_together = ('is_private', 'chat_name')

    def serialize(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "chat_name": self.chat_name,
            "create_time": self.create_time,
            "is_private": self.is_private
        }

    def get_memberships(self) -> models.QuerySet:
        return self.chat_membership.filter(is_approved=True).all()

    def get_owner(self) -> User:
        """
        获取群聊的群主，必须唯一
        """
        queryset = self.get_memberships().filter(privilege='O').all()
        if queryset.count() != 1:
            pass  # TODO 抛出异常
        return queryset.first().user

    def get_admins(self) -> models.QuerySet:
        """
        获取群管理员（可以为空）
        """
        return self.get_memberships().filter(privilege='A').all()

    def get_messages(self, timestamp, user_id):
        """
        获取晚于timestamp的消息
        """
        return self.chat_messages.exclude(
            self.chat_messages.filter(timestamp__gt=timestamp, unable_to_see_users__user_id=user_id)
        )

    def __str__(self) -> str:
        return f"{self.chat_name}"


class Membership(models.Model):
    """
    群组成员 model
    :var user: 用户
    :var chat: 群组
    :var privilege: 成员权限，包括群主(owner)、成员(member)、管理员(admin)
    :var update_time: 关系更新时间
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_membership')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_membership')
    privilege = models.CharField(max_length=10, choices=(('M', 'member'), ('O', 'owner'), ('A', 'admin')))
    update_time = models.FloatField(default=get_timestamp)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'chat')

    def __str__(self) -> str:
        return f"{self.user.user_name} is {self.privilege} of {self.chat.chat_name}"
