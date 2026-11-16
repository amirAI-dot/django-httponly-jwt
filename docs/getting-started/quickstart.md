# Quickstart

A project that signs people in with a username and password, from the
[installation](installation.md) onwards. The sign-in is the project's - here
Django's own `authenticate`; [the example](https://github.com/amirAI-dot/django-httponly-jwt/tree/main/example)
does it with a one-time code. Everything after it is the library's.

## The sign-in, and a page to read

```python
# accounts/views.py
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from httponly_jwt.sessions import start_session


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = authenticate(
            request,
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if person is None:
            return Response({'detail': 'Wrong username or password.'}, status=400)
        return start_session(Response({'id': person.pk}), person, request=request)


class Me(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'username': request.user.get_username()})
```

`start_session` mints a pair for the person and sets both cookies on the
response. The body says nothing about tokens.

```python
# urls.py
from django.urls import path

from accounts.views import Me, SignIn
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    path('auth/sign-in/', SignIn.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
    path('me/', Me.as_view()),
]
```

## Trying it

```bash
python manage.py createsuperuser --username ana
```

Sign in. The answer is `{"id": 1}` and two `Set-Cookie` lines, both
`HttpOnly`:

```bash
curl -i -c jar -X POST localhost:8000/auth/sign-in/ -d username=ana -d password=...
```

The cookies are the session:

```bash
curl -b jar localhost:8000/me/
```

When the access token has run out, the same request is still answered: the
middleware renews it on the way through, and the answer sets the new one.
Signing out blacklists the refresh token and clears both cookies:

```bash
curl -b jar -c jar -X POST localhost:8000/auth/sign-out/
```

## The frontend

```js
const answer = await fetch('/me/', { credentials: 'include' })

if (answer.status === 401) location.assign('/sign-in')
```

That is the whole of it: send the cookies, and go to the sign-in screen on a
401. The frontend never reads, stores or refreshes a token. For a frontend on
another site, for apps, and for everything else, see [the guide](../guide.md).
