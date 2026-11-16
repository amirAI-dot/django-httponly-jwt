# Installation

```bash
pip install django-httponly-jwt
```

With the drf-spectacular schema described:

```bash
pip install "django-httponly-jwt[spectacular]"
```

Django 5.2 to 6.1, Python 3.11 to 3.14, Django REST framework 3.16 and
djangorestframework-simplejwt 5.5 or newer - installed with it.

## Into the project

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'httponly_jwt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'httponly_jwt.middleware.RenewalMiddleware',
    ...,
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

* **`token_blacklist`** is simplejwt's: signing out and rotation end a refresh
  token by blacklisting it. Without it the project refuses to start (E004),
  unless it says it accepts that with `ALLOW_WITHOUT_BLACKLIST`.
* **`RenewalMiddleware`** goes before anything that reads who is asking.
  Without it, with the cookie authenticating, the project refuses to start
  (E002): every session would end with its first access token.
* **The two classes** read the cookie for a browser and the header for
  everything else.

```bash
python manage.py migrate
```

```bash
python manage.py check
```

`check` passing means the configuration is one that works. `check --deploy`
also warns when the cookies are not `Secure`.

Next: [the quickstart](quickstart.md) - signing somebody in.
