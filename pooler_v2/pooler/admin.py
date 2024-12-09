from django.contrib import admin
from .models import EmailCheck


@admin.register(EmailCheck)
class EmailCheckAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'check_type', 'timestamp')
    list_filter = ('status', 'check_type')
    search_fields = ('email',)


