"""
What happened to a session, for a project's audit trail.

Each is sent once the answer is decided, with the person and the request::

    from django.dispatch import receiver
    from httponly_jwt.signals import session_ended

    @receiver(session_ended)
    def note_it(sender, person, request, reason, **kwargs):
        AuditEntry.objects.create(person=person, what=f'session ended: {reason}')

* **``session_started``** - ``start_session`` or ``issue_tokens`` signed a
  person in.
* **``session_renewed``** - the middleware minted a new access token on the
  way through. Sent only when the renewal reached the response: a view that
  decided the session itself keeps its own decision, and nothing was renewed.
* **``session_refreshed``** - ``RefreshView`` rotated the refresh token.
* **``session_ended``** - with ``reason``, one of ``Ended``: signed out, the
  refresh token no longer good, or the person no longer allowed in. ``person``
  is ``None`` when the token named nobody the library could load.

The sender is the class that sent it. Under ASGI the middleware sends with
``asend``, so a receiver that writes to the database runs where it may.
"""

from enum import StrEnum

from django.dispatch import Signal


class Ended(StrEnum):
    """Why a session ended - ``session_ended``'s ``reason``."""

    #: The person asked: ``SignOutView``.
    SIGNED_OUT = 'signed_out'
    #: The refresh token expired, was blacklisted, or could not be read.
    TOKEN_UNUSABLE = 'token_unusable'
    #: The person is gone, switched off, or refused by ``USER_CAN_SIGN_IN``.
    NOT_ALLOWED = 'not_allowed'


#: ``person``, ``request``.
session_started = Signal()
#: ``person``, ``request``.
session_renewed = Signal()
#: ``person``, ``request``.
session_refreshed = Signal()
#: ``person`` (or ``None``), ``request``, ``reason`` - an ``Ended``.
session_ended = Signal()
