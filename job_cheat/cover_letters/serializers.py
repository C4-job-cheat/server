from rest_framework import serializers
from job_cheat.core.serializers import DynamicFieldsMixin, TimestampedSerializer


class HealthSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    feature = serializers.CharField()
    uid = serializers.CharField(allow_null=True, required=False)


class CoverLetterWriteSerializer(TimestampedSerializer, DynamicFieldsMixin):
    title = serializers.CharField(max_length=100)
    body = serializers.CharField()
    job_ref = serializers.CharField(required=False, allow_null=True)


class CoverLetterReadSerializer(TimestampedSerializer, DynamicFieldsMixin):
    id = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    job_ref = serializers.CharField(allow_null=True, required=False)


