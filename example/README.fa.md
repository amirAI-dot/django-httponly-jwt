# پروژه‌ی نمونه

[English](README.md)

یک API که با کد یک‌بارمصرف واردش می‌شوند، همان‌طور که بیشتر پروژه‌ها در ایران آدم‌ها را
وارد می‌کنند - و همه‌ی بخش‌های django-httponly-jwt سر جایش، هر کدام در همان فایلی که
شما می‌گذاشتید:

| چه چیزی | کجا |
|---|---|
| middleware، کلاس‌های احراز هویت، `HTTPONLY_JWT` | `config/settings.py` |
| viewهای تمدید و خروج کتابخانه، و schema | `config/urls.py` |
| ورود به روش خود پروژه، که کار را به `start_session` می‌سپارد | `accounts/views.py` |
| طول نشست، نقش در توکن، حسابی که پروژه می‌بندد | `accounts/sessions.py` |
| سابقه‌ای که از سیگنال‌ها نوشته می‌شود | `accounts/receivers.py`، `accounts/models.py` |
| اینکه همه‌ی این‌ها روی هم چه می‌شوند | `accounts/tests.py` |

## اجرا

از ریشه‌ی مخزن، با کتابخانه نصب‌شده در یک محیط تازه:

```bash
python -m venv .venv && .venv/bin/pip install -e '.[spectacular]'
```

```bash
cd example
```

```bash
../.venv/bin/python manage.py migrate
```

```bash
../.venv/bin/python manage.py runserver
```

کوکی‌ها `Secure` هستند، و مرورگرها کوکی `Secure` را از `http://localhost` می‌پذیرند،
پس برای امتحان کردن چیزی لازم نیست عوض شود.

## ورود

کد بخواهید. به جای اینکه پیامک شود، در خروجی سرور چاپ می‌شود -
`accounts.code to=+989121234567 code=123456`:

```bash
curl -i -X POST localhost:8000/auth/code/ --data-urlencode phone=+989121234567
```

آن را برگردانید. جواب `{"id": 1}` است و دو خط `Set-Cookie` - هیچ توکنی در بدنه نیست:

```bash
curl -i -c jar -X POST localhost:8000/auth/sign-in/ --data-urlencode phone=+989121234567 -d code=123456
```

از آنجا کوکی‌ها خود نشست‌اند:

```bash
curl -b jar localhost:8000/me/
```

`{"phone": "+989121234567", "role": "customer"}` - نقش در توکن access آمده بود.
بعد از پانزده دقیقه توکن access تمام شده، و همان درخواست باز هم جواب می‌گیرد:
middleware سر راه تمدیدش کرد، و جواب توکن تازه را می‌گذارد.

```bash
curl -b jar -c jar -X POST localhost:8000/auth/sign-out/
```

خارج شدید، همه‌جا: توکن refresh در blacklist است، پس نسخه‌ای از همین jar روی
دستگاه دیگر هم دیگر تمدید نمی‌کند.

## تست‌ها

```bash
../.venv/bin/python manage.py test
```

`nox -s package` آن‌ها را روی wheel ساخته‌شده اجرا می‌کند، پس فایلی که از بسته جا
مانده آنجا شکست می‌خورد.
