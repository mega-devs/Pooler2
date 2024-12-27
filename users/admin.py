from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username',)
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                  'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
