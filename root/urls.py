"""
URL configuration for root project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# admin.site.index_template = 'admin/index.html'

schema_view = get_schema_view(
   openapi.Info(
      title="Pool2 API",
      default_version='v1',
      description="API documentation for Pool2",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pooler.urls')),
    path('users/', include('users.urls')),
    path('api/', include('files.urls')),
    path('api/', include('telegram.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
