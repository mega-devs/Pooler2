"""
URL configuration for root project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework.routers import DefaultRouter
from files.views import ExtractedDataModelViewSet, UploadedFileModelViewSet
from users.views import UserViewSet

# admin.site.index_template = 'admin/index.html'

router = DefaultRouter()
router.register('extracted-items', ExtractedDataModelViewSet)
router.register('uploaded-items', UploadedFileModelViewSet)
router.register('users', UserViewSet)

schema_view = get_schema_view(
   openapi.Info(
      title="Pool2 API",
      default_version='v1',
      description="API documentation for Pool2",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

schema_view = get_schema_view(
    openapi.Info(
        title="Pool2 Swagger",
        default_version='v1',
        description="API documentation for Pool2",
        terms_of_service="http://95.215.108.118:8000/",
        contact=openapi.Contact(email="contact@testing.com"),
        license=openapi.License(name="MM License"),
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
   path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + router.urls
