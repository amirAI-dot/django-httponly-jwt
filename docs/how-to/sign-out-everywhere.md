# Sign a person out everywhere

`SignOutView` ends the session it was given - one browser, one app. A stolen
phone, a changed password or an account that was taken over needs every
session of the person ended at once.

## Blacklist every refresh token they hold

simplejwt records every refresh token it issues, as an `OutstandingToken`
row. Blacklisting all of a person's ends every session at its next renewal:

```python
# accounts/sessions.py
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def sign_out_everywhere(person):
    """Every refresh token the person holds, blacklisted: no session of theirs renews again."""
    for token in OutstandingToken.objects.filter(user=person):
        BlacklistedToken.objects.get_or_create(token=token)
```

From there, each browser and app the person was signed in on finds its
refresh token blacklisted the next time its access token runs out: the
middleware clears its cookies and `session_ended` is sent with
`token_unusable`.

## After a password change

The person changing it should stay signed in where they are:

```python
class ChangePassword(APIView):
    def post(self, request):
        person = request.user
        person.set_password(request.data['password'])
        person.save()
        sign_out_everywhere(person)
        # Signed in again here, with a session the blacklist did not reach.
        return start_session(Response(status=204), person, request=request)
```

## Ending them sooner

An access token already issued is good until it expires - minutes, with
simplejwt's `ACCESS_TOKEN_LIFETIME`. A blacklist ends refresh tokens, not
access tokens. When minutes are too long, keep the access-token lifetime
short; that is the trade every JWT session makes.

## Switching an account off

Switching an account off needs nothing more:

```python
person.is_active = False
person.save()
```

The middleware asks `is_active` at every renewal, and the refresh view asks
it at every refresh, so the account's sessions end at the next of either.
`USER_CAN_SIGN_IN` does the same for a project's own reasons - a suspended
account, an unpaid subscription.
