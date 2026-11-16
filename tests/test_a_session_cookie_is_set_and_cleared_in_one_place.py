"""
The session cookies are written by one set of functions, with the same flags
every time, and cleared with the flags they were written with.

If these fail, a script can read a token, a cookie travels over plain HTTP or
to another site, the access cookie dies with its token and leaves nothing to
renew from, or signing out leaves the session in the browser.
"""

from datetime import timedelta
from http.cookies import Morsel

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from rest_framework_simplejwt.settings import api_settings as simplejwt

from httponly_jwt.cookies import (
    clear_session_cookies,
    read_access_token,
    read_refresh_token,
    set_access_cookie,
    set_session_cookies,
)


def cookie(response: HttpResponse, name: str) -> Morsel[str]:
    assert name in response.cookies, f'{name} was not set'
    return response.cookies[name]


def test_both_tokens_are_set_where_no_script_can_read_them() -> None:
    response = set_session_cookies(HttpResponse(), access='A', refresh='R')

    for name, value in (('access_token', 'A'), ('refresh_token', 'R')):
        set_ = cookie(response, name)
        assert set_.value == value
        assert set_['httponly'] is True
        assert set_['secure'] is True
        assert set_['samesite'] == 'Lax'
        assert set_['path'] == '/'


def test_the_access_cookie_outlives_its_token() -> None:
    """It lasts as long as the refresh token, or the browser deletes it with nothing to renew."""
    response = set_session_cookies(HttpResponse(), access='A', refresh='R')
    lasts = int(simplejwt.REFRESH_TOKEN_LIFETIME.total_seconds())

    assert cookie(response, 'access_token')['max-age'] == lasts
    assert cookie(response, 'refresh_token')['max-age'] == lasts
    assert lasts > simplejwt.ACCESS_TOKEN_LIFETIME.total_seconds()


def test_a_session_lasts_what_the_project_says_for_this_person() -> None:
    response = set_session_cookies(
        HttpResponse(), access='A', refresh='R', lifetime=timedelta(hours=8)
    )

    assert cookie(response, 'access_token')['max-age'] == 8 * 3600
    assert cookie(response, 'refresh_token')['max-age'] == 8 * 3600


def test_a_renewal_replaces_the_access_cookie_alone() -> None:
    response = set_access_cookie(HttpResponse(), 'A2')

    assert cookie(response, 'access_token').value == 'A2'
    assert 'refresh_token' not in response.cookies


@override_settings(
    HTTPONLY_JWT={
        'ACCESS_COOKIE': 'a',
        'REFRESH_COOKIE': 'r',
        'COOKIE_DOMAIN': '.example.com',
        'COOKIE_PATH': '/api/',
        'COOKIE_SAMESITE': 'Strict',
        'COOKIE_SECURE': False,
    }
)
def test_names_and_flags_are_the_projects_to_choose() -> None:
    response = set_session_cookies(HttpResponse(), access='A', refresh='R')

    for name in ('a', 'r'):
        set_ = cookie(response, name)
        assert set_['domain'] == '.example.com'
        assert set_['path'] == '/api/'
        assert set_['samesite'] == 'Strict'
        assert set_['secure'] == ''
        assert set_['httponly'] is True, 'HttpOnly is never the project to turn off'


@pytest.mark.parametrize(
    'chosen',
    [
        {},
        {'COOKIE_DOMAIN': '.example.com', 'COOKIE_PATH': '/api/', 'COOKIE_SAMESITE': 'Strict'},
    ],
)
def test_signing_out_clears_the_cookies_with_the_flags_they_were_set_with(
    chosen: dict[str, str],
) -> None:
    """A browser keeps a cookie cleared with another path, domain or SameSite."""
    with override_settings(HTTPONLY_JWT=chosen):
        set_ = set_session_cookies(HttpResponse(), access='A', refresh='R')
        cleared = clear_session_cookies(HttpResponse())

    for name in ('access_token', 'refresh_token'):
        assert cookie(cleared, name).value == ''
        assert cookie(cleared, name)['max-age'] == 0
        for flag in ('path', 'domain', 'samesite'):
            assert cookie(cleared, name)[flag] == cookie(set_, name)[flag], flag


def test_the_tokens_are_read_back_by_name_and_are_empty_when_missing() -> None:
    request = RequestFactory().get('/', HTTP_COOKIE='access_token=A; refresh_token=R')
    nothing = RequestFactory().get('/')

    assert read_access_token(request) == 'A'
    assert read_refresh_token(request) == 'R'
    assert read_access_token(nothing) == ''
    assert read_refresh_token(nothing) == ''
