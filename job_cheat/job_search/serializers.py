from rest_framework import serializers
from job_cheat.core.serializers import DynamicFieldsMixin, TimestampedSerializer


class HealthSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    feature = serializers.CharField()
    uid = serializers.CharField(allow_null=True, required=False)


class JobPostWriteSerializer(TimestampedSerializer, DynamicFieldsMixin):
    title = serializers.CharField(max_length=120)
    company = serializers.CharField(max_length=120)
    url = serializers.URLField()
    description = serializers.CharField(allow_blank=True, required=False)


class JobPostReadSerializer(TimestampedSerializer, DynamicFieldsMixin):
    id = serializers.CharField()
    title = serializers.CharField()
    company = serializers.CharField()
    url = serializers.URLField()
    description = serializers.CharField(allow_blank=True, required=False)


