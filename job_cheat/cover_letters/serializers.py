from rest_framework import serializers
from typing import List, Dict, Any
from core.serializers import DynamicFieldsMixin, TimestampedSerializer


class CoverLetterParagraphSerializer(serializers.Serializer):
    """자기소개서 문단 시리얼라이저."""
    paragraph = serializers.CharField(max_length=2000, help_text="문단 내용")
    reason = serializers.CharField(max_length=500, help_text="문단 작성 이유")


class CoverLetterRequestSerializer(serializers.Serializer):
    """자기소개서 생성 요청 시리얼라이저."""
    user_id = serializers.CharField(max_length=100, help_text="사용자 ID")
    persona_id = serializers.CharField(max_length=100, help_text="페르소나 ID")
    company_name = serializers.CharField(max_length=200, help_text="지원 회사 이름")
    strengths = serializers.CharField(max_length=1000, help_text="본인의 강점")
    activities = serializers.CharField(max_length=1000, help_text="관련 활동 정보")
    style = serializers.ChoiceField(
        choices=[("experience", "경험 중심"), ("knowledge", "지식 위주"), ("creative", "창의적")],
        help_text="자기소개서 스타일"
    )
    
    def validate_user_id(self, value):
        """user_id 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("user_id는 필수입니다.")
        return value.strip()
    
    def validate_persona_id(self, value):
        """persona_id 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("persona_id는 필수입니다.")
        return value.strip()
    
    def validate_company_name(self, value):
        """company_name 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("지원 회사 이름은 필수입니다.")
        return value.strip()
    
    def validate_strengths(self, value):
        """strengths 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("본인의 강점은 필수입니다.")
        return value.strip()
    
    def validate_activities(self, value):
        """activities 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("관련 활동 정보는 필수입니다.")
        return value.strip()

    def validate_style(self, value):
        """style 검증."""
        if not value or not value.strip():
            raise serializers.ValidationError("자기소개서 스타일은 필수입니다.")
        valid_styles = ["experience", "knowledge", "creative"]
        if value not in valid_styles:
            raise serializers.ValidationError(f"자기소개서 스타일은 {valid_styles} 중 하나여야 합니다.")
        return value.strip()


class CoverLetterResponseSerializer(serializers.Serializer):
    """자기소개서 응답 시리얼라이저."""
    id = serializers.CharField(help_text="자기소개서 ID")
    company_name = serializers.CharField(help_text="지원 회사 이름")
    user_id = serializers.CharField(help_text="사용자 ID")
    persona_id = serializers.CharField(help_text="페르소나 ID")
    cover_letter = CoverLetterParagraphSerializer(many=True, help_text="자기소개서 문단들")
    style = serializers.CharField(help_text="자기소개서 스타일")
    character_count = serializers.IntegerField(help_text="글자 수")
    created_at = serializers.DateTimeField(help_text="생성일시")
    updated_at = serializers.DateTimeField(help_text="수정일시")


class CoverLetterSummarySerializer(serializers.Serializer):
    """자기소개서 요약 시리얼라이저."""
    id = serializers.CharField(help_text="자기소개서 ID")
    company_name = serializers.CharField(help_text="지원 회사 이름")
    created_at = serializers.DateTimeField(help_text="생성일시")
    character_count = serializers.IntegerField(help_text="글자 수")
    style = serializers.CharField(help_text="자기소개서 스타일")


class CoverLetterListResponseSerializer(serializers.Serializer):
    """자기소개서 목록 응답 시리얼라이저."""
    cover_letters = CoverLetterSummarySerializer(many=True, help_text="자기소개서 목록")
    total_count = serializers.IntegerField(help_text="총 개수")
    persona_card = serializers.DictField(help_text="페르소나 카드 데이터")


class HealthSerializer(serializers.Serializer):
    """헬스 체크 시리얼라이저."""
    ok = serializers.BooleanField()