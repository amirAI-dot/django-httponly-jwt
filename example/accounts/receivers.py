"""The library's signals, written down - which is all an audit trail needs."""

from typing import Any

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
def record(signal: Any, person: Any, request: Any, **kwargs: Any) -> None:
    SessionEvent.objects.create(
        person=person,
        what=WHAT[signal],
        reason=kwargs.get('reason') or '',
        path=getattr(request, 'path', '') or '',
    )
