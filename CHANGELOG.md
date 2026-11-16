# Changelog

[فارسی](CHANGELOG.fa.md)

## Unreleased

Around it (stage 6):

* **Signals** - `session_started`, `session_renewed`, `session_refreshed` and
  `session_ended`, each with the person and the request, for a project's audit
  trail. `session_ended` carries `reason`, an `Ended`: `signed_out`,
  `token_unusable` or `not_allowed`. A renewal a view overruled is not sent.
  Under ASGI the middleware sends with `asend`. `start_session` and
  `issue_tokens` take `request=` to pass it on.
* **drf-spectacular**, with the `spectacular` extra: the cookie is an
  `apiKey` scheme under the name the project chose, the header simplejwt's
  `jwtAuth`, the optional class either of them; the refresh, sign-out and
  CSRF-token views say what they read and answer. Loaded only when
  drf-spectacular is installed, and described without a warning.
* **Persian** - the catalogue in `httponly_jwt/locale/fa`, compiled and
  shipped; `nox -s messages` fails when a marked string is missing from it.

CSRF (stage 5):

* **`CSRF = True`**, for a frontend on another site with `SameSite=None`: an
  unsafe request the cookie authenticates must carry Django's CSRF token in
  `X-CSRFToken`, or it is refused with 403. A header-signed request is not
  asked, and a stale cookie is still nobody. `RefreshView` and `SignOutView`
  ask when the refresh token came in the cookie, so another site can neither
  rotate a session nor end it. `OptionalAuthentication` serves a cookie write
  without the token as a guest's.
* **`CsrfTokenView`** hands the token to a frontend that cannot read the API's
  cookie.
* **E001**: `SameSite=None` with the check off - any site could act with the
  session. **E005**: `SameSite=None` without `Secure` - browsers refuse the
  cookie. **W002**: the check is on, and Django's `CSRF_COOKIE_SAMESITE`,
  `CSRF_COOKIE_SECURE` or `CSRF_TRUSTED_ORIGINS` would refuse every write.

Sessions (stage 4):

* **`start_session(response, person)`** signs in a person the project has
  identified its own way: a new pair, in both cookies.
  **`issue_tokens(person)`** mints the pair and sets nothing, for a native
  client.
* **`REFRESH_LIFETIME`** - a function of the person: how long their session
  lasts. **`CLAIMS`** - what both tokens carry about them, asked again at every
  renewal, so a role changed today is in the next access token. A claim that
  would overwrite simplejwt's own - who the token is for, its type, `jti`,
  `exp`, `iat` - is refused.
* **`RefreshView`** rotates: the token presented is blacklisted and a new pair
  issued, so a refresh token can be used once. A browser gets `204` and
  cookies, a native client the pair in the body. A refresh for somebody who
  may not sign in is `401`, `session_ended`.
* **`SignOutView`** blacklists the refresh token and clears both cookies - a
  copy of the token elsewhere can no longer renew - and answers `204` whatever
  it was given.

Renewal (stage 3):

* **`RenewalMiddleware`** renews an expired access token on the way through,
  and the request that found it expired is served. It renews when the browser
  has already deleted the access cookie; asks whether the person may still be
  signed in - `is_active`, and `USER_CAN_SIGN_IN`; never rotates the refresh
  token, so two tabs renewing together both stay signed in; and leaves alone a
  response that set or cleared the session itself. A session that is over -
  expired, blacklisted, an account gone or switched off - is cleared. Sync and
  async.
* A good access token costs no query; a renewal costs two - the blacklist,
  and the person.
* **E002**: the cookie authenticates and `RenewalMiddleware` is not installed -
  every session would end with its first access token.

Authentication (stage 2):

* **`CookieAuthentication`** - a browser is the person its access cookie
  names. A cookie that is expired, unreadable, a refresh token, or names an
  account gone or switched off is nobody rather than an error: a page that
  needs somebody answers 401, and a page open to anybody serves a guest.
* **`HeaderAuthentication`** - `Authorization: Bearer` for apps and scripts; a
  bad header is refused, since it was sent on purpose.
* **`OptionalAuthentication`** - the cookie, then the header, and never a
  refusal: for an endpoint anybody may call that does more for somebody
  signed in.

The skeleton, from the design (stage 1):

* **The `HTTPONLY_JWT` setting**, read and checked: every key has a default,
  and a key the library does not know, or a value it cannot use, stops the
  project at start-up.
* **The session cookies, written in one place.** `HttpOnly` always; `Secure`,
  `SameSite=Lax` and `Path=/` by default; both cookies as long as the refresh
  token, so the access cookie is never gone when it has to be renewed; and
  cleared with the flags they were set with.
* **The first system checks**: E003 (the setting), E004 (no blacklist to end a
  token with), W001 (cookies sent over plain HTTP, on `check --deploy`).
