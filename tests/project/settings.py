"""
The project the test suite runs against.

The smallest project the library can be installed in: Django's ``auth`` and
``contenttypes``, DRF, simplejwt with its blacklist, and the library. Each
stage adds what it tests and nothing more.
"""

SECRET_KEY = 'only-for-the-test-suite-and-long-enough-for-hmac-sha256'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'httponly_jwt',
]

MIDDLEWARE = ['httponly_jwt.middleware.RenewalMiddleware']

ROOT_URLCONF = 'tests.project.urls'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

# The browser's way in first, then the header's - as a project lists them.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
