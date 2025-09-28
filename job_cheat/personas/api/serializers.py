from __future__ import annotations

from typing import Any, Dict, Iterable

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from core.services.job_competencies import get_core_competencies_by_job_category


class _SkillListField(serializers.ListField):
    """쉼표 구분 문자열 입력을 허용하는 커스텀 리스트 필드."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [item for item in data.split(",")]
        return super().to_internal_value(data)


class _CertificationListField(serializers.ListField):
    """쉼표 구분 문자열 입력을 허용하는 커스텀 리스트 필드."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [item for item in data.split(",")]
        return super().to_internal_value(data)


class PersonaInputSerializer(serializers.Serializer):
    """페르소나 기본 정보와 HTML 첨부 파일을 동시에 검증한다."""

    MAX_HTML_FILE_SIZE = 200 * 1024 * 1024  # 200MB (100MB 이상 처리 가능)

    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    job_category = serializers.CharField(max_length=80)  # 필수 필드
    job_role = serializers.CharField(max_length=100, required=False, allow_blank=True)
    school_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    major = serializers.CharField(max_length=120, required=False, allow_blank=True)
    skills = _SkillListField(child=serializers.CharField(allow_blank=True), allow_empty=True, required=False)
    certifications = _CertificationListField(child=serializers.CharField(allow_blank=True), allow_empty=True, required=False)
    html_file = serializers.FileField(write_only=True)  # 필수 필드
    html_file_path = serializers.CharField(read_only=True)
    html_content_type = serializers.CharField(read_only=True)
    html_file_size = serializers.IntegerField(read_only=True)
    json_file_path = serializers.CharField(read_only=True)
    json_content_type = serializers.CharField(read_only=True)
    json_file_size = serializers.IntegerField(read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)
    html_file_deleted = serializers.BooleanField(read_only=True)
    embedding_status = serializers.CharField(read_only=True, required=False)
    embedding_message = serializers.CharField(read_only=True, required=False)
    embeddings_count = serializers.IntegerField(read_only=True, required=False)
    embedding_model = serializers.CharField(read_only=True, required=False)
    has_embeddings = serializers.BooleanField(read_only=True, required=False)
    vectorized_competency_tags = serializers.ListField(child=serializers.CharField(), read_only=True, required=False)
    embedding_started_at = serializers.DateTimeField(read_only=True, required=False)
    embedding_completed_at = serializers.DateTimeField(read_only=True, required=False)
    core_competencies = serializers.ListField(read_only=True)  # 직군별 핵심 역량
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def _normalize_str_list(self, raw_values: Iterable[Any]) -> list[str]:
        """문자열 리스트 입력에서 공백과 중복을 정리한다."""

        seen = set()
        normalized: list[str] = []
        for raw in raw_values:
            if not isinstance(raw, str):
                raise serializers.ValidationError("문자열 배열만 허용됩니다.")
            value = raw.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        # 빈 배열도 허용 (선택사항 필드)
        return normalized

    def validate_skills(self, value: Any) -> list[str]:
        """skills 필드는 리스트 또는 쉼표 구분 문자열을 허용한다."""

        if isinstance(value, list):
            return self._normalize_str_list(value)
        raise serializers.ValidationError("skills 필드는 리스트 형식이어야 합니다.")

    def validate_certifications(self, value: Any) -> list[str]:
        """certifications 필드는 리스트 또는 쉼표 구분 문자열을 허용한다."""

        if isinstance(value, list):
            return self._normalize_str_list(value)
        raise serializers.ValidationError("certifications 필드는 리스트 형식이어야 합니다.")

    def validate_html_file(self, value: UploadedFile) -> UploadedFile:
        """HTML 파일의 크기와 MIME 타입을 검사한다."""

        content_type = (value.content_type or "").lower()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise serializers.ValidationError("HTML 파일만 업로드할 수 있습니다.")
        if value.size and value.size > self.MAX_HTML_FILE_SIZE:
            raise serializers.ValidationError(f"HTML 파일은 최대 {self.MAX_HTML_FILE_SIZE // (1024*1024)}MB까지 업로드할 수 있습니다.")
        
        # 대용량 파일의 경우 streaming 처리를 위해 파일 포인터를 처음으로 이동하지 않음
        # (Django가 임시 파일로 저장하도록 함)
        if value.size and value.size > 10 * 1024 * 1024:  # 10MB 이상
            # 대용량 파일은 streaming으로 처리되므로 seek(0) 하지 않음
            pass
        else:
            # 작은 파일은 메모리에서 처리
            value.seek(0)
            
        return value

    def to_firestore_payload(
        self,
        *,
        html_file_path: str,
        html_content_type: str,
        html_file_size: int,
    ) -> Dict[str, Any]:
        """업로드된 파일 정보를 포함해 Firestore 저장 구조를 생성한다."""

        if not self.is_valid():
            raise AssertionError("serializer가 유효성 검사를 통과한 뒤 호출해야 합니다.")
        
        job_category = self.validated_data["job_category"].strip()
        
        # 직군별 핵심 역량 조회
        core_competencies = get_core_competencies_by_job_category(job_category)
        
        return {
            "job_category": job_category,
            "job_role": self.validated_data.get("job_role", "").strip() if self.validated_data.get("job_role") else "",
            "school_name": self.validated_data.get("school_name", "").strip() if self.validated_data.get("school_name") else "",
            "major": self.validated_data.get("major", "").strip() if self.validated_data.get("major") else "",
            "skills": self.validated_data.get("skills", []),
            "certifications": self.validated_data.get("certifications", []),
            "core_competencies": core_competencies,  # 직군별 핵심 역량 추가
            "html_file_path": html_file_path,
            "html_content_type": html_content_type,
            "html_file_size": html_file_size,
        }

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Firestore 문서를 API 응답으로 직렬화한다."""

        if isinstance(instance, dict):
            return {
                "id": instance.get("id"),
                "user_id": instance.get("user_id"),
                "job_category": instance.get("job_category"),
                "job_role": instance.get("job_role"),
                "school_name": instance.get("school_name"),
                "major": instance.get("major"),
                "skills": instance.get("skills", []),
                "certifications": instance.get("certifications", []),
                "html_file_path": instance.get("html_file_path"),
                "html_content_type": instance.get("html_content_type"),
                "html_file_size": instance.get("html_file_size"),
                "json_file_path": instance.get("json_file_path"),
                "json_content_type": instance.get("json_content_type"),
                "json_file_size": instance.get("json_file_size"),
                "conversations_count": instance.get("conversations_count"),
                "html_file_deleted": instance.get("html_file_deleted"),
                "embedding_status": instance.get("embedding_status"),
                "embedding_message": instance.get("embedding_message"),
                "embeddings_count": instance.get("embeddings_count"),
                "embedding_model": instance.get("embedding_model"),
                "has_embeddings": instance.get("has_embeddings"),
                "vectorized_competency_tags": instance.get("vectorized_competency_tags", []),
                "embedding_started_at": instance.get("embedding_started_at"),
                "embedding_completed_at": instance.get("embedding_completed_at"),
                "core_competencies": instance.get("core_competencies", []),
                "created_at": instance.get("created_at"),
                "updated_at": instance.get("updated_at"),
            }
        return super().to_representation(instance)

    @property
    def uploaded_html_file(self) -> UploadedFile:
        """검증된 HTML 파일 객체를 반환한다."""

        file_obj = self.validated_data.get("html_file")
        if file_obj is None:
            raise AssertionError("html_file 필드가 존재하지 않습니다.")
        
        # 파일 포인터 조작을 하지 않고 원본 파일 객체를 그대로 반환
        # 업로드와 읽기는 각각 별도로 파일 포인터를 관리함
        return file_obj


