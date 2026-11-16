"""
What cannot work, or would leave a session exposed, stops the project at
start-up - Django's system checks - rather than on the day it is found.

If these fail, a misspelled setting is quietly ignored and the cookies get
flags nobody chose, two cookies share a name and overwrite each other's
token, signing out cannot end a refresh token, or a deployment sends the
session over plain HTTP without a word.
"""

from typing import Any

import pytest
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from httponly_jwt.authentication import CookieAuthentication
from httponly_jwt.conf import DEFAULTS, httponly_jwt_settings
from httponly_jwt.middleware import RenewalMiddleware


def ids(**settings: Any) -> list[str]:
    """The library's check ids a project with ``settings`` fails, deploy checks too."""
    with override_settings(**settings):
        return sorted(
            message.id
            for message in run_checks(include_deployment_checks=True)
            if message.id and message.id.startswith('httponly_jwt.')
        )


def test_the_default_needs_no_setting_at_all() -> None:
    assert ids() == []
    assert httponly_jwt_settings.access_cookie == 'access_token'
    assert httponly_jwt_settings.refresh_cookie == 'refresh_token'
    assert httponly_jwt_settings.cookie_samesite == 'Lax'
    assert httponly_jwt_settings.cookie_secure is True


@pytest.mark.parametrize(
    'setting',
    [
        ['not', 'a', 'dictionary'],
        {'COOKIE_SAMESIT': 'Lax'},
        {'ACCESS_COOKIE': ''},
        {'REFRESH_COOKIE': 7},
        {'ACCESS_COOKIE': 'token', 'REFRESH_COOKIE': 'token'},
        {'COOKIE_DOMAIN': 42},
        {'COOKIE_PATH': 'api/'},
        {'COOKIE_SAMESITE': 'lax'},
        {'COOKIE_SECURE': 'yes'},
        {'CSRF': 1},
        {'ALLOW_WITHOUT_BLACKLIST': None},
        {'CLAIMS': 42},
        {'REFRESH_LIFETIME': 'nowhere.to.be.found'},
        {'USER_CAN_SIGN_IN': 'httponly_jwt.conf.DEFAULTS'},
    ],
    ids=lambda setting: repr(setting)[:40],
)
def test_a_setting_that_cannot_be_used_is_refused_and_named(setting: Any) -> None:
    assert ids(HTTPONLY_JWT=setting) == ['httponly_jwt.E003']

    with override_settings(HTTPONLY_JWT=setting), pytest.raises(ImproperlyConfigured):
        httponly_jwt_settings.raw()


def test_the_refusal_says_which_keys_the_library_knows() -> None:
    with (
        override_settings(HTTPONLY_JWT={'COOKIE_SAMESIT': 'Lax'}),
        pytest.raises(ImproperlyConfigured) as refused,
    ):
        httponly_jwt_settings.raw()

    assert 'COOKIE_SAMESIT' in str(refused.value)
    assert 'COOKIE_SAMESITE' in str(refused.value)


def test_a_function_named_by_its_path_is_accepted() -> None:
    assert ids(HTTPONLY_JWT={'CLAIMS': 'django.utils.timezone.now'}) == []


def test_every_key_has_a_default() -> None:
    assert ids(HTTPONLY_JWT=dict(DEFAULTS)) == []


BLACKLIST = 'rest_framework_simplejwt.token_blacklist'


def without_blacklist() -> list[str]:
    from django.conf import settings

    return [app for app in settings.INSTALLED_APPS if app != BLACKLIST]


def test_without_the_blacklist_signing_out_could_not_end_a_token() -> None:
    assert ids(INSTALLED_APPS=without_blacklist()) == ['httponly_jwt.E004']


def test_a_project_may_accept_running_without_the_blacklist_by_saying_so() -> None:
    allowed = {'ALLOW_WITHOUT_BLACKLIST': True}

    assert ids(INSTALLED_APPS=without_blacklist(), HTTPONLY_JWT=allowed) == []


def test_cookies_sent_over_plain_http_are_a_warning_on_deploy() -> None:
    assert ids(HTTPONLY_JWT={'COOKIE_SECURE': False}) == ['httponly_jwt.W001']

    with override_settings(HTTPONLY_JWT={'COOKIE_SECURE': False}):
        everyday = [m.id for m in run_checks() if m.id and m.id.startswith('httponly_jwt.')]

    assert everyday == [], 'only check --deploy says it: a laptop serves plain HTTP'


def test_a_broken_setting_is_reported_once_not_by_every_check() -> None:
    assert ids(HTTPONLY_JWT={'COOKIE_SECURE': 'no'}, INSTALLED_APPS=without_blacklist()) == [
        'httponly_jwt.E003'
    ]


COOKIE = 'httponly_jwt.authentication.CookieAuthentication'
OPTIONAL = 'httponly_jwt.authentication.OptionalAuthentication'
HEADER = 'httponly_jwt.authentication.HeaderAuthentication'
RENEWAL = 'httponly_jwt.middleware.RenewalMiddleware'


def reading(*classes: str) -> dict[str, list[str]]:
    return {'DEFAULT_AUTHENTICATION_CLASSES': list(classes)}


@pytest.mark.parametrize('reader', [COOKIE, OPTIONAL])
def test_a_session_read_from_the_cookie_with_no_renewal_is_refused(reader: str) -> None:
    """Every session would end with its first access token, an hour after signing in."""
    assert ids(REST_FRAMEWORK=reading(reader), MIDDLEWARE=[]) == ['httponly_jwt.E002']
    assert ids(REST_FRAMEWORK=reading(reader), MIDDLEWARE=[RENEWAL]) == []


def test_a_project_reading_only_the_header_needs_no_renewal() -> None:
    assert ids(REST_FRAMEWORK=reading(HEADER), MIDDLEWARE=[]) == []
    assert ids(REST_FRAMEWORK={}, MIDDLEWARE=[]) == []


def test_classes_built_on_the_librarys_are_recognised() -> None:
    own_reader = f'{__name__}.OwnCookie'
    own_renewal = f'{__name__}.OwnRenewal'

    assert ids(REST_FRAMEWORK=reading(own_reader), MIDDLEWARE=[]) == ['httponly_jwt.E002']
    assert ids(REST_FRAMEWORK=reading(own_reader), MIDDLEWARE=[own_renewal]) == []


def test_a_class_that_cannot_be_imported_is_left_to_django_and_drf() -> None:
    assert ids(REST_FRAMEWORK=reading('nowhere.Auth'), MIDDLEWARE=['nowhere.Middleware']) == []


class OwnCookie(CookieAuthentication):
    """A project's own class, built on the library's."""


class OwnRenewal(RenewalMiddleware):
    """A project's own middleware, built on the library's."""


# ---------------------------------------------------------------- a frontend on another site

CROSS_SITE_CSRF = {
    'CSRF_COOKIE_SAMESITE': 'None',
    'CSRF_COOKIE_SECURE': True,
    'CSRF_TRUSTED_ORIGINS': ['https://app.example.org'],
}


def test_a_cookie_every_site_s_requests_carry_needs_the_csrf_check() -> None:
    """The one combination that protects nothing."""
    assert ids(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None'}) == ['httponly_jwt.E001']


def test_a_cross_site_cookie_with_the_check_and_django_s_settings_is_accepted() -> None:
    assert ids(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None', 'CSRF': True}, **CROSS_SITE_CSRF) == []


@pytest.mark.parametrize('samesite', ['Lax', 'Strict'])
def test_a_same_site_cookie_needs_no_check_and_may_have_one(samesite: str) -> None:
    assert ids(HTTPONLY_JWT={'COOKIE_SAMESITE': samesite}) == []
    assert ids(HTTPONLY_JWT={'COOKIE_SAMESITE': samesite, 'CSRF': True}) == []


def test_a_cross_site_cookie_that_is_not_secure_is_refused() -> None:
    """Browsers drop SameSite=None without Secure: nobody could stay signed in."""
    setting = {'COOKIE_SAMESITE': 'None', 'CSRF': True, 'COOKIE_SECURE': False}

    assert ids(HTTPONLY_JWT=setting, **CROSS_SITE_CSRF) == [
        'httponly_jwt.E005',
        'httponly_jwt.W001',
    ]


def test_both_are_said_when_both_are_wrong() -> None:
    setting = {'COOKIE_SAMESITE': 'None', 'COOKIE_SECURE': False}

    assert ids(HTTPONLY_JWT=setting) == [
        'httponly_jwt.E001',
        'httponly_jwt.E005',
        'httponly_jwt.W001',
    ]


@pytest.mark.parametrize(
    ('setting', 'said'),
    [
        ('CSRF_COOKIE_SAMESITE', 'Lax'),
        ('CSRF_COOKIE_SECURE', False),
        ('CSRF_TRUSTED_ORIGINS', []),
    ],
)
def test_django_s_csrf_settings_that_would_refuse_every_write_are_named(
    setting: str, said: Any
) -> None:
    django = {**CROSS_SITE_CSRF, setting: said}
    with override_settings(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None', 'CSRF': True}, **django):
        messages = [m for m in run_checks() if m.id == 'httponly_jwt.W002']

    assert len(messages) == 1
    assert setting in messages[0].msg


def test_a_broken_setting_is_not_also_reported_as_cross_site() -> None:
    assert ids(HTTPONLY_JWT={'COOKIE_SAMESITE': 'None', 'CSRF': 'yes'}) == ['httponly_jwt.E003']
