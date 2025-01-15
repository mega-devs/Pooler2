from rest_framework import serializers

from django.contrib.auth import get_user_model


User = get_user_model()


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = '__all__'
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user


class UserSigninSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
