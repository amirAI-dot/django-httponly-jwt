# Test a project that uses it

Most of a project's tests are about what a person may do, not how they signed
in - for those, DRF's `force_authenticate` is enough. The tests below are for
the rest: that the session really is the cookies, and that it holds.

## A signed-in browser

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

`issue_tokens` mints the pair signing in would, with the person's claims and
lifetime. The test client sends `Secure` cookies over plain HTTP, so nothing
needs changing for a test.

## A view that reads sign-ins its own way

`force_authenticate` walks round the authentication classes. A view that sets
its own `authentication_classes` - an endpoint open to anybody that files a
signed-in person's request under their name, say - is tested with real
cookies, or a test passes while the view reads nobody at all.

## Renewal

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

## Signing in

```python
def test_signing_in_sets_the_cookies_and_no_token(client, person):
    answer = client.post('/auth/sign-in/', {'username': 'ana', 'password': 'right'})

    assert answer.cookies['access_token']['httponly']
    assert 'access' not in answer.json()
```

## The CSRF mode

The test client skips Django's CSRF check unless asked:

```python
from django.test import override_settings


@override_settings(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None', 'CSRF': True})
def test_a_write_without_the_csrf_token_is_refused(person):
    client = APIClient(enforce_csrf_checks=True)
    client.cookies['access_token'] = issue_tokens(person).access

    assert client.post('/orders/', {}).status_code == 403
```

## Settings in a test

The library reads `HTTPONLY_JWT` each time it is asked, so `override_settings`
works on it as on any Django setting - the cookie names, the lifetime, the
claims.
