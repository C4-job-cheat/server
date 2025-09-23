#!/usr/bin/env python
"""Firebase Storage 업로드 동작을 수동 검증하기 위한 스크립트."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "job_cheat"
for entry in (PROJECT_ROOT, PACKAGE_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")

import django

django.setup()

from firebase_admin import storage  # noqa: E402  pylint: disable=wrong-import-position


def _load_html_content(html_path: Optional[Path]) -> str:
    """지정된 경로의 HTML 파일을 읽거나 기본 샘플을 반환한다."""

    if html_path is None:
        return "<html><body><h1>Persona Input Test</h1></body></html>"
    if not html_path.exists():
        raise FileNotFoundError(f"HTML 파일을 찾을 수 없습니다: {html_path}")
    return html_path.read_text(encoding="utf-8")


def upload_test_html(user_id: str, html_path: Optional[Path] = None) -> str:
    """Firebase Storage에 테스트 HTML을 업로드하고 경로를 반환한다."""

    if not user_id.strip():
        raise ValueError("user_id 값을 지정해야 합니다.")

    bucket = storage.bucket()
    document_id = uuid4().hex
    blob_path = f"personas/{user_id}/inputs/{document_id}.html"

    html_content = _load_html_content(html_path)

    blob = bucket.blob(blob_path)
    blob.cache_control = "public, max-age=60"
    blob.upload_from_string(html_content, content_type="text/html")

    return blob.public_url or f"gs://{bucket.name}/{blob_path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Firebase Storage 업로드 테스트")
    parser.add_argument("user_id", help="업로드 경로에 사용할 Firebase 사용자 UID")
    parser.add_argument(
        "--html",
        type=Path,
        help="업로드할 HTML 파일 경로. 생략 시 기본 샘플 HTML 사용",
    )
    args = parser.parse_args()

    public_url = upload_test_html(user_id=args.user_id, html_path=args.html)
    print("업로드 완료")
    print(f"버킷: {storage.bucket().name}")
    print(f"공개 URL: {public_url}")


if __name__ == "__main__":
    main()
