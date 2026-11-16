# Introduction

## Where the tokens go wrong

A JWT session has two tokens: an **access token** that lives minutes and is
sent with every request, and a **refresh token** that lives days and buys new
access tokens. Most projects hand both to the frontend, and two things follow.

**The tokens are in the page.** Kept in `localStorage`, they are readable by
every script the page runs - its own, its dependencies', and any a bug lets
in. Whoever reads the refresh token holds the session for as long as it
lives.

**The frontend renews.** Every request may answer 401 because the access
token ran out, so the frontend needs an interceptor that notices, calls the
refresh endpoint, retries the request - and does it once when five requests
fail together, and once across three tabs. Each project writes it again, and
each gets a corner of it wrong.

## What this library does instead

The tokens go in **HttpOnly cookies**, which the browser sends by itself and
no script can read. And the server renews: when a request arrives with an
access cookie that is missing or expired and a refresh cookie that is still
good, a middleware mints a new access token, uses it for this request, and
sets it on the answer. The frontend never learns it happened.

The obvious version of that middleware is a page of code. Four things it gets
wrong, which this library does not:

| the obvious version | what happens | here |
|---|---|---|
| renews only when there is an access cookie to renew | the browser deletes an expired cookie, so it never renews | renews when the cookie is gone |
| rotates the refresh token on every renewal | two tabs renew together, one blacklists the other's token, and the person is signed out by their own tab | never rotates in the middleware |
| never asks about the account | a switched-off account keeps working until its refresh token expires | asks at every renewal |
| renews after the view ran | the request that found the token expired is refused | renews before the view reads the cookie |

Around it: rotation and blacklisting in a refresh view, signing out
everywhere, each person's session length and claims, refusing an unsafe
configuration at start-up, a CSRF mode for a frontend on another site,
signals, a drf-spectacular schema, and Persian.

## What it does not do

* **It does not sign anybody in.** A password, a one-time code, a social
  account - how a person proves who they are is the project's. The library
  takes over once the project knows: `start_session(response, person)`.
* **It does not replace simplejwt.** simplejwt mints and checks the tokens,
  and its settings - lifetimes, signing key, the user id claim - hold as they
  always have.
* **It is for Django REST framework**, in 0.1. Setting `request.user` for a
  plain Django view is the first thing after it.

Next: [installing it](installation.md).
