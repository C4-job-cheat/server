"""Firestore 페르소나에 대해 RAG 기반 핵심역량 평가를 실행하는 스크립트."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import django
from dotenv import load_dotenv


def bootstrap_django(project_root: Path) -> None:
    """Django 설정을 초기화한다."""

    src_path = project_root / "job_cheat"
    sys.path.insert(0, str(src_path))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_cheat.settings")
    django.setup()


async def run_competency_evaluation(
    *,
    user_id: str,
    persona_id: str,
    top_k: int,
    vector_context_top_k: int,
    conversation_limit: int,
) -> Dict[str, Any]:
    """핵심역량 평가 서비스를 호출한다."""

    from core.services import get_competency_evaluator
    from core.services.rag_competency_evaluator import (
        PersonaNotFoundError,
        RAGCompetencyEvaluatorError,
    )

    evaluator = get_competency_evaluator()

    try:
        result = await evaluator.evaluate_persona_competencies(
            user_id=user_id,
            persona_id=persona_id,
            top_k=top_k,
            vector_context_top_k=vector_context_top_k,
            conversation_limit=conversation_limit,
        )
    except PersonaNotFoundError as exc:
        raise RuntimeError(
            f"Firestore에서 페르소나 문서를 찾을 수 없습니다. user_id={user_id}, persona_id={persona_id}"
        ) from exc
    except RAGCompetencyEvaluatorError as exc:
        raise RuntimeError(f"핵심역량 평가가 실패했습니다: {exc}") from exc

    return result


def build_output_lines(result: Dict[str, Any]) -> List[str]:
    """평가 결과를 사람이 읽기 쉬운 문자열 목록으로 변환한다."""

    lines: List[str] = []
    lines.append(f"사용자 ID: {result.get('user_id')}")
    lines.append(f"페르소나 ID: {result.get('persona_id')}")
    lines.append(f"평가 버전: {result.get('evaluation_version')}")
    lines.append(f"평가 시작 시각: {result.get('evaluation_started_at')}")
    lines.append(f"평가 완료 시각: {result.get('evaluation_completed_at')}")

    competency_scores = result.get("competency_scores", {})
    if competency_scores:
        lines.append("핵심역량 점수 요약:")
        for comp_id, score in competency_scores.items():
            lines.append(f" - {comp_id}: {score}")
    else:
        lines.append("핵심역량 점수를 찾을 수 없습니다.")

    details: List[Dict[str, Any]] = result.get("details", []) or []
    if details:
        lines.append("\n세부 평가 결과:")
        for detail in details:
            lines.append(
                " - 역량: {name} ({cid}) | 점수: {score} | 신뢰도: {confidence}".format(
                    name=detail.get("competency_name"),
                    cid=detail.get("competency_id"),
                    score=detail.get("score"),
                    confidence=detail.get("confidence"),
                )
            )
            lines.append(f"   Reasoning: {detail.get('reasoning')}")
            strong_signals = detail.get("strong_signals") or []
            if strong_signals:
                lines.append(f"   Strong signals: {strong_signals}")
            risk_factors = detail.get("risk_factors") or []
            if risk_factors:
                lines.append(f"   Risk factors: {risk_factors}")
            recommended = detail.get("recommended_actions") or []
            if recommended:
                lines.append(f"   Recommended actions: {recommended}")
            evidence = detail.get("evidence") or []
            if evidence:
                lines.append("   Evidence:")
                for item in evidence[:5]:
                    lines.append(
                        "     - source={source}, reference_id={ref}, score={score}".format(
                            source=item.get("source"),
                            ref=item.get("reference_id"),
                            score=item.get("relevance_score"),
                        )
                    )
            lines.append("")

    errors: List[Dict[str, Any]] = result.get("errors", []) or []
    if errors:
        lines.append("오류/경고:")
        for error in errors:
            lines.append(
                " - 역량 {cid} ({name}): {msg}".format(
                    cid=error.get("competency_id"),
                    name=error.get("competency_name"),
                    msg=error.get("error"),
                )
            )

    def _json_default(obj):
        import datetime
        from google.api_core.datetime_helpers import DatetimeWithNanoseconds

        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, DatetimeWithNanoseconds):
            return obj.isoformat()
        return str(obj)

    lines.append("\n전체 JSON 결과:")
    lines.append(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG 핵심역량 평가 실행 스크립트")
    parser.add_argument("--user-id", required=True, help="Firestore 사용자 ID (Pinecone namespace와 동일하게 유지)")
    parser.add_argument("--persona-id", required=True, help="Firestore 페르소나 ID")
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(os.getenv("COMPETENCY_EVAL_TOP_K", "5")),
        help="Pinecone 유사도 검색에서 가져올 최대 개수 (기본 5)",
    )
    parser.add_argument(
        "--vector-context-top-k",
        type=int,
        default=int(os.getenv("COMPETENCY_EVAL_VECTOR_TOP_K", "3")),
        help="LLM 프롬프트에 포함할 벡터 컨텍스트 상위 개수 (기본 3)",
    )
    parser.add_argument(
        "--conversation-limit",
        type=int,
        default=int(os.getenv("COMPETENCY_EVAL_CONVERSATION_LIMIT", "5")),
        help="LLM 프롬프트에 포함할 대화 스니펫 최대 개수 (기본 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="competency-evaluation-result.txt",
        help="결과를 저장할 파일 경로",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    args = parse_args()

    project_root = Path(__file__).resolve().parents[2]
    bootstrap_django(project_root)

    result = asyncio.run(
        run_competency_evaluation(
            user_id=args.user_id,
            persona_id=args.persona_id,
            top_k=max(1, args.top_k),
            vector_context_top_k=max(1, args.vector_context_top_k),
            conversation_limit=max(1, args.conversation_limit),
        )
    )

    lines = build_output_lines(result)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\n결과가 '{output_path}'에 저장되었습니다.")


if __name__ == "__main__":
    main()


