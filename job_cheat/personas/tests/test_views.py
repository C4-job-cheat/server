from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, AsyncMock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.services.firebase_personas import PersonaInputSaveError, PersonaNotFoundError
from core.services.firebase_storage import PersonaHtmlUploadError


class _DummyUser:
    """force_authenticate?ÂÃ¬ÂÂ ?Â¬Ã¬ÂÂ©??ÃªÂ°ÂÃ«ÂÂ¨??Firebase ?Â¬Ã¬ÂÂ©??"""

    def __init__(self, uid: str):
        self.uid = uid

    @property
    def is_authenticated(self):
        return True


class PersonaInputCreateViewTests(TestCase):
    """?ÂÃ«Â¥Â´?ÂÃ«ÂÂ ?Â
Ã«Â Â¥ ?ÂÃ¬ÂÂ± Ã«Â·??ÂÃ¬ÂÂ??ÃªÂ²ÂÃ¬Â¦ÂÃ­ÂÂ??"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("personas-input-create")

    def _build_payload(self, *, skills="React,TypeScript"):
        return {
            "persona_name": "Sample Persona",
            "job_category": "software",
            "job_role": "backend engineer",
            "school_name": "Sample University",
            "major": "Computer Science",
            "skills": skills,
            "html_file": SimpleUploadedFile(
                "profile.html",
                b"<html><body>hello</body></html>",
                content_type="text/html",
            ),
        }

    def test_successful_creation_returns_201(self):
        user = _DummyUser(uid="user-123")
        self.client.force_authenticate(user=user)

        firestore_result = {
            "id": "generated-id",
            "persona_name": "Sample Persona",
            "job_category": "software",
            "job_role": "backend engineer",
            "school_name": "Sample University",
            "major": "Computer Science",
            "skills": ["React", "TypeScript"],
            "html_file_path": "personas/user-123/inputs/generated-id.html",
            "html_content_type": "text/html",
            "html_file_size": 42,
            "created_at": "2024-05-21T12:30:00Z",
            "updated_at": "2024-05-21T12:30:00Z",
        }

        with patch("personas.views.upload_persona_html", return_value={
            "path": "users/user-123/html/user-123.html",
            "content_type": "text/html",
            "size": 42,
        }) as mocked_upload, patch(
            "personas.views.process_persona_html_to_json", return_value={
                "json_file_path": "users/user-123/json/user-123.json",
                "json_content_type": "application/json",
                "json_file_size": 1024,
                "conversations_count": 5,
                "html_file_deleted": True,
            }
        ) as mocked_process, patch(
            "personas.views.save_user_persona_input",
            return_value=firestore_result,
        ) as mocked_save, patch(
            "personas.views.enqueue_embedding_job"
        ) as mocked_enqueue:
            response = self.client.post(self.url, data=self._build_payload(), format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mocked_upload.assert_called_once()
        mocked_process.assert_called_once()
        mocked_save.assert_called_once()
        mocked_enqueue.assert_called_once()
        self.assertEqual(response.data["html_file_path"], firestore_result["html_file_path"])
        self.assertEqual(response["Location"], "/api/personas/inputs/generated-id")

    def test_requires_authentication(self):
        response = self.client.post(self.url, data=self._build_payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_storage_error_returns_500(self):
        user = _DummyUser(uid="user-123")
        self.client.force_authenticate(user=user)

        with patch(
            "personas.views.upload_persona_html",
            side_effect=PersonaHtmlUploadError("boom"),
        ):
            response = self.client.post(self.url, data=self._build_payload(), format="multipart")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("HTML 파일 업로드에 실패했습니다", response.data["detail"])

    def test_firestore_error_returns_500(self):
        user = _DummyUser(uid="user-123")
        self.client.force_authenticate(user=user)

        with patch("personas.views.upload_persona_html", return_value={
            "path": "users/user-123/html/user-123.html",
            "content_type": "text/html",
            "size": 42,
        }), patch(
            "personas.views.process_persona_html_to_json", return_value={
                "json_file_path": "users/user-123/json/user-123.json",
                "json_content_type": "application/json",
                "json_file_size": 1024,
                "conversations_count": 5,
                "html_file_deleted": True,
            }
        ), patch(
            "personas.views.save_user_persona_input",
            side_effect=PersonaInputSaveError("boom"),
        ), patch("personas.views.enqueue_embedding_job"):
            response = self.client.post(self.url, data=self._build_payload(), format="multipart")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("페르소나 입력을 저장할 수 없습니다", response.data["detail"])

