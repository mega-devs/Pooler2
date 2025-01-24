from django.contrib import admin
from .models import Proxy


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('host', 'port', 'is_active', 'country', 'country_code', 'anonymity', 'timeout')
    list_filter = ('is_active', 'country', 'anonymity')
    search_fields = ('host', 'country', 'country_code')
    list_per_page = 25
    list_editable = ('is_active', 'country', 'anonymity', 'timeout')
