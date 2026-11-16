# تست پروژه‌ای که از آن استفاده می‌کند

بیشتر تست‌های یک پروژه درباره‌ی این است که شخص چه کاری می‌تواند بکند، نه اینکه چطور
وارد شده - برای آن‌ها `force_authenticate` در DRF کافی است. تست‌های زیر برای بقیه‌اند:
اینکه نشست واقعاً همان کوکی‌هاست، و پایدار می‌ماند.

## مرورگری که وارد شده

```python
# tests/conftest.py
import pytest
from rest_framework.test import APIClient

from httponly_jwt.sessions import issue_tokens


@pytest.fixture
def signed_in(db):
    """A browser signed in as a person: both cookies, as signing in would set them."""

    def sign_in(person):
        tokens = issue_tokens(person)
        client = APIClient()
        client.cookies['access_token'] = tokens.access
        client.cookies['refresh_token'] = tokens.refresh
        return client

    return sign_in
```

`issue_tokens` همان جفتی را می‌سازد که ورود می‌ساخت، با claimها و طول عمر شخص. کلاینت
تست کوکی‌های `Secure` را روی HTTP ساده هم می‌فرستد، پس برای تست چیزی لازم نیست عوض
شود.

## viewی که ورود را به روش خودش می‌خواند

`force_authenticate` کلاس‌های احراز هویت را دور می‌زند. viewی که
`authentication_classes` خودش را دارد - مثلاً endpointی که برای همه باز است و درخواست
شخص واردشده را به نام او ثبت می‌کند - با کوکی‌های واقعی تست می‌شود، وگرنه تستی پاس
می‌شود در حالی که view اصلاً کسی را نمی‌خواند.

## تمدید

```python
from datetime import timedelta

from rest_framework_simplejwt.tokens import AccessToken


def test_a_session_whose_access_token_ran_out_is_still_served(signed_in, person):
    client = signed_in(person)
    expired = AccessToken.for_user(person)
    expired.set_exp(lifetime=-timedelta(seconds=1))
    client.cookies['access_token'] = str(expired)

    answer = client.get('/me/')

    assert answer.status_code == 200
    assert answer.cookies['access_token'].value, 'the renewed token is set'
```

## ورود

```python
def test_signing_in_sets_the_cookies_and_no_token(client, person):
    answer = client.post('/auth/sign-in/', {'username': 'ana', 'password': 'right'})

    assert answer.cookies['access_token']['httponly']
    assert 'access' not in answer.json()
```

## حالت CSRF

کلاینت تست بررسی CSRF در Django را رد می‌کند مگر اینکه خواسته شود:

```python
from django.test import override_settings


@override_settings(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None', 'CSRF': True})
def test_a_write_without_the_csrf_token_is_refused(person):
    client = APIClient(enforce_csrf_checks=True)
    client.cookies['access_token'] = issue_tokens(person).access

    assert client.post('/orders/', {}).status_code == 403
```

## تنظیمات در تست

کتابخانه هر بار که پرسیده شود `HTTPONLY_JWT` را می‌خواند، پس `override_settings` روی آن
مثل هر تنظیم دیگر Django کار می‌کند - نام کوکی‌ها، طول عمر، claimها.
