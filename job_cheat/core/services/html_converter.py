"""
HTML 파일의 아스키 코드를 한글로 변환하고 JSON으로 변환하는 서비스 모듈
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)


class HtmlConversionError(RuntimeError):
    """HTML 변환 중 발생한 예외."""


def _decode_unicode_escapes(text: str) -> str:
    """문자열 내의 유니코드 이스케이프 시퀀스와 HTML 엔티티를 실제 문자로 변환한다."""
    try:
        # HTML 엔티티 먼저 처리
        decoded_text = text.replace('quot;', '"')
        decoded_text = decoded_text.replace('&quot;', '"')
        decoded_text = decoded_text.replace('&amp;', '&')
        decoded_text = decoded_text.replace('&lt;', '<')
        decoded_text = decoded_text.replace('&gt;', '>')
        
        # \uXXXX 형태의 유니코드 이스케이프 시퀀스를 찾아서 변환
        def replace_unicode(match):
            unicode_str = match.group(0)
            try:
                return unicode_str.encode().decode('unicode_escape')
            except UnicodeDecodeError:
                return unicode_str
        
        # \uXXXX 패턴을 찾아서 변환
        pattern = r'\\u[0-9a-fA-F]{4}'
        decoded_text = re.sub(pattern, replace_unicode, decoded_text)
        
        # 추가적인 이스케이프 처리
        decoded_text = decoded_text.replace('\\"', '"')
        decoded_text = decoded_text.replace("\\'", "'")
        decoded_text = decoded_text.replace('\\\\', '\\')
        
        return decoded_text
    except Exception as exc:
        logger.warning(f"유니코드 디코딩 중 오류 발생: {exc}")
        return text


def _extract_message_text(pre_node) -> str:
    """pre 노드에서 메시지 텍스트를 추출한다."""
    if pre_node is None:
        return ""
    
    content_div = None
    for div in pre_node.css('div'):
        classes = div.attributes.get('class', '')
        if 'author' not in classes:
            content_div = div
            break
    
    if content_div is None:
        return pre_node.text().strip()
    
    text = content_div.text()
    return text.replace('\r\n', '\n').replace('\r', '\n')


def _extract_json_data_from_script(html_str: str) -> List[Dict[str, Any]]:
    """HTML의 script 태그에서 JSON 데이터를 추출하고 디코딩한다."""
    try:
        # 정규식으로 직접 script 태그 내용 추출
        script_match = re.search(r'<script>(.*?)</script>', html_str, re.DOTALL)
        if not script_match:
            logger.warning("script 태그를 찾을 수 없음")
            return []
        
        script_content = script_match.group(1)
        logger.info(f"Script 태그 내용 길이: {len(script_content)} 문자")
        
        if 'jsonData' in script_content:
            # jsonData 변수에서 데이터 추출 - 중괄호 균형을 맞춰서 추출
            start_pos = script_content.find('var jsonData = [')
            if start_pos != -1:
                # '[' 부터 시작해서 균형잡힌 중괄호까지 찾기
                bracket_count = 0
                start_bracket = False
                json_start = -1
                
                for i, char in enumerate(script_content[start_pos:], start_pos):
                    if char == '[':
                        if not start_bracket:
                            start_bracket = True
                            json_start = i
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0 and start_bracket:
                            json_str = script_content[json_start:i+1]
                            break
                else:
                    logger.warning("JSON 배열의 끝을 찾을 수 없음")
                    return []
                
                logger.info(f"JSON 문자열 추출 성공: {len(json_str)} 문자")
                
                # 아스키 코드를 한글로 변환
                decoded_json_str = _decode_unicode_escapes(json_str)
                
                try:
                    json_data = json.loads(decoded_json_str)
                    logger.info(f"JSON 데이터 파싱 성공: {len(json_data)}개 항목")
                    return json_data
                except json.JSONDecodeError as exc:
                    logger.warning(f"JSON 파싱 실패: {exc}")
                    logger.warning(f"원본 JSON 문자열: {json_str[:200]}...")
                    logger.warning(f"디코딩된 JSON 문자열: {decoded_json_str[:200]}...")
                    return []
            else:
                logger.warning("jsonData 변수 패턴을 찾을 수 없음")
                logger.warning(f"Script 내용 일부: {script_content[:300]}...")
                return []
        else:
            logger.warning("jsonData 키워드를 찾을 수 없음")
            return []
            
    except Exception as exc:
        logger.error(f"Script 태그에서 JSON 데이터 추출 실패: {exc}")
        return []


def parse_html_to_conversations(html_str: str) -> List[Dict[str, Any]]:
    """HTML 문자열을 파싱하여 대화 목록을 반환한다."""
    try:
        # 먼저 script 태그에서 JSON 데이터를 추출해보기
        json_data = _extract_json_data_from_script(html_str)
        
        if json_data:
            # JSON 데이터가 있으면 이를 기반으로 대화 목록 생성
            conversations = []
            for conv_index, conv_data in enumerate(json_data):
                title = conv_data.get('title', f'Conversation {conv_index}')
                messages = []
                
                # mapping에서 메시지 추출
                mapping = conv_data.get('mapping', {})
                for msg_id, msg_data in mapping.items():
                    if msg_data and msg_data.get('message'):
                        message_content = msg_data['message']
                        author = message_content.get('author', {}).get('role', 'unknown')
                        text = message_content.get('content', {}).get('parts', [''])[0] if isinstance(message_content.get('content'), dict) else str(message_content.get('content', ''))
                        
                        if text:
                            messages.append({
                                "index": len(messages),
                                "author": author,
                                "text": text,
                            })
                
                conversations.append({
                    "conversation_index": conv_index,
                    "title": title,
                    "messages": messages,
                })
            
            return conversations
        
        # JSON 데이터가 없으면 기존 방식으로 파싱
        parser = HTMLParser(html_str)
        conversations = []
        
        for conv_index, conv in enumerate(parser.css('div.conversation')):
            title_node = conv.css_first('h4')
            title = title_node.text().strip() if title_node else f"Conversation {conv_index}"
            messages = []
            
            for msg_index, pre in enumerate(conv.css('pre.message')):
                author_node = pre.css_first('.author')
                author = author_node.text().strip() if author_node else ""
                text = _extract_message_text(pre)
                
                if author or text:
                    messages.append({
                        "index": msg_index,
                        "author": author,
                        "text": text,
                    })
            
            conversations.append({
                "conversation_index": conv_index,
                "title": title,
                "messages": messages,
            })
        
        return conversations
        
    except Exception as exc:
        logger.error(f"HTML 파싱 중 오류 발생: {exc}")
        raise HtmlConversionError(f"HTML 파싱 실패: {exc}") from exc


def convert_html_to_json(html_content: str) -> str:
    """HTML 내용을 JSON 문자열로 변환한다."""
    try:
        conversations = parse_html_to_conversations(html_content)
        return json.dumps(conversations, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error(f"HTML을 JSON으로 변환 중 오류 발생: {exc}")
        raise HtmlConversionError(f"JSON 변환 실패: {exc}") from exc


def convert_html_file_to_json(html_file_path: str | Path) -> str:
    """HTML 파일을 읽어서 JSON 문자열로 변환한다."""
    try:
        path = Path(html_file_path)
        html_content = path.read_text(encoding="utf-8")
        return convert_html_to_json(html_content)
    except Exception as exc:
        logger.error(f"HTML 파일 변환 중 오류 발생: {exc}")
        raise HtmlConversionError(f"파일 변환 실패: {exc}") from exc
