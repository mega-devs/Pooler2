from django.contrib import admin

from .models import UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count', 'origin', 'is_checked')
    list_filter = ('upload_date', 'country', 'origin', 'is_checked')
    search_fields = ('filename', 'country', 'origin')
