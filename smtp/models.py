from django.db import models

from users.models import User


class SmtpConfig(models.Model):
    timeout = models.FloatField()
    threads = models.PositiveSmallIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class SMTPCombo(models.Model):
    email = models.EmailField()
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.email}:{self.password}"


class SMTPCheckResult(models.Model):
    STATUS_CHOICES = [
        ("hit", "Hit"),
        ("fail", "Fail"),
    ]

    combo = models.ForeignKey(SMTPCombo, on_delete=models.CASCADE, related_name="smtp_check_results")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="smtp_check_results")
    status = models.CharField(max_length=4, choices=STATUS_CHOICES)
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result: {self.status} for {self.combo.email} at {self.checked_at}"


class SMTPStatistics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="statistics_smtp")
    total_combos = models.PositiveIntegerField(default=0)
    total_hits = models.PositiveIntegerField(default=0)
    total_fails = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.user.username}"
