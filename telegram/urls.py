from django.urls import path
from . import views
from .apps import TelegramConfig


app_name = TelegramConfig.name

urlpatterns = [
    path('upload_file_by_telegram/', views.telegram_add_channel, name='upload_file_by_telegram'),    
    path('get_combofiles_from_tg/', views.get_from_tg, name='get_combofiles_from_tg'),

]
