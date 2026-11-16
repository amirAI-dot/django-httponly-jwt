"""
The generated schema - what a frontend is built against - says how each
endpoint is signed in to and what the session endpoints answer.

If these fail, drf-spectacular warns it cannot resolve the library's classes
and every endpoint is documented as open to anybody; a project that lists
simplejwt's own class beside the library's gets two bearer schemes that
disagree; the optional class reads as needing a sign-in; the refresh endpoint
is documented as handing a browser its tokens in the body; or a project that
renamed its cookie is documented with the old name.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from django.test import override_settings
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator

COOKIE = {'httponlyJwtCookie': []}
HEADER = {'jwtAuth': []}
NOBODY: dict[str, list[Any]] = {}


@pytest.fixture
def warned() -> Iterator[list[str]]:
    """What spectacular warned of about the library's classes and views."""
    GENERATOR_STATS.reset()
    said: list[str] = []
    yield said
    GENERATOR_STATS.reset()


def schema(warned: list[str]) -> dict[str, Any]:
    generated = SchemaGenerator().get_schema(request=None, public=True)
    said = [*GENERATOR_STATS._warn_cache, *GENERATOR_STATS._error_cache]
    # The test project's own pages have no serializers; that is theirs to say.
    warned.extend(line for line in said if 'unable to guess serializer' not in line)
    return generated


def operation(generated: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    found: dict[str, Any] = generated['paths'][path][method]
    return found


def test_the_library_is_described_without_a_warning(warned: list[str]) -> None:
    schema(warned)

    assert warned == []


def test_the_cookie_and_the_header_are_schemes(warned: list[str]) -> None:
    schemes = schema(warned)['components']['securitySchemes']

    assert schemes['httponlyJwtCookie'] == {
        'type': 'apiKey',
        'in': 'cookie',
        'name': 'access_token',
        'description': schemes['httponlyJwtCookie']['description'],
    }
    assert schemes['jwtAuth'] == {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}


def test_a_page_that_needs_somebody_is_signed_in_to_by_either(warned: list[str]) -> None:
    assert operation(schema(warned), '/signed-in/', 'get')['security'] == [COOKIE, HEADER]


def test_an_optional_page_is_either_or_nobody(warned: list[str]) -> None:
    security = operation(schema(warned), '/anybody-more/', 'get')['security']

    assert security == [COOKIE, HEADER, NOBODY]


def test_the_refresh_endpoint_says_a_browser_gets_cookies_and_an_app_the_pair(
    warned: list[str],
) -> None:
    refresh = operation(schema(warned), '/auth/refresh/', 'post')

    assert set(refresh['responses']) == {'200', '204', '401', '403'}
    assert 'content' not in refresh['responses']['204'], 'no token in a body for a browser'
    assert [p['name'] for p in refresh['parameters']] == ['refresh_token']
    assert refresh['parameters'][0]['in'] == 'cookie'
    assert refresh['security'] == [NOBODY], 'the refresh token is the credential'


def test_signing_out_and_the_csrf_token_are_described(warned: list[str]) -> None:
    generated = schema(warned)

    assert set(operation(generated, '/auth/sign-out/', 'post')['responses']) == {'204', '403'}
    csrf = operation(generated, '/auth/csrf/', 'get')['responses']['200']
    assert csrf['content']['application/json']['schema'] == {
        '$ref': '#/components/schemas/HttpOnlyJWTCsrfToken'
    }


@override_settings(HTTPONLY_JWT={'ACCESS_COOKIE': 'a', 'REFRESH_COOKIE': 'r'})
def test_the_names_the_project_chose_are_the_names_documented(warned: list[str]) -> None:
    generated = schema(warned)

    assert generated['components']['securitySchemes']['httponlyJwtCookie']['name'] == 'a'
    assert operation(generated, '/auth/refresh/', 'post')['parameters'][0]['name'] == 'r'


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'httponly_jwt.authentication.CookieAuthentication',
            'httponly_jwt.authentication.HeaderAuthentication',
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ],
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    }
)
def test_simplejwt_s_own_class_beside_the_library_s_is_one_scheme(warned: list[str]) -> None:
    generated = schema(warned)

    assert warned == []
    assert operation(generated, '/signed-in/', 'get')['security'] == [COOKIE, HEADER]


def test_without_drf_spectacular_the_app_starts_and_describes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The extra is optional: the app must not import what is not installed."""
    import sys

    from django.apps import apps

    monkeypatch.setattr('httponly_jwt.apps.find_spec', lambda name: None)
    monkeypatch.delitem(sys.modules, 'httponly_jwt.schema')

    apps.get_app_config('httponly_jwt').ready()

    assert 'httponly_jwt.schema' not in sys.modules
