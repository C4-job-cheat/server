from rest_framework import serializers
from job_cheat.core.serializers import DynamicFieldsMixin, TimestampedSerializer


class HealthSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    feature = serializers.CharField()
    uid = serializers.CharField(allow_null=True, required=False)


class InterviewWriteSerializer(TimestampedSerializer, DynamicFieldsMixin):
    title = serializers.CharField(max_length=100)
    company = serializers.CharField(max_length=100)
    content = serializers.CharField(allow_blank=True, required=False)


class InterviewReadSerializer(TimestampedSerializer, DynamicFieldsMixin):
    id = serializers.CharField()
    title = serializers.CharField()
    company = serializers.CharField()
    content = serializers.CharField(allow_blank=True, required=False)


