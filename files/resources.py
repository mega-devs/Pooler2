
from import_export import resources
from import_export.fields import Field
from .models import UploadedFile, ExtractedData


class UploadedFileResource(resources.ModelResource):
    class Meta:
        model = UploadedFile
        fields = ('id', 'filename', 'file_path', 'upload_date', 'country', 
                 'duplicate_count', 'origin', 'is_checked', 'user')
        export_order = fields


class ExtractedDataResource(resources.ModelResource):
    uploaded_file_name = Field()

    def dehydrate_uploaded_file_name(self, obj):
        return obj.uploaded_file.filename if obj.uploaded_file else None

    class Meta:
        model = ExtractedData
        fields = ('id', 'email', 'password', 'provider', 'country', 'filename',
                 'line_number', 'uploaded_file', 'uploaded_file_name', 
                 'upload_origin', 'smtp_is_valid', 'imap_is_valid')
        export_order = fields
