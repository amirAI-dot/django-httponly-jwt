"""
What cannot work, refused when the project starts - ``manage.py check``.

* ``httponly_jwt.E002`` - the cookie authenticates, and ``RenewalMiddleware``
  is not installed: every session would end with its first access token;
* ``httponly_jwt.E003`` - ``HTTPONLY_JWT`` is not a dictionary, has a key the
  library does not know, or a value it cannot use;
* ``httponly_jwt.E004`` - simplejwt's ``token_blacklist`` is not installed:
  rotation and signing out could not end a token;
* ``httponly_jwt.W001`` - the cookies are not ``Secure``, on ``check --deploy``.

E001 (``SameSite=None`` with no CSRF check) comes with the CSRF mode: each
check arrives with what it guards.
"""

from collections.abc import Mapping
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, Tags, Warning, register
from django.utils.module_loading import import_string

from httponly_jwt.conf import httponly_jwt_settings, problems_of

BLACKLIST_APP = 'rest_framework_simplejwt.token_blacklist'
COOKIE_READERS = (
    'httponly_jwt.authentication.CookieAuthentication',
    'httponly_jwt.authentication.OptionalAuthentication',
)
RENEWAL = 'httponly_jwt.middleware.RenewalMiddleware'


@register(Tags.security)
def check_settings(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """E003: the setting is a dictionary of known keys and usable values."""
    raw = getattr(settings, 'HTTPONLY_JWT', {})

    if not isinstance(raw, Mapping):
        return [Error('HTTPONLY_JWT must be a dictionary.', id='httponly_jwt.E003')]

    return [Error(problem, id='httponly_jwt.E003') for problem in problems_of(raw)]


@register(Tags.security)
def check_blacklist(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """E004: signing out and rotation end a token only when it can be blacklisted."""
    if check_settings() or apps.is_installed(BLACKLIST_APP):
        return []

    if httponly_jwt_settings.allow_without_blacklist:
        return []

    return [
        Error(
            f'{BLACKLIST_APP!r} is not in INSTALLED_APPS: signing out could not end a '
            'refresh token, and a stolen one would work until it expired.',
            hint=(
                f'Add {BLACKLIST_APP!r} to INSTALLED_APPS, or set '
                "HTTPONLY_JWT['ALLOW_WITHOUT_BLACKLIST'] to True to accept that."
            ),
            id='httponly_jwt.E004',
        )
    ]


@register(Tags.security, deploy=True)
def check_secure(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """W001: on deploy, the cookies are only sent over HTTPS."""
    if check_settings() or httponly_jwt_settings.cookie_secure:
        return []

    return [
        Warning(
            "HTTPONLY_JWT['COOKIE_SECURE'] is False: the session cookies would be sent "
            'over plain HTTP, where anybody on the network can read them.',
            id='httponly_jwt.W001',
        )
    ]


@register(Tags.security)
def check_renewal(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """E002: a session read from the cookie is renewed, or it ends within the hour."""
    rest = getattr(settings, 'REST_FRAMEWORK', {}) or {}
    reading = rest.get('DEFAULT_AUTHENTICATION_CLASSES', ())

    if not any(_is(path, COOKIE_READERS) for path in reading):
        return []

    if any(_is(path, (RENEWAL,)) for path in getattr(settings, 'MIDDLEWARE', ())):
        return []

    return [
        Error(
            'The session is read from the cookie, and RenewalMiddleware is not in '
            'MIDDLEWARE: every session would end with its first access token.',
            hint=f'Add {RENEWAL!r} to MIDDLEWARE.',
            id='httponly_jwt.E002',
        )
    ]


def _is(path: str, wanted: tuple[str, ...]) -> bool:
    """Whether the class at ``path`` is one of ``wanted``, or built on one."""
    if path in wanted:
        return True

    try:
        found = import_string(path)
    except ImportError:
        return False  # Django and DRF say so themselves

    bases = {f'{base.__module__}.{base.__qualname__}' for base in getattr(found, '__mro__', ())}
    return bool(bases & set(wanted))
