from django.urls import path

from .apps import FilesConfig
from .views import (
    uploaded_files_list, uploaded_file_update, uploaded_file_delete,
    upload_combofile, download_file, panel_table
)
app_name = FilesConfig.name

urlpatterns = [
    path('', uploaded_files_list, name='uploaded_files_list'),
    path('<int:pk>/edit/', uploaded_file_update, name='uploaded_file_update'),
    path('<int:pk>/delete/', uploaded_file_delete, name='uploaded_file_delete'),
    path('/upload/', upload_combofile, name='upload_combofile'),
    path('/download/<str:filename>/', download_file, name='download_file'),
    path('panel/tables/', panel_table, name='panel_table'),
]