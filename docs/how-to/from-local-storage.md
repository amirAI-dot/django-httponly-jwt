# Move off tokens in `localStorage`

A project whose frontend signs in, keeps both tokens in `localStorage`, sends
the access token in a header and refreshes it itself. The move takes two
releases, and nobody is signed out by it.

## 1. Read both ways in

The cookie for the new frontend, the header for the old one - and for apps and
scripts afterwards:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

`HeaderAuthentication` is simplejwt's own class, so every token the project
issued before still works. Add the middleware, `token_blacklist` and the
library's refresh and sign-out views as in [installing it](../getting-started/installation.md).

## 2. Sign in both ways, for one release

The old frontend reads the tokens from the body; the new one ignores the body
and has the cookies. One pair serves both:

```python
from httponly_jwt.cookies import set_session_cookies
from httponly_jwt.sessions import issue_tokens


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])
        tokens = issue_tokens(person, request=request)
        # For one release: the cookies for the new frontend, the body for the old.
        answer = Response({'access': tokens.access, 'refresh': tokens.refresh})
        return set_session_cookies(
            answer, access=tokens.access, refresh=tokens.refresh, lifetime=tokens.lifetime
        )
```

## 3. Release the new frontend

It removes the token storage, the header, the refresh interceptor and the
retry - and sends the cookies:

```js
// Once, when the new frontend loads: what the old one kept is no longer needed.
localStorage.removeItem('access')
localStorage.removeItem('refresh')

// Every request: the cookies, and nothing else.
const answer = await fetch('/api/me/', { credentials: 'include' })
```

A person who had signed in with the old frontend keeps their old tokens in
`localStorage` until the new one loads and removes them; they sign in once
more. Signing in again is the cost of the move, and it is paid once.

## 4. Stop answering with tokens

When no old frontend is left, the sign-in answers with nothing but the person:

```python
from httponly_jwt.sessions import start_session


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])
        return start_session(Response({'id': person.pk}), person, request=request)
```

The header stays in the list for apps and scripts. A project with none may
take `HeaderAuthentication` out.

## What to check

* The frontend and the API are on one site, or the cookies never reach the
  API - see [the frontend](../guide.md) in the guide, section 8.
* CORS allows the frontend's origin with credentials, if the API is on
  another subdomain.
* Nothing on the server still reads `Authorization` for a browser - a view
  that does is reading the header the new frontend no longer sends.
