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
    file_size = models.CharField(max_length=50, null=True, blank=True)
    file_type = models.CharField(max_length=50, null=True, blank=True)
    total_rows_in_file = models.PositiveIntegerField(default=0, null=True, blank=True)
    processing_start_time = models.DateTimeField(null=True, blank=True)
    processing_end_time = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')

    def save(self, *args, **kwargs):
        if self.file_path:
            import os
            import mimetypes
            import pandas as pd

            file_size_bytes = os.path.getsize(self.file_path)
            if file_size_bytes < 1024:
                self.file_size = f"{file_size_bytes} B"
            elif file_size_bytes < 1024 * 1024:
                self.file_size = f"{file_size_bytes/1024:.2f} KB"
            else:
                self.file_size = f"{file_size_bytes/(1024*1024):.2f} MB"

            self.file_type = mimetypes.guess_type(self.file_path)[0] or 'unknown'

            # total rows for csv/excel/txt files
            if self.file_type in ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain']:
                try:
                    if self.file_type == 'text/csv':
                        df = pd.read_csv(self.file_path)
                    elif self.file_type == 'text/plain':
                        df = pd.read_csv(self.file_path)
                    else:
                        df = pd.read_excel(self.file_path)
                    self.total_rows_in_file = len(df)
                except Exception:
                    self.total_rows_in_file = 0
        super().save(*args, **kwargs)

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

    PROVIDER_TYPES = [
        ('BIG', 'Big Provider'),
        ('PRIVATE', 'Private Server'),
        ('NONE', 'None'),
    ]

    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    provider = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=100, choices=PROVIDER_TYPES, default='NONE')
    country = models.CharField(max_length=100, null=True, blank=True)
    filename = models.CharField(max_length=255, null=True, blank=True)
    line_number = models.PositiveIntegerField(null=True, blank=True)
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
