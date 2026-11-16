"""
The one place that knows how a session cookie is written.

Both tokens live in cookies the browser attaches by itself, marked
``HttpOnly`` so no script can read them - which is what keeps a cross-site
script from stealing a session.

Every flag lives here, in functions, rather than being spelled out where a
cookie is set. A project sets these cookies in several places and clears them
in one, and a cookie cleared with flags other than the ones it was set with
is not cleared at all: the browser keeps it, and the session cannot be ended.
"""

from datetime import timedelta
from typing import TypeVar

from django.http import HttpRequest
from django.http.response import HttpResponseBase
from rest_framework_simplejwt.settings import api_settings as simplejwt

from httponly_jwt.conf import httponly_jwt_settings as conf

ResponseT = TypeVar('ResponseT', bound=HttpResponseBase)


def set_session_cookies(
    response: ResponseT, *, access: str, refresh: str, lifetime: timedelta | None = None
) -> ResponseT:
    """
    Put a signed-in session on ``response``: both tokens, in their cookies.

    Both cookies last as long as the refresh token - ``lifetime``, or
    simplejwt's ``REFRESH_TOKEN_LIFETIME``. The access cookie deliberately
    outlives the access token inside it: if it expired with the token, the
    browser would delete it the moment the token ran out, and there would be
    nothing left to renew - the person would be signed out with a refresh
    token that had weeks left on it.
    """
    _set(response, conf.access_cookie, access, lifetime)
    _set(response, conf.refresh_cookie, refresh, lifetime)
    return response


def set_access_cookie(
    response: ResponseT, access: str, *, lifetime: timedelta | None = None
) -> ResponseT:
    """Replace only the access cookie - what a silent renewal does."""
    _set(response, conf.access_cookie, access, lifetime)
    return response


def clear_session_cookies(response: ResponseT) -> ResponseT:
    """
    Remove both cookies, with the flags they were set with.

    A browser does not delete a cookie when the path, the domain or SameSite
    differ: it keeps the first and writes a second, empty one - a session
    that cannot be ended.
    """
    for name in (conf.access_cookie, conf.refresh_cookie):
        response.delete_cookie(
            name,
            path=conf.cookie_path,
            domain=conf.cookie_domain,
            samesite=conf.cookie_samesite,
        )

    return response


def read_access_token(request: HttpRequest) -> str:
    """The access token the browser sent, or ``''``."""
    return request.COOKIES.get(conf.access_cookie, '')


def read_refresh_token(request: HttpRequest) -> str:
    """The refresh token the browser sent, or ``''``."""
    return request.COOKIES.get(conf.refresh_cookie, '')


def _set(response: HttpResponseBase, name: str, value: str, lifetime: timedelta | None) -> None:
    lasts: timedelta = lifetime or simplejwt.REFRESH_TOKEN_LIFETIME
    response.set_cookie(
        key=name,
        value=value,
        max_age=int(lasts.total_seconds()),
        # No script may read either token. This is the whole reason the
        # frontend is not given them.
        httponly=True,
        secure=conf.cookie_secure,
        samesite=conf.cookie_samesite,
        domain=conf.cookie_domain,
        # Site-wide, because renewal has to see the refresh cookie on an
        # ordinary request. Scoped to the auth endpoints, renewal would only
        # work on the auth endpoints - which is the same as not working.
        path=conf.cookie_path,
    )
