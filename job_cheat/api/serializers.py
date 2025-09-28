from rest_framework import serializers


class FirebaseClaimsSerializer(serializers.Serializer):
    uid = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)
    email_verified = serializers.BooleanField(allow_null=True, required=False)
    name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    picture = serializers.URLField(allow_null=True, allow_blank=True, required=False)
    provider = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class FirebaseUserSerializer(serializers.Serializer):
    uid = serializers.CharField()
    email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)
    display_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    email_verified = serializers.BooleanField(allow_null=True, required=False)
    last_login_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    updated_at = serializers.DateTimeField(allow_null=True, required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 선택적 클레임이 비어 있을 때 응답을 간결하게 유지하기 위해 None 값을 제거합니다.
        return {key: value for key, value in data.items() if value is not None}
