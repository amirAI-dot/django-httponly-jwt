# Keep an audit trail

Every change to a session is a signal, sent once the answer is decided, with
the person and the request. Writing them down is the whole of an audit trail.

## A table, and a receiver

```python
# accounts/models.py
from django.conf import settings
from django.db import models


class SessionEvent(models.Model):
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+'
    )
    what = models.CharField(max_length=16)
    reason = models.CharField(max_length=32, blank=True)
    address = models.GenericIPAddressField(null=True)
    at = models.DateTimeField(auto_now_add=True)
```

```python
# accounts/receivers.py
from django.dispatch import receiver

from accounts.models import SessionEvent
from httponly_jwt.signals import (
    session_ended,
    session_refreshed,
    session_renewed,
    session_started,
)

WHAT = {
    session_started: 'started',
    session_renewed: 'renewed',
    session_refreshed: 'refreshed',
    session_ended: 'ended',
}


@receiver([session_started, session_renewed, session_refreshed, session_ended])
def record(signal, person, request, **kwargs):
    SessionEvent.objects.create(
        person=person,
        what=WHAT[signal],
        reason=kwargs.get('reason') or '',
        address=request.META.get('REMOTE_ADDR') if request is not None else None,
    )
```

```python
# accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        from accounts import receivers  # noqa: F401
```

The [example project](https://github.com/amirAI-dot/django-httponly-jwt/tree/main/example)
has this, with tests.

## What each row says

| `what` | `reason` | it means |
|---|---|---|
| `started` | | signed in |
| `renewed` | | the access token ran out and was renewed on the way through |
| `refreshed` | | the refresh view rotated the refresh token |
| `ended` | `signed_out` | the person signed out |
| `ended` | `token_unusable` | the refresh token expired, was blacklisted, or could not be read |
| `ended` | `not_allowed` | the account is gone, switched off, or refused by `USER_CAN_SIGN_IN` |

`person` is empty when the token named nobody the library could load.

## Choosing what to keep

A renewal happens once per access-token lifetime for every person signed in -
with fifteen-minute tokens, a busy day is a great many rows. A project that
wants only sign-ins, sign-outs and refusals listens to those:

```python
from httponly_jwt.signals import Ended, session_ended


@receiver(session_ended)
def note_refusals(sender, person, request, reason, **kwargs):
    if reason == Ended.NOT_ALLOWED:
        ...
```

## Under ASGI

The middleware sends its signals with `asend`, so a receiver that writes to
the database - a synchronous one, like the one above - runs in a thread, where
Django allows it. Nothing needs to change.

## What never to keep

The tokens. A row holding a refresh token is a session anybody who reads the
table can use.
