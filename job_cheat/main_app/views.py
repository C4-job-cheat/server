from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings

from firebase_admin import auth
import json

# Create your views here.
def home(request):
    return JsonResponse({"message": "Hello, World!"})


@method_decorator(csrf_exempt, name='dispatch')
class VerifyFirebaseIdTokenView(View):
    def post(self, request):
        try:
            body_unicode = request.body.decode('utf-8') if request.body else '{}'
            payload = json.loads(body_unicode)

            id_token = payload.get('idToken') or payload.get('token')
            if not id_token:
                # Authorization: Bearer <idToken> 도 허용
                auth_header = request.headers.get('Authorization') or ''
                if auth_header.lower().startswith('bearer '):
                    id_token = auth_header.split(' ', 1)[1].strip()

            if not id_token:
                return JsonResponse({"detail": "Missing idToken"}, status=400)

            decoded = auth.verify_id_token(id_token, check_revoked=False)

            user_record = None
            try:
                user_record = auth.get_user(decoded['uid'])
            except Exception:
                pass

            return JsonResponse({
                "uid": decoded.get('uid'),
                "email": decoded.get('email'),
                "email_verified": decoded.get('email_verified'),
                "name": decoded.get('name'),
                "picture": decoded.get('picture'),
                "firebase": decoded.get('firebase'),
                "provider": (decoded.get('firebase') or {}).get('sign_in_provider'),
                "user": {
                    "uid": getattr(user_record, 'uid', None),
                    "phone_number": getattr(user_record, 'phone_number', None),
                    "disabled": getattr(user_record, 'disabled', None),
                }
            })
        except auth.ExpiredIdTokenError:
            return JsonResponse({"detail": "Expired token"}, status=401)
        except auth.InvalidIdTokenError:
            return JsonResponse({"detail": "Invalid token"}, status=401)
        except auth.RevokedIdTokenError:
            return JsonResponse({"detail": "Revoked token"}, status=401)
        except Exception as exc:
            return JsonResponse({"detail": str(exc)}, status=400)