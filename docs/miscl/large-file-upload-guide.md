# 200MB 대용량 HTML 파일 업로드 가이드

## 🚨 문제 상황
대용량 HTML 파일을 `/api/personas/inputs/` 엔드포인트로 업로드할 때 서버에 도착하지 않고 중간에 끊기는 문제가 발생합니다.

## 🔍 원인 분석
1. **Django 개발 서버 한계**: 단일 스레드로 동작하여 대용량 파일 처리에 최적화되지 않음
2. **타임아웃 설정 부족**: 기본적으로 타임아웃이 설정되지 않아 무한 대기 상태 발생
3. **메모리 제한**: 기본 10MB 제한으로 인한 메모리 부족
4. **연결 끊김 처리**: 클라이언트 연결이 끊어져도 서버가 감지하지 못함

## ✅ 해결 방안

### 1. 서버 설정 개선 (완료)
- 파일 업로드 메모리 제한을 10MB → **200MB**로 증가
- 요청 타임아웃을 5분 → **30분**으로 연장
- 임시 파일 업로드 핸들러 우선 사용
- 세션 타임아웃 설정 추가 (2시간)

### 2. ASGI 서버 실행 (권장 - 200MB 지원)
```bash
# 기존 WSGI 방식 (50MB 제한)
uv run python manage.py runserver 0.0.0.0:8000

# 🚀 ASGI 서버 (200MB 지원, 비동기 처리) - 권장
uv run python runserver_asgi.py 0.0.0.0:8000
```

### 3. 엔드포인트
- **메인 엔드포인트**: `/api/personas/inputs/` (200MB 지원, Firebase 인증 필요)

### 3. 클라이언트 측 업로드 최적화

#### JavaScript/Fetch API 사용 시 (200MB 지원):
```javascript
// 대용량 파일 업로드 (200MB 지원)
const uploadLargeFile = async (file, authToken) => {
    const formData = new FormData();
    formData.append('html_file', file);
    formData.append('title', 'My Persona');
    formData.append('description', 'Generated from ChatGPT export');
    
    try {
        const response = await fetch('/api/personas/inputs/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'ngrok-skip-browser-warning': 'true'
            },
            body: formData,
            // 타임아웃 설정 (30분)
            signal: AbortSignal.timeout(1800000)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        if (error.name === 'TimeoutError') {
            throw new Error('파일 업로드 시간이 초과되었습니다. 파일 크기를 확인해주세요.');
        }
        throw error;
    }
};
```

#### cURL 사용 시:
```bash
# 대용량 파일 업로드 (200MB 지원, 타임아웃 30분)
curl -X POST \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "ngrok-skip-browser-warning: true" \
  -F "html_file=@large_file.html" \
  -F "title=My Persona" \
  -F "description=Generated from ChatGPT export" \
  --max-time 1800 \
  --connect-timeout 30 \
  http://localhost:8000/api/personas/inputs/
```

### 4. 파일 크기 제한 확인
- **최대 파일 크기**: 200MB
- **처리 시간**: 파일 크기에 따라 1-30분 소요 가능
- **메모리 사용량**: 서버 메모리 사용량 모니터링 필요

### 5. 업로드 진행 상황 모니터링
```javascript
// 업로드 진행 상황 표시
const uploadWithProgress = async (file, authToken, onProgress) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
        }
    });
    
    const formData = new FormData();
    formData.append('html_file', file);
    formData.append('title', 'My Persona');
    formData.append('description', 'Generated from ChatGPT export');
    
    return new Promise((resolve, reject) => {
        xhr.onload = () => {
            if (xhr.status === 201) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(`HTTP error! status: ${xhr.status}`));
            }
        };
        
        xhr.onerror = () => reject(new Error('Network error'));
        xhr.ontimeout = () => reject(new Error('Upload timeout'));
        
        xhr.open('POST', '/api/personas/inputs/');
        xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);
        xhr.setRequestHeader('ngrok-skip-browser-warning', 'true');
        xhr.timeout = 1800000; // 30분
        
        xhr.send(formData);
    });
};
```

## 🔧 추가 권장사항

### 1. 파일 압축
- HTML 파일을 ZIP으로 압축하여 업로드 크기 줄이기
- 서버에서 압축 해제 후 처리

### 2. 청크 업로드
- 대용량 파일을 작은 조각으로 나누어 순차 업로드
- 서버에서 조각들을 합쳐서 처리

### 3. 백그라운드 처리
- 파일 업로드 후 즉시 응답 반환
- 실제 처리는 백그라운드에서 진행
- 처리 완료 시 웹훅 또는 폴링으로 알림

## 📊 모니터링 및 디버깅

### 서버 로그 확인:
```bash
# 실시간 로그 모니터링
tail -f django.log

# 특정 사용자 요청 추적
grep "user_id=USER_ID" django.log
```

### 클라이언트 측 오류 처리:
```javascript
// 상세한 오류 정보 수집
const handleUploadError = (error) => {
    console.error('Upload failed:', {
        error: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        fileSize: file.size,
        fileName: file.name
    });
};
```

## 🚀 성능 최적화 팁

1. **파일 크기 최적화**: 불필요한 HTML 태그 제거
2. **네트워크 최적화**: 안정적인 네트워크 환경에서 업로드
3. **서버 리소스**: 충분한 메모리와 CPU 리소스 확보
4. **동시 업로드 제한**: 한 번에 하나의 대용량 파일만 업로드

이 가이드를 따라하면 대용량 HTML 파일 업로드 문제를 해결할 수 있습니다.
