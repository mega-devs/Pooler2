from rest_framework import serializers

from .models import SMTPCombo, SMTPStatistics, SmtpConfig, SMTPCheckResult


class SmtpConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmtpConfig
        fields = ['id', 'timeout', 'threads', 'user', 'created_at']
        read_only_fields = ['created_at']


class ComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMTPCombo
        fields = ['id', 'email', 'password', 'created_at']
        read_only_fields = ['created_at']


class SMTPCheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMTPCheckResult
        fields = ['id', 'combo', 'user', 'status', 'checked_at']
        read_only_fields = ['checked_at']


class StatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMTPStatistics
        fields = ['id', 'user', 'total_combos', 'total_hits', 'total_fails', 'updated_at']
        read_only_fields = ['updated_at']
