#!/usr/bin/env python3
"""jobStandards.json을 개선 스키마로 변환하는 스크립트."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable


def _extract_job_group_entry(raw_entry: Dict[str, object]) -> Dict[str, object]:
    """원본 데이터의 직군 항목에서 직군명과 핵심역량을 분리한다."""

    job_keys = [key for key in raw_entry.keys() if key != "핵심역량"]
    if len(job_keys) != 1:
        raise ValueError(f"직군 항목 구조가 예상과 다릅니다: {raw_entry.keys()}")

    job_name = job_keys[0]
    roles = raw_entry[job_name]
    if not isinstance(roles, list):
        raise TypeError(f"직군 '{job_name}'의 직무 정보가 리스트가 아닙니다: {type(roles)!r}")

    core_competencies = raw_entry.get("핵심역량", {})
    if not isinstance(core_competencies, dict):
        raise TypeError(
            f"직군 '{job_name}'의 핵심역량 정보가 딕셔너리가 아닙니다: {type(core_competencies)!r}"
        )

    return {
        "name": job_name,
        "roles": roles,
        "core": core_competencies,
    }


def convert_job_standards(
    raw_data: Dict[str, object],
    *,
    version: str | None = None,
    source: str | None = None,
    last_updated: str | None = None,
) -> Dict[str, object]:
    """원본 jobStandards.json 데이터를 개선된 스키마로 변환한다."""

    job_groups = raw_data.get("직군")
    if not isinstance(job_groups, list):
        raise ValueError("'직군' 키가 리스트 형태로 존재해야 합니다.")

    converted_groups = []

    for group_index, raw_entry in enumerate(job_groups, start=1):
        if not isinstance(raw_entry, dict):
            raise TypeError(f"직군 항목이 딕셔너리가 아닙니다: {type(raw_entry)!r}")

        extracted = _extract_job_group_entry(raw_entry)
        group_id = f"JG_{group_index:02d}"

        converted_roles = []
        for role_index, role_name in enumerate(extracted["roles"], start=1):
            if not isinstance(role_name, str):
                raise TypeError(f"직무명이 문자열이 아닙니다: {role_name!r}")
            role_id = f"{group_id}_{role_index:02d}"
            converted_roles.append({"id": role_id, "name": role_name})

        converted_competencies = []
        for comp_index, (competency_name, description) in enumerate(
            extracted["core"].items(), start=1
        ):
            if not isinstance(description, str):
                raise TypeError(
                    f"핵심역량 '{competency_name}' 설명이 문자열이 아닙니다: {description!r}"
                )
            competency_id = f"{group_id}_C{comp_index:02d}"
            converted_competencies.append(
                {
                    "id": competency_id,
                    "name": competency_name,
                    "description": description,
                }
            )

        converted_groups.append(
            {
                "id": group_id,
                "name": extracted["name"],
                "roles": converted_roles,
                "core_competencies": converted_competencies,
            }
        )

    result: Dict[str, object] = {"job_groups": converted_groups}

    if version:
        result["version"] = version

    metadata = {}
    if source:
        metadata["source"] = source
    if last_updated:
        metadata["last_updated"] = last_updated
    if metadata:
        result["metadata"] = metadata

    return result


def main(argv: Iterable[str] | None = None) -> int:
    """CLI 진입점."""

    parser = argparse.ArgumentParser(
        description="jobStandards.json을 개선된 스키마로 변환하는 도구"
    )
    parser.add_argument(
        "-i",
        "--input",
        default="jobStandards.json",
        help="원본 JSON 파일 경로",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="jobStandards_v2.json",
        help="변환 결과를 저장할 JSON 파일 경로",
    )
    parser.add_argument("--version", help="출력 데이터 버전 문자열")
    parser.add_argument("--source", help="데이터 출처 정보")
    parser.add_argument("--last-updated", help="YYYY-MM-DD 형식의 수정일")

    args = parser.parse_args(list(argv) if argv is not None else None)

    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"입력 파일을 찾을 수 없습니다: {input_path}")

    with input_path.open("r", encoding="utf-8") as infile:
        raw_data = json.load(infile)

    converted = convert_job_standards(
        raw_data,
        version=args.version,
        source=args.source,
        last_updated=args.last_updated,
    )

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as outfile:
        json.dump(converted, outfile, ensure_ascii=False, indent=2)
        outfile.write("\n")

    print(f"개선된 스키마 JSON을 '{output_path}'에 저장했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
