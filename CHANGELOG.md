# Changelog

[فارسی](CHANGELOG.fa.md)

## Unreleased

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
