# نصب

```bash
pip install django-httponly-jwt
```

با توصیف schema در drf-spectacular:

```bash
pip install "django-httponly-jwt[spectacular]"
```

Django نسخه‌ی 5.2 تا 6.1، Python نسخه‌ی 3.11 تا 3.14، Django REST framework نسخه‌ی 3.16 و
djangorestframework-simplejwt نسخه‌ی 5.5 یا جدیدتر - همراهش نصب می‌شوند.

## در پروژه

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

* **`token_blacklist`** مال simplejwt است: خروج و چرخاندن، توکن refresh را با
  blacklist کردنش تمام می‌کنند. بدون آن پروژه بالا نمی‌آید (E004)، مگر اینکه با
  `ALLOW_WITHOUT_BLACKLIST` بگوید این را می‌پذیرد.
* **`RenewalMiddleware`** پیش از هر چیزی قرار می‌گیرد که می‌خواند چه کسی درخواست داده.
  بدون آن، وقتی کوکی احراز هویت می‌کند، پروژه بالا نمی‌آید (E002): هر نشست با اولین
  توکن access تمام می‌شد.
* **دو کلاس** کوکی را برای مرورگر و هدر را برای بقیه می‌خوانند.

```bash
python manage.py migrate
```

```bash
python manage.py check
```

پاس شدن `check` یعنی پیکربندی کار می‌کند. `check --deploy` هم وقتی کوکی‌ها `Secure`
نیستند هشدار می‌دهد.

بعدی: [شروع سریع](quickstart.md) - وارد کردن کسی.
