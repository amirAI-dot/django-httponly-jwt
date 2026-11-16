"""
A browser is known by its access cookie, an app by its header, and an
endpoint anybody may call knows the person when there is one.

If these fail, a signed-in person is a stranger, a refresh token passes for
an access token, an account switched off still gets in, or a guest is turned
away from a public page because their browser still holds yesterday's cookie.
"""

from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient

from tests.conftest import Access

pytestmark = pytest.mark.django_db


def browser(**cookies: str) -> APIClient:
    client = APIClient()

    for name, value in cookies.items():
        client.cookies[name] = value

    return client


def app(token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


# ---------------------------------------------------------------- the cookie


def test_a_browser_is_the_person_its_access_cookie_names(person: User, access: Access) -> None:
    answer = browser(access_token=access(person)).get('/signed-in/')

    assert answer.status_code == 200
    assert answer.json() == {'person': 'ana'}


def test_a_browser_with_no_cookie_is_asked_to_sign_in() -> None:
    answer = browser().get('/signed-in/')

    assert answer.status_code == 401, 'a 401 - sign in - not a 403'


@pytest.mark.parametrize(
    'stale',
    ['expired', 'garbled', 'a refresh token', 'the account is gone', 'the account is off'],
)
def test_a_cookie_that_names_no_usable_session_is_nobody(
    stale: str, person: User, access: Access, refresh: Callable[[User], str]
) -> None:
    """Asked to sign in where somebody is needed, and served as a guest where nobody is."""
    token = {
        'expired': lambda: access(person, expired=True),
        'garbled': lambda: 'not.a.token',
        'a refresh token': lambda: refresh(person),
        'the account is gone': lambda: access(person),
        'the account is off': lambda: access(person),
    }[stale]()

    if stale == 'the account is gone':
        person.delete()
    if stale == 'the account is off':
        person.is_active = False
        person.save()

    client = browser(access_token=token)

    assert client.get('/signed-in/').status_code == 401
    public = client.get('/anybody/')
    assert public.status_code == 200, 'a stale cookie does not turn a guest away'
    assert public.json() == {'person': None}


@override_settings(HTTPONLY_JWT={'ACCESS_COOKIE': 'a'})
def test_the_cookie_is_read_by_the_name_the_project_chose(person: User, access: Access) -> None:
    assert browser(a=access(person)).get('/signed-in/').json() == {'person': 'ana'}
    assert browser(access_token=access(person)).get('/signed-in/').status_code == 401


# ---------------------------------------------------------------- the header


def test_an_app_is_the_person_its_header_names(person: User, access: Access) -> None:
    answer = app(access(person)).get('/signed-in/')

    assert answer.status_code == 200
    assert answer.json() == {'person': 'ana'}


def test_an_app_sending_a_bad_token_is_told_so(person: User, access: Access) -> None:
    """A header is set on purpose: a bad one is refused, not taken for a guest."""
    for token in (access(person, expired=True), 'not.a.token'):
        assert app(token).get('/anybody/').status_code == 401


# ---------------------------------------------------------------- optional


def test_an_open_endpoint_knows_the_person_by_cookie_or_header(
    person: User, access: Access
) -> None:
    assert browser(access_token=access(person)).get('/anybody-more/').json() == {'person': 'ana'}
    assert app(access(person)).get('/anybody-more/').json() == {'person': 'ana'}


def test_an_open_endpoint_never_turns_a_guest_away(person: User, access: Access) -> None:
    """Not for a stale cookie, and not for a stale header either."""
    for client in (
        browser(),
        browser(access_token=access(person, expired=True)),
        app(access(person, expired=True)),
        app('not.a.token'),
    ):
        answer = client.get('/anybody-more/')
        assert answer.status_code == 200
        assert answer.json() == {'person': None}
