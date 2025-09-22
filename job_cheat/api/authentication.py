"""Deprecated: moved to core.authentication.

This module remains to avoid import errors during refactor. Prefer
`core.authentication.FirebaseAuthentication`.
"""

from core.authentication import FirebaseAuthentication, FirebaseUser  # noqa: F401


