from unittest.mock import MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from google.cloud import exceptions as gcloud_exceptions

from core.services.firebase_storage import (
    PersonaHtmlUploadError,
    upload_persona_html,
)


class UploadPersonaHtmlTests(SimpleTestCase):
    """Firebase Storage 업로드 로직을 검증한다."""

    def test_uploads_file_and_returns_metadata(self):
        file_obj = SimpleUploadedFile(
            "profile.html",
            b"<html></html>",
            content_type="text/html",
        )
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob

        result = upload_persona_html(
            user_id="user-123",
            document_id="doc-123",
            file_obj=file_obj,
            bucket=bucket,
        )

        bucket.blob.assert_called_once_with("personas/user-123/inputs/doc-123.html")
        blob.upload_from_file.assert_called_once()
        self.assertEqual(result["path"], "personas/user-123/inputs/doc-123.html")
        self.assertEqual(result["content_type"], "text/html")
        self.assertEqual(result["size"], file_obj.size)

    def test_raises_custom_error_when_upload_fails(self):
        file_obj = SimpleUploadedFile(
            "profile.html",
            b"<html></html>",
            content_type="text/html",
        )
        blob = MagicMock()
        blob.upload_from_file.side_effect = gcloud_exceptions.GoogleCloudError("boom")
        bucket = MagicMock()
        bucket.blob.return_value = blob

        with self.assertRaises(PersonaHtmlUploadError):
            upload_persona_html(
                user_id="user-123",
                document_id="doc-123",
                file_obj=file_obj,
                bucket=bucket,
            )
