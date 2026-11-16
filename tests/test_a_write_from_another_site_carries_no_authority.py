"""
A request another site causes carries the person's cookie, and must not carry
their authority.

If these fail, the default asks a same-site frontend for a CSRF token it has
no way to need; a frontend on another site, with the check on, has its
session used by any page the person visits - to write, to rotate their
session or to sign them out; a guest is refused for a cookie they did not
choose to send; or a header-signed client, which no site can forge, is asked
for a token it has no cookie for.
"""

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.conftest import Access

pytestmark = pytest.mark.django_db

CROSS_SITE = {'COOKIE_SAMESITE': 'None', 'CSRF': True}
csrf_on = override_settings(HTTPONLY_JWT=CROSS_SITE)


def another_site(**cookies: str) -> APIClient:
    """A browser that sends the cookies and no CSRF token - what a forged request is."""
    client = APIClient(enforce_csrf_checks=True)

    for name, value in cookies.items():
        client.cookies[name] = value

    return client


def the_frontend(**cookies: str) -> tuple[APIClient, dict[str, str]]:
    """The person's own frontend: it asked for the token first, and sends it back."""
    client = another_site(**cookies)
    token = client.get('/auth/csrf/').json()['csrf_token']
    return client, {'HTTP_X_CSRFTOKEN': token}


# ---------------------------------------------------------------- the default


def test_by_default_a_same_site_frontend_needs_no_csrf_token(person: User, access: Access) -> None:
    answer = another_site(access_token=access(person)).post('/writes/')

    assert answer.status_code == 200
    assert answer.json() == {'person': 'ana'}


# ---------------------------------------------------------------- the check on


@csrf_on
def test_a_cookie_write_without_the_token_is_refused(person: User, access: Access) -> None:
    answer = another_site(access_token=access(person)).post('/writes/')

    assert answer.status_code == 403
    assert 'CSRF' in answer.json()['detail']


@csrf_on
def test_a_cookie_write_with_the_token_is_served(person: User, access: Access) -> None:
    client, token = the_frontend(access_token=access(person))

    answer = client.post('/writes/', **token)

    assert answer.status_code == 200
    assert answer.json() == {'person': 'ana'}


@csrf_on
def test_reading_needs_no_token(person: User, access: Access) -> None:
    assert another_site(access_token=access(person)).get('/signed-in/').status_code == 200


@csrf_on
def test_a_header_write_needs_no_token(person: User, access: Access) -> None:
    client = APIClient(enforce_csrf_checks=True)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access(person)}')

    assert client.post('/writes/').status_code == 200


@csrf_on
def test_a_stale_cookie_is_nobody_not_a_csrf_failure(person: User, access: Access) -> None:
    answer = another_site(access_token=access(person, expired=True)).post('/writes/')

    assert answer.status_code == 401


@csrf_on
def test_an_optional_page_serves_a_cookie_write_without_the_token_as_a_guest(
    person: User, access: Access
) -> None:
    answer = another_site(access_token=access(person)).post('/anybody-more/')

    assert answer.status_code == 200
    assert answer.json() == {'person': None}


@csrf_on
def test_the_token_view_sets_the_cookie_the_token_belongs_with() -> None:
    answer = another_site().get('/auth/csrf/')

    assert answer.json()['csrf_token']
    assert answer.cookies['csrftoken'].value


# ---------------------------------------------------------------- the session views


def still_good(raw: str) -> bool:
    try:
        RefreshToken(raw)  # type: ignore[arg-type]
    except Exception:
        return False

    return True


@csrf_on
@pytest.mark.parametrize('endpoint', ['/auth/refresh/', '/auth/sign-out/'])
def test_another_site_cannot_rotate_or_end_the_session(endpoint: str, person: User) -> None:
    raw = str(RefreshToken.for_user(person))

    answer = another_site(refresh_token=raw).post(endpoint)

    assert answer.status_code == 403
    assert 'refresh_token' not in answer.cookies
    assert still_good(raw), 'the session is exactly as it was'


@csrf_on
@pytest.mark.parametrize('endpoint', ['/auth/refresh/', '/auth/sign-out/'])
def test_the_frontend_with_the_token_rotates_and_ends_it(endpoint: str, person: User) -> None:
    raw = str(RefreshToken.for_user(person))
    client, token = the_frontend(refresh_token=raw)

    answer = client.post(endpoint, **token)

    assert answer.status_code == 204
    assert not still_good(raw)


@csrf_on
def test_a_native_refresh_by_the_body_needs_no_token(person: User) -> None:
    body: dict[str, Any] = {'refresh': str(RefreshToken.for_user(person))}

    answer = APIClient(enforce_csrf_checks=True).post('/auth/refresh/', body, format='json')

    assert answer.status_code == 200
