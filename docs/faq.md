# Questions

## Is a cookie really safer than `localStorage`?

Against the attack that matters most, yes. A script injected into the page can
read `localStorage` and send the refresh token anywhere - and the session is
theirs for as long as it lives, from any machine. It cannot read an HttpOnly
cookie. While the page is open it can still make requests as the person, as
it could with any kind of session; once the page is closed, it has nothing.

## Then what stops another site from using the cookie?

`SameSite=Lax`: the browser attaches the cookie only to requests from the same
site. That is why the frontend and the API must share a site, and why
`SameSite=None` without a CSRF check is refused at start-up (E001). See
[a frontend on another site](guide.md), section 9 of the guide.

## Why not `SameSite=Strict`?

With `Strict`, following a link to the site from an email or a chat arrives
with no cookie, and the person looks signed out on the first page they open.
`Lax` sends the cookie on that navigation and withholds it from the requests
another site causes, which is the part that matters. `Strict` is a setting
for a project that wants it.

## Why does the access cookie last as long as the refresh token?

So the middleware finds a stale access token rather than none. The browser
deletes a cookie whose `Max-Age` has passed; a cookie that outlives its token
is still sent, and a token that has expired is refused by its own signature,
whatever the cookie says. The library renews either way - it renews when the
cookie is gone, too - but nothing is gained by the browser forgetting it
sooner.

## Does every request now cost a query?

No. A request with a good access token costs a signature check and no query.
A renewal - once per access-token lifetime, per person - costs two: whether
the refresh token was blacklisted, and loading the person.

## What happens when two tabs renew at the same moment?

Both are served, and both stay signed in. The middleware never rotates the
refresh token, so neither renewal invalidates the token the other is using.
Rotation is the refresh view's, called on purpose by one client.

## How is it different from dj-rest-auth?

dj-rest-auth is a set of endpoints - sign-in, registration, password reset,
social accounts - and can put its JWTs in cookies; renewing them is still the
client's, by calling the refresh endpoint. This library is the part that
dj-rest-auth leaves to the client: renewal on the way through, so the
frontend never deals with tokens at all. The two can be combined - a sign-in
view from anywhere hands the person to `start_session`.

## Can I use it without the blacklist?

With `ALLOW_WITHOUT_BLACKLIST = True`. Nothing breaks, but signing out only
clears the cookies: a copy of the refresh token, wherever it is, keeps working
until it expires. That is why it is refused (E004) unless the project says it
accepts it.

## Does the blacklist grow for ever?

simplejwt's own command removes the tokens that have expired:

```bash
python manage.py flushexpiredtokens
```

Run it daily, from cron or a scheduled task - with 0.1.1 or later: under
0.1.0 it could take a signed-out token off the blacklist (see the
[changelog](changelog.md)).

## Does it work with Django's own views?

Not in 0.1 - it is for Django REST framework. Setting `request.user` for a
view that is not DRF's is the first thing planned after it.

## Does it work under ASGI?

Yes. The middleware is sync and async capable, and under ASGI it sends its
signals with `asend`.

## Does it work for a mobile app?

Yes - an app keeps its tokens itself. It signs in with `issue_tokens`, sends
`Authorization: Bearer`, and refreshes and signs out by sending the refresh
token in the body. See apps and scripts in the [guide](guide.md), section 10.
