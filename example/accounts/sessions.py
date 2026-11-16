"""What the example tells the library about each person - named in HTTPONLY_JWT."""

from datetime import timedelta
from typing import Any


def lifetime(person: Any) -> timedelta | None:
    """Staff for a working day; everybody else simplejwt's REFRESH_TOKEN_LIFETIME."""
    return timedelta(hours=8) if person.is_staff else None


def claims(person: Any) -> dict[str, Any]:
    """The role, so the frontend chooses its screen without asking."""
    return {'role': 'staff' if person.is_staff else 'customer'}


def may_sign_in(person: Any) -> bool:
    """A project's own reason to end a session: here, an account marked as closed."""
    return not person.username.startswith('closed-')
