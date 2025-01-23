from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.core.management import call_command
from .models import UFWRule

@admin.register(UFWRule)
class UFWRuleAdmin(admin.ModelAdmin):
    list_display = ('direction', 'protocol', 'port', 'from_ip', 'to_ip', 'action', 'description')
    list_filter = ('direction', 'protocol', 'action')
    search_fields = ('from_ip', 'to_ip', 'description')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('apply_rules/', self.admin_site.admin_view(self.apply_rules), name='apply_ufw_rules'),
        ]
        return custom_urls + urls

    def apply_rules(self, request):
        try:
            call_command('apply_ufw_rules')
            messages.success(request, 'UFW rules have been applied successfully')
        except Exception as e:
            messages.error(request, f'Error applying UFW rules: {str(e)}')
        return redirect(request.META.get('HTTP_REFERER', '/admin/ufw_manager/ufwrule/'))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['apply_rules_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
