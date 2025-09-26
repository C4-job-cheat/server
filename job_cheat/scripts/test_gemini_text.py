"""Gemini 텍스트 생성 API 응답을 점검하는 간단한 스크립트."""

from __future__ import annotations

import logging
import os
import sys

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - 런타임 환경 문제
    raise RuntimeError("google-generativeai 패키지를 불러올 수 없습니다.") from exc

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def main() -> int:
    """Gemini LLM에 간단한 인사말을 전송하고 응답을 표시한다."""

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        return 1

    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-1.5-pro")
    model = genai.GenerativeModel(model_name)

    prompt = "안녕"
    logger.info("Gemini 모델(%s)에 프롬프트를 전송합니다.", model_name)

    try:
        result = model.generate_content(prompt)
    except Exception as exc:  # pragma: no cover - 외부 API 호출 예외
        logger.exception("Gemini API 호출에 실패했습니다.")
        print(f"Gemini API 호출 실패: {exc}")
        return 1

    text_output = getattr(result, "text", None)
    if not text_output:
        logger.warning("응답에서 text 필드를 찾을 수 없어 원본을 출력합니다.")
        print("원본 응답:")
        print(result)
    else:
        print("Gemini 응답:")
        print(text_output)

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())


