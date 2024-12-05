from django.urls import path

from . import views


urlpatterns = [
    path('', views.redirect_to_panel, name='redirect_to_panel'),
    path('panel/', views.panel, name='panel'),
    path('panel/tables/', views.panel_table, name='panel_table'),
    path('panel/settings/', views.panel_settings, name='panel_settings'),
    path('upload_file_by_url/', views.upload_file_by_url, name='upload_file_by_url'),
    path('upload_file_by_telegram/', views.telegram_add_channel, name='upload_file_by_telegram'),
    path('check-emails-file/<str:filename>/', views.check_emails_route, name='check_emails_route'),
    path('logs/<int:ind>/', views.get_logs, name='get_logs'),
    path('clear_temp_logs/', views.clear_temp_logs, name='clear_temp_logs'),
    path('clear_full_logs/', views.clear_full_logs, name='clear_full_logs'),
    path('get_combofiles_from_tg/', views.get_from_tg, name='get_combofiles_from_tg'),
    path('upload_combofile/', views.upload_combofile, name='upload_combofile'),  # Удалил `/api/`
    path('download_combofile/<str:filename>/', views.download_file, name='download_file'),
    path('download_full_logs/', views.download_logs_file, name='download_logs_file'),
]
