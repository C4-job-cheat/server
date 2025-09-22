from rest_framework import serializers


class DynamicFieldsMixin:
    """선택적 필드만 출력/검증하도록 허용하는 Mixin.

    Serializer(...) 호출 시 kwargs로 fields=[...]를 전달하면 해당 필드만 유지합니다.
    Firestore 기반 리소스에서 엔드포인트별 노출 필드를 간단히 조절할 때 사용합니다.
    """

    def __init__(self, *args, **kwargs):
        allowed_fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        if allowed_fields is not None:
            allowed = set(allowed_fields)
            for field_name in list(self.fields):
                if field_name not in allowed:
                    self.fields.pop(field_name)


class TimestampedSerializer(serializers.Serializer):
    """생성/수정 시각을 표준 필드로 제공하는 베이스 Serializer.

    Firestore의 Timestamp 또는 ISO 문자열을 응답 전용으로 노출합니다.
    입력값 검증에는 사용하지 않고, 앱 레벨에서 설정/매핑합니다.
    """

    created_at = serializers.DateTimeField(read_only=True, required=False)
    updated_at = serializers.DateTimeField(read_only=True, required=False)


