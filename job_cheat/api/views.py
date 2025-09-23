from django.http import JsonResponse
from django.conf import settings
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
            # request.user는 FirebaseAuthentication이 만든 FirebaseUser
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
    """Create or update Firestore user doc based on Firebase idToken claims.

    - If the user doc doesn't exist, create it (sign-up) and return profile.
    - If it exists, update last_login_at/profile fields (sign-in) and return profile.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            claims = getattr(request.user, "claims", {})
            data = upsert_user_from_claims(claims, settings.FIREBASE_DB)
            serializer = FirebaseUserSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RuntimeError as e:
            # Firestore not initialized
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
