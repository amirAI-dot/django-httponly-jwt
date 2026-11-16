# فرانت‌اند Next.js

یک صفحه‌ی Next.js ممکن است API را از مرورگر صدا بزند، از سرور هنگام رندر، یا هر دو.
درخواست‌های مرورگر چیز خاصی لازم ندارند؛ درخواست‌های سرور باید کوکی‌ها را به آن‌ها
بدهند.

## یک سایت، و کوکی روی آن

فرانت‌اند و API باید روی یک سایت باشند - `example.com` و `api.example.com`. کوکی‌ای که
API بدون دامنه می‌گذارد فقط به `api.example.com` برگردانده می‌شود، پس سرور Next.js
روی `example.com` هیچ‌وقت آن را نمی‌دید. دامنه‌ی سایت را به آن بدهید:

```python
# settings.py - the frontend at example.com, the API at api.example.com
HTTPONLY_JWT = {'COOKIE_DOMAIN': '.example.com'}

CORS_ALLOWED_ORIGINS = ['https://example.com']
CORS_ALLOW_CREDENTIALS = True
```

خط‌های CORS مال [django-cors-headers](https://github.com/adamchainz/django-cors-headers)
هستند: مرورگر فقط وقتی کوکی‌ها را به origin دیگر می‌فرستد که با credentials اجازه داشته
باشد، و هیچ‌وقت به wildcard.

## در مرورگر

```ts
// In the browser - a client component, an event handler.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })

if (answer.status === 401) router.push('/sign-in')
```

تمدید سر راه انجام می‌شود، و مرورگر کوکی‌ای را که جواب می‌گذارد نگه می‌دارد. هیچ
interceptorی برای نوشتن نیست.

## روی سرور

server component مرورگر ندارد: کوکی‌هایی را که به آن فرستاده شده جلو می‌فرستد.

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

server component نمی‌تواند کوکی بگذارد، پس وقتی API برایش توکن access را تمدید
می‌کند، توکن تازه جلو فرستاده نمی‌شود. چیزی خراب نمی‌شود: کوکی refresh هنوز معتبر است،
درخواست بعدی دوباره تمدید می‌کند، و مرورگر اولین باری که خودش API را صدا بزند توکن
تمدیدشده را نگه می‌دارد. هر تمدید دو کوئری کوچک هزینه دارد.

## صفحه‌هایی که هیچ‌وقت API را از مرورگر صدا نمی‌زنند

وقتی همه‌ی درخواست‌ها روی سرور انجام می‌شوند، مرورگر هیچ‌وقت کوکی تمدیدشده را نمی‌گیرد،
و هر صفحه با یک تمدید رندر می‌شود. یک middleware در Next.js می‌تواند کوکی تمدیدشده را
جلو بفرستد:

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

برای هر صفحه‌ای که با آن جور شود یک درخواست به API هزینه دارد، پس فقط صفحه‌هایی را که
لازمش دارند جور کنید.

## ورود و خروج

فرم ورود را از مرورگر بفرستید، با `credentials: 'include'`، تا کوکی‌هایی که می‌گذارد به
مرورگر برسند. برای خروج هم همین‌طور. server actionی که وارد می‌کند باید `Set-Cookie`
در جواب API را روی پاسخ خودش کپی کند.
