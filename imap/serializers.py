from rest_framework import serializers

from .models import ImapConfig, Combo, IMAPCheckResult, Statistics


class ImapConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImapConfig
        fields = ['id', 'timeout', 'threads', 'user', 'created_at']
        read_only_fields = ['created_at']


class ComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = Combo
        fields = ['id', 'email', 'password', 'created_at']
        read_only_fields = ['created_at']


class IMAPCheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = IMAPCheckResult
        fields = ['id', 'combo', 'user', 'status', 'checked_at']
        read_only_fields = ['checked_at']


class StatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistics
        fields = ['id', 'user', 'total_combos', 'total_hits', 'total_fails', 'updated_at']
        read_only_fields = ['updated_at']
