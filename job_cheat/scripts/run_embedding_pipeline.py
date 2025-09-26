"""chat_converted.json을 이용해 임베딩 파이프라인을 실행하고 결과를 TXT로 기록하는 스크립트."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import List

import django
from dotenv import load_dotenv


def bootstrap_django(project_root: Path) -> None:
    """Django 환경을 초기화한다."""

    src_path = project_root / "job_cheat"
    sys.path.insert(0, str(src_path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")
    django.setup()


async def run_embedding_pipeline(json_path: Path, user_id: str, output_path: Path) -> None:
    """JSON 파일을 임베딩하고 Pinecone에 업서트한 뒤 결과를 파일에 기록한다."""

    from core.services.rag_embedding_service import RAGEmbeddingService
    from core.services.pinecone_service import get_pinecone_service

    service = RAGEmbeddingService()
    pinecone_service = get_pinecone_service()

    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

    json_content = json_path.read_text(encoding="utf-8")

    conversations = await service.extract_user_conversations(json_content)
    conversation_count = len(conversations)

    embeddings = await service.generate_embeddings(conversations)
    embedding_count = len(embeddings)

    formatted_vectors = service._format_pinecone_vectors(embeddings)

    batch_size_env = os.getenv("EMBEDDING_UPSERT_BATCH_SIZE")
    try:
        batch_size = int(batch_size_env) if batch_size_env else 50
    except ValueError:
        batch_size = 50
    batch_size = max(1, batch_size)

    total_vectors = len(formatted_vectors)
    batches = 0
    for start in range(0, total_vectors, batch_size):
        batch = formatted_vectors[start : start + batch_size]
        pinecone_service.upsert_vectors(batch, namespace=user_id)
        batches += 1

    namespace_vector_count = pinecone_service.namespace_vector_count(user_id)

    matches: List[dict] = []
    if embeddings:
        reference_vector = embeddings[0]["embedding"]
        query_response = pinecone_service.query_similar(
            reference_vector,
            namespace=user_id,
            top_k=3,
        )
        matches = query_response.get("matches", []) or []

    unique_tags = sorted(
        {
            tag
            for item in embeddings
            for tag in item.get("competency_tags", [])
            if tag
        }
    )

    lines: List[str] = []
    lines.append(f"사용자 ID: {user_id}")
    lines.append(f"입력 JSON: {json_path}")
    lines.append(f"총 사용자 발화 수: {conversation_count}")

    lines.append("샘플 사용자 발화 (최대 3건):")
    for conv in conversations[:3]:
        snippet = conv.get("content", "")[:120].replace("\n", " ")
        lines.append(f" - 대화ID={conv.get('conversation_id')} 내용={snippet}")
    if conversation_count == 0:
        lines.append(" - (발화를 찾을 수 없습니다.)")

    lines.append(f"생성된 임베딩 개수: {embedding_count}")
    lines.append(f"Pinecone 업서트 배치 크기: {batch_size} (총 배치 수: {batches})")
    lines.append(f"Pinecone namespace 벡터 수: {namespace_vector_count}")
    lines.append(f"임베딩 모델: {service.embedding_model}")
    lines.append(f"역량 태그 수: {len(unique_tags)} / 태그 목록: {unique_tags if unique_tags else '[]'}")

    lines.append("쿼리 상위 매치 (top 3):")
    if matches:
        for match in matches:
            match_id = match.get("id") or match.get("metadata", {}).get("id")
            score = match.get("score")
            lines.append(f" - id={match_id}, score={score}")
    else:
        lines.append(" - (매치 결과가 없습니다.)")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\n결과가 '{output_path}'에 저장되었습니다.")


def main() -> None:
    load_dotenv()

    project_root = Path(__file__).resolve().parents[2]
    bootstrap_django(project_root)

    json_path = project_root / "chatgpt_export" / "chat_converted.json"
    output_path = project_root / "embedding-test-result.txt"

    user_id = os.getenv("TEST_EMBEDDING_USER_ID")
    if not user_id:
        raise RuntimeError(
            "TEST_EMBEDDING_USER_ID 환경 변수가 설정되지 않았습니다."
        )

    asyncio.run(run_embedding_pipeline(json_path, user_id, output_path))


if __name__ == "__main__":
    main()


