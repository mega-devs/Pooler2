from django.contrib import admin
from smtp.models import SMTPCheckResult, SMTPCombo, SMTPStatistics, SmtpConfig


@admin.register(SMTPCheckResult)
class SMTPCheckResultAdmin(admin.ModelAdmin):
    list_display = ('combo', 'user', 'status', 'checked_at')
    list_filter = ('status', 'checked_at')
    search_fields = ('combo__email', 'user__username')
    ordering = ('-checked_at',)


@admin.register(SMTPStatistics)
class SMTPStatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_combos', 'total_hits', 'total_fails', 'updated_at')
    list_filter = ('user', )
    search_fields = ('user__username',)
    ordering = ('-updated_at',)


@admin.register(SMTPCombo)
class SMTPComboAdmin(admin.ModelAdmin):
    list_display = ('email', 'password', 'created_at', 'user')
    search_fields = ('email', 'user__username')
    ordering = ('-created_at',)


@admin.register(SmtpConfig)
class SMTPConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'timeout', 'threads', 'created_at')
    search_fields = ('user__username', )
    ordering = ('-created_at',)
