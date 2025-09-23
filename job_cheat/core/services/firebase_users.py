from __future__ import annotations

from typing import Dict, Any

from django.utils import timezone


def _coerce_profile_from_claims(claims: Dict[str, Any]) -> Dict[str, Any]:
    firebase_info = (claims or {}).get("firebase") or {}
    return {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "display_name": claims.get("name"),
        "photo_url": claims.get("picture"),
        "email_verified": claims.get("email_verified"),
        "provider_id": firebase_info.get("sign_in_provider"),
    }


def upsert_user_from_claims(claims: Dict[str, Any], db) -> Dict[str, Any]:
    """Create or update Firestore users/{uid} doc from Firebase ID token claims.

    - Creates the document when not exists and sets created_at.
    - Updates existing document and refreshes last_login_at/updated_at.
    - Returns a flat dict including uid and timestamps for API serialization.
    """
    if db is None:
        raise RuntimeError("Firestore is not initialized")

    ts = timezone.now()
    profile = _coerce_profile_from_claims(claims)
    uid = profile.get("uid")
    if not uid:
        raise ValueError("Missing uid in claims")

    doc_ref = db.collection("users").document(uid)
    snapshot = doc_ref.get()

    payload = {
        "email": profile["email"],
        "display_name": profile["display_name"],
        "photo_url": profile["photo_url"],
        "email_verified": profile["email_verified"],
        "provider_id": profile["provider_id"],
        "last_login_at": ts,
        "updated_at": ts,
    }

    if not snapshot.exists:
        payload["created_at"] = ts
        doc_ref.set(payload)
    else:
        doc_ref.update(payload)

    # Include uid in the response dict
    payload["uid"] = uid
    return payload

