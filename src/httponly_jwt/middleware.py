"""
Silent renewal: the reason the frontend never sees a token.

An access token lives minutes; a session lives days or months. Something has
to bridge that gap, and there are two places it can be. Either the client
notices a 401, calls a refresh endpoint, retries the request and holds the
tokens to do it - or the server does it on the way through, and the client
never learns that tokens exist. This is the second.

    MIDDLEWARE = [..., 'httponly_jwt.middleware.RenewalMiddleware', ...]

When the access cookie is missing or no longer good and the refresh cookie
is, a new access token is minted, used for **this** request, and set on the
way out. Four things it does that the obvious version does not:

* **It renews when the access cookie is gone, not only when it is expired.**
  The browser deletes an expired cookie, so the guard "nothing to renew
  without an access cookie" breaks the exact case it was written for.
* **It asks whether the person may still be signed in** - ``is_active``, and
  ``USER_CAN_SIGN_IN`` when the project names one. Switching an account off
  ends its sessions at the next renewal, not when its refresh token expires.
* **It never rotates the refresh token.** Two requests from two tabs would
  renew together, one blacklisting the token the other is using, and the
  person would be signed out by their own second tab. Rotation is the
  refresh view's, called on purpose.
* **It leaves alone what a view decided.** A response that already sets or
  clears the session cookies - signing in, signing out - keeps them.

A request with a good access token costs a signature check and no query. A
renewal costs two: whether the refresh token was blacklisted - signed out
elsewhere - and loading the person.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.utils.module_loading import import_string
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as simplejwt
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from httponly_jwt.conf import httponly_jwt_settings as conf
from httponly_jwt.cookies import (
    clear_session_cookies,
    read_access_token,
    read_refresh_token,
    set_access_cookie,
)

logger = logging.getLogger(__name__)

#: The session is over: clear both cookies on the way out.
ENDED: Final = 'ended'


class Renewed:
    """A new access token, and how long its cookie may last."""

    def __init__(self, access: str, lifetime: timedelta) -> None:
        self.access = access
        self.lifetime = lifetime


Outcome = Renewed | str | None


class RenewalMiddleware:
    """Renews the access cookie in place, before any view reads it - sync or async."""

    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> Any:
        if iscoroutinefunction(self):
            return self.__acall__(request)

        outcome = renew(request)
        return settle(outcome, self.get_response(request))

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        outcome = await sync_to_async(renew, thread_sensitive=True)(request)
        return settle(outcome, await self.get_response(request))


def renew(request: HttpRequest) -> Outcome:
    """
    What this request's session needs: a new access token, ``ENDED``, or nothing.

    Nothing when there is no refresh cookie - a client signed in by header
    never had one, and clearing would delete cookies it never set - or when
    the access token is still good.
    """
    raw_refresh = read_refresh_token(request)

    if not raw_refresh or _usable(read_access_token(request)):
        return None

    try:
        refresh = RefreshToken(raw_refresh)  # type: ignore[arg-type]
    except TokenError:
        # Expired, unreadable, or blacklisted - signed out elsewhere. Leaving
        # the cookies would make every later request repeat this work.
        return ENDED

    person = _person_of(refresh)

    if person is None or not may_sign_in(person):
        return ENDED

    access = str(refresh.access_token)
    # This request authenticates with it too. Without this line the renewal
    # only took effect from the next request, and every session would answer
    # one 401 per access-token lifetime.
    request.COOKIES[conf.access_cookie] = access
    logger.info('httponly_jwt.renewed', extra={'user_id': person.pk})
    return Renewed(access, _remaining(refresh))


def may_sign_in(person: Any) -> bool:
    """Whether ``person`` may still hold a session: active, and whatever the project adds."""
    if not getattr(person, 'is_active', True):
        return False

    path = conf.value('USER_CAN_SIGN_IN')
    return path is None or bool(import_string(path)(person))


def settle(outcome: Outcome, response: HttpResponseBase) -> HttpResponseBase:
    """Put the renewal on ``response`` - unless the view already set the session itself."""
    if outcome is None or _decided_by_view(response):
        return response

    if isinstance(outcome, Renewed):
        return set_access_cookie(response, outcome.access, lifetime=outcome.lifetime)

    return clear_session_cookies(response)


def _usable(raw_access: str) -> bool:
    if not raw_access:
        return False

    try:
        AccessToken(raw_access)  # type: ignore[arg-type]
    except TokenError:
        return False

    return True


def _person_of(refresh: RefreshToken) -> Any:
    key = refresh.get(simplejwt.USER_ID_CLAIM)

    if key is None:
        return None

    return get_user_model().objects.filter(**{simplejwt.USER_ID_FIELD: key}).first()


def _remaining(refresh: RefreshToken) -> timedelta:
    """How long the refresh token has left: the renewed cookie lasts no longer."""
    expires = datetime.fromtimestamp(refresh['exp'], tz=UTC)
    return max(expires - datetime.now(tz=UTC), timedelta(0))


def _decided_by_view(response: HttpResponseBase) -> bool:
    return conf.access_cookie in response.cookies or conf.refresh_cookie in response.cookies
