from rest_framework import serializers


class FirebaseClaimsSerializer(serializers.Serializer):
    uid = serializers.CharField(allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    email_verified = serializers.BooleanField(allow_null=True, required=False)
    name = serializers.CharField(allow_null=True, required=False)
    picture = serializers.URLField(allow_null=True, required=False)
    provider = serializers.CharField(allow_null=True, required=False)


class FirebaseUserSerializer(serializers.Serializer):
    uid = serializers.CharField()
    email = serializers.EmailField(allow_null=True, required=False)
    display_name = serializers.CharField(allow_null=True, required=False)
    photo_url = serializers.URLField(allow_null=True, required=False)
    email_verified = serializers.BooleanField(allow_null=True, required=False)
    provider_id = serializers.CharField(allow_null=True, required=False)
    last_login_at = serializers.DateTimeField(required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)


