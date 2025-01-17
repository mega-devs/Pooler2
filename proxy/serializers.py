from rest_framework.serializers import ModelSerializer

from .models import Proxy


class ProxySerizalizer(ModelSerializer):
    class Meta:
        model = Proxy
        fields = ('host', 'port', 'is_active', 'country', 'country_code', 'anonymity', 'timeout')
        read_only_fields = ('is_active', 'country', 'country_code', 'anonymity', 'timeout')
