# Security

django-httponly-jwt holds sessions. A way round it - a session used by
somebody it was not given to, a token that keeps working after it was ended,
a request another site causes carrying the person's authority - is a security
problem, and is treated as one.

## Reporting one

**Report it privately, not in a public issue.** On GitHub, open the
repository's *Security* tab and choose *Report a vulnerability*. The report
is seen only by the maintainers until a fix is out.

Say what you can of:

* what somebody can do that they should not;
* the steps, or a test that shows it;
* the configuration - `HTTPONLY_JWT`, `SIMPLE_JWT` - and the versions of the
  library, Django, DRF, simplejwt and Python.

## What happens next

The problem is reproduced, fixed in a release with a test that holds it, and
the changelog says what was wrong, who was affected and what to do - as it
did for 0.1.1, where a blacklisted refresh token could work again after
`flushexpiredtokens`.

## Supported versions

Fixes go into the latest release. The library is young - alpha, `0.x` - so
upgrading to the latest release is the way to receive one.

## What the library relies on

* **simplejwt** for the tokens themselves - the signature, the expiry, the
  blacklist.
* **The browser** for the cookie flags - HttpOnly, Secure, SameSite. A
  configuration whose flags protect nothing is refused at start-up; see the
  checks in [the guide](../guide.md), section 14.
* **The project** for signing people in, and for keeping the signing key
  secret.
