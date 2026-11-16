# The example

[فارسی](README.fa.md)

An API signed in to by a one-time code, the way most projects in Iran sign
people in - and every part of django-httponly-jwt in place, each in the file
you would put it in:

| what | where |
|---|---|
| the middleware, the authentication classes, `HTTPONLY_JWT` | `config/settings.py` |
| the library's refresh and sign-out views, and the schema | `config/urls.py` |
| the project's own sign-in, handing over to `start_session` | `accounts/views.py` |
| a session's length, the role in the token, an account the project closes | `accounts/sessions.py` |
| an audit trail written from the signals | `accounts/receivers.py`, `accounts/models.py` |
| what all of it adds up to | `accounts/tests.py` |

## Running it

From the repository's root, with the library installed in a fresh
environment:

```bash
python -m venv .venv && .venv/bin/pip install -e '.[spectacular]'
```

```bash
cd example
```

```bash
../.venv/bin/python manage.py migrate
```

```bash
../.venv/bin/python manage.py runserver
```

The cookies are `Secure`, and browsers accept a `Secure` cookie from
`http://localhost`, so nothing needs changing to try it.

## Signing in

Ask for a code. It is printed in the server's output instead of sent by SMS -
`accounts.code to=+989121234567 code=123456`:

```bash
curl -i -X POST localhost:8000/auth/code/ --data-urlencode phone=+989121234567
```

Type it back. The answer is `{"id": 1}` and two `Set-Cookie` lines - no token
in the body:

```bash
curl -i -c jar -X POST localhost:8000/auth/sign-in/ --data-urlencode phone=+989121234567 -d code=123456
```

From there the cookies are the session:

```bash
curl -b jar localhost:8000/me/
```

`{"phone": "+989121234567", "role": "customer"}` - the role came in the
access token. After fifteen minutes the access token has run out, and the
same request is still answered: the middleware renewed it on the way through,
and the answer sets the new one.

```bash
curl -b jar -c jar -X POST localhost:8000/auth/sign-out/
```

Signed out, everywhere: the refresh token is blacklisted, so a copy of the
jar on another machine no longer renews either.

## Tests

```bash
../.venv/bin/python manage.py test
```

`nox -s package` runs them against the built wheel, so a file left out of the
package fails there.
