from user.models import User
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from secrets import token_hex


@receiver(post_migrate)
def create_system_user(sender, **kwargs):
    # 检查是否存在系统用户，如果不存在，则创建一个
    if not User.objects.filter(user_name='system').exists():
        # 创建系统用户，此用户的密码为随机生成的32位字符串
        admin_user = User.objects.create(user_name='system', password=token_hex(32))
        print("System user created successfully.")
