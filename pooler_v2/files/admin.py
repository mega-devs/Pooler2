from django.contrib import admin

from .models import UploadedFile, ExtractedData


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count', 'origin', 'is_checked')
    list_filter = ('upload_date', 'country', 'origin', 'is_checked')
    search_fields = ('filename', 'country', 'origin')

@admin.register(ExtractedData)
class ExtractedDataAdmin(admin.ModelAdmin):
    list_display = (
        'filename', 'email', 'provider', 'country',
        'uploaded_file', 'smtp_is_valid', 'imap_is_valid'
    )
    list_filter = ('provider', 'country', 'smtp_is_valid', 'imap_is_valid')
    search_fields = ('email', 'provider', 'filename', 'uploaded_file__filename')
    ordering = ('-uploaded_file__upload_date',)