"""
The example: an API signed in to by a one-time code, the way the owner's
projects sign people in - and every part of django-httponly-jwt in place.

Only for trying it out: the secret is written here and the database is a file.
"""

from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'only-for-the-example-and-long-enough-for-hmac-sha256'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    # Signing out and rotation end a refresh token by blacklisting it (E004).
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'httponly_jwt',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Before anything reads who is asking: it renews the access cookie in place.
    'httponly_jwt.middleware.RenewalMiddleware',
]

ROOT_URLCONF = 'config.urls'

DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'example.sqlite3'}
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True

# The code is kept here between asking for it and typing it.
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # A browser: the access cookie. Anything else: Authorization: Bearer.
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    # Only the default: REFRESH_LIFETIME below answers it per person.
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

HTTPONLY_JWT = {
    # Staff for a working day, everybody else for simplejwt's thirty days.
    'REFRESH_LIFETIME': 'accounts.sessions.lifetime',
    # The role travels in the token, read again at every renewal.
    'CLAIMS': 'accounts.sessions.claims',
    # Asked beside is_active at every renewal and refresh.
    'USER_CAN_SIGN_IN': 'accounts.sessions.may_sign_in',
}

SPECTACULAR_SETTINGS = {'TITLE': 'django-httponly-jwt example', 'VERSION': '1'}

LOGGING = {
    'version': 1,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'accounts': {'handlers': ['console'], 'level': 'INFO'}},
}
