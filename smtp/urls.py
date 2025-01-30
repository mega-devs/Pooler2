from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import SmtpConfigViewSet, ComboViewSet, SMTPCheckResultViewSet, StatisticsViewSet


router = DefaultRouter()
router.register(r'smtpconfigs', SmtpConfigViewSet)
router.register(r'combos', ComboViewSet)
router.register(r'smtpcheckresults', SMTPCheckResultViewSet)
router.register(r'statistics', StatisticsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
