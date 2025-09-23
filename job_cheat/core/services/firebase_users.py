from __future__ import annotations

from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


USER_COLLECTION = "users"

# Firestore에 저장을 허용하는 필드 목록
ALLOWED_PROFILE_FIELDS = (
    "email",
    "display_name",
    "photo_url",
    "email_verified",
    "provider_id",
)


def _coerce_profile_from_claims(claims: Dict[str, Any]) -> Dict[str, Any]:
    """Firebase 토큰 클레임에서 Firestore 사용자 문서에 필요한 필드만 추출한다."""

    claims = claims or {}
    firebase_info = claims.get("firebase") or {}

    display_name = claims.get("name") or None
    if isinstance(display_name, str):
        display_name = display_name.strip() or None

    photo_url = claims.get("picture") or None
    if isinstance(photo_url, str):
        photo_url = photo_url.strip() or None

    provider_id = firebase_info.get("sign_in_provider") or None
    if isinstance(provider_id, str):
        provider_id = provider_id.strip() or None

    return {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "display_name": display_name,
        "photo_url": photo_url,
        "email_verified": claims.get("email_verified"),
        "provider_id": provider_id,
    }


def upsert_user_from_claims(claims: Dict[str, Any], db) -> Dict[str, Any]:
    """Firebase 클레임을 이용해 Firestore ``users`` 문서를 생성하거나 갱신한다.

    최초 호출 시 `created_at`을 설정하고, 이후 호출에서는 `last_login_at`과
    `updated_at`만 새로 기록하도록 보장한다.
    """
    if db is None:
        raise ImproperlyConfigured(
            "Firestore client is not configured. Ensure FIREBASE_DB is available."
        )

    ts = timezone.now()
    profile = _coerce_profile_from_claims(claims)
    uid = profile.get("uid")
    if not uid:
        raise ValueError("Missing uid in claims")

    doc_ref = db.collection(USER_COLLECTION).document(uid)
    snapshot = doc_ref.get()
    existing_data = snapshot.to_dict() if snapshot.exists else {}

    payload = {
        field_name: profile.get(field_name)
        for field_name in ALLOWED_PROFILE_FIELDS
    }
    payload.update(
        {
            "last_login_at": ts,
            "updated_at": ts,
        }
    )

    if snapshot.exists:
        doc_ref.update(payload)
        created_at = existing_data.get("created_at")
    else:
        created_at = ts
        write_payload = {**payload, "created_at": created_at}
        doc_ref.set(write_payload)

    return {
        **payload,
        "uid": uid,
        "created_at": created_at,
    }
