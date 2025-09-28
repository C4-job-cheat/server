# 📚 chatgpt_to_json.py 라이브러리 사용법

ChatGPT 대화 기록 HTML 파일을 한국어 JSON으로 변환하는 라이브러리입니다.

## 🚀 설치 및 기본 사용법

### 1. 기본 사용법 (진행상황 출력)

```python
from chatgpt_to_json import ChatGPTToJSONConverter

# 변환기 생성
converter = ChatGPTToJSONConverter(verbose=True)

# HTML 파일을 JSON으로 변환
result = converter.convert_html_to_json(
    html_path="chat.html",
    json_path="output.json"  # 선택사항
)

print(f"총 대화 수: {result['total_conversations']}")
print(f"총 메시지 수: {result['total_messages']}")
```

### 2. 조용한 모드 (진행상황 출력 없음)

```python
from chatgpt_to_json import ChatGPTToJSONConverter

# 조용한 모드로 변환기 생성
converter = ChatGPTToJSONConverter(verbose=False)

# 자동 파일명으로 변환 (chat.html → chat.json)
result = converter.convert_html_to_json("chat.html")

# 사용자 지정 파일명으로 변환
result = converter.convert_html_to_json(
    html_path="chat.html",
    json_path="my_output.json"
)

# 변환된 데이터 활용
conversations = result['conversations']
for conv in conversations:
    print(f"제목: {conv['title']}")
    print(f"메시지 수: {len(conv['messages'])}")
```

## 📊 반환 데이터 구조

```python
{
    "conversations": [
        {
            "title": "대화 제목",
            "conversation_id": "대화 ID",
            "messages": [
                {
                    "role": "user",  # 또는 "assistant", "system"
                    "content": "메시지 내용"
                }
            ]
        }
    ],
    "total_conversations": 157,
    "total_messages": 1068
}
```

## 🔧 고급 사용법

### 데이터 분석 예제

```python
from chatgpt_to_json import ChatGPTToJSONConverter

converter = ChatGPTToJSONConverter(verbose=False)
result = converter.convert_html_to_json("chat.html")

# 실제 대화만 필터링 (링크/문서 제외)
real_conversations = [
    conv for conv in result['conversations'] 
    if conv.get('messages') and len(conv['messages']) > 0
]

print(f"실제 대화 수: {len(real_conversations)}")

# 역할별 메시지 통계
role_counts = {}
for conv in real_conversations:
    for msg in conv['messages']:
        role = msg['role']
        role_counts[role] = role_counts.get(role, 0) + 1

for role, count in role_counts.items():
    print(f"{role}: {count}개")
```

### 에러 처리

```python
from chatgpt_to_json import ChatGPTToJSONConverter

converter = ChatGPTToJSONConverter(verbose=False)

try:
    result = converter.convert_html_to_json("chat.html")
except FileNotFoundError:
    print("파일을 찾을 수 없습니다!")
except ValueError as e:
    print(f"파일 형식 오류: {e}")
```

## 🎯 주요 기능

- ✅ **대용량 파일 지원**: 100MB+ 파일도 안정적 처리
- ✅ **완벽한 한국어 변환**: ASCII 유니코드 → 한국어
- ✅ **메모리 효율적**: 스트리밍 방식으로 처리
- ✅ **에러 복구**: UTF-8 인코딩 문제 자동 해결
- ✅ **유연한 사용**: CLI와 라이브러리 모드 모두 지원

## 📝 매개변수

### `ChatGPTToJSONConverter(verbose=True)`
- `verbose` (bool): 진행상황 출력 여부 (기본값: True)

### `convert_html_to_json(html_path, json_path=None)`
- `html_path` (str): 입력 HTML 파일 경로 (필수)
- `json_path` (str, optional): 출력 JSON 파일 경로 (None이면 자동 생성)

## 🚀 CLI 사용법 (기존 방식)

```bash
# 기본 사용법
python chatgpt_to_json.py -i chat.html -o output.json

# 대용량 파일 처리
python chatgpt_to_json.py -i large_chat.html -o large_output.json
```

## 💡 사용 팁

1. **대용량 파일**: `verbose=False`로 설정하면 더 빠르게 처리됩니다
2. **자동 파일명**: `json_path=None`으로 설정하면 HTML 파일명에서 자동으로 JSON 파일명 생성
3. **에러 처리**: 항상 try-except로 감싸서 사용하세요
4. **데이터 검증**: 변환 후 `total_conversations`와 `total_messages`를 확인하세요
5. **조용한 모드**: `verbose=False`로 설정해도 파일은 자동으로 저장됩니다

## 🔍 문제 해결

### 자주 발생하는 오류

1. **FileNotFoundError**: 입력 파일 경로를 확인하세요
2. **ValueError: jsonData를 찾을 수 없습니다**: ChatGPT에서 내보낸 HTML 파일인지 확인하세요
3. **UnicodeEncodeError**: 자동으로 해결되지만, 특수 문자가 포함된 경우 발생할 수 있습니다

### 성능 최적화

- 대용량 파일: `verbose=False` 사용
- 자동 파일명: `json_path=None`으로 설정하면 HTML 파일명에서 자동 생성
- 배치 처리: 여러 파일을 순차적으로 처리할 때는 한 번만 변환기 생성
