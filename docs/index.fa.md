# django-httponly-jwt

نشست‌های JWT برای Django در کوکی‌های HttpOnly، که سرور آن‌قدر بی‌صدا تمدیدشان می‌کند
که **فرانت‌اند هیچ‌وقت توکنی در دست ندارد.**

ورود دو کوکی HttpOnly می‌گذارد. وقتی توکن access تمام می‌شود، سرور سر راه تمدیدش
می‌کند - درخواستی که آن را منقضی یافت جواب می‌گیرد، و جواب توکن تازه را با خودش دارد.
فرانت‌اند درخواست‌ها را با کوکی‌ها می‌فرستد و با 401 به صفحه‌ی ورود می‌رود.

<div class="grid cards" markdown>

- **هیچ توکنی در صفحه نیست.** کوکی‌های HttpOnly: هیچ اسکریپتی نمی‌تواند بخواندشان،
  پس اسکریپتی که به صفحه تزریق شده نمی‌تواند نشست را بدزدد.
- **بدون رقص تمدید.** نه interceptor، نه تلاش دوباره، نه مسابقه بین تب‌ها: سرور تمدید
  می‌کند، و درخواست جواب می‌گیرد.
- **نشست وقتی باید تمام می‌شود** - در تمدید بعد از غیرفعال شدن حساب، و وقتی شخص خارج
  می‌شود همه‌جا با هم.
- **موقع بالا آمدن رد می‌شود** وقتی کار نمی‌کند یا از چیزی محافظت نمی‌کند - نه روزی
  که کسی متوجهش شود.

</div>

## نصب

```bash
pip install django-httponly-jwt
```

```python
INSTALLED_APPS = [..., 'rest_framework_simplejwt.token_blacklist', 'httponly_jwt']

MIDDLEWARE = [..., 'httponly_jwt.middleware.RenewalMiddleware', ...]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

بعد یک view ورود شخص را به `start_session` می‌سپارد - [شروع
سریع](getting-started/quickstart.md) را ببینید.

## کجا بروید

| | |
|---|---|
| [معرفی](getting-started/introduction.md) | چه چیزی با توکن در مرورگر خراب می‌شود، و این کتابخانه چه می‌کند |
| [شروع سریع](getting-started/quickstart.md) | پروژه‌ای که در پنج دقیقه آدم‌ها را وارد می‌کند |
| [راهنما](guide.md) | همه‌ی بخش‌ها، از ورود تا فرانت‌اندی روی سایت دیگر |
| [راهنماهای کاربردی](how-to/index.md) | Next.js، مهاجرت از `localStorage`، سابقه، خروج از همه‌جا، تست |
| [مرجع](reference/index.md) | تنظیمات، بررسی‌ها، سیگنال‌ها، و API پایتون |
| [طراحی](design.md) | چرا این‌طور ساخته شده |
| [پرسش‌ها](faq.md) | کوکی امن‌تر است؟ چرا `Lax`؟ چه هزینه‌ای دارد؟ |

Django نسخه‌ی 5.2 تا 6.1، Python نسخه‌ی 3.11 تا 3.14، روی
[djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt).
انگلیسی و فارسی. مجوز BSD.
