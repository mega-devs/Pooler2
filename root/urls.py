"""
URL configuration for root project.
"""

from django.contrib import admin
from django.urls import path, include

# admin.site.index_template = 'admin/index.html'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pooler.urls')),
    path('users/', include('users.urls')),
    path('api/', include('files.urls')),
    path('api/', include('telegram.urls')),
]
