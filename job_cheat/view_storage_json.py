#!/usr/bin/env python3
"""
Firebase Storage에서 JSON 파일을 가져와서 보여주는 스크립트
"""

import os
import sys
import json
import django
from google.cloud import storage
from google.cloud.exceptions import NotFound

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_cheat.settings')
django.setup()

from django.conf import settings

def get_storage_client():
    """Firebase Storage 클라이언트를 가져옵니다."""
    try:
        # Django의 Firebase 설정 사용
        from firebase_admin import storage as firebase_storage
        
        bucket_name = getattr(settings, "FIREBASE_STORAGE_BUCKET", None)
        if bucket_name:
            bucket = firebase_storage.bucket(name=bucket_name)
            return bucket
        else:
            bucket = firebase_storage.bucket()
            return bucket
    except Exception as e:
        print(f"❌ Storage 클라이언트 생성 실패: {e}")
        return None

def download_and_show_json(storage_path):
    """Storage에서 JSON 파일을 다운로드하고 내용을 보여줍니다."""
    
    print(f"🔍 Storage 경로: {storage_path}")
    
    # Storage 클라이언트 가져오기
    bucket = get_storage_client()
    if not bucket:
        return False
    
    try:
        # Blob 객체 생성
        blob = bucket.blob(storage_path)
        
        # 파일 존재 여부 확인
        if not blob.exists():
            print(f"❌ 파일이 존재하지 않습니다: {storage_path}")
            return False
        
        print(f"📁 파일 크기: {blob.size:,} bytes" if blob.size else "📁 파일 크기: 알 수 없음")
        print(f"📅 생성 시간: {blob.time_created}" if blob.time_created else "📅 생성 시간: 알 수 없음")
        print(f"📅 수정 시간: {blob.updated}" if blob.updated else "📅 수정 시간: 알 수 없음")
        print(f"📄 Content-Type: {blob.content_type}" if blob.content_type else "📄 Content-Type: 알 수 없음")
        
        # 파일 다운로드
        print("\n📥 파일 다운로드 중...")
        json_content = blob.download_as_text(encoding='utf-8')
        
        print(f"📄 다운로드된 내용 크기: {len(json_content):,} 문자")
        
        # JSON 파싱
        try:
            json_data = json.loads(json_content)
            print("\n✅ JSON 파싱 성공!")
            
            # JSON 구조 분석
            print(f"\n📊 JSON 구조 분석:")
            if isinstance(json_data, dict):
                print(f"  📋 최상위 키들: {list(json_data.keys())}")
                
                # conversations 정보 확인
                if 'conversations' in json_data:
                    conversations = json_data['conversations']
                    print(f"  💬 대화 수: {len(conversations)}")
                    
                    if conversations:
                        first_conv = conversations[0]
                        print(f"  📝 첫 번째 대화 제목: {first_conv.get('title', 'N/A')}")
                        print(f"  📝 첫 번째 대화 메시지 수: {len(first_conv.get('messages', []))}")
                
                # 총 메시지 수 확인
                if 'total_messages' in json_data:
                    print(f"  📊 총 메시지 수: {json_data['total_messages']}")
                
                # 총 대화 수 확인
                if 'total_conversations' in json_data:
                    print(f"  📊 총 대화 수: {json_data['total_conversations']}")
            
            # 전체 JSON 내용 출력 (처음 1000자만)
            print(f"\n📄 JSON 내용 (처음 1000자):")
            print("=" * 50)
            print(json.dumps(json_data, indent=2, ensure_ascii=False)[:1000])
            if len(json.dumps(json_data, ensure_ascii=False)) > 1000:
                print("...")
            print("=" * 50)
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            print(f"📄 원본 내용 (처음 500자):")
            print("=" * 50)
            print(json_content[:500])
            print("=" * 50)
            return False
            
    except NotFound:
        print(f"❌ 파일을 찾을 수 없습니다: {storage_path}")
        return False
    except Exception as e:
        print(f"❌ 파일 다운로드 실패: {e}")
        return False

def show_storage_info():
    """Storage 버킷 정보를 보여줍니다."""
    bucket = get_storage_client()
    if not bucket:
        return
    
    try:
        print(f"🪣 Storage 버킷: {bucket.name}")
        print(f"📍 위치: {bucket.location}" if bucket.location else "📍 위치: 알 수 없음")
        print(f"📅 생성 시간: {bucket.time_created}" if bucket.time_created else "📅 생성 시간: 알 수 없음")
        
        # 모든 파일 목록 확인
        print(f"\n📁 전체 파일 목록:")
        blobs = bucket.list_blobs()
        
        file_count = 0
        user_files = {}
        
        for blob in blobs:
            file_count += 1
            if blob.name.startswith("users/"):
                parts = blob.name.split("/")
                if len(parts) >= 2:
                    user_id = parts[1]
                    if user_id not in user_files:
                        user_files[user_id] = []
                    user_files[user_id].append(blob.name)
        
        print(f"  📊 총 파일 수: {file_count}")
        print(f"  👥 사용자별 파일:")
        
        for user_id, files in user_files.items():
            print(f"    👤 {user_id}:")
            for file_path in files:
                print(f"      📄 {file_path}")
        
        if not user_files:
            print("    📭 사용자 파일이 없습니다.")
            
    except Exception as e:
        print(f"❌ Storage 정보 조회 실패: {e}")

def main():
    """메인 함수"""
    print("🚀 Firebase Storage JSON 파일 뷰어")
    print("=" * 50)
    
    # Storage 정보 표시
    show_storage_info()
    
    print("\n" + "=" * 50)
    
    # 명령행 인수에서 경로 가져오기
    if len(sys.argv) > 1:
        storage_path = sys.argv[1]
    else:
        # 기본 경로 (사용자가 제공한 경로)
        storage_path = "users/9EORlthAy1MhGlaGtsHhDvMbBrb2/json/9EORlthAy1MhGlaGtsHhDvMbBrb2.json"
    
    # JSON 파일 다운로드 및 표시
    success = download_and_show_json(storage_path)
    
    if success:
        print("\n✅ JSON 파일 조회 완료!")
    else:
        print("\n❌ JSON 파일 조회 실패!")
        
        # 다른 가능한 경로들 시도
        print("\n🔍 다른 가능한 경로들을 시도해보겠습니다...")
        
        possible_paths = [
            "users/9EORlthAy1MhGlaGtsHhDvMbBrb2/json/9EORlthAy1MhGlaGtsHhDvMbBrb2.json",
            "users/9EORlthAy1MhGlaGtsHhDvMbBrb2/html/9EORlthAy1MhGlaGtsHhDvMbBrb2.html",
        ]
        
        for path in possible_paths:
            print(f"\n🔍 시도 중: {path}")
            if download_and_show_json(path):
                break

if __name__ == "__main__":
    main()
