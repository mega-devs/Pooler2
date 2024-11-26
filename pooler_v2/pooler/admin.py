from django.contrib import admin
from .models import EmailCheck, TelegramMessage, TelegramFile, UploadedFile


@admin.register(EmailCheck)
class EmailCheckAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'check_type', 'timestamp')
    list_filter = ('status', 'check_type')
    search_fields = ('email',)


@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'sender_id', 'date', 'message_id')
    list_filter = ('date',)
    search_fields = ('chat_id', 'sender_id', 'message_id')


@admin.register(TelegramFile)
class TelegramFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_path', 'uploaded_at', 'telegram_message')
    list_filter = ('uploaded_at',)
    search_fields = ('file_name', 'file_path')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count')
    list_filter = ('upload_date', 'country')
    search_fields = ('filename', 'country')