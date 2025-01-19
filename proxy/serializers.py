from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Proxy


class ProxySerizalizer(ModelSerializer):
    class Meta:
        model = Proxy
        fields = '__all__'
        read_only_fields = ('id', 'is_active', 'country', 'country_code', 'anonymity', 'timeout', 'last_time_checked')


class TextFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
