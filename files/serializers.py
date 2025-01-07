
from rest_framework import serializers
from .models import UploadedFile, ExtractedData


class ExtractedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedData
        fields = '__all__'


class UploadedFileSerializer(serializers.ModelSerializer):
    extracted_data = ExtractedDataSerializer(many=True, read_only=True)

    class Meta:
        model = UploadedFile
        fields = '__all__'
