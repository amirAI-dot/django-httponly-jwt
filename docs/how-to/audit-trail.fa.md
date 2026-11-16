# نگه داشتن سابقه

هر تغییر در یک نشست یک سیگنال است، که وقتی جواب معلوم شد با شخص و درخواست فرستاده
می‌شود. نوشتن آن‌ها همه‌ی کار نگه داشتن سابقه است.

## یک جدول، و یک گیرنده

```python
# accounts/models.py
from django.conf import settings
from django.db import models


class SessionEvent(models.Model):
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+'
    )
    what = models.CharField(max_length=16)
    reason = models.CharField(max_length=32, blank=True)
    address = models.GenericIPAddressField(null=True)
    at = models.DateTimeField(auto_now_add=True)
```

```python
# accounts/receivers.py
from django.dispatch import receiver

from accounts.models import SessionEvent
from httponly_jwt.signals import (
    session_ended,
    session_refreshed,
    session_renewed,
    session_started,
)

WHAT = {
    session_started: 'started',
    session_renewed: 'renewed',
    session_refreshed: 'refreshed',
    session_ended: 'ended',
}


@receiver([session_started, session_renewed, session_refreshed, session_ended])
def record(signal, person, request, **kwargs):
    SessionEvent.objects.create(
        person=person,
        what=WHAT[signal],
        reason=kwargs.get('reason') or '',
        address=request.META.get('REMOTE_ADDR') if request is not None else None,
    )
```

```python
# accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        from accounts import receivers  # noqa: F401
```

[پروژه‌ی نمونه](https://github.com/amirAI-dot/django-httponly-jwt/tree/main/example)
همین را دارد، با تست.

## هر سطر چه می‌گوید

| `what` | `reason` | یعنی |
|---|---|---|
| `started` | | وارد شد |
| `renewed` | | توکن access تمام شد و سر راه تمدید شد |
| `refreshed` | | view تمدید توکن refresh را چرخاند |
| `ended` | `signed_out` | شخص خارج شد |
| `ended` | `token_unusable` | توکن refresh منقضی شد، blacklist شد، یا خوانا نبود |
| `ended` | `not_allowed` | حساب حذف شده، غیرفعال است، یا `USER_CAN_SIGN_IN` ردش کرد |

وقتی توکن کسی را نام می‌برد که کتابخانه نتوانست بارش کند، `person` خالی است.

## انتخاب اینکه چه نگه داریم

تمدید برای هر کسی که وارد است در هر طول عمر توکن access یک بار اتفاق می‌افتد - با
توکن‌های پانزده‌دقیقه‌ای، یک روز شلوغ سطرهای خیلی زیادی است. پروژه‌ای که فقط ورودها،
خروج‌ها و ردها را می‌خواهد به همان‌ها گوش می‌دهد:

```python
from httponly_jwt.signals import Ended, session_ended


@receiver(session_ended)
def note_refusals(sender, person, request, reason, **kwargs):
    if reason == Ended.NOT_ALLOWED:
        ...
```

## زیر ASGI

middleware سیگنال‌هایش را با `asend` می‌فرستد، پس گیرنده‌ای که در پایگاه داده می‌نویسد -
یک گیرنده‌ی همگام، مثل بالایی - در یک thread اجرا می‌شود، جایی که Django اجازه می‌دهد.
چیزی لازم نیست عوض شود.

## آنچه هیچ‌وقت نباید نگه داشت

توکن‌ها. سطری که توکن refresh دارد نشستی است که هر کس جدول را بخواند می‌تواند به کار
ببرد.
