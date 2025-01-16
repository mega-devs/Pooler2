from django.db import models


class Proxy(models.Model):
    host = models.CharField(max_length=12)
    port = models.PositiveSmallIntegerField()
    is_active = models.BooleanField()
    country = models.CharField(max_length=255)
    country_code = models.CharField(max_length=5)
    anonymity = models.CharField(max_length=15)
    timeout = models.PositiveIntegerField()
