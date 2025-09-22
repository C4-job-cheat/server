from typing import Optional, Tuple

from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from firebase_admin import auth as firebase_auth
from django.conf import settings


class FirebaseUser:
    """Lightweight user-like object for DRF permissions.

    Provides is_authenticated and basic Firebase claims access.
    """

    def __init__(self, uid: str, claims: dict):
        self.uid = uid
        self.claims = claims or {}

    @property
    def is_authenticated(self) -> bool:  # for DRF IsAuthenticated
        return True

    def __str__(self) -> str:
        return f"FirebaseUser(uid={self.uid})"


class FirebaseAuthentication(BaseAuthentication):
    """Authenticate requests using Firebase idToken in Authorization header.

    Expected header: Authorization: Bearer <idToken>
    """

    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[FirebaseUser, None]]:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None

        parts = auth_header.split(" ", 1)
        if len(parts) != 2:
            return None
        scheme, token = parts[0], parts[1].strip()

        if scheme != self.keyword or not token:
            return None

        firebase_app = getattr(settings, "FIREBASE_APP", None)
        try:
            decoded = firebase_auth.verify_id_token(token, check_revoked=False, app=firebase_app)
        except firebase_auth.ExpiredIdTokenError:
            raise exceptions.AuthenticationFailed("Expired Firebase idToken")
        except firebase_auth.InvalidIdTokenError:
            raise exceptions.AuthenticationFailed("Invalid Firebase idToken")
        except firebase_auth.RevokedIdTokenError:
            raise exceptions.AuthenticationFailed("Revoked Firebase idToken")
        except Exception as exc:  # pragma: no cover - pass message upstream
            raise exceptions.AuthenticationFailed(str(exc))

        uid = decoded.get("uid")
        if not uid:
            raise exceptions.AuthenticationFailed("Missing uid in token")

        user = FirebaseUser(uid=uid, claims=decoded)
        return (user, None)


