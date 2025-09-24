#!/usr/bin/env python
"""
HTML 변환기 테스트 스크립트
"""

import os
import sys
import django
from pathlib import Path

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_cheat.settings')
django.setup()

from core.services.html_converter import convert_html_to_json


def test_html_conversion():
    """chat.html 파일을 사용하여 HTML 변환 테스트"""
    
    # chat.html 파일 경로 (프로젝트 루트에 있음)
    html_file_path = Path(__file__).parent.parent / "chat.html"
    
    if not html_file_path.exists():
        print(f"❌ HTML 파일을 찾을 수 없습니다: {html_file_path}")
        return False
    
    try:
        # HTML 파일 읽기
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ HTML 파일 읽기 완료: {len(html_content)} 문자")
        
        # script 태그 내용 확인
        import re
        script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)
        if script_match:
            script_content = script_match.group(1)
            print(f"✅ Script 태그 내용 길이: {len(script_content)} 문자")
            print(f"✅ Script 내용 일부: {script_content[:200]}...")
        else:
            print("❌ Script 태그를 찾을 수 없음")
        
        # HTML을 JSON으로 변환
        json_content = convert_html_to_json(html_content)
        
        print(f"✅ JSON 변환 완료: {len(json_content)} 문자")
        print(f"✅ JSON 내용: {json_content}")
        
        # JSON 파싱 테스트
        import json
        conversations = json.loads(json_content)
        
        print(f"✅ 대화 수: {len(conversations)}")
        
        # 첫 번째 대화 정보 출력
        if conversations:
            first_conv = conversations[0]
            print(f"✅ 첫 번째 대화 제목: {first_conv.get('title', 'N/A')}")
            print(f"✅ 첫 번째 대화 메시지 수: {len(first_conv.get('messages', []))}")
            
            # 첫 번째 메시지 내용 일부 출력
            if first_conv.get('messages'):
                first_msg = first_conv['messages'][0]
                text_preview = first_msg.get('text', '')[:100] + "..." if len(first_msg.get('text', '')) > 100 else first_msg.get('text', '')
                print(f"✅ 첫 번째 메시지 미리보기: {text_preview}")
        
        # 결과를 파일로 저장
        output_file = Path(__file__).parent / "test_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        print(f"✅ 결과 파일 저장: {output_file}")
        
        return True
        
    except Exception as exc:
        print(f"❌ 변환 중 오류 발생: {exc}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 HTML 변환기 테스트 시작")
    print("=" * 50)
    
    success = test_html_conversion()
    
    print("=" * 50)
    if success:
        print("🎉 테스트 성공!")
    else:
        print("💥 테스트 실패!")
        sys.exit(1)
