from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from utils.utils_time import get_timestamp
from utils.utils_require import MAX_NAME_LENGTH, MAX_EMAIL_LENGTH, MAX_DESCRIPTION_LENGTH

import os


class User(models.Model):
    """
    用户 model
    :var user_id: 用户id
    :var user_name: 用户名
    :var password: 密码
    :var register_time: 注册时间
    :var login_time: 登录时间
    :var user_email: 用户邮箱
    :var user_icon: 用户头像
    :var jwt_token_salt : 该用户的 jwt token 盐 (后端持有，前端不知)
    """
    user_id = models.BigAutoField(primary_key=True)
    user_name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    password = models.CharField(max_length=MAX_NAME_LENGTH)
    description = models.TextField(max_length=MAX_DESCRIPTION_LENGTH, default="这个人很懒，什么都没留下")

    register_time = models.FloatField(default=get_timestamp)
    login_time = models.FloatField(default=get_timestamp)

    user_email = models.CharField(max_length=MAX_EMAIL_LENGTH, blank=True)
    user_icon = models.ImageField(upload_to='assets/avatars/', blank=True)

    jwt_token_salt = models.BinaryField(max_length=100, default=b'\x00' * 16)

    def serialize(self):
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "description": self.description,
            "register_time": self.register_time,
        }

    def get_memberships(self) -> models.QuerySet:
        return self.user_membership.filter(is_approved=True)

    def get_friends(self) -> models.QuerySet:
        return self.user_friendship.filter(is_approved=True).values('friend')

    def get_chats(self) -> models.QuerySet:
        return self.get_memberships().values('chat')

    def get_notifications(self, only_unread=False, later_than=0) -> models.QuerySet:
        if only_unread:
            return self.receiver_notifications.filter(is_read=False).filter(timestamp__gt=later_than)
        return self.receiver_notifications.filter(timestamp__gt=later_than)

    def __str__(self) -> str:
        return str(self.user_name)


# 定义一个信号处理函数，在用户删除前删除对应的头像文件
@receiver(pre_delete, sender=User)
def delete_avatar_file(sender, instance, **kwargs):
    if instance.user_icon:  # 如果用户有头像文件
        # 删除对应的头像文件
        if os.path.isfile(instance.user_icon.path):
            os.remove(instance.user_icon.path)


class Friendship(models.Model):
    """
    好友关系 model
    每形成一个好友关系，需要添加两条
    :var user: 用户
    :var friend: 好友
    :var update_time: 关系更新时间
    :var is_approved: 是否通过验证
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_friendship')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_friendship')
    update_time = models.FloatField(default=get_timestamp)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'friend')  # 每一条需要独一无二

    def __str__(self) -> str:
        return f"{self.user.user_name} and {self.friend.user_name} are friends"
