from uuid import uuid4

from rest_framework import exceptions, status
from rest_framework.decorators import api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import FirebaseAuthentication
from core.services.firebase_personas import (
    PersonaInputSaveError,
    save_user_persona_input,
)
from core.services.firebase_storage import (
    PersonaHtmlUploadError,
    upload_persona_html,
)
from personas.api.serializers import PersonaInputSerializer


@api_view(["GET"])
def health(request):
    user = getattr(request, "user", None)
    uid = getattr(user, "uid", None)
    return Response({"ok": True, "feature": "personas", "uid": uid})


class PersonaInputCreateView(APIView):
    """사용자 페르소나 정보를 HTML 파일과 함께 저장한다."""

    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        serializer = PersonaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = getattr(request, "user", None)
        user_id = getattr(user, "uid", None)
        if not user_id:
            raise exceptions.NotAuthenticated("Firebase 사용자 인증이 필요합니다.")

        document_id = str(uuid4())
        html_file = serializer.uploaded_html_file

        try:
            upload_result = upload_persona_html(
                user_id=user_id,
                document_id=document_id,
                file_obj=html_file,
            )
        except PersonaHtmlUploadError as exc:
            raise exceptions.APIException(f"HTML 파일 업로드에 실패했습니다: {exc}") from exc

        payload = serializer.to_firestore_payload(
            html_file_path=upload_result["path"],
            html_content_type=upload_result["content_type"],
            html_file_size=upload_result["size"],
        )

        try:
            firestore_result = save_user_persona_input(
                user_id=user_id,
                payload=payload,
                document_id=document_id,
            )
        except PersonaInputSaveError as exc:
            raise exceptions.APIException(f"페르소나 입력을 저장할 수 없습니다: {exc}") from exc

        response_serializer = PersonaInputSerializer(instance=firestore_result)
        headers = {}
        if firestore_result.get("id"):
            headers["Location"] = f"/api/personas/inputs/{firestore_result['id']}"

        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
