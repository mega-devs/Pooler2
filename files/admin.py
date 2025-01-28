from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import UploadedFile, ExtractedData
from files.resources import ExtractedDataResource, UploadedFileResource


@admin.register(UploadedFile)
class UploadedFileAdmin(ImportExportModelAdmin):
    resource_class = UploadedFileResource    
    
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count', 'origin', 'is_checked')
    list_filter = ('upload_date', 'country', 'origin', 'is_checked')
    search_fields = ('filename', 'country', 'origin')
    ordering = ('-upload_date',)


@admin.register(ExtractedData)
class ExtractedDataAdmin(ImportExportModelAdmin):
    resource_class = ExtractedDataResource

    list_display = ('line_number', 'email', 'provider', 'provider_type', 'country', 'uploaded_file', 'smtp_is_valid', 'imap_is_valid')
    list_filter = ('provider', 'country', 'smtp_is_valid', 'imap_is_valid')
    search_fields = ('email', 'provider', 'filename', 'uploaded_file__filename')
    ordering = ('-uploaded_file__upload_date',)
