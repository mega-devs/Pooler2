from django.urls import path

from . import views


urlpatterns = [
    path('signup/', views.signup),
    path('signin/', views.signin),
    path('logout/', views.custom_logout_view),
    path('session/token/<str:token>/', views.get_session_by_token, name='get_session_by_token'),
]
