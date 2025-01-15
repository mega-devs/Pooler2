from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('getsession/', views.get_session, name='get_session_data'),
]
