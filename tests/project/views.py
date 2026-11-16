"""Pages that say who is asking - one for somebody signed in, two for anybody."""

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from httponly_jwt.authentication import OptionalAuthentication
from httponly_jwt.cookies import clear_session_cookies, set_session_cookies


def who(request: Request) -> Response:
    return Response({'person': request.user.get_username() or None})


class SignedIn(APIView):
    """Somebody signed in, or 401."""

    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        return who(request)


class Anybody(APIView):
    """Anybody - with the project's default authentication."""

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return who(request)


class AnybodyMoreIfSignedIn(APIView):
    """Anybody, never refused - and the person, when there is one."""

    authentication_classes = (OptionalAuthentication,)
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return who(request)


class SetsTheSessionItself(APIView):
    """Like signing in: the response carries a session the view chose."""

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return set_session_cookies(Response({}), access='chosen-access', refresh='chosen-refresh')


class ClearsTheSessionItself(APIView):
    """Like signing out: the response ends the session."""

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return clear_session_cookies(Response({}))
