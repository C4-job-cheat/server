from pathlib import Path
import os

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


# Firebase Admin 초기화 (서비스 계정 경로 또는 JSON 문자열)
import firebase_admin
from firebase_admin import credentials, auth, firestore

FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', '')
FIREBASE_CRED_PATH = os.getenv('FIREBASE_CREDENTIALS')
FIREBASE_CRED_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON')
FIREBASE_INIT_ERROR = None

if not firebase_admin._apps:
    try:
        cred = None
        if FIREBASE_CRED_JSON:
            cred = credentials.Certificate.from_json(FIREBASE_CRED_JSON)
        elif FIREBASE_CRED_PATH:
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
        else:
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': FIREBASE_PROJECT_ID or None,
        })
        
        # Firestore 클라이언트 초기화
        db = firestore.client()
        # 앱 핸들을 전역으로 유지
        app = firebase_admin.get_app()
    except Exception as e:
        # 개발 초기 단계에서는 Firebase 미설정이어도 앱이 뜨도록 허용
        db = None
        app = None
        FIREBASE_INIT_ERROR = str(e)

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

# Firestore 클라이언트와 앱 핸들을 전역에서 사용할 수 있도록 설정
FIREBASE_DB = db
FIREBASE_APP = app
FIREBASE_INIT_ERROR = FIREBASE_INIT_ERROR




