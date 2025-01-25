from django.urls import path
from django.conf.urls.static import static

from . import views
from .apps import PoolerConfig
from root import settings


app_name = PoolerConfig.name

urlpatterns = [
    path('', views.redirect_to_panel, name='redirect_to_panel'),
    path('panel/', views.panel, name='panel'),
    path('panel/settings/', views.panel_settings, name='panel_settings'),
    path('upload_file_by_url/', views.upload_file_by_url, name='upload_file_by_url'),
    path('logs/', views.get_logs, name='get_logs'),
    path('clear_temp_logs/', views.clear_temp_logs, name='clear_temp_logs'),
    path('clear_full_logs/', views.clear_full_logs, name='clear_full_logs'),
    path('download_full_logs/', views.download_logs_file, name='download_logs_file'),
    path('valid_smtp/', views.get_valid_smtp, name='valid-smtp'),
    path('valid_imap/', views.get_valid_imap, name='valid-imap'),
    path('checking_smtp/', views.check_smtp_view, name='checking_smtp'),
    path('checking_imap/', views.check_imap_view, name='checking_imap'),
    path('tests/', views.get_test_list, name='get_tests'),
    path('run_test/', views.run_selected_tests, name='run_test'),
    path('test_logs/<int:pk>/', views.get_test_logs, name='get_test_logs'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
