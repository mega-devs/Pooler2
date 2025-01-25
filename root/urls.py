"""
URL configuration for root project.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from files.views import ExtractedDataModelViewSet, UploadedFileModelViewSet
from proxy.views import ProxyViewSet, set_backup_delay, get_backup_delay
from root import settings
from users.views import UserViewSet
from django.conf import settings as main_settings
from django.conf.urls.static import static

# admin.site.index_template = 'admin/index.html'

router = DefaultRouter()
router.register('extracted-items', ExtractedDataModelViewSet)
router.register('uploaded-items', UploadedFileModelViewSet)
router.register('users', UserViewSet)
router.register('proxy', ProxyViewSet)


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
   path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
   path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
   path('users/', include('users.urls')),
   path('files/', include('files.urls')),
   path('api/', include('pooler.urls')),
   path('telegram/', include('telegram.urls')),
   path('ufw_manager/', include('ufw_manager.urls')),
   path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   path('prometheus/', include('django_prometheus.urls')),
   path(r'ht/', include('health_check.urls')),
   path('silk/', include('silk.urls', namespace='silk')),
   path('django-rq/', include('django_rq.urls')),
   path('backup/set/', set_backup_delay),
   path('backup/get/', get_backup_delay),
] + router.urls + static(main_settings.MEDIA_URL, document_root=main_settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
