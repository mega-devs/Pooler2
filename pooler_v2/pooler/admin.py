from django.contrib import admin
from .models import EmailCheck, UploadedFile


@admin.register(EmailCheck)
class EmailCheckAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'check_type', 'timestamp')
    list_filter = ('status', 'check_type')
    search_fields = ('email',)


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count', 'origin', 'is_checked')  # Добавлены новые поля
    list_filter = ('upload_date', 'country', 'origin', 'is_checked')  # Добавлены фильтры для новых полей
    search_fields = ('filename', 'country', 'origin')  # Добавлено поле `origin` для поиска