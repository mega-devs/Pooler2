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
    path('setting/', views.dynamic_settings, name='dynamic_settings'),
    path('visitors/', views.get_visitors, name='visitors_list'),
    path('pageviews/', views.get_pageviews, name='pageviews_list'),
    path('visitors/statistics/', views.get_visitor_statistics, name='visitor_statistics'),
    path('visitors/<str:visitor_id>/', views.get_visitor_details, name='visitor_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
