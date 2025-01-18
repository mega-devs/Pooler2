from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Proxy


class ProxySerizalizer(ModelSerializer):
    class Meta:
        model = Proxy
        fields = ('id', 'host', 'port', 'is_active', 'country', 'country_code', 'anonymity', 'timeout')
        read_only_fields = ('id', 'is_active', 'country', 'country_code', 'anonymity', 'timeout')


class TextFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
