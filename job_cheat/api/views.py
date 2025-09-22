from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


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
