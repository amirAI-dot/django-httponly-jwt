"""
The ``HTTPONLY_JWT`` setting, read and checked.

Every key lives in one dictionary in the project's settings, and the default
needs none of them::

    HTTPONLY_JWT = {
        'COOKIE_DOMAIN': '.example.com',
    }

A key the library does not know is refused rather than ignored: a misspelled
``COOKIE_SAMESIT`` that is quietly ignored is a cookie with flags nobody chose,
and nobody can tell why. The refusal is a system check (``httponly_jwt.E003``),
so the project does not start with it.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final, Literal, cast

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

#: Every key the setting may hold, and what it is when left out.
DEFAULTS: Final[Mapping[str, object]] = MappingProxyType(
    {
        'ACCESS_COOKIE': 'access_token',
        'REFRESH_COOKIE': 'refresh_token',
        'COOKIE_DOMAIN': None,
        'COOKIE_PATH': '/',
        'COOKIE_SAMESITE': 'Lax',
        'COOKIE_SECURE': True,
        'CSRF': False,
        'REFRESH_LIFETIME': None,
        'CLAIMS': None,
        'USER_CAN_SIGN_IN': None,
        'ALLOW_WITHOUT_BLACKLIST': False,
    }
)

#: The values ``COOKIE_SAMESITE`` may take, as the browser spells them.
SameSite = Literal['Lax', 'Strict', 'None']
SAMESITE: Final = ('Lax', 'Strict', 'None')

#: The keys that name a function by its dotted path.
_CALLABLES: Final = ('REFRESH_LIFETIME', 'CLAIMS', 'USER_CAN_SIGN_IN')
_FLAGS: Final = ('COOKIE_SECURE', 'CSRF', 'ALLOW_WITHOUT_BLACKLIST')
_NAMES: Final = ('ACCESS_COOKIE', 'REFRESH_COOKIE')


class HttpOnlyJWTSettings:
    """The project's ``HTTPONLY_JWT`` setting, with defaults."""

    def raw(self) -> Mapping[str, Any]:
        """The setting as written, or ``ImproperlyConfigured`` naming what is wrong."""
        raw = getattr(settings, 'HTTPONLY_JWT', {})

        if not isinstance(raw, Mapping):
            raise ImproperlyConfigured('HTTPONLY_JWT must be a dictionary.')

        problems = list(problems_of(raw))

        if problems:
            raise ImproperlyConfigured(' '.join(problems))

        return raw

    def value(self, key: str) -> Any:
        """``key`` as the project set it, or its default."""
        return self.raw().get(key, DEFAULTS[key])

    @property
    def access_cookie(self) -> str:
        return str(self.value('ACCESS_COOKIE'))

    @property
    def refresh_cookie(self) -> str:
        return str(self.value('REFRESH_COOKIE'))

    @property
    def cookie_domain(self) -> str | None:
        domain = self.value('COOKIE_DOMAIN')
        return None if domain is None else str(domain)

    @property
    def cookie_path(self) -> str:
        return str(self.value('COOKIE_PATH'))

    @property
    def cookie_samesite(self) -> SameSite:
        return cast(SameSite, self.value('COOKIE_SAMESITE'))  # raw() refuses any other

    @property
    def cookie_secure(self) -> bool:
        return bool(self.value('COOKIE_SECURE'))

    @property
    def csrf(self) -> bool:
        return bool(self.value('CSRF'))

    @property
    def allow_without_blacklist(self) -> bool:
        return bool(self.value('ALLOW_WITHOUT_BLACKLIST'))


def problems_of(raw: Mapping[str, Any]) -> list[str]:
    """Everything wrong with ``raw``, each in a sentence; nothing when it is sound."""
    unknown = sorted(set(raw) - set(DEFAULTS))

    if unknown:
        return [
            f'HTTPONLY_JWT has keys the library does not know: {", ".join(unknown)}. '
            f'It knows {", ".join(DEFAULTS)}.'
        ]

    merged = {**DEFAULTS, **raw}
    problems = []

    for key in _NAMES:
        if not isinstance(merged[key], str) or not merged[key]:
            problems.append(f'HTTPONLY_JWT[{key!r}] must be a cookie name, not {merged[key]!r}.')

    if not problems and merged['ACCESS_COOKIE'] == merged['REFRESH_COOKIE']:
        problems.append(
            "HTTPONLY_JWT['ACCESS_COOKIE'] and ['REFRESH_COOKIE'] are the same name: "
            'the two tokens would overwrite each other.'
        )

    if merged['COOKIE_DOMAIN'] is not None and not isinstance(merged['COOKIE_DOMAIN'], str):
        problems.append(
            f"HTTPONLY_JWT['COOKIE_DOMAIN'] must be a domain or None, "
            f'not {merged["COOKIE_DOMAIN"]!r}.'
        )

    path = merged['COOKIE_PATH']

    if not isinstance(path, str) or not path.startswith('/'):
        problems.append(f"HTTPONLY_JWT['COOKIE_PATH'] must start with '/', not {path!r}.")

    if merged['COOKIE_SAMESITE'] not in SAMESITE:
        problems.append(
            f"HTTPONLY_JWT['COOKIE_SAMESITE'] must be one of {', '.join(SAMESITE)}, "
            f'not {merged["COOKIE_SAMESITE"]!r}.'
        )

    for key in _FLAGS:
        if not isinstance(merged[key], bool):
            problems.append(f'HTTPONLY_JWT[{key!r}] must be True or False, not {merged[key]!r}.')

    for key in _CALLABLES:
        problems.extend(_callable_problems(key, merged[key]))

    return problems


def _callable_problems(key: str, path: object) -> list[str]:
    if path is None:
        return []

    if not isinstance(path, str):
        return [f'HTTPONLY_JWT[{key!r}] must be the dotted path of a function, not {path!r}.']

    try:
        found = import_string(path)
    except ImportError:
        return [f'HTTPONLY_JWT[{key!r}] names {path!r}, which cannot be imported.']

    if not callable(found):
        return [f'HTTPONLY_JWT[{key!r}] names {path!r}, which is not a function.']

    return []


#: The project's settings, as the library reads them.
httponly_jwt_settings = HttpOnlyJWTSettings()
