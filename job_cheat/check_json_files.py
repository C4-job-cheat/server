#!/usr/bin/env python
"""
개발 과정에서 Firebase Storage에 저장된 JSON 파일들을 확인하는 스크립트
"""

import os
import sys
import json
from pathlib import Path

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_cheat.settings')

import django
django.setup()

from core.services.firebase_storage import download_persona_json, list_user_persona_files


def check_user_files(user_id: str):
    """사용자의 모든 파일 목록을 확인합니다."""
    print(f"🔍 사용자 {user_id}의 파일 목록 조회 중...")
    
    try:
        result = list_user_persona_files(user_id=user_id)
        
        print(f"📁 HTML 파일: {result['total_html_files']}개")
        for file_info in result['html_files']:
            print(f"  - {file_info['name']} ({file_info['size']:,} bytes)")
        
        print(f"📄 JSON 파일: {result['total_json_files']}개")
        for file_info in result['json_files']:
            print(f"  - {file_info['name']} ({file_info['size']:,} bytes)")
            print(f"    생성일: {file_info['created']}")
            print(f"    수정일: {file_info['updated']}")
        
        return result['json_files']
        
    except Exception as exc:
        print(f"❌ 파일 목록 조회 실패: {exc}")
        return []


def download_and_check_json(user_id: str, document_id: str):
    """특정 JSON 파일을 다운로드하고 내용을 확인합니다."""
    print(f"📥 JSON 파일 다운로드 중: {document_id}")
    
    try:
        result = download_persona_json(
            user_id=user_id,
            document_id=document_id,
        )
        
        if not result["exists"]:
            print(f"❌ JSON 파일을 찾을 수 없습니다: {document_id}")
            return None
        
        print(f"✅ JSON 파일 다운로드 성공!")
        print(f"  - 경로: {result['path']}")
        
        # 안전하게 크기 출력
        size = result.get('size')
        if size is not None:
            print(f"  - 크기: {size:,} bytes")
        else:
            print(f"  - 크기: 알 수 없음")
        
        print(f"  - 타입: {result['content_type']}")
        
        # JSON 내용 파싱
        json_data = json.loads(result['content'])
        
        print(f"\n📊 JSON 내용 분석:")
        print(f"  - 총 대화 수: {json_data.get('total_conversations', 0)}")
        print(f"  - 총 메시지 수: {json_data.get('total_messages', 0)}")
        
        # JSON 구조 정보 출력
        print(f"\n🔍 JSON 구조 정보:")
        print(f"  - 최상위 키들: {list(json_data.keys())}")
        
        # 첫 번째 대화 내용 미리보기
        conversations = json_data.get('conversations', [])
        if conversations:
            first_conv = conversations[0]
            print(f"  - 대화 객체 키들: {list(first_conv.keys())}")
            
            # 안전하게 값 가져오기
            title = first_conv.get('title')
            if title is None:
                title = 'N/A'
            print(f"\n💬 첫 번째 대화 미리보기:")
            print(f"  - 제목: {title}")
            
            messages = first_conv.get('messages', [])
            print(f"  - 메시지 수: {len(messages)}")
            
            # 첫 번째 메시지 내용
            if messages:
                first_msg = messages[0]
                print(f"  - 메시지 객체 키들: {list(first_msg.keys())}")
                
                content = first_msg.get('content', '')
                if content is None:
                    content = ''
                preview = content[:100] + "..." if len(content) > 100 else content
                print(f"  - 첫 메시지: {preview}")
        
        return json_data
        
    except Exception as exc:
        print(f"❌ JSON 파일 다운로드 실패: {exc}")
        import traceback
        traceback.print_exc()
        return None


def save_json_to_file(user_id: str, document_id: str, output_path: str = None):
    """JSON 파일을 로컬 파일로 저장합니다."""
    if not output_path:
        output_path = f"downloaded_{user_id}_{document_id}.json"
    
    print(f"💾 JSON 파일을 로컬에 저장 중: {output_path}")
    
    try:
        result = download_persona_json(
            user_id=user_id,
            document_id=document_id,
        )
        
        if not result["exists"]:
            print(f"❌ JSON 파일을 찾을 수 없습니다: {document_id}")
            return False
        
        # 로컬 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        
        print(f"✅ JSON 파일 저장 완료: {output_path}")
        return True
        
    except Exception as exc:
        print(f"❌ JSON 파일 저장 실패: {exc}")
        return False


def main():
    """메인 함수"""
    print("🚀 Firebase Storage JSON 파일 확인 도구")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python check_json_files.py <user_id> [document_id]")
        print("  python check_json_files.py <user_id> list")
        print("  python check_json_files.py <user_id> save <document_id> [output_file]")
        print("\n예시:")
        print("  python check_json_files.py test_user_postman")
        print("  python check_json_files.py test_user_postman list")
        print("  python check_json_files.py test_user_postman save doc123")
        return
    
    user_id = sys.argv[1]
    
    if len(sys.argv) >= 3:
        command = sys.argv[2]
        
        if command == "list":
            # 파일 목록 조회
            check_user_files(user_id)
            
        elif command == "save":
            # JSON 파일 저장
            if len(sys.argv) >= 4:
                document_id = sys.argv[3]
                output_file = sys.argv[4] if len(sys.argv) >= 5 else None
                save_json_to_file(user_id, document_id, output_file)
            else:
                print("❌ document_id가 필요합니다.")
                
        else:
            # 특정 JSON 파일 확인
            document_id = command
            download_and_check_json(user_id, document_id)
    else:
        # 파일 목록 조회
        json_files = check_user_files(user_id)
        
        if json_files:
            print(f"\n📥 다운로드할 JSON 파일을 선택하세요:")
            for i, file_info in enumerate(json_files):
                print(f"  {i+1}. {file_info['name']}")
            
            try:
                choice = input("\n번호를 입력하세요 (Enter로 종료): ").strip()
                if choice:
                    idx = int(choice) - 1
                    if 0 <= idx < len(json_files):
                        # 파일명에서 document_id 추출
                        file_name = json_files[idx]['name']
                        document_id = Path(file_name).stem  # 확장자 제거
                        download_and_check_json(user_id, document_id)
            except (ValueError, IndexError):
                print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    main()
