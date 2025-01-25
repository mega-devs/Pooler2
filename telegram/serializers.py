from rest_framework import serializers


class LocalFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.name.split('.')[-1] != 'zip':
            raise serializers.ValidationError("Only .zip files are allowed.")
        return value


class URLFileUploadSerializer(serializers.Serializer):
    file_url = serializers.URLField()

    def validate_file_url(self, value):
        if value.split('.')[-1] != 'zip':
            raise serializers.ValidationError("Only .zip files are allowed.")
        return value
