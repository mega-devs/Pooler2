from django.db import models

from users.models import User


class ImapConfig(models.Model):
    timeout = models.FloatField()
    threads = models.PositiveSmallIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Combo(models.Model):
    email = models.EmailField()
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.email}:{self.password}"


class IMAPCheckResult(models.Model):
    STATUS_CHOICES = [
        ("hit", "Hit"),
        ("fail", "Fail"),
    ]

    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name="check_results")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="imap_check_results")
    status = models.CharField(max_length=4, choices=STATUS_CHOICES)
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result: {self.status} for {self.combo.email} at {self.checked_at}"


class Statistics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="statistics")
    total_combos = models.PositiveIntegerField(default=0)
    total_hits = models.PositiveIntegerField(default=0)
    total_fails = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.user.username}"
