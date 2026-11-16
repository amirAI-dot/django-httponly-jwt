"""
Every change to a session is told to the project, once, with who and why - so
an audit trail can be written without the project wrapping the library.

If these fail, a sign-in or a sign-out leaves no trace; a renewal a view
overruled is recorded as if it happened; an account switched off is recorded
as having signed out; or a receiver that writes to the database breaks under
ASGI.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import AsyncClient
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from httponly_jwt.sessions import issue_tokens
from httponly_jwt.signals import (
    Ended,
    session_ended,
    session_refreshed,
    session_renewed,
    session_started,
)
from tests.conftest import Access

pytestmark = pytest.mark.django_db

SIGNALS = {
    'started': session_started,
    'renewed': session_renewed,
    'refreshed': session_refreshed,
    'ended': session_ended,
}


@dataclass
class Told:
    """Everything the signals said, in order: (which, person, reason)."""

    heard: list[tuple[str, Any, Any]] = field(default_factory=list)
    requests: list[Any] = field(default_factory=list)

    def which(self) -> list[str]:
        return [name for name, _, _ in self.heard]


@pytest.fixture
def told() -> Iterator[Told]:
    record = Told()
    receivers = {}

    for name, signal in SIGNALS.items():

        def receive(sender: Any, name: str = name, **kwargs: Any) -> None:
            record.heard.append((name, kwargs['person'], kwargs.get('reason')))
            record.requests.append(kwargs['request'])
            # A receiver writing an audit row: under ASGI it must run where it may.
            User.objects.count()

        receivers[name] = receive
        signal.connect(receive)

    yield record

    for name, signal in SIGNALS.items():
        signal.disconnect(receivers[name])


def browser(**cookies: str) -> APIClient:
    client = APIClient()

    for name, value in cookies.items():
        client.cookies[name] = value

    return client


def test_signing_in_is_told_with_the_person_and_the_request(person: User, told: Told) -> None:
    APIClient().post('/sign-in/', {'username': 'ana'})

    assert told.heard == [('started', person, None)]
    assert told.requests[0].path == '/sign-in/'


def test_a_native_sign_in_is_told_too(person: User, told: Told) -> None:
    issue_tokens(person)

    assert told.heard == [('started', person, None)]


def test_a_renewal_is_told(person: User, told: Told) -> None:
    browser(refresh_token=str(RefreshToken.for_user(person))).get('/signed-in/')

    assert told.heard == [('renewed', person, None)]


def test_a_renewal_a_view_overruled_is_not_told(person: User, told: Told) -> None:
    browser(refresh_token=str(RefreshToken.for_user(person))).get('/clears-session/')

    assert told.heard == []


def test_a_good_session_says_nothing(person: User, access: Access, told: Told) -> None:
    browser(access_token=access(person), refresh_token='unused').get('/signed-in/')

    assert told.heard == []


@pytest.mark.parametrize(
    ('why', 'reason', 'known'),
    [
        ('expired', Ended.TOKEN_UNUSABLE, False),
        ('switched off', Ended.NOT_ALLOWED, True),
    ],
)
def test_a_session_the_middleware_ends_is_told_with_why(
    why: str, reason: Ended, known: bool, person: User, told: Told
) -> None:
    token = RefreshToken.for_user(person)

    if why == 'expired':
        token.blacklist()
    else:
        User.objects.filter(pk=person.pk).update(is_active=False)

    browser(refresh_token=str(token)).get('/signed-in/')

    assert told.heard == [('ended', person if known else None, reason)]


def test_a_refresh_is_told(person: User, told: Told) -> None:
    browser(refresh_token=str(RefreshToken.for_user(person))).post('/auth/refresh/')

    assert told.heard == [('refreshed', person, None)]


@pytest.mark.parametrize(
    ('why', 'reason'),
    [('garbled', Ended.TOKEN_UNUSABLE), ('switched off', Ended.NOT_ALLOWED)],
)
def test_a_refresh_refused_is_told_as_the_end(
    why: str, reason: Ended, person: User, told: Told
) -> None:
    raw = 'not.a.token' if why == 'garbled' else str(RefreshToken.for_user(person))
    User.objects.filter(pk=person.pk).update(is_active=why != 'switched off')

    browser(refresh_token=raw).post('/auth/refresh/')

    assert told.which() == ['ended']
    assert told.heard[0][2] == reason


def test_signing_out_is_told_once_with_the_person(person: User, told: Told) -> None:
    raw = str(RefreshToken.for_user(person))

    browser(refresh_token=raw).post('/auth/sign-out/')
    browser(refresh_token=raw).post('/auth/sign-out/')

    assert told.heard == [('ended', person, Ended.SIGNED_OUT)], 'a dead token ends nothing'


def test_under_asgi_a_receiver_that_writes_to_the_database_still_works(
    person: User, told: Told
) -> None:
    """Sent from the async middleware with ``asend``, the receiver runs in a thread."""
    client = AsyncClient()
    client.cookies['refresh_token'] = str(RefreshToken.for_user(person))

    async_to_sync(client.get)('/signed-in/')

    assert told.which() == ['renewed']


def test_under_asgi_a_good_session_says_nothing(person: User, access: Access, told: Told) -> None:
    client = AsyncClient()
    client.cookies['access_token'] = access(person)

    async_to_sync(client.get)('/signed-in/')

    assert told.heard == []
