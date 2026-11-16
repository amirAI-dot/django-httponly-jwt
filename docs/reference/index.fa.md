# مرجع

همه‌ی آنچه کتابخانه ارائه می‌دهد، فهرست‌شده. [راهنما](../guide.md) توضیح می‌دهد بخش‌ها
چطور کنار هم قرار می‌گیرند؛ این بخش برای پیدا کردن یکی از آن‌هاست.

## پیکربندی

| صفحه | چه چیزی آنجاست |
|---|---|
| [تنظیمات](../guide.md) (بخش ۱۳) | همه‌ی کلیدهای `HTTPONLY_JWT`، با پیش‌فرضشان |
| [بررسی‌های سیستمی](../guide.md) (بخش ۱۴) | همه‌ی `httponly_jwt.E0xx` و `W0xx`، و آنچه موقع بالا آمدن رد می‌کنند |
| [سیگنال‌ها](api/signals.md) | هر تغییر در یک نشست، و آنچه هر کدام دارد |

## API پایتون

از خود کد خوانده می‌شود، پس هیچ‌وقت از آن عقب نمی‌ماند. توضیح‌ها مال خود کد هستند،
به انگلیسی.

| صفحه | چه چیزی آنجاست |
|---|---|
| [نشست‌ها](api/sessions.md) | `start_session`، `issue_tokens`، و طول عمر و claimهای هر نفر |
| [احراز هویت](api/authentication.md) | `CookieAuthentication`، `HeaderAuthentication`، `OptionalAuthentication` |
| [تمدید](api/middleware.md) | `RenewalMiddleware`، و گام‌هایی که از آن‌ها ساخته شده |
| [ویوها](api/views.md) | `RefreshView`، `SignOutView`، `CsrfTokenView`، و بررسی CSRF |
| [سیگنال‌ها](api/signals.md) | چهار سیگنال، و `Ended` |
| [کوکی‌ها](api/cookies.md) | گذاشتن، پاک کردن و خواندن کوکی‌های نشست |
| [schema](api/schema.md) | افزونه‌های drf-spectacular |
