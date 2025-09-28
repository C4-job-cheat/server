# Firebase 사용자 동기화 API

## 개요
- Firebase ID 토큰의 클레임을 이용해 Firestore `users/{uid}` 문서를 생성하거나 갱신합니다.
- 최초 호출 시 새 사용자로 간주하여 문서를 생성하고, 이후 호출에서는 로그인 정보만 업데이트합니다.

## 엔드포인트
- 메서드: `POST`
- 경로: `/api/auth/sync/`
- URL name: `api-auth-sync`

## 인증
- 헤더 `Authorization: Bearer <firebase-id-token>` 필수
- 토큰이 없거나 검증에 실패하면 401 또는 403으로 응답합니다.

## 요청
### 헤더
| 헤더 | 필수 | 설명 |
| --- | --- | --- |
| Authorization | ✅ | Firebase ID 토큰, 예시: `Bearer eyJhbGciOi...` |
| Content-Type | ✅ | `application/json`

### 요청 본문
요청 본문은 필요하지 않습니다. 토큰에서 정보를 추출합니다.

### 요청 예시

#### cURL
```bash
curl -X POST https://api.example.com/api/auth/sync/ \
  -H "Authorization: Bearer <firebase-id-token>" \
  -H "Content-Type: application/json"
```

#### TypeScript (Fetch API)
```typescript
interface SyncedUserData {
  uid: string;
  email: string | null;
  display_name: string | null;
  email_verified: boolean | null;
  last_login_at: string;
  created_at: string;
  updated_at: string;
}

const syncUser = async (idToken: string): Promise<SyncedUserData> => {
  try {
    const response = await fetch('/api/auth/sync/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const userData: SyncedUserData = await response.json();
    console.log('동기화된 사용자 정보:', userData);
    return userData;
  } catch (error) {
    console.error('사용자 동기화 실패:', error);
    throw error;
  }
};

// 사용 예시
const idToken: string = await firebase.auth().currentUser.getIdToken();
const syncedUser: SyncedUserData = await syncUser(idToken);
```

#### React Hook 예시 (TypeScript)
```typescript
import { useState, useCallback } from 'react';

interface SyncedUserData {
  uid: string;
  email: string | null;
  display_name: string | null;
  email_verified: boolean | null;
  last_login_at: string;
  created_at: string;
  updated_at: string;
}

interface UseAuthSyncReturn {
  syncUser: (idToken: string) => Promise<SyncedUserData>;
  loading: boolean;
  error: string | null;
}

const useAuthSync = (): UseAuthSyncReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const syncUser = useCallback(async (idToken: string): Promise<SyncedUserData> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/sync/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '사용자 동기화에 실패했습니다.');
      }
      
      const userData: SyncedUserData = await response.json();
      return userData;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { syncUser, loading, error };
};

// 컴포넌트에서 사용
const AuthSyncComponent: React.FC = () => {
  const { syncUser, loading, error } = useAuthSync();
  
  const handleSync = async (): Promise<void> => {
    try {
      const idToken: string = await firebase.auth().currentUser.getIdToken();
      const userData: SyncedUserData = await syncUser(idToken);
      console.log('동기화 완료:', userData);
      // 사용자 정보를 상태나 컨텍스트에 저장
    } catch (err) {
      console.error('동기화 실패:', err);
    }
  };
  
  return (
    <div>
      <button onClick={handleSync} disabled={loading}>
        {loading ? '동기화 중...' : '사용자 동기화'}
      </button>
      {error && <p style={{color: 'red'}}>오류: {error}</p>}
    </div>
  );
};
```

## 응답
### 200 OK
```json
{
  "uid": "firebase_uid_123",
  "email": "user@example.com",
  "display_name": "홍길동",
  "email_verified": true,
  "last_login_at": "2025-01-27T10:30:45.123456Z",
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| uid | string | Firebase 사용자 고유 식별자 |
| email | string | 사용자 이메일 주소 |
| display_name | string \| null | 사용자 표시 이름 (없으면 null) |
| email_verified | boolean | 이메일 인증 여부 |
| last_login_at | timestamp | 마지막 로그인 시각 |
| created_at | timestamp | 문서 생성 시각 (최초 생성 시에만 설정) |
| updated_at | timestamp | 최근 동기화 시각 |

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 400 Bad Request | 토큰 검증 실패 또는 기타 오류 | `{"detail": "토큰 검증에 실패했습니다."}` |
| 401 Unauthorized | 토큰이 제공되지 않음 | `{"detail": "인증 자격 증명이 제공되지 않았습니다."}` |
| 403 Forbidden | 토큰이 유효하지 않음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |
| 503 Service Unavailable | Firestore 클라이언트 미초기화 | `{"detail": "Firestore 클라이언트를 찾을 수 없습니다. FIREBASE_DB 설정을 확인하세요."}` |

## Firestore 저장 구조
```
users/{uid}
├── email: string
├── display_name: string | null
├── email_verified: boolean
├── last_login_at: timestamp
├── created_at: timestamp
└── updated_at: timestamp
```

## 비고
- **새 사용자**: 문서가 존재하지 않으면 새로 생성하고 `created_at`을 설정합니다.
- **기존 사용자**: 문서가 존재하면 `last_login_at`과 `updated_at`만 업데이트하고 `created_at`은 유지합니다.
- Firebase 클레임의 `name` 필드가 `display_name`으로 변환되어 저장됩니다.
- `photo_url`과 `provider_id`는 현재 구현에서 저장되지 않습니다.
- 모든 타임스탬프는 서버 시간(`timezone.now()`)으로 저장됩니다.
