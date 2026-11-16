"""
A refresh token that was blacklisted - signed out, or rotated by a refresh -
stays refused for as long as it would otherwise have worked.

simplejwt keeps a row for every refresh token it issues, with the moment it
expires, and its ``flushexpiredtokens`` command deletes the rows that have
expired - and the blacklist entries with them. The library sets each person's
own lifetime after simplejwt has written that row. If these fail, the row
keeps simplejwt's default expiry: a person signed in for longer than the
default, who signed out, has their old refresh token deleted from the
blacklist by the first flush after the default - and the token, still good by
its own signature, works again.
"""

from collections.abc import Iterator
from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.settings import api_settings as simplejwt
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch

from httponly_jwt.sessions import issue_tokens

pytestmark = pytest.mark.django_db

YEAR = timedelta(days=365)
FLUSH = 'rest_framework_simplejwt.token_blacklist.management.commands.flushexpiredtokens'


def a_year(person: User) -> timedelta:
    return YEAR


@pytest.fixture(autouse=True)
def signed_in_for_a_year() -> Iterator[None]:
    """Longer than simplejwt's REFRESH_TOKEN_LIFETIME - the case the row got wrong."""
    assert simplejwt.REFRESH_TOKEN_LIFETIME < YEAR

    with override_settings(HTTPONLY_JWT={'REFRESH_LIFETIME': f'{__name__}.a_year'}):
        yield


def flush_after_the_default() -> None:
    """``flushexpiredtokens``, run once simplejwt's default lifetime has passed."""
    later = timezone.now() + simplejwt.REFRESH_TOKEN_LIFETIME + timedelta(days=1)

    with mock.patch(f'{FLUSH}.aware_utcnow', return_value=later):
        call_command('flushexpiredtokens')


def refused(raw: str) -> bool:
    return APIClient().post('/auth/refresh/', {'refresh': raw}, format='json').status_code == 401


def test_the_row_simplejwt_keeps_says_when_the_token_really_expires(person: User) -> None:
    raw = issue_tokens(person).refresh
    token = RefreshToken(raw)

    row = OutstandingToken.objects.get(jti=token['jti'])

    assert row.expires_at == datetime_from_epoch(token['exp'])
    assert row.token == raw, 'the row holds the token issued, claims and all'


def test_a_token_signed_out_stays_refused_after_a_flush(person: User) -> None:
    raw = issue_tokens(person).refresh
    APIClient().post('/auth/sign-out/', {'refresh': raw}, format='json')

    flush_after_the_default()

    assert refused(raw)


def test_a_token_rotated_away_stays_refused_after_a_flush(person: User) -> None:
    raw = issue_tokens(person).refresh
    APIClient().post('/auth/refresh/', {'refresh': raw}, format='json')

    flush_after_the_default()

    assert refused(raw)


def test_a_session_still_good_survives_a_flush(person: User) -> None:
    raw = issue_tokens(person).refresh

    flush_after_the_default()

    assert not refused(raw)


def test_without_the_blacklist_there_is_no_row_to_correct(
    person: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project that chose ``ALLOW_WITHOUT_BLACKLIST`` signs in as before."""
    monkeypatch.setattr('httponly_jwt.sessions.apps.is_installed', lambda name: False)

    tokens = issue_tokens(person)

    assert RefreshToken(tokens.refresh)['exp'] - RefreshToken(tokens.refresh)['iat'] == (
        YEAR.total_seconds()
    )
