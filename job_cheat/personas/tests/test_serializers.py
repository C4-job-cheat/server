from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from personas.api.serializers import PersonaInputSerializer


class PersonaInputSerializerTests(SimpleTestCase):
    """페르소나 입력 serializer 동작을 검증한다."""

    def _base_payload(self):
        return {
            "persona_name": "취업 전환 준비생",
            "job_category": "프론트엔드",
            "job_role": "시니어 프론트엔드 엔지니어",
            "school_name": "서울대학교",
            "major": "컴퓨터공학과",
            "skills": ["React", "TypeScript"],
            "html_file": SimpleUploadedFile(
                "profile.html",
                b"<html><body><h1>Profile</h1></body></html>",
                content_type="text/html",
            ),
        }

    def test_valid_payload_generates_firestore_payload(self):
        serializer = PersonaInputSerializer(data=self._base_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        payload = serializer.to_firestore_payload(
            html_file_path="personas/user-123/inputs/doc.html",
            html_content_type="text/html",
            html_file_size=123,
        )
        self.assertEqual(payload["skills"], ["React", "TypeScript"])
        self.assertEqual(payload["html_file_path"], "personas/user-123/inputs/doc.html")
        self.assertEqual(payload["school_name"], "서울대학교")
        self.assertEqual(payload["major"], "컴퓨터공학과")

    def test_skills_accepts_comma_separated_string(self):
        data = self._base_payload()
        data["skills"] = "React, React , TypeScript"

        serializer = PersonaInputSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["skills"], ["React", "TypeScript"])

    def test_rejects_invalid_html_mime(self):
        data = self._base_payload()
        data["html_file"] = SimpleUploadedFile(
            "profile.txt",
            b"not html",
            content_type="text/plain",
        )

        serializer = PersonaInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("html_file", serializer.errors)

    def test_accepts_empty_skills(self):
        """빈 skills 배열은 허용되어야 한다 (선택사항 필드)."""
        data = self._base_payload()
        data["skills"] = ["   "]  # 공백만 있는 배열

        serializer = PersonaInputSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["skills"], [])  # 빈 배열로 정규화됨
