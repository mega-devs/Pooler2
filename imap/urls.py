from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import ImapConfigViewSet, ComboViewSet, IMAPCheckResultViewSet, StatisticsViewSet


router = DefaultRouter()
router.register(r'imapconfigs', ImapConfigViewSet)
router.register(r'combos', ComboViewSet)
router.register(r'imapcheckresults', IMAPCheckResultViewSet)
router.register(r'statistics', StatisticsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
