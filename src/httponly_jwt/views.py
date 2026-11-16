"""
The two endpoints a session needs besides signing in: refreshing it, and ending it.

::

    from httponly_jwt.views import RefreshView, SignOutView

    urlpatterns = [
        path('auth/refresh/', RefreshView.as_view()),
        path('auth/sign-out/', SignOutView.as_view()),
    ]

Both read the refresh token from its cookie - a browser's - or from the body as
``{"refresh": "..."}`` - a native client's. The cookie is asked first. What
comes back follows where the token came from: a browser gets cookies and never
a token in a body, a native client gets the pair in the body and no cookie.

**Refreshing rotates.** The token presented is blacklisted and a new pair is
issued, with the person's claims and lifetime read again - so it also extends
the session by a full lifetime. The middleware never does this, because two
tabs renewing together would sign each other out; a refresh is called on
purpose, by one client.

**Signing out blacklists**, so the refresh token is dead everywhere it was
copied, not only in this browser. It answers 204 whatever it was given - a
token already dead, or none at all - because a person asking to be signed out
is signed out either way, and an error would only tell them their sign-out
failed when it had not.

Neither takes authentication: the refresh token is the credential, and a
sign-out must work when the access token has already run out. With
``CSRF = True`` both ask for the CSRF token when the refresh token came in the
cookie, since that is the cookie another site's request would carry.

``CsrfTokenView`` hands that token to a frontend on another site::

    path('auth/csrf/', CsrfTokenView.as_view()),
"""

import logging
from typing import Any

from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as simplejwt
from rest_framework_simplejwt.tokens import RefreshToken

from httponly_jwt.cookies import clear_session_cookies, read_refresh_token, set_session_cookies
from httponly_jwt.csrf import enforce_csrf
from httponly_jwt.sessions import issue_tokens, may_sign_in, person_of

logger = logging.getLogger(__name__)


class RefreshView(APIView):
    """A new pair for the refresh token presented, which is blacklisted."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        raw, from_cookie = presented(request)

        if from_cookie:
            enforce_csrf(request)

        refresh = readable(raw)
        person = None if refresh is None else person_of(refresh)

        if refresh is None or person is None or not may_sign_in(person):
            answer = Response(
                {
                    'detail': _('Your session has ended. Please sign in again.'),
                    'code': 'session_ended',
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return clear_session_cookies(answer) if from_cookie else answer

        blacklist(refresh)
        tokens = issue_tokens(person)
        logger.info('httponly_jwt.refreshed', extra={'user_id': person.pk})

        if from_cookie:
            return set_session_cookies(
                Response(status=status.HTTP_204_NO_CONTENT),
                access=tokens.access,
                refresh=tokens.refresh,
                lifetime=tokens.lifetime,
            )

        return Response({'access': tokens.access, 'refresh': tokens.refresh})


class SignOutView(APIView):
    """The refresh token presented is blacklisted, and both cookies cleared."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        raw, from_cookie = presented(request)

        if from_cookie:
            enforce_csrf(request)

        refresh = readable(raw)

        if refresh is not None:
            blacklist(refresh)
            logger.info(
                'httponly_jwt.signed_out', extra={'user_id': refresh.get(simplejwt.USER_ID_CLAIM)}
            )

        return clear_session_cookies(Response(status=status.HTTP_204_NO_CONTENT))


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfTokenView(APIView):
    """
    ``GET``: the CSRF token, for a frontend on another site, which cannot read the API's cookie.

    Only needed with ``CSRF = True``. The answer is ``{"csrf_token": "..."}``,
    and the CSRF cookie it belongs with is set on the same response.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return Response({'csrf_token': get_token(request)})


def presented(request: Request) -> tuple[str, bool]:
    """The refresh token this request presents, and whether it came in the cookie."""
    from_cookie = read_refresh_token(request)

    if from_cookie:
        return from_cookie, True

    data: Any = request.data
    raw = data.get('refresh') if hasattr(data, 'get') else None
    return (raw if isinstance(raw, str) else ''), False


def readable(raw: str) -> RefreshToken | None:
    """``raw`` as a refresh token still good - not expired, garbled or blacklisted."""
    if not raw:
        return None

    try:
        return RefreshToken(raw)  # type: ignore[arg-type]
    except TokenError:
        return None


def blacklist(refresh: RefreshToken) -> None:
    """Blacklist ``refresh`` - when the project runs the blacklist at all."""
    if hasattr(refresh, 'blacklist'):
        refresh.blacklist()
