"""
The CSRF check, for a frontend on another site.

The default needs none. The cookies are ``SameSite=Lax``, so the browser
attaches them only to requests from the same site - ``example.com`` and
``api.example.com`` are one site - and a write another site causes arrives
with nobody's authority. That is the protection, and it is why the default
asks the frontend for nothing.

A frontend on a different site needs ``SameSite=None``, and then the browser
attaches the cookie to whatever any site sends. ``CSRF = True`` puts Django's
CSRF check back, as DRF's ``SessionAuthentication`` has it: an unsafe request
authenticated by the cookie must carry the token in ``X-CSRFToken``, and one
that does not is refused with 403. A request authenticated by a header is not
asked - another site cannot set a header. The frontend reads the token from
``CsrfTokenView``, since a page on another site cannot read the API's cookie.

E001 refuses ``SameSite=None`` without it: the one combination that protects
nothing.
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied

from httponly_jwt.conf import httponly_jwt_settings as conf


def enforce_csrf(request: Any) -> None:
    """Refuse ``request`` with 403 when the CSRF mode is on and its token is missing or wrong."""
    if not conf.csrf:
        return

    check = CSRFCheck(_no_response)
    check.process_request(request)  # reads the CSRF cookie into request.META
    reason = check.process_view(request, _no_response, (), {})

    if reason:
        raise PermissionDenied(f'CSRF Failed: {reason}')


def _no_response(request: HttpRequest) -> HttpResponse:  # pragma: no cover - never called
    """The view the check stands in front of: it only answers whether to refuse."""
    return HttpResponse()
