from django.urls import path
from . import views
from .apps import TelegramConfig


app_name = TelegramConfig.name

urlpatterns = [
    path('upload_file_by_telegram/', views.telegram_add_channel, name='upload_file_by_telegram'),
    path('download_files/', views.download_files_from_tg, name='download_files'),
    path('get_combofiles_from_tg/', views.get_combofiles_from_tg, name='get_combofiles_from_tg'),
    path('get_from_tg/', views.get_from_tg, name='get_from_tg'),
]
