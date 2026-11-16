# A Next.js frontend

A Next.js page may call the API from the browser, from the server while it
renders, or both. The browser's calls need nothing special; the server's need
the cookies handed to them.

## One site, and the cookie on it

The frontend and the API must be on one site - `example.com` and
`api.example.com`. A cookie the API sets without a domain is sent back only to
`api.example.com`, so the Next.js server at `example.com` would never see it.
Give it the site's domain:

```python
# settings.py - the frontend at example.com, the API at api.example.com
HTTPONLY_JWT = {'COOKIE_DOMAIN': '.example.com'}

CORS_ALLOWED_ORIGINS = ['https://example.com']
CORS_ALLOW_CREDENTIALS = True
```

The CORS lines are [django-cors-headers](https://github.com/adamchainz/django-cors-headers)'s:
a browser sends cookies to another origin only when it is allowed to with
credentials, and never to a wildcard.

## In the browser

```ts
// In the browser - a client component, an event handler.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })

if (answer.status === 401) router.push('/sign-in')
```

Renewal happens on the way through, and the browser keeps the cookie the
answer sets. There is no interceptor to write.

## On the server

A server component has no browser: it forwards the cookies it was sent.

```ts
// lib/api.ts - on the server: a server component, a route handler, a server action.
import { cookies } from 'next/headers'

export async function api(path: string, init: RequestInit = {}) {
  const jar = await cookies()

  return fetch(`${process.env.API_URL}${path}`, {
    ...init,
    headers: { ...init.headers, cookie: jar.toString() },
    cache: 'no-store',
  })
}
```

```tsx
// app/account/page.tsx
import { redirect } from 'next/navigation'
import { api } from '@/lib/api'

export default async function Account() {
  const answer = await api('/me/')

  if (answer.status === 401) redirect('/sign-in')

  const me = await answer.json()
  return <h1>{me.username}</h1>
}
```

A server component cannot set a cookie, so when the API renews the access
token for it, the new token is not handed on. Nothing breaks: the refresh
cookie is still good, the next request renews again, and the browser keeps a
renewed token the first time it calls the API itself. A renewal costs two
small queries.

## Pages that never call the API from the browser

When every call is made on the server, the browser never receives a renewed
cookie, and every page renders with a renewal. A Next.js middleware can pass
the renewed cookie on:

```ts
// middleware.ts - only for pages that never call the API from the browser.
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  const answer = await fetch(`${process.env.API_URL}/me/`, {
    headers: { cookie: request.headers.get('cookie') ?? '' },
  })
  const response = NextResponse.next()

  // Hand the renewed cookie on to the browser.
  for (const line of answer.headers.getSetCookie()) {
    response.headers.append('set-cookie', line)
  }

  return response
}

export const config = { matcher: ['/account/:path*'] }
```

It costs one request to the API per page it matches, so match only the pages
that need it.

## Signing in and out

Post the sign-in form from the browser, with `credentials: 'include'`, so the
cookies it sets reach the browser. The same for signing out. A server action
that signs in has to copy the API's `Set-Cookie` onto its own response.
