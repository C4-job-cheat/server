# Job Search Health Check API

## 개요
- Job Search 기능 앱의 상태를 확인하는 헬스 체크 엔드포인트입니다.
- 인증된 사용자의 UID와 함께 앱 상태를 반환합니다.

## 엔드포인트
- 메서드: `GET`
- 경로: `/api/job-search/health/`
- URL name: `job-search-health`

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
curl -X GET https://api.example.com/api/job-search/health/ \
  -H "Authorization: Bearer <firebase-id-token>"
```

#### TypeScript (Fetch API)
```typescript
interface HealthStatus {
  ok: boolean;
  feature: string;
  uid: string;
}

const checkJobSearchHealth = async (idToken: string): Promise<HealthStatus> => {
  try {
    const response = await fetch('/api/job-search/health/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const healthData: HealthStatus = await response.json();
    console.log('Job Search 앱 상태:', healthData);
    return healthData;
  } catch (error) {
    console.error('헬스 체크 실패:', error);
    throw error;
  }
};

// 사용 예시
const idToken: string = await firebase.auth().currentUser.getIdToken();
const healthStatus: HealthStatus = await checkJobSearchHealth(idToken);
```

#### React Hook 예시 (TypeScript)
```typescript
import { useState, useCallback } from 'react';

interface HealthStatus {
  ok: boolean;
  feature: string;
  uid: string;
}

interface UseJobSearchHealthReturn {
  checkHealth: (idToken: string) => Promise<HealthStatus>;
  loading: boolean;
  error: string | null;
}

const useJobSearchHealth = (): UseJobSearchHealthReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const checkHealth = useCallback(async (idToken: string): Promise<HealthStatus> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/job-search/health/', {
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
const JobSearchHealthComponent: React.FC = () => {
  const { checkHealth, loading, error } = useJobSearchHealth();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  
  const handleCheckHealth = async (): Promise<void> => {
    try {
      const idToken: string = await firebase.auth().currentUser.getIdToken();
      const status: HealthStatus = await checkHealth(idToken);
      setHealthStatus(status);
      console.log('Job Search 앱 상태:', status);
    } catch (err) {
      console.error('헬스 체크 실패:', err);
    }
  };
  
  return (
    <div>
      <button onClick={handleCheckHealth} disabled={loading}>
        {loading ? '확인 중...' : 'Job Search 앱 상태 확인'}
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
  "feature": "job_search",
  "uid": "firebase_uid_123"
}
```

### 응답 필드 설명
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| ok | boolean | 앱 상태 (항상 true) |
| feature | string | 기능 앱 이름 (항상 "job_search") |
| uid | string | 인증된 사용자의 Firebase UID |

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 401 Unauthorized | 토큰이 제공되지 않음 | `{"detail": "인증 자격 증명이 제공되지 않았습니다."}` |
| 403 Forbidden | 토큰이 유효하지 않음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |

## 비고
- 이 엔드포인트는 단순한 상태 확인용입니다.
- 실제 채용 공고 검색 관련 기능은 아직 구현되지 않았습니다.
- 모든 기능 앱은 동일한 패턴의 헬스 체크 엔드포인트를 제공합니다.
