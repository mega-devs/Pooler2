from django.urls import path

from . import views


urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.custom_logout_view, name='custom-logout'),
    path('session/token/<str:token>/', views.get_session_by_token, name='get_session_by_token'),
    path('details/<int:user_id>/', views.user_details, name='details'),
]
