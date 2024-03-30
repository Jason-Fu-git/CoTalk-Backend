from django.db import models
from utils.utils_time import get_timestamp


class Client(models.Model):
    """
    Client model
    :var channel_name: channel name, unique
    :var user_id: user id, unique
    :var create_time: create time
    """
    channel_name = models.CharField(max_length=1024, unique=True)
    user_id = models.IntegerField(unique=True)
    create_time = models.FloatField(default=get_timestamp)

    def __str__(self):
        return self.channel_name
