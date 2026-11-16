# django-httponly-jwt

JWT sessions for Django in HttpOnly cookies, renewed by the server so quietly
that the frontend never holds a token.

[![PyPI](https://img.shields.io/pypi/v/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![Python](https://img.shields.io/pypi/pyversions/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![Django](https://img.shields.io/pypi/frameworkversions/django/django-httponly-jwt)](https://pypi.org/project/django-httponly-jwt/)
[![CI](https://github.com/amirAI-dot/django-httponly-jwt/actions/workflows/ci.yml/badge.svg)](https://github.com/amirAI-dot/django-httponly-jwt/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/pyproject.toml)
[![Licence](https://img.shields.io/pypi/l/django-httponly-jwt)](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/LICENSE)

[فارسی](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/README.fa.md) ·
[Guide](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/guide.md) ·
[Design](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/design.md) ·
[Example](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/example/README.md)

Signing in sets two HttpOnly cookies. When the access token runs out, the
server renews it on the way through - the request that found it expired is
answered, and the answer carries the new one. The frontend sends requests with
the cookies and goes to the sign-in screen on a 401; it never reads, stores or
refreshes a token, and no script on the page can.

* **Renews when the browser has already deleted the expired cookie** - the
  case the obvious middleware breaks.
* **Never rotates in the middleware**, so two tabs renewing together do not
  sign each other out. Rotation is the refresh view's, and it blacklists the
  old token.
* **Ends a session at the next renewal** when the account is switched off, or
  the project says so - not weeks later, when the refresh token expires.
* **Each person's session**: its length (staff for a day, customers for a
  month), and claims such as the role, read again at every renewal.
* **Refuses at start-up** what cannot work or protects nothing:
  `SameSite=None` without a CSRF check, renewal not installed, no blacklist.
* **Native apps and scripts** use `Authorization: Bearer` and get their tokens
  in the body; a frontend on another site gets Django's CSRF check back.
* Signals for an audit trail, drf-spectacular descriptions, sync and async,
  English and Persian.

It is a layer over [djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt):
simplejwt mints and checks the tokens; how a person proves who they are stays
the project's.

## Installing

```bash
pip install django-httponly-jwt
```

```python
# settings.py
INSTALLED_APPS = [..., 'rest_framework_simplejwt.token_blacklist', 'httponly_jwt']

MIDDLEWARE = [..., 'httponly_jwt.middleware.RenewalMiddleware', ...]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

```python
# views.py - the project signs the person in, its own way, then:
from httponly_jwt.sessions import start_session


class SignInView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])
        return start_session(Response({'id': person.pk}), person, request=request)
```

```python
# urls.py
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    path('auth/sign-in/', SignInView.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
```

```js
// The frontend: the cookies go with every request, and 401 means sign in again.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })
```

That is all of it: from there every request from the browser carries the
cookies, the middleware renews the access token when it runs out, and
`request.user` is the person. The [guide](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/guide.md) has the rest -
lifetimes and claims, the frontend, a frontend on another site, apps,
signals, the schema, every setting and every check - and
[`example/`](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/example/README.md) has all of it running.

Django 5.2 to 6.1, Python 3.11 to 3.14.

## Working on it

Every check runs through [nox](https://nox.thea.codes), the same sessions
locally and in CI. With [uv](https://docs.astral.sh/uv/) installed, a Python
that is missing is fetched for you.

```bash
uv tool install nox
```

```bash
nox -s lint
```

```bash
nox -s types
```

```bash
nox -s tests
```

`tests` runs every supported Python and Django, with 100% coverage; one
combination is `nox -s "tests(3.13-django6.1)"`, and `nox -l` lists them all.
`package` builds the wheel and runs the suite and the example against it. `messages` extracts
the marked strings again and fails if the Persian catalogue is missing one; it
needs gettext.

## Licence

BSD 3-Clause - see [`LICENSE`](LICENSE).
