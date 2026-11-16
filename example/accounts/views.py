"""
Signing in by a one-time code - the project's part. The library takes over at
``start_session``: from there the person is in the cookies, renewed on the way
through, and the frontend never sees a token.
"""

import logging
import secrets

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from httponly_jwt.sessions import start_session

logger = logging.getLogger(__name__)

CODE_LIFETIME = 120


class PhoneSerializer(serializers.Serializer):
    phone = serializers.RegexField(r'^\+[1-9]\d{6,14}$')


class CodeSerializer(PhoneSerializer):
    code = serializers.RegexField(r'^\d{6}$')


class SendCode(APIView):
    """A code for a phone number - printed in the server's output instead of sent."""

    permission_classes = (AllowAny,)
    serializer_class = PhoneSerializer

    def post(self, request: Request) -> Response:
        given = PhoneSerializer(data=request.data)
        given.is_valid(raise_exception=True)
        phone = given.validated_data['phone']
        code = f'{secrets.randbelow(10**6):06d}'
        cache.set(f'code:{phone}', code, CODE_LIFETIME)
        logger.info('accounts.code to=%s code=%s', phone, code)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SignIn(APIView):
    """The code typed back: the person is signed in, by cookies, with nothing in the body."""

    permission_classes = (AllowAny,)
    serializer_class = CodeSerializer

    def post(self, request: Request) -> Response:
        given = CodeSerializer(data=request.data)
        given.is_valid(raise_exception=True)
        phone, code = given.validated_data['phone'], given.validated_data['code']
        expected = cache.get(f'code:{phone}')

        if expected is None or not secrets.compare_digest(expected, code):
            return Response({'detail': 'Wrong or expired code.'}, status=400)

        cache.delete(f'code:{phone}')
        person, _ = User.objects.get_or_create(username=phone)
        return start_session(Response({'id': person.pk}), person, request=request)


class MeSerializer(serializers.Serializer):
    phone = serializers.CharField(source='username')
    role = serializers.CharField()


class Me(APIView):
    """Who is signed in, and the role the access token carries."""

    serializer_class = MeSerializer

    def get(self, request: Request) -> Response:
        role = request.auth['role'] if request.auth is not None else None
        return Response({'phone': request.user.get_username(), 'role': role})
