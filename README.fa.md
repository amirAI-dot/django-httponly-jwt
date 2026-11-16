# django-httponly-jwt

نشست‌های JWT برای Django در کوکی‌های HttpOnly، که سرور آن‌قدر بی‌صدا تمدیدشان می‌کند
که فرانت‌اند هیچ‌وقت توکنی در دست ندارد.

[![PyPI](https://img.shields.io/pypi/v/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![Python](https://img.shields.io/pypi/pyversions/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![Django](https://img.shields.io/pypi/frameworkversions/django/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![CI](https://github.com/amirAI-dot/django-httponly-jwt/actions/workflows/ci.yml/badge.svg)](https://github.com/amirAI-dot/django-httponly-jwt/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-English%20%7C%20%D9%81%D8%A7%D8%B1%D8%B3%DB%8C-blue)](https://amirai-dot.github.io/django-httponly-jwt/)
[![Licence](https://img.shields.io/pypi/l/django-httponly-jwt)](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/LICENSE)

[English](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/README.md) ·
[مستندات](https://amirai-dot.github.io/django-httponly-jwt/fa/) ·
[طراحی](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/design.fa.md) ·
[نمونه](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/example/README.fa.md)

ورود دو کوکی HttpOnly می‌گذارد. وقتی توکن access تمام می‌شود، سرور سر راه تمدیدش
می‌کند - درخواستی که آن را منقضی یافت جواب می‌گیرد، و جواب توکن تازه را با خودش دارد.
فرانت‌اند درخواست‌ها را با کوکی‌ها می‌فرستد و با 401 به صفحه‌ی ورود می‌رود؛ هیچ‌وقت
توکنی نمی‌خواند، نگه نمی‌دارد یا تمدید نمی‌کند، و هیچ اسکریپتی در صفحه هم نمی‌تواند.

* **وقتی مرورگر کوکی منقضی را از قبل پاک کرده هم تمدید می‌کند** - همان حالتی که
  middleware ساده خرابش می‌کند.
* **در middleware هیچ‌وقت نمی‌چرخاند**، پس دو تبی که با هم تمدید می‌کنند همدیگر را
  خارج نمی‌کنند. چرخاندن کار view تمدید است، و توکن قبلی را blacklist می‌کند.
* **نشست را در تمدید بعدی تمام می‌کند** وقتی حساب غیرفعال شده، یا پروژه بگوید - نه
  هفته‌ها بعد، وقتی توکن refresh منقضی شود.
* **نشست هر نفر**: طولش (کارمند یک روز، مشتری یک ماه)، و claimهایی مثل نقش، که در هر
  تمدید دوباره خوانده می‌شوند.
* **موقع بالا آمدن رد می‌کند** آنچه را که کار نمی‌کند یا از چیزی محافظت نمی‌کند:
  `SameSite=None` بدون بررسی CSRF، تمدید نصب‌نشده، نبودن blacklist.
* **اپ‌های موبایل و اسکریپت‌ها** از `Authorization: Bearer` استفاده می‌کنند و
  توکن‌هایشان را در بدنه می‌گیرند؛ فرانت‌اندی روی سایت دیگر بررسی CSRF خود Django را
  پس می‌گیرد.
* سیگنال برای سابقه‌ی پروژه، توصیف در drf-spectacular، sync و async، انگلیسی و
  فارسی.

لایه‌ای است روی [djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt):
simplejwt توکن‌ها را می‌سازد و بررسی می‌کند؛ اینکه شخص چطور ثابت می‌کند کیست مال خود
پروژه می‌ماند.

## نصب

```bash
pip install django-httponly-jwt
```

```python
# settings.py
INSTALLED_APPS = [..., 'rest_framework_simplejwt.token_blacklist', 'httponly_jwt']

MIDDLEWARE = [..., 'httponly_jwt.middleware.RenewalMiddleware', ...]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

```python
# views.py - the project signs the person in, its own way, then:
from httponly_jwt.sessions import start_session


class SignInView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])
        return start_session(Response({'id': person.pk}), person, request=request)
```

```python
# urls.py
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    path('auth/sign-in/', SignInView.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
```

```js
// The frontend: the cookies go with every request, and 401 means sign in again.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })
```

همه‌اش همین است: از آنجا هر درخواست مرورگر کوکی‌ها را دارد، middleware توکن access را
وقتی تمام شد تمدید می‌کند، و `request.user` همان شخص است. بقیه در
[مستندات](https://amirai-dot.github.io/django-httponly-jwt/fa/) است - طول نشست و claimها، فرانت‌اند، فرانت‌اند روی
سایت دیگر، اپ‌ها، سیگنال‌ها، schema، همه‌ی تنظیمات و همه‌ی بررسی‌ها - و
[`example/`](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/example/README.fa.md) همه‌اش را در حال کار دارد.

Django نسخه‌ی 5.2 تا 6.1، Python نسخه‌ی 3.11 تا 3.14.

## کار روی آن

همه‌ی بررسی‌ها از طریق [nox](https://nox.thea.codes) اجرا می‌شوند، همان sessionها روی
سیستم خودتان و در CI. با [uv](https://docs.astral.sh/uv/) نصب‌شده، Pythonی که نیست
برایتان گرفته می‌شود.

```bash
uv tool install nox
```

```bash
nox -s lint
```

```bash
nox -s types
```

```bash
nox -s tests
```

`tests` همه‌ی نسخه‌های پشتیبانی‌شده‌ی Python و Django را با پوشش ۱۰۰٪ اجرا می‌کند؛ یک
ترکیب `nox -s "tests(3.13-django6.1)"` است، و `nox -l` همه را فهرست می‌کند. `package`
wheel را می‌سازد و تست‌ها و پروژه‌ی نمونه را روی آن اجرا می‌کند. `messages` رشته‌های
علامت‌خورده را دوباره استخراج می‌کند و اگر کاتالوگ فارسی یکی را نداشته باشد شکست
می‌خورد؛ gettext لازم دارد. `docs` سایت مستندات را می‌سازد و با هر لینکی که نتواند دنبالش کند
شکست می‌خورد؛ `nox -s docs -- serve` آن را هنگام نوشتن نشان می‌دهد.

## مجوز

BSD 3-Clause - [`LICENSE`](LICENSE) را ببینید.
