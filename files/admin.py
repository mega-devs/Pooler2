from django.contrib import admin
from django.db.models import Count
from django.contrib.auth import get_user_model

from files.resources import ExtractedDataResource, UploadedFileResource
from .models import UploadedFile, ExtractedData
from import_export.admin import ImportExportModelAdmin
from users.admin import CustomUserAdmin

User = get_user_model()


class UploadedFileAdmin(ImportExportModelAdmin):
    resource_class = UploadedFileResource
    list_display = ('filename', 'upload_date', 'country', 'duplicate_count', 'origin', 'is_checked')
    list_filter = ('upload_date', 'country', 'origin', 'is_checked')
    search_fields = ('filename', 'country', 'origin')
    ordering = ('-upload_date',)

class ExtractedDataAdmin(ImportExportModelAdmin):
    resource_class = ExtractedDataResource
    list_display = ('filename', 'email', 'provider', 'country', 'uploaded_file', 'smtp_is_valid', 'imap_is_valid')
    list_filter = ('provider', 'country', 'smtp_is_valid', 'imap_is_valid')
    search_fields = ('email', 'provider', 'filename', 'uploaded_file__filename')
    ordering = ('-uploaded_file__upload_date',)

class CustomAdminSite(admin.AdminSite):
    def index(self, request, extra_context=None):
        total_emails = ExtractedData.objects.count()
        smtp_valid = ExtractedData.objects.filter(smtp_is_valid=True).count()
        imap_valid = ExtractedData.objects.filter(imap_is_valid=True).count()
        
        smtp_success_rate = round((smtp_valid / total_emails * 100) if total_emails > 0 else 0)
        imap_success_rate = round((imap_valid / total_emails * 100) if total_emails > 0 else 0)
        active_users = User.objects.filter(is_active=True).count()

        provider_stats = ExtractedData.objects.values('provider').annotate(
            count=Count('provider')
        ).order_by('-count')[:4]

        context = {
            'total_emails': total_emails,
            'smtp_success_rate': smtp_success_rate,
            'imap_success_rate': imap_success_rate,
            'active_users': active_users,
            'smtp_valid': smtp_valid,
            'smtp_invalid': total_emails - smtp_valid,
            'imap_valid': imap_valid,
            'imap_invalid': total_emails - imap_valid,
            'provider_labels': [stat['provider'] for stat in provider_stats],
            'provider_counts': [stat['count'] for stat in provider_stats],
        }
        
        if extra_context:
            context.update(extra_context)
        return super().index(request, context)

# Create the custom admin site instance
admin_site = CustomAdminSite()

# Register all models with the custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(UploadedFile, UploadedFileAdmin)
admin_site.register(ExtractedData, ExtractedDataAdmin)

# Replace the default admin site
admin.site = admin_site