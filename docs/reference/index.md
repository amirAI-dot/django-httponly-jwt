# Reference

Everything the library offers, listed. The [guide](../guide.md) explains how
the parts fit; this section is for looking one up.

## Configuration

| page | what is there |
|---|---|
| [Settings](../guide.md) (section 13) | every key of `HTTPONLY_JWT`, with its default |
| [System checks](../guide.md) (section 14) | every `httponly_jwt.E0xx` and `W0xx`, and what it refuses at start-up |
| [Signals](api/signals.md) | every change to a session, and what each carries |

## Python API

Read from the code itself, so it never falls behind it. The descriptions are
the code's own, in English.

| page | what is there |
|---|---|
| [Sessions](api/sessions.md) | `start_session`, `issue_tokens`, and each person's lifetime and claims |
| [Authentication](api/authentication.md) | `CookieAuthentication`, `HeaderAuthentication`, `OptionalAuthentication` |
| [Renewal](api/middleware.md) | `RenewalMiddleware`, and the steps it is made of |
| [Views](api/views.md) | `RefreshView`, `SignOutView`, `CsrfTokenView`, and the CSRF check |
| [Signals](api/signals.md) | the four signals, and `Ended` |
| [Cookies](api/cookies.md) | setting, clearing and reading the session cookies |
| [The schema](api/schema.md) | the drf-spectacular extensions |
