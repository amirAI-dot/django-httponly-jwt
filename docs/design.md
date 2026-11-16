# django-httponly-jwt - design

> **Status: first edition, accepted.** The owner's four decisions are in
> section 14. Nothing is built that this document does not describe; a change
> to it comes first, in its own pull request.
>
> Persian: [`design.fa.md`](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/design.fa.md).

**django-httponly-jwt** - JWT sessions for Django in HttpOnly cookies, renewed
by the server so quietly that the frontend never holds a token.

## In one paragraph

Signing in sets two HttpOnly cookies - a short-lived access token and a
long-lived refresh token - that no script can read. When the access token
runs out, a middleware renews it on the way through: the request that found
it expired is answered as if nothing happened, and the new token goes back
in the response. The frontend never sees a token, never handles a 401 to
refresh, and never stores anything. A native app or a script sends the token
in a header instead. Everything about the cookies - their names, their flags,
how they are cleared - lives in one place, and a project that sets them
unsafely does not start.

---

## 1. Why it exists

Django REST framework with simplejwt hands both tokens to the client in a
JSON body. Keeping them out of reach of scripts means cookies; keeping the
session alive without the frontend's help means the server renews them. Each
project that wants both writes the same three pieces - cookie helpers, an
authentication class, a renewal middleware - and the obvious version of each
is wrong in a way that does not show:

| the obvious version | what goes wrong |
|---|---|
| renew only when an access cookie is present and expired | the browser deletes an expired cookie, so when renewal is needed there is nothing to find: the person is signed out with weeks left on their refresh token |
| the access cookie lives as long as the access token | the same thing, from the other side |
| renew from any valid refresh token | an account switched off an hour ago is handed fresh access tokens until its refresh token expires - days later |
| rotate the refresh token on every silent renewal | two requests from two tabs renew together, one blacklists the token the other is using, and the person is signed out by their own second tab |
| set the new access token on the response only | the request that found the token expired still fails; every session answers one 401 an hour |
| write each cookie's flags where it is set | four places that set them and one that clears them; a cookie cleared with different flags is not cleared at all - the browser keeps it |
| `SameSite=None` because the frontend is on another domain | with no CSRF check, any site can cause a request that carries the session |

These were found in three projects of the owner's and in the libraries that
exist (section 13). This library is the corrected version, written once.

## 2. Principles

1. **The frontend never holds a token.** Both live in HttpOnly cookies.
   A header is for clients that are not browsers.
2. **Renewal is the server's, and invisible.** A request that arrives with
   an expired access token and a good refresh token is served, and leaves
   with a new access token.
3. **Switching an account off ends its sessions** at the next renewal, at
   the latest - not when the refresh token expires.
4. **One place knows the cookies.** Every flag is set by the same functions,
   and clearing uses the flags the cookie was set with.
5. **Unsafe is refused at start-up.** Cookies a browser would send on a
   request another site caused, with nothing to stop it, are a system check
   error - not a line in the documentation.
6. **Small.** It does not sign anybody in. How a person proves who they are -
   a password, a one-time code, a social account - is the project's. The
   library starts at "this person is signed in" and ends at "they signed
   out".
7. **Built on simplejwt.** Tokens, signing, lifetimes, the blacklist: all
   simplejwt's. The library adds cookies and renewal; it does not reimplement
   cryptography.

## 3. What is in it, and what is not

| in | not in |
|---|---|
| setting, renewing and clearing the session cookies | signing in - passwords, one-time codes, social login |
| the renewal middleware | registration, e-mail verification, password reset |
| DRF authentication: cookie, header, and "if anybody" | permissions and roles - that is django-clearance's |
| a refresh view (rotation) and a sign-out view (blacklist) | token storage of its own |
| a helper that starts a session for a person the project signed in | a frontend |
| system checks on the cookie flags | |
| an optional CSRF check, for a frontend on another site | |
| a lifetime per person - by role, by anything | |
| signals: started, renewed, ended | |
| drf-spectacular descriptions, when it is installed | |

## 4. The API, by example

```python
# settings.py
INSTALLED_APPS = [..., 'rest_framework_simplejwt.token_blacklist', 'httponly_jwt']

MIDDLEWARE = [
    ...,
    'httponly_jwt.middleware.RenewalMiddleware',
    ...,
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}

HTTPONLY_JWT = {
    'COOKIE_DOMAIN': '.example.com',       # the frontend and the API share the site
}
```

```python
# The project signs the person in, its own way, then:
from httponly_jwt.sessions import start_session

class SignInView(APIView):
    def post(self, request):
        user = verify_code(request.data['phone'], request.data['code'])   # the project's
        return start_session(Response({'id': user.pk}), user)
```

```python
# urls.py
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
```

From there, every request from the browser carries the cookies, the
middleware renews the access token when it runs out, and `request.user` is
the person. Nothing else is written.

## 5. The cookies

Two cookies, `access_token` and `refresh_token` by name (settable):

| flag | value | why |
|---|---|---|
| `HttpOnly` | always | no script reads either token; this is the point |
| `Secure` | on, unless `COOKIE_SECURE` says otherwise | refused off in production (section 10) |
| `SameSite` | `Lax` | the browser attaches the cookie only to requests from the same site |
| `Path` | `/` | the middleware must see the refresh cookie on ordinary requests; scoped to the auth endpoints, renewal would only work on the auth endpoints |
| `Domain` | `COOKIE_DOMAIN` | `.example.com` when the API is `api.example.com` and the frontend `example.com` |
| `Max-Age` | the refresh token's lifetime, for **both** | the access cookie must outlive the access token, or the browser deletes it and there is nothing to renew from |

`httponly_jwt.cookies` is the only code that sets or clears them:

```python
set_session_cookies(response, access=..., refresh=...)
set_access_cookie(response, access)
clear_session_cookies(response)          # with the flags they were set with
read_access_token(request)
read_refresh_token(request)
```

## 6. Renewal

`RenewalMiddleware` runs before any view; it touches only cookies, so its
place among Django's own middleware does not matter:

1. **No refresh cookie** - nothing to do. A client that authenticates by
   header never had one, and clearing would delete cookies it never set.
2. **A usable access token** - nothing to do. Usable is: present, signed, not
   expired. No database query.
3. **Otherwise** - the access cookie is missing, expired or unreadable:
   1. the refresh token is read; if it is expired, malformed or blacklisted,
      the session is over and both cookies are cleared on the way out;
   2. the person is loaded and must be active - `is_active`, and whatever
      `USER_CAN_SIGN_IN` adds; if not, the session is over;
   3. a new access token is minted, with the claims `CLAIMS` adds;
   4. it is put into the request's cookies, so **this** request authenticates
      with it, and set on the response.

It does **not** rotate the refresh token: two requests renewing together
would blacklist each other's. Rotation is the refresh view's, which a client
calls on purpose (section 8).

A response that already sets or clears the session cookies - a view that
signed somebody in or out - keeps them: the renewal never undoes what the
view decided.

Renewal costs two queries - whether the refresh token was blacklisted, and
loading the person - once per access-token lifetime per session. Every other
request costs a signature check and no query.

The middleware works under WSGI and ASGI, as a sync and async middleware.

## 7. Authentication

| class | reads | for |
|---|---|---|
| `CookieAuthentication` | the access cookie | browsers |
| `HeaderAuthentication` | `Authorization: Bearer ...` | native apps, scripts, tests |
| `OptionalAuthentication` | the cookie, then the header; never refuses | an endpoint anybody may call that does more for somebody signed in |

`CookieAuthentication` returns no user, rather than an error, when the
cookie is missing or invalid: DRF moves on to the next class and answers a
plain 401. The middleware has already had its chance to renew.

`OptionalAuthentication` exists because the ordinary classes answer a stale
header with a 401, which turns a guest away for a token they did not mean to
send.

## 8. The views

- **`RefreshView`** - `POST`. Reads the refresh token from the cookie, or the
  body for a native client. Checks the person is still allowed in, blacklists
  the old refresh token (rotation), and sets both cookies again - or returns
  the pair in the body to a client that sent its token in the body.
- **`SignOutView`** - `POST`. Blacklists the refresh token and clears both
  cookies. A token that is unreadable or already blacklisted is not an error:
  the caller asked to be signed out, and they are.

Both ask the cookie first and the body second, and answer the way the token
came: from the cookie, `204` and cookies, never a token in a body; from the
body, the pair in the body (`200`) and no cookie. A refresh that cannot be
honoured is `401` with `code: session_ended`, and clears the cookies when the
token came in one. A refresh issues a full new lifetime, so it also extends
the session.

Both are ordinary DRF views a project may subclass, throttle and mount where
it likes.

`start_session(response, user)` mints a pair for `user` - with the claims
and the lifetime the settings give that person - and sets both cookies.
`issue_tokens(user)` returns the pair without setting anything, for a native
client's sign-in.

## 9. Lifetimes and claims

simplejwt's `ACCESS_TOKEN_LIFETIME` and `REFRESH_TOKEN_LIFETIME` stay the
defaults. Two settings add what a project needs beyond them:

```python
HTTPONLY_JWT = {
    # A patient stays signed in for months; staff for a working day.
    'REFRESH_LIFETIME': 'myproject.auth.session_length',      # (user) -> timedelta | None
    # The role travels in the token, so the frontend need not ask.
    'CLAIMS': 'myproject.auth.claims',                        # (user) -> dict
}
```

`CLAIMS` is asked again at every renewal and every refresh, so a role changed
today is in the next access token without signing anybody out. It may not set
simplejwt's own claims - who the token is for, its type, `jti`, `exp`, `iat` -
and one that tries is `ImproperlyConfigured`, not a token for somebody else.

## 10. CSRF, and the system checks

A cookie the browser attaches by itself could be attached to a request
another site caused. Two things can stop that:

1. **`SameSite=Lax` or `Strict`** - the browser attaches the cookie only to
   requests from the same site. `example.com` and `api.example.com` are one
   site. This is enough when the frontend and the API share a site, and it
   is the default.
2. **A CSRF check** - needed when they do not, and the cookie must be
   `SameSite=None`. `CSRF = True` makes `CookieAuthentication` require
   Django's CSRF token on unsafe methods, as DRF's `SessionAuthentication`
   does.

The checks make the combination that protects nothing impossible:

| id | when | level |
|---|---|---|
| `httponly_jwt.E001` | `COOKIE_SAMESITE` is `None` and `CSRF` is off | error |
| `httponly_jwt.E002` | `CookieAuthentication` is used and `RenewalMiddleware` is not installed - sessions would end with their first access token | error |
| `httponly_jwt.E003` | a setting the library does not know, or a value it cannot use | error |
| `httponly_jwt.E004` | `token_blacklist` is not installed - rotation and sign-out could not end a token | error, unless `ALLOW_WITHOUT_BLACKLIST` |
| `httponly_jwt.W001` | `COOKIE_SECURE` is off (`check --deploy`) | warning |

## 11. Signals

Sent after the response is decided, each with the person and the request:
`session_started`, `session_renewed`, `session_refreshed` (rotation),
`session_ended` (signed out, or ended by the middleware - with the reason).
For a project's audit trail.

## 12. Settings

All under `HTTPONLY_JWT`; the default needs none of them.

| key | default | |
|---|---|---|
| `ACCESS_COOKIE` | `'access_token'` | the access cookie's name |
| `REFRESH_COOKIE` | `'refresh_token'` | the refresh cookie's name |
| `COOKIE_DOMAIN` | `None` | |
| `COOKIE_PATH` | `'/'` | |
| `COOKIE_SAMESITE` | `'Lax'` | `Lax`, `Strict` or `None` |
| `COOKIE_SECURE` | `True` | |
| `CSRF` | `False` | require Django's CSRF token on cookie-authenticated writes |
| `REFRESH_LIFETIME` | `None` | a dotted path: `(user) -> timedelta`, or `None` for simplejwt's |
| `CLAIMS` | `None` | a dotted path: `(user) -> dict` of claims added to both tokens |
| `USER_CAN_SIGN_IN` | `None` | a dotted path: `(user) -> bool`, asked beside `is_active` |
| `ALLOW_WITHOUT_BLACKLIST` | `False` | |

## 13. What exists already

| | renews in a middleware | renews when the access cookie is gone | checks the account is active | no rotation in the middleware | one place for the flags | refuses unsafe flags |
|---|---|---|---|---|---|---|
| dj-rest-auth | no - the client calls a refresh view | - | - | - | - | - |
| django-cookiejwt 0.0.2 | yes | no | on authentication | yes | yes | no |
| secure-bite 0.1.4 | yes - on every request | yes | no | yes | partly | no |
| **django-httponly-jwt** | yes | yes | yes | yes | yes | yes |

A dash is a question that does not arise, or one not checked in its code.
dj-rest-auth is the established choice, and much larger: registration, social
accounts, password reset. This library does not compete with it; a project
can use dj-rest-auth to sign in and this to keep the session.

## 14. Decisions

The owner's, on the first edition:

1. **No CSRF token by default.** The cookies are `SameSite=Lax`, which is the
   protection when the frontend and the API share a site; E001 refuses the
   combination that would protect nothing, and `CSRF = True` serves a
   frontend on another site.
2. **The cookies are `access_token` and `refresh_token`**, the names the
   owner's projects use already, so their frontends notice nothing when they
   move onto the library.
3. **Django's own views come after 0.1.** 0.1 is DRF's: the authentication
   classes are DRF's, and so are the owner's projects. Setting
   `request.user` for a plain Django view is the first thing after it.
4. **The documentation is in English and Persian**, as django-clearance's,
   each page beside its twin.

## 15. Compatibility and conventions

Python 3.11 - 3.14; Django 5.2, 6.0, 6.1; DRF 3.16+; simplejwt 5.5+. The
conventions of django-clearance: English in the code, every message marked
for translation with the Persian in the catalogue, tests named after the
behaviour they hold, ruff and mypy strict, 100% coverage, nox, one stage per
pull request, released from a tag by Trusted Publishing.

## 16. Stages

| | stage | delivers |
|---|---|---|
| 0 | design | this document, accepted |
| 1 | skeleton | the package, settings, `httponly_jwt.cookies`, the checks, CI |
| 2 | authentication | the three classes |
| 3 | renewal | the middleware, sync and async |
| 4 | sessions | `start_session`, `issue_tokens`, the refresh and sign-out views, lifetimes and claims |
| 5 | CSRF | the CSRF mode, and E001 |
| 6 | around it | signals, drf-spectacular, Persian |
| 7 | release | documentation, an example project, 0.1.0 on PyPI |
| 8 | adoption | DayarDarman, Elin and Idehsaz on the library |

After 0.1, first: Django's own views - `request.user` set for a view that is
not DRF's (decision 3).
