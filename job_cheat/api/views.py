from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.services.firebase_users import upsert_user_from_claims
from .serializers import FirebaseUserSerializer


class VerifyFirebaseIdTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # request.user는 FirebaseAuthentication이 만든 FirebaseUser입니다.
            firebase_user = request.user
            claims = getattr(firebase_user, 'claims', {})

            response_data = {
                "uid": claims.get('uid'),
                "email": claims.get('email'),
                "email_verified": claims.get('email_verified'),
                "name": claims.get('name'),
                "picture": claims.get('picture'),
                "firebase": claims.get('firebase'),
                "provider": (claims.get('firebase') or {}).get('sign_in_provider'),
            }
            return JsonResponse(response_data)
        except Exception as exc:
            return JsonResponse({"detail": str(exc)}, status=400)


class SyncFirebaseUserView(APIView):
    '''Firebase idToken 클레임을 이용해 Firestore 사용자 문서를 생성하거나 갱신합니다.

    - 문서가 없으면 가입 흐름으로 간주해 새 문서를 생성하고 프로필을 반환합니다.
    - 문서가 있으면 마지막 로그인과 프로필 필드를 갱신한 뒤 프로필을 반환합니다.
    '''

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            claims = getattr(request.user, "claims", {})
            data = upsert_user_from_claims(claims, settings.FIREBASE_DB)
            serializer = FirebaseUserSerializer(instance=data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ImproperlyConfigured as exc:
            # Firestore가 초기화되지 않은 경우
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
