from django.db import models
from django.utils.timezone import now

from users.models import User


class UploadedFile(models.Model):
    MANAGEMENT_ORIGINS = [
        ('SMTP', 'SMTP Server'),
        ('IMAP', 'IMAP Server'),
        ('MANUAL', 'Manual Upload'),
        ('TELEGRAM', 'Telegram'),
        ('UNKNOWN', 'Unknown'),
    ]

    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    upload_date = models.DateTimeField(default=now)
    country = models.CharField(max_length=100, null=True, blank=True)
    duplicate_count = models.PositiveIntegerField(default=0)
    origin = models.CharField(max_length=50, choices=MANAGEMENT_ORIGINS, default='MANUAL')
    is_checked = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')

    def __str__(self):
        return f"{self.filename} ({self.origin}) - {self.upload_date}"

    class Meta:
        verbose_name = "Uploaded File"
        verbose_name_plural = "Uploaded Files"
        ordering = ["-upload_date"]


class ExtractedData(models.Model):
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    provider = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True, blank=True)
    filename = models.CharField(max_length=255, null=True, blank=True)
    uploaded_file = models.ForeignKey(
        'UploadedFile', on_delete=models.CASCADE, related_name='extracted_data'
    )
    smtp_is_valid = models.BooleanField(null=True, blank=True, default=None)
    imap_is_valid = models.BooleanField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.email} - {self.provider} ({self.country})"

    class Meta:
        verbose_name = "Extracted Data"
        verbose_name_plural = "Extracted Data"