from rest_framework import serializers
from job_cheat.core.serializers import DynamicFieldsMixin, TimestampedSerializer


class HealthSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    feature = serializers.CharField()
    uid = serializers.CharField(allow_null=True, required=False)


class PersonaWriteSerializer(TimestampedSerializer, DynamicFieldsMixin):
    name = serializers.CharField(max_length=50)
    role = serializers.CharField()
    bio = serializers.CharField(allow_blank=True, required=False)


class PersonaReadSerializer(TimestampedSerializer, DynamicFieldsMixin):
    id = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()
    bio = serializers.CharField(allow_blank=True, required=False)


