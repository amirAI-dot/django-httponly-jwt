"""
A session whose access token has run out is renewed by the server, on the way
through, and the request that found it out is served as if nothing happened.

If these fail, a person is signed out every hour while their refresh token has
weeks left; a browser that has deleted the expired cookie can never renew; an
account switched off keeps getting in until its refresh token expires; a
second tab signs the person out of the first; signing out is undone by the
renewal on the same response; or every request costs a database query.
"""

from collections.abc import Callable
from datetime import timedelta
from http.cookies import Morsel

import pytest
from asgiref.sync import async_to_sync, iscoroutinefunction
from django.contrib.auth.models import User
from django.db import connection
from django.test import AsyncClient, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from httponly_jwt.middleware import RenewalMiddleware
from tests.conftest import Access

pytestmark = pytest.mark.django_db

Refresh = Callable[[User], str]


def browser(**cookies: str) -> APIClient:
    client = APIClient()

    for name, value in cookies.items():
        client.cookies[name] = value

    return client


def cookie(response: object, name: str) -> Morsel[str] | None:
    return response.cookies.get(name)  # type: ignore[attr-defined]


def renewed(response: object) -> str:
    """The access token the response renewed, which must be a real one."""
    set_ = cookie(response, 'access_token')
    assert set_ is not None, 'no access cookie was renewed'
    assert set_.value, 'the renewed access cookie is empty'
    return set_.value


def cleared(response: object) -> bool:
    return all(
        (set_ := cookie(response, name)) is not None and set_['max-age'] == 0
        for name in ('access_token', 'refresh_token')
    )


# ---------------------------------------------------------------- renewing


def test_an_expired_access_token_is_renewed_and_the_request_served(
    person: User, access: Access, refresh: Refresh
) -> None:
    answer = browser(access_token=access(person, expired=True), refresh_token=refresh(person)).get(
        '/signed-in/'
    )

    assert answer.status_code == 200, 'the request that found it expired is served'
    assert answer.json() == {'person': 'ana'}
    assert renewed(answer) != ''
    assert cookie(answer, 'refresh_token') is None, 'the refresh token is not touched'


def test_a_session_is_renewed_when_the_browser_has_already_deleted_the_access_cookie(
    person: User, refresh: Refresh
) -> None:
    """The case the obvious guard - nothing to renew without an access cookie - breaks."""
    answer = browser(refresh_token=refresh(person)).get('/signed-in/')

    assert answer.status_code == 200
    assert answer.json() == {'person': 'ana'}
    assert renewed(answer)


def test_the_renewed_token_signs_the_next_request_in(
    person: User, access: Access, refresh: Refresh
) -> None:
    client = browser(access_token=access(person, expired=True), refresh_token=refresh(person))
    client.get('/signed-in/')

    again = client.get('/signed-in/')

    assert again.status_code == 200
    assert cookie(again, 'access_token') is None, 'a good token is not renewed again'


def test_a_renewed_cookie_lasts_no_longer_than_its_refresh_token(person: User) -> None:
    token = RefreshToken.for_user(person)
    token.set_exp(lifetime=timedelta(minutes=30))

    answer = browser(refresh_token=str(token)).get('/signed-in/')

    assert 0 < answer.cookies['access_token']['max-age'] <= 30 * 60


def test_two_tabs_renewing_together_both_stay_signed_in(person: User, refresh: Refresh) -> None:
    """No rotation in the middleware: neither renewal blacklists the other's token."""
    shared = refresh(person)

    first = browser(refresh_token=shared).get('/signed-in/')
    second = browser(refresh_token=shared).get('/signed-in/')

    assert first.status_code == second.status_code == 200
    assert renewed(first)
    assert renewed(second)


# ---------------------------------------------------------------- nothing to do


def test_a_good_access_token_costs_no_query_and_no_cookie(
    person: User, access: Access, refresh: Refresh
) -> None:
    good = browser(access_token=access(person), refresh_token=refresh(person))
    without_middleware = browser(access_token=access(person))

    with override_settings(MIDDLEWARE=[]), CaptureQueriesContext(connection) as alone:
        without_middleware.get('/signed-in/')
    with CaptureQueriesContext(connection) as through:
        answer = good.get('/signed-in/')

    assert answer.status_code == 200
    assert len(through) == len(alone), 'the middleware adds no query to a good session'
    assert cookie(answer, 'access_token') is None


def test_a_client_signed_in_by_header_is_left_alone(person: User, access: Access) -> None:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access(person)}')

    answer = client.get('/signed-in/')

    assert answer.status_code == 200
    assert answer.cookies == {}, 'no cookie set, and none cleared, for a client that has none'


def test_renewal_costs_two_queries_whether_the_token_was_revoked_and_the_person(
    person: User, refresh: Refresh
) -> None:
    with CaptureQueriesContext(connection) as plain:
        browser(access_token=str(RefreshToken.for_user(person).access_token)).get('/signed-in/')
    with CaptureQueriesContext(connection) as renewing:
        browser(refresh_token=refresh(person)).get('/signed-in/')

    assert len(renewing) == len(plain) + 2


# ---------------------------------------------------------------- the session is over


@pytest.mark.parametrize(
    'why',
    [
        'expired',
        'garbled',
        'an access token',
        'blacklisted',
        'names nobody',
        'gone',
        'switched off',
    ],
)
def test_a_session_that_is_over_is_cleared_and_nobody_is_signed_in(
    why: str, person: User, access: Access
) -> None:
    token = RefreshToken.for_user(person)

    if why == 'expired':
        token.set_exp(lifetime=-timedelta(seconds=1))
    if why == 'blacklisted':
        token.blacklist()
    if why == 'gone':
        person.delete()
    if why == 'switched off':
        person.is_active = False
        person.save()

    raw = {
        'garbled': 'not.a.token',
        'an access token': access(person),
        'names nobody': str(RefreshToken()),
    }.get(why, str(token))
    client = browser(access_token=access(person, expired=True), refresh_token=raw)

    answer = client.get('/signed-in/')

    assert answer.status_code == 401
    assert cleared(answer)


def can_sign_in(person: User) -> bool:
    return person.username != 'ana'


@override_settings(
    HTTPONLY_JWT={'USER_CAN_SIGN_IN': f'{__name__}.can_sign_in'},
)
def test_the_project_may_end_a_session_for_its_own_reasons(person: User, refresh: Refresh) -> None:
    answer = browser(refresh_token=refresh(person)).get('/signed-in/')

    assert answer.status_code == 401
    assert cleared(answer)


# ---------------------------------------------------------------- the view decides


def test_a_view_that_signs_in_keeps_its_own_cookies(access: Access, person: User) -> None:
    answer = browser(access_token=access(person, expired=True), refresh_token='not.a.token').get(
        '/sets-session/'
    )

    assert answer.cookies['access_token'].value == 'chosen-access'
    assert answer.cookies['refresh_token'].value == 'chosen-refresh'


def test_a_view_that_signs_out_is_not_undone_by_a_renewal(
    person: User, access: Access, refresh: Refresh
) -> None:
    answer = browser(access_token=access(person, expired=True), refresh_token=refresh(person)).get(
        '/clears-session/'
    )

    assert cleared(answer), 'the renewal does not set the access cookie again'


@override_settings(HTTPONLY_JWT={'ACCESS_COOKIE': 'a', 'REFRESH_COOKIE': 'r'})
def test_renewal_reads_and_writes_the_names_the_project_chose(
    person: User, refresh: Refresh
) -> None:
    answer = browser(r=refresh(person)).get('/signed-in/')

    assert answer.status_code == 200
    assert answer.cookies['a'].value


# ---------------------------------------------------------------- async


def test_under_asgi_the_middleware_is_async(person: User, refresh: Refresh) -> None:
    async def view(request: object) -> object:
        return None

    assert iscoroutinefunction(RenewalMiddleware(view))

    client = AsyncClient()
    client.cookies['refresh_token'] = refresh(person)
    answer = async_to_sync(client.get)('/signed-in/')

    assert answer.status_code == 200
    assert renewed(answer)
