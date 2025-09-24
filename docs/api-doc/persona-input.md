# Persona HTML 입력 업로드 API

## 개요
- 사용자 페르소나 기본 정보와 HTML 파일을 업로드해 Firestore에 메타데이터를 저장하고 Firebase Storage에 파일을 기록합니다.
- Firestore 문서는 `users/{user_id}/personas/{persona_id}` 경로에 생성되며, HTML 파일은 Firebase Storage에 업로드됩니다.

## 엔드포인트
- 메서드: `POST`
- 경로: `/api/personas/inputs/`
- URL name: `personas-input-create`

## 인증
- 헤더 `Authorization: Bearer <firebase-id-token>` 필수
- 토큰이 없거나 검증에 실패하면 401 또는 403으로 응답합니다.

## 요청
### 헤더
| 헤더 | 필수 | 설명 |
| --- | --- | --- |
| Authorization | ✅ | Firebase ID 토큰, 예시: `Bearer eyJhbGciOi...` |
| Content-Type | ✅ | `multipart/form-data`

### 폼 필드
| 필드 | 타입 | 필수 | 제약 및 설명 |
| --- | --- | --- | --- |
| job_category | string | ✅ | 최대 80자, ex) "프론트엔드" |
| job_role | string | ❌ | 최대 100자, ex) "시니어 프론트엔드 엔지니어" |
| school_name | string | ❌ | 예) "서울대학교" |
| major | string | ❌ | 예) "컴퓨터공학과" |
| skills | string[] / string | ❌ | 쉼표 구분 문자열 또는 JSON 배열 허용, 빈 배열 허용 |
| certifications | string[] / string | ❌ | 선택사항, 쉼표 구분 문자열 또는 JSON 배열 허용 |
| html_file | file | ✅ | MIME `text/html` 또는 `application/xhtml+xml`, 최대 5MB |

### 요청 예시

#### cURL
```bash
curl -X POST https://api.example.com/api/personas/inputs/ \
  -H "Authorization: Bearer <firebase-id-token>" \
  -F "job_category=프론트엔드" \
  -F "job_role=시니어 프론트엔드 엔지니어" \
  -F "school_name=서울대학교" \
  -F "major=컴퓨터공학과" \
  -F "skills=React,TypeScript,Firebase" \
  -F "certifications=정보처리기사,AWS Certified Developer" \
  -F "html_file=@/path/to/profile.html;type=text/html"
```

#### TypeScript (Fetch API)
```typescript
interface PersonaData {
  job_category: string;  // 필수 필드
  job_role?: string;      // 선택사항
  school_name?: string;   // 선택사항
  major?: string;         // 선택사항
  skills?: string[];      // 선택사항, 빈 배열 허용
  certifications?: string[]; // 선택사항
}

interface PersonaResponse {
  id: string;
  user_id: string;
  job_category: string;
  job_role: string;
  school_name: string;
  major: string;
  skills: string[];
  certifications: string[];
  html_file_path: string;
  html_content_type: string;
  html_file_size: number;
  created_at: string;
  updated_at: string;
}

const createPersona = async (
  idToken: string, 
  personaData: PersonaData, 
  htmlFile: File
): Promise<PersonaResponse> => {
  try {
    const formData = new FormData();
    
    // 기본 정보 추가
    formData.append('job_category', personaData.job_category);
    formData.append('job_role', personaData.job_role);
    formData.append('school_name', personaData.school_name);
    formData.append('major', personaData.major);
    
    // 배열 필드 처리 (쉼표로 구분된 문자열로 전송)
    formData.append('skills', personaData.skills.join(','));
    if (personaData.certifications && personaData.certifications.length > 0) {
      formData.append('certifications', personaData.certifications.join(','));
    }
    
    // HTML 파일 추가
    formData.append('html_file', htmlFile);
    
    const response = await fetch('/api/personas/inputs/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`
        // Content-Type은 자동으로 설정됨 (multipart/form-data)
      },
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || '페르소나 생성에 실패했습니다.');
    }
    
    const result: PersonaResponse = await response.json();
    console.log('생성된 페르소나:', result);
    return result;
  } catch (error) {
    console.error('페르소나 생성 실패:', error);
    throw error;
  }
};

// 사용 예시
const personaData: PersonaData = {
  job_category: '프론트엔드',
  job_role: '시니어 프론트엔드 엔지니어',
  school_name: '서울대학교',
  major: '컴퓨터공학과',
  skills: ['React', 'TypeScript', 'Firebase'],
  certifications: ['정보처리기사', 'AWS Certified Developer']
};

const htmlFileInput = document.getElementById('htmlFileInput') as HTMLInputElement;
const htmlFile: File = htmlFileInput.files![0];
const idToken: string = await firebase.auth().currentUser.getIdToken();
const persona: PersonaResponse = await createPersona(idToken, personaData, htmlFile);
```

#### React Hook 예시 (TypeScript)
```typescript
import { useState, useCallback } from 'react';

interface PersonaData {
  job_category: string;  // 필수 필드
  job_role?: string;      // 선택사항
  school_name?: string;   // 선택사항
  major?: string;         // 선택사항
  skills?: string[];      // 선택사항, 빈 배열 허용
  certifications?: string[]; // 선택사항
}

interface PersonaResponse {
  id: string;
  user_id: string;
  job_category: string;
  job_role: string;
  school_name: string;
  major: string;
  skills: string[];
  certifications: string[];
  html_file_path: string;
  html_content_type: string;
  html_file_size: number;
  created_at: string;
  updated_at: string;
}

interface UsePersonaCreateReturn {
  createPersona: (idToken: string, personaData: PersonaData, htmlFile: File) => Promise<PersonaResponse>;
  loading: boolean;
  error: string | null;
}

const usePersonaCreate = (): UsePersonaCreateReturn => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const createPersona = useCallback(async (
    idToken: string, 
    personaData: PersonaData, 
    htmlFile: File
  ): Promise<PersonaResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      
      // 기본 정보 추가
      formData.append('job_category', personaData.job_category);
      formData.append('job_role', personaData.job_role);
      formData.append('school_name', personaData.school_name);
      formData.append('major', personaData.major);
      
      // 배열 필드 처리
      formData.append('skills', personaData.skills.join(','));
      if (personaData.certifications?.length && personaData.certifications.length > 0) {
        formData.append('certifications', personaData.certifications.join(','));
      }
      
      // HTML 파일 추가
      formData.append('html_file', htmlFile);
      
      const response = await fetch('/api/personas/inputs/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '페르소나 생성에 실패했습니다.');
      }
      
      const result: PersonaResponse = await response.json();
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return { createPersona, loading, error };
};

// 컴포넌트에서 사용
interface PersonaFormData {
  job_category: string;  // 필수 필드
  job_role: string;      // 선택사항 (폼에서는 빈 문자열로 초기화)
  school_name: string;   // 선택사항 (폼에서는 빈 문자열로 초기화)
  major: string;         // 선택사항 (폼에서는 빈 문자열로 초기화)
  skills: string[];      // 선택사항 (폼에서는 빈 배열로 초기화)
  certifications: string[]; // 선택사항 (폼에서는 빈 배열로 초기화)
}

const PersonaCreateForm: React.FC = () => {
  const { createPersona, loading, error } = usePersonaCreate();
  const [formData, setFormData] = useState<PersonaFormData>({
    job_category: '',
    job_role: '',
    school_name: '',
    major: '',
    skills: [],
    certifications: []
  });
  const [htmlFile, setHtmlFile] = useState<File | null>(null);
  
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    
    if (!htmlFile) {
      alert('HTML 파일을 선택해주세요.');
      return;
    }
    
    try {
      const idToken: string = await firebase.auth().currentUser.getIdToken();
      const personaData: PersonaData = {
        job_category: formData.job_category,
        job_role: formData.job_role,
        school_name: formData.school_name,
        major: formData.major,
        skills: formData.skills,
        certifications: formData.certifications.length > 0 ? formData.certifications : undefined
      };
      const result: PersonaResponse = await createPersona(idToken, personaData, htmlFile);
      console.log('페르소나 생성 완료:', result);
      // 성공 처리 (리다이렉트, 상태 업데이트 등)
    } catch (err) {
      console.error('페르소나 생성 실패:', err);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="직군"
        value={formData.job_category}
        onChange={(e) => setFormData({...formData, job_category: e.target.value})}
        required
      />
      <input
        type="text"
        placeholder="직무 (선택사항)"
        value={formData.job_role}
        onChange={(e) => setFormData({...formData, job_role: e.target.value})}
      />
      <input
        type="text"
        placeholder="학교명 (선택사항)"
        value={formData.school_name}
        onChange={(e) => setFormData({...formData, school_name: e.target.value})}
      />
      <input
        type="text"
        placeholder="전공 (선택사항)"
        value={formData.major}
        onChange={(e) => setFormData({...formData, major: e.target.value})}
      />
      <input
        type="text"
        placeholder="기술 (쉼표로 구분, 선택사항)"
        onChange={(e) => setFormData({...formData, skills: e.target.value.split(',').map(s => s.trim()).filter(s => s.length > 0)})}
      />
      <input
        type="text"
        placeholder="자격증 (쉼표로 구분, 선택사항)"
        onChange={(e) => setFormData({...formData, certifications: e.target.value.split(',').map(s => s.trim()).filter(s => s.length > 0)})}
      />
      <input
        type="file"
        accept=".html,.htm"
        onChange={(e) => setHtmlFile(e.target.files?.[0] || null)}
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? '생성 중...' : '페르소나 생성'}
      </button>
      {error && <p style={{color: 'red'}}>오류: {error}</p>}
    </form>
  );
};
```

## 응답
### 201 Created
- 헤더: `Location: /api/personas/inputs/{document_id}`
- 본문:
```json
{
  "id": "b0a8d4c6-2b11-4f2b-9011-2a4d8c9c6b1a",
  "user_id": "firebase_uid_123",
  "job_category": "프론트엔드",
  "job_role": "시니어 프론트엔드 엔지니어",
  "school_name": "서울대학교",
  "major": "컴퓨터공학과",
  "skills": ["React", "TypeScript", "Firebase"],
  "certifications": ["정보처리기사", "AWS Certified Developer"],
  "html_file_path": "personas/user123/persona456/resume.html",
  "html_content_type": "text/html",
  "html_file_size": 48321,
  "created_at": "2025-01-27T10:30:45.123456Z",
  "updated_at": "2025-01-27T10:30:45.123456Z"
}
```

### 오류 응답
| 상태 코드 | 설명 | 예시 메시지 |
| --- | --- | --- |
| 400 Bad Request | 요청 데이터 검증 실패 | `{"skills": ["최소 한 개 이상의 기술이 필요합니다."]}` |
| 401 Unauthorized / 403 Forbidden | Firebase 인증 실패 또는 권한 없음 | `{"detail": "자격 증명이 유효하지 않습니다."}` |
| 413 Payload Too Large | 파일 크기가 허용 범위를 초과 | `{"detail": "HTML 파일은 최대 5MB까지 업로드할 수 있습니다."}` |
| 500 Internal Server Error | Firestore/Storage 저장 중 예외 발생 | `{"detail": "페르소나 입력을 저장할 수 없습니다: ..."}` |

## 비고
- Storage 버킷은 환경 변수 `FIREBASE_STORAGE_BUCKET`으로 지정합니다. 미설정 시 Firebase 기본 버킷을 사용합니다.
- `skills`와 `certifications`는 쉼표로 구분된 문자열을 자동 분리하거나 JSON 배열 그대로 처리합니다.
- 업로드된 파일은 응답에 포함되지 않으며, 필요 시 `html_file_path`로 Firebase Storage에서 다운로드 URL을 생성해야 합니다.



