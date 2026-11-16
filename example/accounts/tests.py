"""
The example does what its README says - run with ``python manage.py test``.

If these fail, the example teaches something the library does not do: a
browser handed a token in a body, a session that ends with its first access
token, staff signed in for a month, a role that never reaches the token, a
sign-out that leaves the refresh token working, or a session that changes
without a line in the record.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.models import SessionEvent

PHONE = '+989121234567'


class SigningIn(TestCase):
    def sign_in(self, phone: str = PHONE) -> object:
        with self.assertLogs('accounts', 'INFO') as said:
            self.client.post('/auth/code/', {'phone': phone})

        code = said.records[0].args[1]
        return self.client.post('/auth/sign-in/', {'phone': phone, 'code': code})

    def recorded(self) -> list[str]:
        return [str(event) for event in SessionEvent.objects.all()]

    def test_a_code_signs_the_person_in_by_cookies_and_nothing_else(self) -> None:
        answer = self.sign_in()

        self.assertEqual(answer.status_code, 200)
        self.assertEqual(set(answer.json()), {'id'}, 'no token in the body')
        self.assertTrue(answer.cookies['access_token']['httponly'])
        self.assertEqual(self.client.get('/me/').json(), {'phone': PHONE, 'role': 'customer'})
        self.assertEqual(self.recorded(), ['started'])

    def test_a_wrong_code_signs_nobody_in(self) -> None:
        with self.assertLogs('accounts', 'INFO'):
            self.client.post('/auth/code/', {'phone': PHONE})

        answer = self.client.post('/auth/sign-in/', {'phone': PHONE, 'code': '000000'})

        self.assertEqual(answer.status_code, 400)
        self.assertNotIn('access_token', answer.cookies)

    def test_an_expired_access_token_is_renewed_on_the_way_through(self) -> None:
        self.sign_in()
        person = User.objects.get(username=PHONE)
        expired = AccessToken.for_user(person)
        expired.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies['access_token'] = str(expired)

        answer = self.client.get('/me/')

        self.assertEqual(answer.status_code, 200)
        self.assertEqual(AccessToken(answer.cookies['access_token'].value)['role'], 'customer')
        self.assertEqual(self.recorded(), ['started', 'renewed'])

    def test_staff_are_signed_in_for_a_working_day_with_their_role(self) -> None:
        User.objects.create_user(PHONE, is_staff=True)

        answer = self.sign_in()

        self.assertEqual(answer.cookies['refresh_token']['max-age'], 8 * 60 * 60)
        self.assertEqual(self.client.get('/me/').json()['role'], 'staff')

    def test_signing_out_ends_the_session_everywhere(self) -> None:
        self.sign_in()
        refresh = self.client.cookies['refresh_token'].value

        self.client.post('/auth/sign-out/')

        self.assertEqual(self.client.get('/me/').status_code, 401)
        elsewhere = self.client_class()
        elsewhere.cookies['refresh_token'] = refresh
        self.assertEqual(elsewhere.get('/me/').status_code, 401)
        self.assertEqual(self.recorded(), ['started', 'ended signed_out', 'ended token_unusable'])

    def test_a_refresh_rotates_and_is_recorded(self) -> None:
        self.sign_in()
        old = self.client.cookies['refresh_token'].value

        answer = self.client.post('/auth/refresh/')

        self.assertEqual(answer.status_code, 204)
        self.assertNotEqual(answer.cookies['refresh_token'].value, old)
        self.assertEqual(self.recorded(), ['started', 'refreshed'])

    def test_a_closed_account_is_signed_out_at_its_next_renewal(self) -> None:
        person = User.objects.create_user('closed-1')
        self.client.cookies['refresh_token'] = str(RefreshToken.for_user(person))

        answer = self.client.get('/me/')

        self.assertEqual(answer.status_code, 401)
        self.assertEqual(answer.cookies['refresh_token']['max-age'], 0)
        self.assertEqual(self.recorded(), ['ended not_allowed'])

    def test_the_schema_describes_the_cookie(self) -> None:
        answer = self.client.get('/schema/', HTTP_ACCEPT='application/vnd.oai.openapi+json')

        self.assertEqual(answer.status_code, 200)
        self.assertIn('httponlyJwtCookie', answer.json()['components']['securitySchemes'])
