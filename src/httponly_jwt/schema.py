"""
The library in a drf-spectacular schema - loaded only when drf-spectacular is installed.

Without it, spectacular warns that it cannot resolve the library's classes and
leaves every endpoint without a word about how it is signed in to. With it:

* ``CookieAuthentication`` is an ``apiKey`` in the access cookie, under the
  name the project chose;
* ``HeaderAuthentication`` is simplejwt's bearer scheme, ``jwtAuth``, so a
  project that lists simplejwt's own class too sees one scheme, not two;
* ``OptionalAuthentication`` is either of the two, or nobody;
* the refresh, sign-out and CSRF-token views say what they read and answer,
  including that a browser is never handed a token in a body.

Nothing to install beyond the package's extra::

    pip install "django-httponly-jwt[spectacular]"
"""

from typing import Any

from django.utils.translation import gettext_lazy as _
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.drainage import set_override
from drf_spectacular.extensions import OpenApiAuthenticationExtension, OpenApiViewExtension
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers

from httponly_jwt.authentication import HeaderAuthentication, OptionalAuthentication
from httponly_jwt.conf import httponly_jwt_settings as conf

COOKIE_SCHEME = 'httponlyJwtCookie'
HEADER_SCHEME = SimpleJWTScheme.name


def cookie_definition() -> dict[str, Any]:
    return {
        'type': 'apiKey',
        'in': 'cookie',
        'name': conf.access_cookie,
        'description': str(
            _(
                'The access token, in an HttpOnly cookie the browser sends by itself. '
                'Signing in sets it; the server renews it on the way through.'
            )
        ),
    }


class CookieScheme(OpenApiAuthenticationExtension):
    target_class = 'httponly_jwt.authentication.CookieAuthentication'
    match_subclasses = True
    name = COOKIE_SCHEME

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return cookie_definition()


class HeaderScheme(SimpleJWTScheme):
    target_class = 'httponly_jwt.authentication.HeaderAuthentication'
    match_subclasses = True


class OptionalScheme(OpenApiAuthenticationExtension):
    target_class = 'httponly_jwt.authentication.OptionalAuthentication'
    match_subclasses = True
    name = [COOKIE_SCHEME, HEADER_SCHEME]  # noqa: RUF012 - spectacular's own attribute

    def get_security_requirement(self, auto_schema: Any) -> list[dict[str, list[Any]]]:
        # Either one - not both. Nobody, too, is the permission's to say.
        return [{COOKIE_SCHEME: []}, {HEADER_SCHEME: []}]

    def get_security_definition(self, auto_schema: Any) -> list[dict[str, Any]]:
        header = HeaderScheme(self.target).get_security_definition(auto_schema)
        return [cookie_definition(), header]


# The same two schemes, described by more than one class: one definition, no warning.
set_override(OptionalAuthentication, 'suppress_collision_warning', True)
set_override(HeaderAuthentication, 'suppress_collision_warning', True)


# ---------------------------------------------------------------- the session views


def refresh_cookie() -> OpenApiParameter:
    return OpenApiParameter(
        conf.refresh_cookie,
        str,
        OpenApiParameter.COOKIE,
        required=False,
        description=_("A browser's refresh token. Read before the body."),
    )


#: One serializer each, shared by every view that names it: a component is one class.
REFRESH_BODY = inline_serializer(
    'HttpOnlyJWTRefreshRequest',
    {
        'refresh': serializers.CharField(
            required=False,
            help_text=_("A native client's refresh token, when there is no cookie."),
        )
    },
)
PAIR = inline_serializer(
    'HttpOnlyJWTTokenPair',
    {'access': serializers.CharField(), 'refresh': serializers.CharField()},
)
ENDED = inline_serializer(
    'HttpOnlyJWTSessionEnded',
    {'detail': serializers.CharField(), 'code': serializers.CharField()},
)
CSRF_TOKEN = inline_serializer('HttpOnlyJWTCsrfToken', {'csrf_token': serializers.CharField()})


class RefreshViewSchema(OpenApiViewExtension):
    target_class = 'httponly_jwt.views.RefreshView'
    match_subclasses = True

    def view_replacement(self) -> Any:
        @extend_schema(
            summary=_('Refresh the session'),
            description=_(
                'The refresh token presented is blacklisted and a new pair issued, '
                "with the person's claims and lifetime read again. A browser gets both "
                'cookies and no token in the body; a native client the pair in the body.'
            ),
            parameters=[refresh_cookie()],
            request=REFRESH_BODY,
            responses={
                200: OpenApiResponse(PAIR, description=_('A native client: the new pair.')),
                204: OpenApiResponse(description=_('A browser: both cookies set again.')),
                401: OpenApiResponse(ENDED, description=_('The session has ended: sign in again.')),
                403: OpenApiResponse(description=_('The CSRF check is on, and failed.')),
            },
        )
        class Described(self.target_class):  # type: ignore[name-defined,misc]
            pass

        return Described


class SignOutViewSchema(OpenApiViewExtension):
    target_class = 'httponly_jwt.views.SignOutView'
    match_subclasses = True

    def view_replacement(self) -> Any:
        @extend_schema(
            summary=_('Sign out'),
            description=_(
                'The refresh token presented is blacklisted, so no copy of it renews '
                'anywhere, and both cookies are cleared. Answers 204 whatever it was given.'
            ),
            parameters=[refresh_cookie()],
            request=REFRESH_BODY,
            responses={
                204: OpenApiResponse(description=_('Signed out.')),
                403: OpenApiResponse(description=_('The CSRF check is on, and failed.')),
            },
        )
        class Described(self.target_class):  # type: ignore[name-defined,misc]
            pass

        return Described


class CsrfTokenViewSchema(OpenApiViewExtension):
    target_class = 'httponly_jwt.views.CsrfTokenView'
    match_subclasses = True

    def view_replacement(self) -> Any:
        @extend_schema(
            summary=_('The CSRF token'),
            description=_(
                "For a frontend on another site, which cannot read the API's cookie. "
                'Send it back in X-CSRFToken on every write.'
            ),
            responses={
                200: CSRF_TOKEN,
            },
        )
        class Described(self.target_class):  # type: ignore[name-defined,misc]
            pass

        return Described
