# Personas Health Check API

## 개요
- Personas 기능 앱의 상태를 확인하는 헬스 체크 엔드포인트입니다.
- 인증된 사용자의 UID와 함께 앱 상태를 반환합니다.

## 엔드포인트
- 메서드: `GET`
- 경로: `/api/personas/health/`
- URL name: `personas-health`

## 인증
- 헤더 `Authorization: Bearer <firebase-id-token>` 필수
- 토큰이 없거나 검증에 실패하면 401 또는 403으로 응답합니다.

## 요청
### 헤더
| 헤더 | 필수 | 설명 |
| --- | --- | --- |
| Authorization | ✅ | Firebase ID 토큰, 예시: `Bearer eyJhbGciOi...` |

### 요청 예시

#### cURL
```bash
curl -X GET https://api.example.com/api/personas/health/ \
  -H "Authorization: Bearer <firebase-id-token>"
```

#### TypeScript (Fetch API)
```typescript
interface HealthStatus {
  ok: boolean;
  feature: string;
  uid: string;
}

const checkPersonasHealth = async (idToken: string): Promise<HealthStatus> => {
  try {
    const response = await fetch('/api/personas/health/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const healthData: HealthStatus = await response.json();
    console.log('Personas 앱 상태:', healthData);
    return healthData;
  } catch (error) {
    console.error('헬스 체크 실패:', error);
    throw error;
  }
};

// 사용 예시
const idToken: string = await firebase.auth().currentUser.getIdToken();
const healthStatus: HealthStatus = await checkPersonasHealth(idToken);
```

#### React Hook 예시 (TypeScript)
```typescript
import { useState, useCallback } from 'react';

interface HealthStatus {
  ok: boolean;
  feature: string;
  uid: string;
}

interface UsePersonasHealthReturn {
  checkHealth: (idToken: string) => Promise<HealthStatus>;
  loading: boolean;
  error: string | null;
}

const usePersonasHealth = (): UsePersonasHealthReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const checkHealth = useCallback(async (idToken: string): Promise<HealthStatus> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/personas/health/', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '헬스 체크에 실패했습니다.');
      }
      
      const healthData: HealthStatus = await response.json();
      return healthData;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { checkHealth, loading, error };
};

// 컴포넌트에서 사용
const PersonasHealthComponent: React.FC = () => {
  const { checkHealth, loading, error } = usePersonasHealth();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  
  const handleCheckHealth = async (): Promise<void> => {
    try {
      const idToken: string = await firebase.auth().currentUser.getIdToken();
      const status: HealthStatus = await checkHealth(idToken);
      setHealthStatus(status);
      console.log('Personas 앱 상태:', status);
    } catch (err) {
      console.error('헬스 체크 실패:', err);
    }
  };
  
  return (
    <div>
      <button onClick={handleCheckHealth} disabled={loading}>
        {loading ? '확인 중...' : 'Personas 앱 상태 확인'}
      </button>
      {healthStatus && (
        <div>
          <p>상태: {healthStatus.ok ? '정상' : '오류'}</p>
          <p>기능: {healthStatus.feature}</p>
          <p>사용자 ID: {healthStatus.uid}</p>
        </div>
      )}
      {error && <p style={{color: 'red'}}>오류: {error}</p>}
    </div>
  );
};
```

## 응답
### 200 OK
```json
{
  "ok": true,
  "feature": "personas",
  "uid": "firebase_uid_123"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| ok | boolean | 앱 상태 (항상 true) |
| feature | string | 기능 앱 이름 (항상 "personas") |
| uid | string | 인증된 사용자의 Firebase UID |

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 401 Unauthorized | 토큰이 제공되지 않음 | `{"detail": "인증 자격 증명이 제공되지 않았습니다."}` |
| 403 Forbidden | 토큰이 유효하지 않음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |

## 비고
- 이 엔드포인트는 단순한 상태 확인용입니다.
- 실제 페르소나 관련 기능은 `/api/personas/inputs/` 엔드포인트를 사용하세요.
- 모든 기능 앱은 동일한 패턴의 헬스 체크 엔드포인트를 제공합니다.
