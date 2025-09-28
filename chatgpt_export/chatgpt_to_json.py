#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

class ChatGPTToJSONConverter:
    def __init__(self, verbose: bool = True):
        """
        ChatGPT 대화 기록 변환기 초기화
        
        Args:
            verbose (bool): 진행상황 출력 여부 (기본값: True)
        """
        self.verbose = verbose
        
    def convert_html_to_json(self, html_path: str, json_path: str = None) -> dict:
        """
        HTML 파일을 JSON으로 변환합니다 (라이브러리 모드)
        
        Args:
            html_path (str): 입력 HTML 파일 경로
            json_path (str, optional): 출력 JSON 파일 경로. None이면 자동으로 생성
            
        Returns:
            dict: 변환된 대화 데이터
        """
        input_path = Path(html_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {html_path}")
        
        # 전체 파일을 한 번에 읽기
        if self.verbose:
            print("📖 파일 읽기 중...")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if self.verbose:
            print(f"📊 파일 크기: {len(content):,} 문자")
        
        # jsonData 시작점 찾기
        json_start = content.find('jsonData = [')
        if json_start == -1:
            raise ValueError("jsonData를 찾을 수 없습니다!")
        
        if self.verbose:
            print(f"📍 jsonData 시작 위치: {json_start}")
        
        # jsonData 끝점 찾기
        json_end = self.find_json_end(content, json_start)
        if json_end == -1:
            raise ValueError("jsonData 끝을 찾을 수 없습니다!")
        
        if self.verbose:
            print(f"📍 jsonData 끝 위치: {json_end}")
        
        # jsonData 부분만 추출
        json_data = content[json_start:json_end]
        if self.verbose:
            print(f"📊 jsonData 길이: {len(json_data):,} 문자")
        
        # 대화 추출
        if self.verbose:
            print("🔍 대화 추출 중...")
        conversations = self.extract_all_conversations(json_data)
        
        # 결과 구성
        result = {
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_messages": sum(len(conv.get("messages", [])) for conv in conversations)
        }
        
        if self.verbose:
            print(f"\n📊 최종 결과:")
            print(f"  💬 총 대화 수: {result['total_conversations']}")
            print(f"  📝 총 메시지 수: {result['total_messages']}")
        
        # JSON 파일로 저장 (자동 생성 또는 지정된 경로)
        if json_path is None:
            # 자동으로 파일명 생성 (HTML 파일명에서 확장자만 변경)
            input_path = Path(html_path)
            json_path = input_path.with_suffix('.json')
        
        self.save_result(result, Path(json_path))
        
        return result
        
    def process_file(self, input_path: Path, output_path: Path):
        """파일을 처리합니다 - 메시지 내용 잘림 문제 해결"""
        print(f"📁 입력 파일: {input_path}")
        print(f"📁 출력 파일: {output_path}")
        
        # 전체 파일을 한 번에 읽기
        print("📖 파일 읽기 중...")
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📊 파일 크기: {len(content):,} 문자")
        
        # jsonData 시작점 찾기
        json_start = content.find('jsonData = [')
        if json_start == -1:
            print("❌ jsonData를 찾을 수 없습니다!")
            return
        
        print(f"📍 jsonData 시작 위치: {json_start}")
        
        # jsonData 끝점 찾기
        json_end = self.find_json_end(content, json_start)
        if json_end == -1:
            print("❌ jsonData 끝을 찾을 수 없습니다!")
            return
        
        print(f"📍 jsonData 끝 위치: {json_end}")
        
        # jsonData 부분만 추출
        json_data = content[json_start:json_end]
        print(f"📊 jsonData 길이: {len(json_data):,} 문자")
        
        # 대화 추출
        print("🔍 대화 추출 중...")
        conversations = self.extract_all_conversations(json_data)
        
        # 결과 저장
        result = {
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_messages": sum(len(conv.get("messages", [])) for conv in conversations)
        }
        
        print(f"\n📊 최종 결과:")
        print(f"  💬 총 대화 수: {result['total_conversations']}")
        print(f"  📝 총 메시지 수: {result['total_messages']}")
        
        self.save_result(result, output_path)
        
    def find_json_end(self, content: str, start_pos: int) -> int:
        """jsonData의 끝 위치를 찾습니다"""
        bracket_count = 0
        pos = start_pos
        
        while pos < len(content):
            if content[pos] == '[':
                bracket_count += 1
            elif content[pos] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    return pos + 1
            pos += 1
        
        return -1
    
    def extract_all_conversations(self, json_data: str) -> List[Dict[str, Any]]:
        """모든 대화를 추출합니다"""
        conversations = []
        
        # 대화 시작점들 찾기
        conversation_starts = []
        for match in re.finditer(r'\{"title":\s*"[^"]*"', json_data):
            conversation_starts.append(match.start())
        
        if self.verbose:
            print(f"  🔍 {len(conversation_starts)}개 대화 시작점 발견")
        
        for i, start_pos in enumerate(conversation_starts):
            if self.verbose and i % 50 == 0:  # 50개마다 진행상황 출력
                print(f"  📝 대화 {i+1}/{len(conversation_starts)} 처리 중...")
            
            # 대화 끝 찾기
            end_pos = self.find_conversation_end(json_data, start_pos)
            if end_pos == -1:
                continue
            
            conversation_text = json_data[start_pos:end_pos]
            
            # 대화 파싱
            conversation = self.parse_conversation_complete(conversation_text, i+1)
            if conversation:
                conversations.append(conversation)
        
        return conversations
    
    def find_conversation_end(self, text: str, start_pos: int) -> int:
        """대화의 끝 위치를 찾습니다"""
        # 다음 대화 시작점 찾기
        next_conversation = text.find('{"title":', start_pos + 1)
        if next_conversation != -1:
            return next_conversation
        
        # 텍스트 끝까지
        return len(text)
    
    def parse_conversation_complete(self, text: str, conv_num: int) -> Optional[Dict[str, Any]]:
        """완전한 대화 파싱 - 메시지 내용 잘림 문제 해결"""
        try:
            # 제목 추출 및 유니코드 디코딩
            title_match = re.search(r'"title":\s*"([^"]*)"', text)
            title = title_match.group(1) if title_match else f"대화 {conv_num}"
            # title도 유니코드 디코딩 적용
            title = self.decode_unicode_strings(title)
            
            # 대화 ID 추출
            conv_id_match = re.search(r'"conversation_id":\s*"([^"]*)"', text)
            conversation_id = conv_id_match.group(1) if conv_id_match else ""
            
            # current_node 추출
            current_node_match = re.search(r'"current_node":\s*"([^"]*)"', text)
            current_node = current_node_match.group(1) if current_node_match else ""
            
            # 메시지 ID들 찾기
            message_ids = re.findall(r'"([a-f0-9-]{36})":\s*\{', text)
            
            messages = []
            for msg_id in message_ids:
                # 메시지 내용 추출 (완전한 방법)
                msg_content = self.extract_complete_message_content(text, msg_id)
                if msg_content:
                    # role 추출
                    role_match = re.search(r'"role":\s*"([^"]*)"', msg_content)
                    role = role_match.group(1) if role_match else "unknown"
                    
                    # parts 추출
                    parts = self.extract_parts_complete(msg_content)
                    
                    if parts and any(part.strip() for part in parts):
                        messages.append({
                            "role": role,
                            "content": parts[0] if parts else ""
                        })
            
            return {
                "title": title,
                "conversation_id": conversation_id,
                "messages": messages
            }
            
        except Exception as e:
            if self.verbose:
                print(f"  ❌ 대화 {conv_num} 파싱 실패: {e}")
            return None
    
    def extract_complete_message_content(self, text: str, msg_id: str) -> str:
        """완전한 메시지 내용을 추출합니다 - 잘림 문제 해결"""
        msg_start = text.find(f'"{msg_id}":')
        if msg_start == -1:
            return ""
        
        brace_start = text.find('{', msg_start)
        if brace_start == -1:
            return ""
        
        # 중괄호 균형을 맞춰서 완전한 메시지 내용 추출
        brace_count = 0
        pos = brace_start
        
        while pos < len(text):
            if text[pos] == '{':
                brace_count += 1
            elif text[pos] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[brace_start+1:pos]
            pos += 1
        
        return ""
    
    def extract_parts_complete(self, msg_content: str) -> List[str]:
        """완전한 parts를 추출합니다"""
        parts = []
        
        # parts 패턴 찾기
        parts_pattern = r'"parts":\s*\[(.*?)\]'
        parts_match = re.search(parts_pattern, msg_content, re.DOTALL)
        
        if parts_match:
            parts_text = parts_match.group(1)
            
            # 각 part 추출 (안전한 방법)
            pos = 0
            while pos < len(parts_text):
                # 다음 큰따옴표 찾기
                quote_start = parts_text.find('"', pos)
                if quote_start == -1:
                    break
                
                # 문자열 끝 찾기 (이스케이프 처리)
                quote_end = quote_start + 1
                while quote_end < len(parts_text):
                    if parts_text[quote_end] == '"' and parts_text[quote_end-1] != '\\':
                        break
                    quote_end += 1
                
                if quote_end < len(parts_text):
                    part = parts_text[quote_start+1:quote_end]
                    # 유니코드 디코딩
                    decoded_part = self.decode_unicode_strings(part)
                    if decoded_part and decoded_part.strip():
                        parts.append(decoded_part)
                    
                    pos = quote_end + 1
                else:
                    break
        
        return parts
    
    def decode_unicode_strings(self, obj: Any) -> Any:
        """유니코드 문자열을 안전하게 디코딩합니다"""
        if isinstance(obj, str):
            if '\\u' not in obj:
                return obj
            
            try:
                decoded = obj.encode('latin-1').decode('unicode_escape')
                
                # 서로게이트 쌍 문제 해결
                if '\ud800' <= decoded <= '\udfff':
                    return obj
                
                return decoded
            except (UnicodeDecodeError, UnicodeEncodeError):
                return obj
        elif isinstance(obj, dict):
            return {self.decode_unicode_strings(k): self.decode_unicode_strings(v) 
                   for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.decode_unicode_strings(item) for item in obj]
        else:
            return obj
    
    def save_result(self, result: Dict[str, Any], output_path: Path):
        """결과를 저장합니다"""
        if self.verbose:
            print(f"\n💾 결과 저장 중...")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            if self.verbose:
                print(f"✅ 저장 완료: {output_path}")
        except UnicodeEncodeError as e:
            if self.verbose:
                print(f"⚠️ UTF-8 인코딩 오류: {e}")
                print("UTF-8로 인코딩할 수 없는 문자를 제거하고 다시 시도합니다...")
            
            # UTF-8로 인코딩할 수 없는 문자 제거
            def clean_unicode(obj):
                if isinstance(obj, str):
                    return obj.encode('utf-8', errors='ignore').decode('utf-8')
                elif isinstance(obj, dict):
                    return {clean_unicode(k): clean_unicode(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_unicode(item) for item in obj]
                else:
                    return obj
            
            cleaned_result = clean_unicode(result)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_result, f, ensure_ascii=False, indent=2)
            if self.verbose:
                print(f"✅ 정리 후 저장 완료: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='ChatGPT 대화 기록을 한국어 JSON으로 변환합니다')
    parser.add_argument('-i', '--input', required=True, help='입력 HTML 파일 경로')
    parser.add_argument('-o', '--output', required=True, help='출력 JSON 파일 경로')
    
    args = parser.parse_args()
    
    converter = ChatGPTToJSONConverter()
    converter.process_file(Path(args.input), Path(args.output))

if __name__ == "__main__":
    main()
