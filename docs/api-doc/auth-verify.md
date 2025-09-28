# Firebase ID 토큰 검증 API

## 개요
- Firebase ID 토큰을 검증하고 주요 클레임 정보를 반환합니다.
- 인증된 사용자의 기본 정보를 확인할 때 사용합니다.

## 엔드포인트
- 메서드: `POST`
- 경로: `/api/auth/verify/`
- URL name: `api-auth-verify`

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
curl -X POST https://api.example.com/api/auth/verify/ \
  -H "Authorization: Bearer <firebase-id-token>" \
  -H "Content-Type: application/json"
```

#### TypeScript (Fetch API)
```typescript
interface FirebaseClaims {
  uid: string;
  email: string | null;
  email_verified: boolean | null;
  name: string | null;
  picture: string | null;
  firebase: {
    sign_in_provider: string | null;
    identities: Record<string, string[]> | null;
  } | null;
  provider: string | null;
}

const verifyToken = async (idToken: string): Promise<FirebaseClaims> => {
  try {
    const response = await fetch('/api/auth/verify/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data: FirebaseClaims = await response.json();
    console.log('사용자 정보:', data);
    return data;
  } catch (error) {
    console.error('토큰 검증 실패:', error);
    throw error;
  }
};

// 사용 예시
const idToken: string = await firebase.auth().currentUser.getIdToken();
const userInfo: FirebaseClaims = await verifyToken(idToken);
```

#### React Hook 예시 (TypeScript)
```typescript
import { useState, useCallback } from 'react';

interface FirebaseClaims {
  uid: string;
  email: string | null;
  email_verified: boolean | null;
  name: string | null;
  picture: string | null;
  firebase: {
    sign_in_provider: string | null;
    identities: Record<string, string[]> | null;
  } | null;
  provider: string | null;
}

interface UseAuthVerifyReturn {
  verifyToken: (idToken: string) => Promise<FirebaseClaims>;
  loading: boolean;
  error: string | null;
}

const useAuthVerify = (): UseAuthVerifyReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const verifyToken = useCallback(async (idToken: string): Promise<FirebaseClaims> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/verify/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '토큰 검증에 실패했습니다.');
      }
      
      const userInfo: FirebaseClaims = await response.json();
      return userInfo;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { verifyToken, loading, error };
};

// 컴포넌트에서 사용
const LoginComponent: React.FC = () => {
  const { verifyToken, loading, error } = useAuthVerify();
  
  const handleLogin = async (): Promise<void> => {
    try {
      const idToken: string = await firebase.auth().currentUser.getIdToken();
      const userInfo: FirebaseClaims = await verifyToken(idToken);
      console.log('인증된 사용자:', userInfo);
    } catch (err) {
      console.error('로그인 실패:', err);
    }
  };
  
  return (
    <div>
      <button onClick={handleLogin} disabled={loading}>
        {loading ? '검증 중...' : '로그인'}
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
  "email_verified": true,
  "name": "홍길동",
  "picture": "https://lh3.googleusercontent.com/a/example-photo-url",
  "firebase": {
    "sign_in_provider": "google.com",
    "identities": {
      "google.com": ["user@example.com"]
    }
  },
  "provider": "google.com"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| uid | string | Firebase 사용자 고유 식별자 |
| email | string \| null | 사용자 이메일 주소 (없으면 null) |
| email_verified | boolean \| null | 이메일 인증 여부 (없으면 null) |
| name | string \| null | 사용자 표시 이름 (없으면 null) |
| picture | string \| null | 프로필 사진 URL (없으면 null) |
| firebase | object \| null | Firebase 인증 정보 (없으면 null) |
| firebase.sign_in_provider | string \| null | 로그인 제공자 (예: "google.com") |
| firebase.identities | object \| null | 제공자별 식별자 정보 |
| provider | string \| null | 로그인 제공자 (firebase.sign_in_provider와 동일) |

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 400 Bad Request | 토큰 검증 실패 또는 기타 오류 | `{"detail": "토큰 검증에 실패했습니다."}` |
| 401 Unauthorized | 토큰이 제공되지 않음 | `{"detail": "인증 자격 증명이 제공되지 않았습니다."}` |
| 403 Forbidden | 토큰이 유효하지 않음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |

## 비고
- 이 엔드포인트는 토큰 검증만 수행하며, Firestore에 사용자 정보를 저장하지 않습니다.
- 사용자 정보를 Firestore에 저장하려면 `/api/auth/sync/` 엔드포인트를 사용하세요.
- 토큰의 유효성은 Firebase Admin SDK를 통해 검증됩니다.
- 응답의 모든 필드는 Firebase 클레임에서 직접 추출되며, 클레임에 없는 필드는 `null`로 반환됩니다.
- `picture`, `name`, `email` 등의 필드는 사용자가 프로필을 설정하지 않은 경우 `null`일 수 있습니다.
