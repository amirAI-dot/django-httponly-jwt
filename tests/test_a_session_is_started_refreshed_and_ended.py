"""
A session is started for a person the project signed in, refreshed on purpose,
and ended - in a browser by cookies, in a native app by the body.

If these fail, signing in sets no cookie or one that outlives nothing; a
patient and a member of staff are signed in for the same length of time; a
role changed today is not in the token until the person signs in again; a
project can overwrite who a token is for; a refresh token stolen and used
once can be used again; a browser is handed a token in a body it should never
see; or signing out leaves a refresh token that still renews somewhere else.
"""

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.settings import api_settings as simplejwt
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, BlacklistMixin, RefreshToken

from httponly_jwt.sessions import issue_tokens

pytestmark = pytest.mark.django_db

SHIFT = timedelta(hours=8)


def lifetime_by_kind(person: User) -> timedelta | None:
    """Staff for a working day; everybody else simplejwt's default."""
    return SHIFT if person.is_staff else None


def claims_of(person: User) -> dict[str, Any]:
    return {'role': 'nurse' if person.is_staff else 'patient'}


def claims_overwriting_who(person: User) -> dict[str, Any]:
    return {'user_id': 999, 'role': 'patient'}


def browser(**cookies: str) -> APIClient:
    client = APIClient()

    for name, value in cookies.items():
        client.cookies[name] = value

    return client


def cleared(response: Any) -> bool:
    return all(response.cookies[name]['max-age'] == 0 for name in ('access_token', 'refresh_token'))


# ---------------------------------------------------------------- starting


def test_signing_in_sets_both_cookies_and_no_token_in_the_body(person: User) -> None:
    answer = APIClient().post('/sign-in/', {'username': 'ana'})

    assert answer.json() == {'id': person.pk}
    assert AccessToken(answer.cookies['access_token'].value)['user_id'] == str(person.pk)
    assert RefreshToken(answer.cookies['refresh_token'].value)['user_id'] == str(person.pk)
    assert answer.cookies['refresh_token']['httponly']


def test_the_session_started_signs_the_next_request_in(person: User) -> None:
    client = APIClient()
    client.post('/sign-in/', {'username': 'ana'})

    assert client.get('/signed-in/').json() == {'person': 'ana'}


@override_settings(HTTPONLY_JWT={'REFRESH_LIFETIME': f'{__name__}.lifetime_by_kind'})
def test_each_person_is_signed_in_for_as_long_as_the_project_says(person: User) -> None:
    staff = User.objects.create_user('sam', is_staff=True)

    patient = APIClient().post('/sign-in/', {'username': 'ana'})
    nurse = APIClient().post('/sign-in/', {'username': 'sam'})

    default = simplejwt.REFRESH_TOKEN_LIFETIME
    assert nurse.cookies['refresh_token']['max-age'] == SHIFT.total_seconds()
    assert patient.cookies['refresh_token']['max-age'] == default.total_seconds()
    token = RefreshToken(nurse.cookies['refresh_token'].value)
    assert token['exp'] - token['iat'] == SHIFT.total_seconds()
    assert issue_tokens(staff).lifetime == SHIFT


def test_a_native_client_is_issued_a_pair_and_nothing_is_set(person: User) -> None:
    tokens = issue_tokens(person)

    assert AccessToken(tokens.access)['user_id'] == str(person.pk)
    assert RefreshToken(tokens.refresh)['user_id'] == str(person.pk)


# ---------------------------------------------------------------- claims


@override_settings(HTTPONLY_JWT={'CLAIMS': f'{__name__}.claims_of'})
def test_the_project_s_claims_are_in_both_tokens(person: User) -> None:
    tokens = issue_tokens(person)

    assert AccessToken(tokens.access)['role'] == 'patient'
    assert RefreshToken(tokens.refresh)['role'] == 'patient'


@override_settings(HTTPONLY_JWT={'CLAIMS': f'{__name__}.claims_of'})
def test_a_renewal_reads_the_claims_again(person: User) -> None:
    """The person became staff after signing in: the renewed token says so."""
    refresh = issue_tokens(person).refresh
    person.is_staff = True
    person.save()

    answer = browser(refresh_token=refresh).get('/claims/')

    assert answer.json()['role'] == 'nurse'
    assert AccessToken(answer.cookies['access_token'].value)['role'] == 'nurse'


@override_settings(HTTPONLY_JWT={'CLAIMS': f'{__name__}.claims_overwriting_who'})
def test_a_claim_may_not_overwrite_who_the_token_is_for(person: User) -> None:
    with pytest.raises(ImproperlyConfigured, match='user_id'):
        issue_tokens(person)


# ---------------------------------------------------------------- refreshing


def test_a_browser_refresh_rotates_both_cookies_and_shows_no_token(person: User) -> None:
    old = str(RefreshToken.for_user(person))

    answer = browser(refresh_token=old).post('/auth/refresh/')

    assert answer.status_code == 204
    assert not answer.content
    new = answer.cookies['refresh_token'].value
    assert new
    assert new != old
    assert AccessToken(answer.cookies['access_token'].value)['user_id'] == str(person.pk)


def test_a_refresh_token_used_once_cannot_be_used_again(person: User) -> None:
    old = str(RefreshToken.for_user(person))
    browser(refresh_token=old).post('/auth/refresh/')

    again = browser(refresh_token=old).post('/auth/refresh/')

    assert again.status_code == 401
    assert again.json()['code'] == 'session_ended'
    assert cleared(again)


def test_a_native_refresh_answers_the_pair_in_the_body_and_sets_no_cookie(person: User) -> None:
    old = str(RefreshToken.for_user(person))

    answer = APIClient().post('/auth/refresh/', {'refresh': old}, format='json')

    assert answer.status_code == 200
    assert set(answer.json()) == {'access', 'refresh'}
    assert answer.cookies == {}
    assert RefreshToken(answer.json()['refresh'])['user_id'] == str(person.pk)


@pytest.mark.parametrize('body', [{}, {'refresh': 'not.a.token'}, {'refresh': 7}])
def test_a_native_refresh_with_no_good_token_is_refused_and_sets_no_cookie(
    body: dict[str, Any],
) -> None:
    answer = APIClient().post('/auth/refresh/', body, format='json')

    assert answer.status_code == 401
    assert answer.cookies == {}


def test_a_refresh_with_a_body_that_is_not_an_object_is_refused() -> None:
    answer = APIClient().post('/auth/refresh/', '"text"', content_type='application/json')

    assert answer.status_code == 401


@pytest.mark.parametrize('why', ['switched off', 'gone', 'names nobody'])
def test_a_refresh_for_somebody_who_may_not_sign_in_ends_the_session(
    why: str, person: User
) -> None:
    raw = str(RefreshToken() if why == 'names nobody' else RefreshToken.for_user(person))

    if why == 'switched off':
        person.is_active = False
        person.save()
    if why == 'gone':
        person.delete()

    answer = browser(refresh_token=raw).post('/auth/refresh/')

    assert answer.status_code == 401
    assert cleared(answer)


@override_settings(HTTPONLY_JWT={'REFRESH_LIFETIME': f'{__name__}.lifetime_by_kind'})
def test_a_refresh_extends_the_session_by_the_person_s_lifetime(person: User) -> None:
    User.objects.filter(pk=person.pk).update(is_staff=True)
    old = RefreshToken.for_user(person)
    old.set_exp(lifetime=timedelta(minutes=5))

    answer = browser(refresh_token=str(old)).post('/auth/refresh/')

    assert answer.cookies['refresh_token']['max-age'] == SHIFT.total_seconds()


# ---------------------------------------------------------------- signing out


def test_signing_out_clears_the_cookies_and_kills_the_token_everywhere(person: User) -> None:
    raw = str(RefreshToken.for_user(person))

    answer = browser(refresh_token=raw).post('/auth/sign-out/')

    assert answer.status_code == 204
    assert cleared(answer)
    elsewhere = browser(refresh_token=raw).get('/signed-in/')
    assert elsewhere.status_code == 401, 'another browser holding the copy cannot renew'


def test_a_native_client_signs_out_by_the_body(person: User) -> None:
    raw = str(RefreshToken.for_user(person))

    answer = APIClient().post('/auth/sign-out/', {'refresh': raw}, format='json')

    assert answer.status_code == 204
    assert BlacklistedToken.objects.filter(
        token__jti=RefreshToken(raw, verify=False)['jti']
    ).exists()


@pytest.mark.parametrize('cookie', ['', 'not.a.token', 'used'])
def test_signing_out_twice_or_with_nothing_still_signs_out(cookie: str, person: User) -> None:
    raw = str(RefreshToken.for_user(person))

    if cookie == 'used':
        browser(refresh_token=raw).post('/auth/sign-out/')
        cookie = raw

    answer = (browser(refresh_token=cookie) if cookie else APIClient()).post('/auth/sign-out/')

    assert answer.status_code == 204
    assert cleared(answer)


# ---------------------------------------------------------------- without the blacklist


def test_without_the_blacklist_a_refresh_and_a_sign_out_still_work(
    person: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project that chose ``ALLOW_WITHOUT_BLACKLIST``: rotation cannot revoke, but works."""
    monkeypatch.delattr(BlacklistMixin, 'blacklist')
    raw = str(RefreshToken.for_user(person))

    refreshed = browser(refresh_token=raw).post('/auth/refresh/')
    signed_out = browser(refresh_token=raw).post('/auth/sign-out/')

    assert refreshed.status_code == signed_out.status_code == 204
    assert not BlacklistedToken.objects.exists()
