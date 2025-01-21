# from django.db import models


# class EmailCheck(models.Model):
#     CHECK_TYPE_CHOICES = [
#         ('SMTP', 'SMTP'),
#         ('IMAP', 'IMAP'),
#     ]

#     email = models.EmailField(unique=True, verbose_name="Email Address")
#     status = models.CharField(max_length=20, verbose_name="Check Status")  # For example: valid, invalid
#     check_type = models.CharField(max_length=10, choices=CHECK_TYPE_CHOICES, verbose_name="Check Type")
#     timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")

#     def __str__(self):
#         return f"{self.email} ({self.check_type}) - {self.status}"

#     class Meta:
#         verbose_name = "Email Check"
#         verbose_name_plural = "Email Checks"
#         ordering = ["-timestamp"]
