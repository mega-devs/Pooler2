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
    ORIGINS = [
        ('SMTP', 'SMTP Server'),
        ('IMAP', 'IMAP Server'),
        ('MANUAL', 'Manual Upload'),
        ('TELEGRAM', 'Telegram'),
        ('UNKNOWN', 'Unknown'),
    ]

    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    provider = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True, blank=True)
    filename = models.CharField(max_length=255, null=True, blank=True)
    line_number = models.PositiveIntegerField(null=True, blank=True)  # Новое поле
    uploaded_file = models.ForeignKey(
        'UploadedFile', on_delete=models.CASCADE, related_name='extracted_data'
    )
    upload_origin = models.CharField(
        max_length=50, choices=ORIGINS, default='UNKNOWN'
    )
    smtp_is_valid = models.BooleanField(null=True, blank=True, default=None)
    imap_is_valid = models.BooleanField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.email} - {self.provider} ({self.country})"

    class Meta:
        verbose_name = "Extracted Data"
        verbose_name_plural = "Extracted Data"


class URLFetcher(models.Model):
    link = models.CharField(max_length=255)
    total_files_fetched = models.PositiveIntegerField(default=0)
    total_lines_added = models.PositiveIntegerField(default=0)
    total_size_fetched = models.DecimalField(default=0, decimal_places=2, max_digits=7)
    last_time_fetched = models.DateTimeField(blank=True, null=True)
    success = models.BooleanField(default=False)
