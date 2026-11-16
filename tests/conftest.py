"""
What the tests ask for: a person, and the tokens a browser or an app holds for
them - good ones, expired ones, and ones of the wrong kind.
"""

from collections.abc import Callable
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

Access = Callable[..., str]


@pytest.fixture
def person(db: None) -> User:
    return User.objects.create_user('ana', password='unused-in-tests')


@pytest.fixture
def access() -> Access:
    """An access token for a person - expired, when asked."""

    def make(user: User, *, expired: bool = False) -> str:
        token = AccessToken.for_user(user)

        if expired:
            token.set_exp(lifetime=-timedelta(seconds=1))

        return str(token)

    return make


@pytest.fixture
def refresh() -> Callable[[User], str]:
    """A refresh token for a person."""

    def make(user: User) -> str:
        return str(RefreshToken.for_user(user))

    return make
