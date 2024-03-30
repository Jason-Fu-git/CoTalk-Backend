from django.db import models

from utils.utils_time import get_timestamp
from utils.utils_require import MAX_NAME_LENGTH, MAX_EMAIL_LENGTH


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
    """
    user_id = models.BigAutoField(primary_key=True)
    user_name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True)
    password = models.CharField(max_length=MAX_NAME_LENGTH)

    register_time = models.FloatField(default=get_timestamp)
    login_time = models.FloatField(default=get_timestamp)

    user_email = models.CharField(max_length=MAX_EMAIL_LENGTH, blank=True)
    user_icon = models.ImageField(upload_to='../assets/avatars/', blank=True)

    def serialize(self):
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            # "avatar": self.user_icon, # todo: handle avatar
        }

    def get_memberships(self) -> models.QuerySet:
        return self.user_membership.filter(is_approved=True)

    def get_friends(self) -> models.QuerySet:
        return self.user_friendship.filter(is_approved=True).values('friend')

    def get_chats(self) -> models.QuerySet:
        return self.get_memberships().values('chat')

    def __str__(self) -> str:
        return str(self.user_name)


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
