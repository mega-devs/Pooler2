from django.db import models
from django.utils.timezone import now

class EmailCheck(models.Model):
    CHECK_TYPE_CHOICES = [
        ('SMTP', 'SMTP'),
        ('IMAP', 'IMAP'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email Address")
    status = models.CharField(max_length=20, verbose_name="Check Status")  # Например: valid, invalid
    check_type = models.CharField(max_length=10, choices=CHECK_TYPE_CHOICES, verbose_name="Check Type")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")

    def __str__(self):
        return f"{self.email} ({self.check_type}) - {self.status}"

    class Meta:
        verbose_name = "Email Check"
        verbose_name_plural = "Email Checks"
        ordering = ["-timestamp"]


class TelegramMessage(models.Model):
    chat_id = models.CharField(max_length=100, verbose_name="Chat ID")
    sender_id = models.CharField(max_length=100, verbose_name="Sender ID")
    date = models.DateTimeField(verbose_name="Message Date")
    text = models.TextField(verbose_name="Message Text", blank=True, null=True)
    message_id = models.CharField(max_length=100, verbose_name="Message ID", unique=True)

    def __str__(self):
        return f"Message {self.message_id} from {self.sender_id}"

    class Meta:
        verbose_name = "Telegram Message"
        verbose_name_plural = "Telegram Messages"
        ordering = ['-date']


class TelegramFile(models.Model):
    file_name = models.CharField(max_length=255, verbose_name="File Name")
    file_path = models.CharField(max_length=500, verbose_name="File Path")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Uploaded At")
    telegram_message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name="files", verbose_name="Related Telegram Message")

    def __str__(self):
        return self.file_name

    class Meta:
        verbose_name = "Telegram File"
        verbose_name_plural = "Telegram Files"
        ordering = ['-uploaded_at']


class UploadedFile(models.Model):
    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    upload_date = models.DateTimeField(default=now)
    country = models.CharField(max_length=100, null=True, blank=True)
    duplicate_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.upload_date})"

    class Meta:
        verbose_name = "Uploaded File"
        verbose_name_plural = "Uploaded Files"