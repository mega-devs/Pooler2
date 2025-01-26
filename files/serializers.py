import os

from rest_framework import serializers

from .models import UploadedFile, ExtractedData, URLFetcher


class ExtractedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedData
        fields = '__all__'


class UploadedFileSerializer(serializers.ModelSerializer):
    extracted_data = ExtractedDataSerializer(many=True, read_only=True)

    class Meta:
        model = UploadedFile
        fields = '__all__'


class URLFetcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = URLFetcher
        fields = '__all__'
        read_only_fields = ('id', 'total_files_fetched', 'total_lines_added', 'total_size_fetched', 'last_time_fetched', 'success')

    def validate_link(self, value):
        if not os.path.exists(value):
            raise serializers.ValidationError("Directory does not exist.")
        return value
