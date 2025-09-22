from rest_framework import serializers


class FirebaseClaimsSerializer(serializers.Serializer):
    uid = serializers.CharField(allow_null=True, required=False)
    email = serializers.EmailField(allow_null=True, required=False)
    email_verified = serializers.BooleanField(allow_null=True, required=False)
    name = serializers.CharField(allow_null=True, required=False)
    picture = serializers.URLField(allow_null=True, required=False)
    provider = serializers.CharField(allow_null=True, required=False)


