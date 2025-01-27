from django.db import models

from users.models import User


class ProxyConfig(models.Model):
    timeout = models.FloatField()
    threads = models.PositiveSmallIntegerField()
    email = models.EmailField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
