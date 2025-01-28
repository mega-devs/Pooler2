from django.contrib import admin
from imap.models import IMAPCheckResult, Statistics, ImapConfig, Combo


@admin.register(IMAPCheckResult)
class IMAPCheckResultAdmin(admin.ModelAdmin):
    list_display = ('combo', 'user', 'proxy_config', 'status', 'checked_at')
    list_filter = ('status', 'checked_at')
    search_fields = ('combo__email', 'user__username')
    ordering = ('-checked_at',)


@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_combos', 'total_hits', 'total_fails', 'updated_at')
    list_filter = ('user', )
    search_fields = ('user__username',)
    ordering = ('-updated_at',)


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ('email', 'password', 'created_at')
    search_fields = ('email',)
    ordering = ('-created_at',)


@admin.register(ImapConfig)
class ProxyConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'timeout', 'threads', 'created_at')
    search_fields = ('user__username', )
    ordering = ('-created_at',)
