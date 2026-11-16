# The guide

> Persian: [`guide.fa.md`](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/guide.fa.md).

Everything django-httponly-jwt does, and how a project uses it. Why it is
built this way is in the [design](design.md); a project with all of it in
place is in [`example/`](../example/).

## 1. What it is for

A frontend that keeps a JWT in `localStorage` hands it to every script on the
page, and one that keeps a refresh token has to notice a 401, call a refresh
endpoint, retry the request - and get it right in every tab at once. This
library takes both away from the frontend:

* **the tokens live only in HttpOnly cookies** - no script can read them;
* **the server renews the access token on the way through** - the request that
  found it expired is answered, and the answer carries the new one;
* **the frontend never holds a token**: it sends requests with the cookies and
  goes to the sign-in screen when a request answers 401.

It is a layer over [djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt):
simplejwt mints and checks the tokens, and its settings hold as they always
have. How a person proves who they are - a password, a one-time code, a
social account - stays the project's.

## 2. Installing

```bash
pip install django-httponly-jwt
```

With the drf-spectacular schema described (section 12):

```bash
pip install "django-httponly-jwt[spectacular]"
```

Django 5.2 to 6.1, Python 3.11 to 3.14, DRF 3.16 and simplejwt 5.5 or newer.

## 3. Setting it up

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'rest_framework_simplejwt.token_blacklist',
    'httponly_jwt',
]

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
```

```python
# urls.py
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    ...,
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
```

```bash
python manage.py migrate
```

`migrate` creates simplejwt's blacklist tables. Nothing else is required:
`HTTPONLY_JWT` is needed only to change a default (section 13), and every
mistake in it is refused when the project starts (section 14).

Put `RenewalMiddleware` before anything that reads who is asking - after
Django's `SecurityMiddleware` and `CommonMiddleware` is the usual place.

## 4. Signing in

The project checks who the person is, its own way, then hands them over:

```python
from httponly_jwt.sessions import start_session

class SignInView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])   # the project's
        return start_session(Response({'id': person.pk}), person, request=request)
```

`start_session` mints a pair - with the person's claims and lifetime (section
7) - sets both cookies on the response and returns it. `request=` is passed on
to `session_started` (section 11) and may be left out.

Both cookies are HttpOnly, `Secure`, `SameSite=Lax` and `Path=/`, and both
last as long as the refresh token: the access cookie outlives its token on
purpose, so the middleware finds a stale token rather than none.

A native client keeps its tokens itself. `issue_tokens` mints the same pair
and sets nothing:

```python
from httponly_jwt.sessions import issue_tokens

tokens = issue_tokens(person, request=request)
return Response({'access': tokens.access, 'refresh': tokens.refresh})
```

## 5. Renewal

When the access cookie is missing or no longer good and the refresh cookie
is, `RenewalMiddleware` mints a new access token, uses it for this request,
and sets it on the answer. The view never learns it happened.

* **It renews when the browser has already deleted the access cookie**, not
  only when the cookie holds an expired token.
* **It asks whether the person may still be signed in** - `is_active`, and
  `USER_CAN_SIGN_IN` (section 7). Switching an account off ends its sessions
  at the next renewal, not when its refresh token expires.
* **It reads the claims again**, so a role changed today is in the next
  access token.
* **It never rotates the refresh token.** Two tabs renewing together would
  each blacklist the other's token, and the person would be signed out by
  their own second tab.
* **It leaves alone a response that set or cleared the session itself** -
  signing in, signing out.

A session that is over - the refresh token expired, blacklisted or
unreadable, the person gone or not allowed in - has both cookies cleared, and
the request goes on as nobody's.

A request with a good access token costs a signature check and no query. A
renewal costs two: whether the refresh token was blacklisted, and loading the
person. It works under WSGI and ASGI.

A client signed in by header, with no refresh cookie, is left alone: no
cookie is set or cleared for it.

## 6. Refreshing and signing out

Both views read the refresh token from its cookie first, then from the body as
`{"refresh": "..."}`, and answer the way it came.

**`RefreshView`** (`POST`) rotates: the token presented is blacklisted and a
new pair issued, with the person's claims and lifetime read again - so it also
extends the session by a full lifetime. A refresh token can therefore be used
once.

| the token came | answer |
|---|---|
| in the cookie | `204`, both cookies set; never a token in the body |
| in the body | `200`, `{"access": "...", "refresh": "..."}`; no cookie |
| and cannot be honoured | `401`, `{"detail": "...", "code": "session_ended"}`; the cookies cleared when it came in one |

A browser seldom needs it - the middleware renews without it. It is for a
native client, and for a frontend that wants a session extended on purpose.

**`SignOutView`** (`POST`) blacklists the refresh token, so no copy of it
renews anywhere, clears both cookies, and answers `204` whatever it was
given: a person asking to be signed out is signed out either way.

Neither view takes authentication - the refresh token is the credential, and
signing out must work when the access token has run out. Both are ordinary
DRF views a project may subclass, throttle and mount where it likes.

## 7. Each person's session

Three settings name a function of the person, by dotted path:

```python
HTTPONLY_JWT = {
    'REFRESH_LIFETIME': 'myproject.auth.session_length',
    'CLAIMS': 'myproject.auth.claims',
    'USER_CAN_SIGN_IN': 'myproject.auth.may_sign_in',
}
```

```python
# myproject/auth.py
def session_length(person):
    """Staff for a working day; everybody else simplejwt's REFRESH_TOKEN_LIFETIME."""
    return timedelta(hours=8) if person.is_staff else None


def claims(person):
    """What both tokens carry beyond who the person is."""
    return {'role': person.role}


def may_sign_in(person):
    """Asked beside is_active, at every renewal and refresh."""
    return not person.is_suspended
```

* **`REFRESH_LIFETIME`** answers a `timedelta`, or `None` for simplejwt's
  `REFRESH_TOKEN_LIFETIME`. The cookies last as long.
* **`CLAIMS`** answers a dictionary. It is asked at sign-in, at every renewal
  and at every refresh. It may not set simplejwt's own claims - who the token
  is for, its type, `jti`, `exp`, `iat` - and one that tries is
  `ImproperlyConfigured`, not a token for somebody else.
* **`USER_CAN_SIGN_IN`** answers whether the person may still hold a session.

A view reads the claims from `request.auth`:

```python
role = request.auth['role']
```

## 8. The frontend

The frontend and the API must be on **one site** - `example.com` and
`api.example.com` are one site - so the browser attaches the cookies to the
API's requests and to nobody else's. Then:

```js
// Every request sends the cookies.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })

if (answer.status === 401) {
  // The session is over: the middleware has already cleared the cookies.
  location.assign('/sign-in')
}
```

* It never reads, stores or sends a token. It cannot - the cookies are
  HttpOnly - and it does not need to.
* It never calls the refresh endpoint to keep a session going: renewal happens
  on the way through.
* Signing out is a `POST` to the sign-out view.
* A different subdomain for the API needs `COOKIE_DOMAIN`, such as
  `'.example.com'`, when the frontend reads the session on its own server too;
  and the API's CORS settings must allow the frontend's origin with
  credentials.

When the frontend renders on the server (Next.js, for instance), the server
forwards the browser's `Cookie` header to the API and passes any `Set-Cookie`
in the answer back to the browser - or the renewed token is lost on the way.

## 9. A frontend on another site

When the frontend is on a different site from the API, the browser will send
the cookies only if they are `SameSite=None` - and then it sends them with a
request any site causes. That needs Django's CSRF check back:

```python
HTTPONLY_JWT = {'COOKIE_SAMESITE': 'None', 'CSRF': True}

CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = ['https://app.example.org']
```

```python
from httponly_jwt.views import CsrfTokenView

urlpatterns += [path('auth/csrf/', CsrfTokenView.as_view())]
```

* The frontend asks `auth/csrf/` for the token - a page on another site cannot
  read the API's cookie - and sends it in `X-CSRFToken` on every write.
* An unsafe request the cookie authenticates without it is refused with 403.
* A request signed in by header is never asked: another site cannot set one.
  A stale cookie is still nobody, not a CSRF failure.
* The refresh and sign-out views ask too, when the refresh token came in the
  cookie, so another site can neither rotate a session nor end it.
* `OptionalAuthentication` serves a cookie write without the token as a
  guest's.

`SameSite=None` without the check is refused at start-up (E001), and so is
`SameSite=None` without `Secure` (E005). W002 names a Django CSRF setting that
would refuse the frontend's every write.

## 10. Apps, scripts and optional sign-in

**`HeaderAuthentication`** is simplejwt's `Authorization: Bearer` under the
library's name. A native app or a script signs in with `issue_tokens` (section
4), refreshes and signs out with the body (section 6), and is never sent a
cookie. A bad header is refused with 401 - it was sent on purpose.

**`CookieAuthentication`** treats a cookie that is expired, unreadable, a
refresh token, or names an account gone or switched off as **nobody** rather
than an error: a page that needs somebody answers 401, and a page open to
anybody serves a guest.

**`OptionalAuthentication`** is for an endpoint anybody may call that does
more for somebody signed in: the cookie, then the header, and never a
refusal - a guest is not turned away for a stale token they did not mean to
send.

```python
from httponly_jwt.authentication import OptionalAuthentication

class Catalogue(APIView):
    authentication_classes = (OptionalAuthentication,)
    permission_classes = (AllowAny,)
```

## 11. Signals

Sent once the answer is decided, each with `person` and `request`, for a
project's audit trail:

| signal | when |
|---|---|
| `session_started` | `start_session` or `issue_tokens` signed somebody in |
| `session_renewed` | the middleware renewed the access token, and the renewal reached the answer |
| `session_refreshed` | `RefreshView` rotated the refresh token |
| `session_ended` | with `reason`: `signed_out`, `token_unusable` or `not_allowed` |

```python
from django.dispatch import receiver
from httponly_jwt.signals import Ended, session_ended

@receiver(session_ended)
def note_it(sender, person, request, reason, **kwargs):
    if reason == Ended.NOT_ALLOWED:
        AuditEntry.objects.create(person=person, what='refused at renewal')
```

`person` is `None` when the token named nobody the library could load.
Under ASGI the middleware sends with `asend`, so a receiver that writes to the
database runs where it may.

## 12. The schema

With the `spectacular` extra installed, drf-spectacular describes:

* `CookieAuthentication` as an `apiKey` in the cookie, under the name the
  project chose (`httponlyJwtCookie`);
* `HeaderAuthentication` as simplejwt's bearer scheme (`jwtAuth`), so listing
  simplejwt's own class beside it is one scheme;
* `OptionalAuthentication` as either;
* the refresh, sign-out and CSRF-token views, with every answer.

Nothing to configure: the descriptions load when drf-spectacular is installed,
and the schema is generated without a warning about the library.

## 13. Settings

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
| `REFRESH_LIFETIME` | `None` | a dotted path: `(person) -> timedelta \| None` |
| `CLAIMS` | `None` | a dotted path: `(person) -> dict` |
| `USER_CAN_SIGN_IN` | `None` | a dotted path: `(person) -> bool`, asked beside `is_active` |
| `ALLOW_WITHOUT_BLACKLIST` | `False` | run without simplejwt's blacklist, accepting that a token cannot be ended |

The token lifetimes, the signing key and the user id claim are simplejwt's
own settings, in `SIMPLE_JWT`.

## 14. What is refused at start-up

`manage.py check`, and so `runserver` and `migrate`, refuse what cannot work:

| id | when | level |
|---|---|---|
| `httponly_jwt.E001` | `COOKIE_SAMESITE` is `None` and `CSRF` is off | error |
| `httponly_jwt.E002` | the cookie authenticates and `RenewalMiddleware` is not installed | error |
| `httponly_jwt.E003` | a key the library does not know, or a value it cannot use | error |
| `httponly_jwt.E004` | `token_blacklist` is not installed | error, unless `ALLOW_WITHOUT_BLACKLIST` |
| `httponly_jwt.E005` | `COOKIE_SAMESITE` is `None` and `COOKIE_SECURE` is off | error |
| `httponly_jwt.W001` | `COOKIE_SECURE` is off (`check --deploy`) | warning |
| `httponly_jwt.W002` | the CSRF check is on for another site, and Django's CSRF settings would refuse its writes | warning |

## 15. Languages

The library's own words - the refusal when a session has ended, the schema's
descriptions - come in English and Persian, and follow the request's language
as the rest of Django does.
