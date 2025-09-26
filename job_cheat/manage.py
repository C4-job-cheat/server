#!/usr/bin/env python
"""Django의 명령줄 유틸리티입니다."""
import os
import sys


def main():
    """Django 관리 작업을 실행합니다."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_cheat.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django를 가져올 수 없습니다. 가상환경이 활성화되어 있고 "
            "Django가 설치되어 있는지 확인하세요. "
            f"오류: {exc}"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
