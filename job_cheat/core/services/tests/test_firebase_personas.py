from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import SimpleTestCase
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions

from core.services.firebase_personas import (
    PersonaInputSaveError,
    save_user_persona_input,
)


class SaveUserPersonaInputTests(SimpleTestCase):
    """Firestore 저장 서비스 로직을 검증한다."""

    def _build_client(self, snapshot_payload=None):
        doc_ref = MagicMock()
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.to_dict.return_value = snapshot_payload or {}
        doc_ref.get.return_value = snapshot

        input_collection = MagicMock()
        input_collection.document.return_value = doc_ref

        user_doc = MagicMock()
        user_doc.collection.return_value = input_collection

        collection = MagicMock()
        collection.document.return_value = user_doc

        client = MagicMock()
        client.collection.return_value = collection

        return client, doc_ref

    def _payload(self):
        return {
            "persona_name": "취업 전환 준비생",
            "job_category": "프론트엔드",
            "job_role": "시니어 프론트엔드 엔지니어",
            "school_name": "서울대학교",
            "major": "컴퓨터공학과",
            "skills": ["React"],
            "html_file_path": "personas/user-123/inputs/doc.html",
            "html_content_type": "text/html",
            "html_file_size": 1024,
        }

    def test_save_sets_timestamps_and_returns_data(self):
        payload = self._payload()
        snapshot_payload = {**payload, "created_at": "ts", "updated_at": "ts"}
        client, doc_ref = self._build_client(snapshot_payload=snapshot_payload)

        fixed_uuid = UUID("11111111-1111-1111-1111-111111111111")
        with patch("core.services.firebase_personas.uuid4", return_value=fixed_uuid):
            result = save_user_persona_input(
                user_id="user-123",
                payload=payload,
                db=client,
            )

        doc_ref.set.assert_called_once()
        stored_payload = doc_ref.set.call_args[0][0]
        self.assertEqual(stored_payload["persona_name"], payload["persona_name"])
        self.assertIs(stored_payload["created_at"], firestore.SERVER_TIMESTAMP)
        self.assertEqual(result["id"], str(fixed_uuid))
        self.assertEqual(result["school_name"], payload["school_name"])

    def test_error_from_firestore_wraps_exception(self):
        payload = self._payload()
        client, doc_ref = self._build_client()
        doc_ref.set.side_effect = google_exceptions.GoogleAPICallError("boom")

        with patch("core.services.firebase_personas.uuid4", return_value=UUID("11111111-1111-1111-1111-111111111111")):
            with self.assertRaises(PersonaInputSaveError):
                save_user_persona_input(user_id="user-123", payload=payload, db=client)

    def test_missing_user_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            save_user_persona_input(user_id="", payload={}, db=MagicMock())
