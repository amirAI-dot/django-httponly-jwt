"""
Starting a session for a person the project has signed in.

The library does not sign anybody in: how a person proves who they are - a
password, a one-time code, a social account - is the project's. Once it knows,
it hands the person over::

    from httponly_jwt.sessions import start_session

    class SignInView(APIView):
        def post(self, request):
            person = verify_code(request.data['phone'], request.data['code'])
            return start_session(Response({'id': person.pk}), person)

``start_session`` mints a pair and sets both cookies. ``issue_tokens`` mints
the pair and sets nothing, for a native client that keeps its tokens itself.

Each pair carries what the project says about this person:

* **``REFRESH_LIFETIME``** - how long the session lasts. A patient stays
  signed in for months; staff for a working day. ``None``, or a function that
  answers ``None``, is simplejwt's ``REFRESH_TOKEN_LIFETIME``.
* **``CLAIMS``** - what the tokens carry beyond who the person is: their role,
  so the frontend need not ask before it chooses a screen. Read again at every
  renewal, so a role changed today is in the next access token.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeVar

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponseBase
from django.utils.module_loading import import_string
from rest_framework_simplejwt.settings import api_settings as simplejwt
from rest_framework_simplejwt.tokens import RefreshToken, Token

from httponly_jwt.conf import httponly_jwt_settings as conf
from httponly_jwt.cookies import set_session_cookies

ResponseT = TypeVar('ResponseT', bound=HttpResponseBase)


@dataclass(frozen=True)
class Tokens:
    """A pair for one person, and how long their session lasts."""

    access: str
    refresh: str
    #: How long the refresh token - and so the session - lasts.
    lifetime: timedelta


def issue_tokens(person: Any) -> Tokens:
    """A new pair for ``person``, with their claims and their lifetime; nothing is set."""
    refresh = RefreshToken.for_user(person)
    lifetime = lifetime_for(person)
    refresh.set_exp(lifetime=lifetime)
    add_claims(refresh, person)
    return Tokens(access=str(refresh.access_token), refresh=str(refresh), lifetime=lifetime)


def start_session(response: ResponseT, person: Any) -> ResponseT:
    """Sign ``person`` in on ``response``: a new pair, in both cookies."""
    tokens = issue_tokens(person)
    return set_session_cookies(
        response, access=tokens.access, refresh=tokens.refresh, lifetime=tokens.lifetime
    )


def lifetime_for(person: Any) -> timedelta:
    """How long a session of ``person``'s lasts - the project's answer, or simplejwt's."""
    path = conf.value('REFRESH_LIFETIME')
    chosen: timedelta | None = None if path is None else import_string(path)(person)
    default: timedelta = simplejwt.REFRESH_TOKEN_LIFETIME
    return chosen or default


def add_claims(token: Token, person: Any) -> None:
    """Put the project's claims about ``person`` on ``token``."""
    path = conf.value('CLAIMS')

    if path is None:
        return

    claims = import_string(path)(person)
    reserved = sorted(set(claims) & _reserved())

    if reserved:
        raise ImproperlyConfigured(
            f"HTTPONLY_JWT['CLAIMS'] may not set {', '.join(reserved)}: simplejwt's own "
            'claims say who the token is for, what kind it is and when it expires.'
        )

    for name, value in claims.items():
        token[name] = value


def may_sign_in(person: Any) -> bool:
    """Whether ``person`` may still hold a session: active, and whatever the project adds."""
    if not getattr(person, 'is_active', True):
        return False

    path = conf.value('USER_CAN_SIGN_IN')
    return path is None or bool(import_string(path)(person))


def person_of(refresh: RefreshToken) -> Any:
    """The person ``refresh`` was issued to, or ``None`` when there is nobody."""
    key = refresh.get(simplejwt.USER_ID_CLAIM)

    if key is None:
        return None

    return get_user_model().objects.filter(**{simplejwt.USER_ID_FIELD: key}).first()


def _reserved() -> set[str]:
    return {
        simplejwt.USER_ID_CLAIM,
        simplejwt.TOKEN_TYPE_CLAIM,
        simplejwt.JTI_CLAIM,
        'exp',
        'iat',
        'jti',
    }
