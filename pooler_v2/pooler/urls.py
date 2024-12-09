from django.urls import path
from . import views
from .apps import PoolerConfig
from root import settings
from django.conf.urls.static import static


app_name = PoolerConfig.name

urlpatterns = [
    path('', views.redirect_to_panel, name='redirect_to_panel'),
    path('panel/', views.panel, name='panel'),
    path('panel/tables/', views.panel_table, name='panel_table'),
    path('panel/settings/', views.panel_settings, name='panel_settings'),
    path('upload_file_by_url/', views.upload_file_by_url, name='upload_file_by_url'),
    path('check-emails-file/<str:filename>/', views.check_emails_route, name='check_emails_route'),
    path('logs/<int:ind>/', views.get_logs, name='get_logs'),
    path('clear_temp_logs/', views.clear_temp_logs, name='clear_temp_logs'),
    path('clear_full_logs/', views.clear_full_logs, name='clear_full_logs'),
    path('download_full_logs/', views.download_logs_file, name='download_logs_file'),


]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)