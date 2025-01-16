from rest_framework.serializers import ModelSerializer

from .models import Proxy


class ProxySerizalizer(ModelSerializer):
    class Meta:
        model = Proxy
        fields = '__all__'
