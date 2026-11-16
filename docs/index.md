# django-httponly-jwt

JWT sessions for Django in HttpOnly cookies, renewed by the server so quietly
that **the frontend never holds a token.**

Signing in sets two HttpOnly cookies. When the access token runs out, the
server renews it on the way through - the request that found it expired is
answered, and the answer carries the new one. The frontend sends requests with
the cookies and goes to the sign-in screen on a 401.

<div class="grid cards" markdown>

- **No token in the page.** HttpOnly cookies: no script can read them, so a
  script injected into the page cannot take the session away.
- **No refresh dance.** No interceptor, no retry, no race between tabs: the
  server renews, and the request is answered.
- **A session ends when it should** - at the next renewal after the account is
  switched off, and everywhere at once when the person signs out.
- **Refused at start-up** when it cannot work or protects nothing - not on
  the day somebody finds out.

</div>

## Install

```bash
pip install django-httponly-jwt
```

```python
INSTALLED_APPS = [..., 'rest_framework_simplejwt.token_blacklist', 'httponly_jwt']

MIDDLEWARE = [..., 'httponly_jwt.middleware.RenewalMiddleware', ...]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

Then a sign-in view hands the person to `start_session` - see the
[quickstart](getting-started/quickstart.md).

## Where to go

| | |
|---|---|
| [Introduction](getting-started/introduction.md) | what goes wrong with tokens in the browser, and what this does about it |
| [Quickstart](getting-started/quickstart.md) | a project signing people in, in five minutes |
| [The guide](guide.md) | every part, from signing in to a frontend on another site |
| [Reference](reference/index.md) | settings, checks, signals, and the Python API |
| [Design](design.md) | why it is built this way |

Django 5.2 to 6.1, Python 3.11 to 3.14, over
[djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt).
English and Persian. BSD licence.
