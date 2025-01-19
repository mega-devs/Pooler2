from django.db import models


class Proxy(models.Model):
    host = models.CharField(max_length=20)
    port = models.PositiveIntegerField()
    is_active = models.BooleanField(blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    country_code = models.CharField(max_length=5, blank=True, null=True)
    anonymity = models.CharField(max_length=15, blank=True, null=True)
    timeout = models.PositiveIntegerField(blank=True, null=True)
    last_time_checked = models.DateTimeField()
