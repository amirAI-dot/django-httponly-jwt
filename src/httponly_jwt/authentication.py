"""
Who is asking: DRF authentication from the session cookie, or a header.

Three classes, in the order a project lists them::

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'httponly_jwt.authentication.CookieAuthentication',
            'httponly_jwt.authentication.HeaderAuthentication',
        ],
    }

**The cookie is the browser's way in.** It is attached by the browser, not by
the page, so it arrives on every request - including on pages anybody may
open. A cookie that is stale, unreadable, or names an account that is gone or
switched off is therefore not an error: it is a request from nobody. DRF moves
on to the next class, and an endpoint that needs somebody answers a plain
401 - while one that does not answers as it would to a guest.

**The header is everything else's** - a native app, a script, a test. A header
is set on purpose, so a bad one is an error, as simplejwt has it: the client
is told its token is not good rather than being treated as a guest.

**Optional authentication** is for an endpoint anybody may call that does more
for somebody signed in. The cookie, then the header - and never a refusal: a
guest is not turned away for a stale token they did not mean to send.

Each is simplejwt's ``JWTAuthentication`` underneath, so its settings -
``AUTH_TOKEN_CLASSES``, ``USER_ID_CLAIM``, ``CHECK_USER_IS_ACTIVE`` - hold as
they always have.
"""

from typing import Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from httponly_jwt.cookies import read_access_token

#: What a token or its account can be wrong with - each one, from a cookie, is nobody.
_NOT_A_SESSION = (AuthenticationFailed, InvalidToken, TokenError)


class CookieAuthentication(JWTAuthentication):
    """The person the access cookie names - or nobody, never an error."""

    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        raw = read_access_token(request)

        if not raw:
            return None

        try:
            token = self.get_validated_token(raw.encode())
            return self.get_user(token), token
        except _NOT_A_SESSION:
            # Expired, unreadable, or an account gone or switched off: an
            # ordinary state for a cookie, not something to refuse a page for.
            return None


class HeaderAuthentication(JWTAuthentication):
    """
    ``Authorization: Bearer <access token>`` - for clients that are not browsers.

    simplejwt's own class, under the library's name, so a project lists the
    library's classes together. A bad header is refused, as simplejwt has it.
    Browsers use the cookie: the frontend never holds a token.
    """


class OptionalAuthentication(JWTAuthentication):
    """The cookie, then the header - and nobody, rather than a refusal."""

    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        found = CookieAuthentication().authenticate(request)

        if found is not None:
            return found

        try:
            return super().authenticate(request)
        except _NOT_A_SESSION:
            return None
