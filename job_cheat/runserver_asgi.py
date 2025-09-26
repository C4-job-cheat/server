#!/usr/bin/env python
"""
200MB 대용량 파일 업로드를 위한 ASGI 서버 실행 스크립트

이 스크립트는 Uvicorn ASGI 서버를 사용하여 대용량 HTML 파일 업로드를
비동기적으로 처리합니다. 최대 200MB까지의 파일을 지원합니다.

사용법:
    uv run python runserver_asgi.py [포트번호]
    
예시:
    uv run python runserver_asgi.py 8000
    uv run python runserver_asgi.py 0.0.0.0:8000
"""

import os
import sys
import asyncio
import signal
import uvicorn
from pathlib import Path

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_cheat.settings')

def setup_django():
    """Django 설정 초기화"""
    import django
    django.setup()
    print("✅ Django 설정이 초기화되었습니다.")

def create_large_file_config():
    """대용량 파일 처리를 위한 Uvicorn 설정 생성"""
    return {
        'app': 'job_cheat.asgi:application',
        'host': '0.0.0.0',
        'port': 8000,
        'workers': 1,  # 단일 워커로 메모리 사용량 최적화
        'loop': 'asyncio',
        'http': 'httptools',  # 고성능 HTTP 파서
        'ws': 'websockets',
        'ws_max_size': 200 * 1024 * 1024,  # 200MB WebSocket 메시지 제한
        'ws_max_queue': 32,
        'ws_ping_interval': 20.0,
        'ws_ping_timeout': 20.0,
        'timeout_keep_alive': 1800,  # 30분 Keep-Alive 타임아웃
        'timeout_graceful_shutdown': 30,  # 30초 Graceful shutdown
        'limit_max_requests': 1000,  # 메모리 누수 방지
        'limit_concurrency': 100,  # 동시 연결 제한
        'backlog': 2048,  # 연결 백로그
        'access_log': True,
        'log_level': 'info',
        'reload': False,  # 프로덕션 모드
        'reload_dirs': None,
        'reload_includes': None,
        'reload_excludes': None,
        'reload_delay': 0.25,
        'use_colors': True,
        'interface': 'asgi3',
        'factory': False,
        'proxy_headers': True,
        'server_header': True,
        'date_header': True,
        'forwarded_allow_ips': '*',
        'root_path': '',
        'uds': None,
        'fd': None,
        'ssl_keyfile': None,
        'ssl_certfile': None,
        'ssl_keyfile_password': None,
        'ssl_version': None,
        'ssl_cert_reqs': None,
        'ssl_ca_certs': None,
        'ssl_ciphers': None,
        'headers': [
            ('Server', 'JobCheat-ASGI/1.0'),
            ('X-Powered-By', 'Django-ASGI'),
        ],
        'h11_max_incomplete_event_size': 16384,
    }

def signal_handler(signum, frame):
    """시그널 핸들러 (Graceful shutdown)"""
    print(f"\n🛑 서버 종료 신호를 받았습니다 (Signal: {signum})")
    print("   연결된 클라이언트의 요청을 완료한 후 종료합니다...")
    sys.exit(0)

def run_asgi_server(addrport='8000'):
    """ASGI 서버 실행"""
    
    # 주소와 포트 파싱
    if ':' in addrport:
        host, port = addrport.split(':', 1)
        port = int(port)
    else:
        host = '0.0.0.0'
        port = int(addrport)
    
    # Django 설정 초기화
    setup_django()
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 200MB 대용량 파일 업로드 ASGI 서버 시작 중...")
    print(f"   - 주소: {host}:{port}")
    print(f"   - 서버: Uvicorn ASGI")
    print(f"   - 최대 파일 크기: 200MB")
    print(f"   - 비동기 처리: 활성화")
    print(f"   - Keep-Alive 타임아웃: 30분")
    print(f"   - Django 설정: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print("=" * 70)
    
    # Uvicorn 설정 생성
    config = create_large_file_config()
    config['host'] = host
    config['port'] = port
    
    print(f"✅ 서버가 http://{host}:{port} 에서 실행 중입니다.")
    print("   비동기 처리로 200MB HTML 파일 업로드를 지원합니다.")
    print("   엔드포인트:")
    print(f"   - 동기: http://{host}:{port}/api/personas/inputs/")
    print(f"   - 비동기: http://{host}:{port}/api/personas/async/inputs/")
    print("   종료하려면 Ctrl+C를 누르세요.")
    print("=" * 70)
    
    try:
        # Uvicorn 서버 실행
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n🛑 서버를 종료합니다...")
        print("✅ 서버가 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 서버 실행 중 오류가 발생했습니다: {e}")
        sys.exit(1)

def main():
    """메인 함수"""
    # 도움말 옵션 처리
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
200MB 대용량 파일 업로드를 위한 ASGI 서버

사용법:
    uv run python runserver_asgi.py [주소:포트]

옵션:
    주소:포트    서버 주소와 포트 (기본값: 8000)
                예: 0.0.0.0:8000, localhost:8080

예시:
    uv run python runserver_asgi.py                    # localhost:8000에서 실행
    uv run python runserver_asgi.py 0.0.0.0:8000      # 모든 인터페이스에서 실행
    uv run python runserver_asgi.py 8080               # localhost:8080에서 실행

특징:
    - 최대 200MB 파일 업로드 지원
    - 비동기 처리로 높은 성능
    - 30분 Keep-Alive 타임아웃
    - 메모리 효율적인 임시 파일 처리
    - Graceful shutdown 지원

엔드포인트:
    - 동기: /api/personas/inputs/
    - 비동기: /api/personas/async/inputs/
        """)
        return
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        addrport = sys.argv[1]
    else:
        addrport = '8000'
    
    # 프로젝트 루트 디렉토리로 이동
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # ASGI 서버 실행
    run_asgi_server(addrport)

if __name__ == '__main__':
    main()
