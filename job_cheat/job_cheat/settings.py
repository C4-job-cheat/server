from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-1j-@1=0)%671b9b-r6^r7!notaw=zm5pw9!)wa)(92py51gta('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv('DEBUG', 'true').lower() == 'true' else False

# Django 개발 서버 경고 메시지 숨기기
def hide_django_warnings(hide_warnings=True):
    """
    Django 개발 서버 경고 메시지를 숨기는 함수
    
    Args:
        hide_warnings (bool): True면 경고 메시지를 숨김, False면 경고 메시지를 표시
    """
    if not hide_warnings:
        return
        
    import warnings
    import os
    import sys
    
    # 환경 변수로 모든 경고 비활성화
    os.environ['PYTHONWARNINGS'] = 'ignore'
    warnings.filterwarnings('ignore')
    
    # 표준 출력을 필터링하여 경고 메시지 제거
    class NoWarningOutput:
        def __init__(self, original_stream):
            self.original_stream = original_stream
            
        def write(self, message):
            if 'WARNING: This is a development server' not in message and 'Do not use it in a production setting' not in message:
                self.original_stream.write(message)
                
        def flush(self):
            self.original_stream.flush()
            
        def __getattr__(self, name):
            return getattr(self.original_stream, name)
    
    # 표준 출력과 표준 에러를 필터링
    sys.stdout = NoWarningOutput(sys.stdout)
    sys.stderr = NoWarningOutput(sys.stderr)

# 함수 실행 (환경 변수로 제어 가능)
HIDE_DJANGO_WARNINGS = os.getenv('HIDE_DJANGO_WARNINGS', 'true').lower() == 'true'
hide_django_warnings(HIDE_DJANGO_WARNINGS)

# 백엔드가 수신할 호스트(ngrok 서브도메인 전체 허용)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.app', '.ngrok.io']

# CSRF: 스킴+도메인, 서브도메인 와일드카드
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://192.168.12.1',
    'http://192.168.12.1:3000',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
]

# CORS: ngrok 도메인이 매번 바뀌면 정규식으로 허용 (django-cors-headers)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/[a-z0-9\-]+\.ngrok-free\.app$",
    r"^https:\/\/[a-z0-9\-]+\.ngrok\.io$",
    r"^http:\/\/192\.168\.12\.1(?::\d+)?$",
]

# 프론트가 로컬이면 그대로 허용
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'api',

    # common/core utilities
    'core',

    # feature apps
    'personas',
    'cover_letters',
    'interviews',
    'job_search',

    'rest_framework',

    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Django REST framework global settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.FirebaseAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

ROOT_URLCONF = 'job_cheat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'job_cheat.wsgi.application'


# Firebase Admin 초기화 (환경 변수 기반 설정)
import firebase_admin
from firebase_admin import credentials, auth, firestore

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CREDENTIALS")
FIREBASE_CRED_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_EMULATOR_HOST = os.getenv("FIRESTORE_EMULATOR_HOST")
FIREBASE_INIT_ERROR = None
FIREBASE_APP = None
FIREBASE_DB = None


def _load_firebase_credentials():
    """환경 변수에서 Firebase 서비스 계정 정보를 읽어온다."""
    if FIREBASE_CRED_JSON:
        return credentials.Certificate.from_json(FIREBASE_CRED_JSON)
    if FIREBASE_CRED_PATH:
        cred_path = Path(FIREBASE_CRED_PATH).expanduser()
        if not cred_path.exists():
            raise ImproperlyConfigured(
                f"FIREBASE_CREDENTIALS 경로를 찾을 수 없습니다: {cred_path}"
            )
        return credentials.Certificate(str(cred_path))
    google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if google_credentials:
        cred_path = Path(google_credentials).expanduser()
        if not cred_path.exists():
            raise ImproperlyConfigured(
                f"GOOGLE_APPLICATION_CREDENTIALS 경로를 찾을 수 없습니다: {cred_path}"
            )
        return credentials.Certificate(str(cred_path))
    raise ImproperlyConfigured(
        "Firebase 자격 증명 환경 변수가 설정되지 않았습니다. "
        "FIREBASE_CREDENTIALS 또는 FIREBASE_CREDENTIALS_JSON을 지정하세요."
    )


def _initialize_firebase():
    """Initialise Firebase Admin app and Firestore client once."""
    global FIREBASE_APP, FIREBASE_DB, FIREBASE_INIT_ERROR

    app = None

    if firebase_admin._apps:
        app = firebase_admin.get_app()
    else:
        try:
            credential = _load_firebase_credentials()
            options = {}
            if FIREBASE_PROJECT_ID:
                options["projectId"] = FIREBASE_PROJECT_ID
            if FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = FIREBASE_STORAGE_BUCKET
            app = firebase_admin.initialize_app(credential, options)
        except Exception as exc:
            FIREBASE_INIT_ERROR = str(exc)
            FIREBASE_APP = None
            FIREBASE_DB = None
            return

    try:
        FIREBASE_APP = app
        FIREBASE_DB = firestore.client(app=app)
    except Exception as exc:
        FIREBASE_APP = None
        FIREBASE_DB = None
        FIREBASE_INIT_ERROR = str(exc)


_initialize_firebase()

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS 커스텀 헤더 허용: ngrok 경고 우회 헤더 포함
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    'ngrok-skip-browser-warning',
]

# CORS 추가 설정 (파일 업로드를 위한)
CORS_ALLOW_CREDENTIALS = True  # 쿠키 및 인증 헤더 허용
CORS_PREFLIGHT_MAX_AGE = 86400  # 24시간 (preflight 캐시 시간)

# 허용할 HTTP 메서드
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# 파일 업로드 관련 설정 (대용량 파일 streaming 처리)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB (메모리에 올리지 않고 임시 파일로 저장)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB (메모리에 올리지 않고 임시 파일로 저장)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # 폼 필드 수 제한

# 대용량 파일 처리를 위한 임시 파일 설정
FILE_UPLOAD_TEMP_DIR = None  # 시스템 기본 임시 디렉토리 사용
FILE_UPLOAD_PERMISSIONS = 0o644  # 임시 파일 권한

# 요청 타임아웃 설정 (대용량 파일 처리용)
REQUEST_TIMEOUT = 300  # 5분

# 로깅 설정 (Broken pipe 오류 처리)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',  # Broken pipe 오류를 WARNING으로 처리
            'propagate': False,
        },
    },
}





