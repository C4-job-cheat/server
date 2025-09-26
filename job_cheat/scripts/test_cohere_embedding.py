"""chat-standard.json 데이터를 이용해 Cohere 임베딩 파이프라인을 점검하는 스크립트."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv
import tiktoken


def bootstrap_django(project_root: Path) -> None:
    """Django 설정을 초기화한다."""

    src_path = project_root / "job_cheat"
    sys.path.insert(0, str(src_path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")
    django.setup()


async def run_embedding_test(json_path: Path) -> None:
    """지정한 JSON 파일을 기반으로 임베딩을 생성하고 요약 정보를 출력한다."""

    from core.services.rag_embedding_service import RAGEmbeddingService
    from core.services.pinecone_service import get_pinecone_service

    tokenizer = tiktoken.get_encoding("cl100k_base")
    service = RAGEmbeddingService()
    pinecone_service = get_pinecone_service()

    with json_path.open("r", encoding="utf-8") as fp:
        json_content = fp.read()

    conversations = await service.extract_user_conversations(json_content)
    print(f"사용자 발화 개수: {len(conversations)}")

    sample = conversations[:3]
    if sample:
        print("샘플 사용자 발화:")
        for conv in sample:
            tokens = tokenizer.encode(conv["content"])
            print(f" - {conv['content'][:80]} (토큰 수: {len(tokens)})")

    embeddings = await service.generate_embeddings(conversations)
    print(f"생성된 임베딩 개수: {len(embeddings)}")

    if embeddings:
        formatted = service._format_pinecone_vectors(embeddings)
        pinecone_service.upsert_vectors(formatted, namespace="test")
        print("Pinecone upsert 완료")
        first_embedding = embeddings[0]["embedding"]
        query_result = pinecone_service.query_similar(first_embedding, namespace="test", top_k=3)
        print(f"쿼리 결과 개수: {len(query_result.get('matches', []))}")
        print(f"임베딩 모델: {service.embedding_model}")
        print(f"역량 태그 샘플: {embeddings[0].get('competency_tags', [])}")


def main() -> None:
    load_dotenv()
    project_root = Path(__file__).resolve().parents[2]
    bootstrap_django(project_root)
    json_path = project_root / "chatgpt_export" / "chat-standard.json"

    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

    asyncio.run(run_embedding_test(json_path))


if __name__ == "__main__":
    main()

