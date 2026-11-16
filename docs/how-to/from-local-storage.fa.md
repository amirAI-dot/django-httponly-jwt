# مهاجرت از توکن در `localStorage`

پروژه‌ای که فرانت‌اندش وارد می‌شود، هر دو توکن را در `localStorage` نگه می‌دارد، توکن
access را در هدر می‌فرستد و خودش تمدیدش می‌کند. مهاجرت دو انتشار طول می‌کشد، و هیچ کس
به خاطر آن خارج نمی‌شود.

## ۱. خواندن از هر دو راه

کوکی برای فرانت‌اند تازه، هدر برای فرانت‌اند قدیمی - و بعد از آن برای اپ‌ها و
اسکریپت‌ها:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

`HeaderAuthentication` همان کلاس خود simplejwt است، پس هر توکنی که پروژه قبلاً داده
همچنان کار می‌کند. middleware، `token_blacklist` و viewهای تمدید و خروج کتابخانه را
مثل [نصبش](../getting-started/installation.md) اضافه کنید.

## ۲. ورود از هر دو راه، برای یک انتشار

فرانت‌اند قدیمی توکن‌ها را از بدنه می‌خواند؛ فرانت‌اند تازه بدنه را نادیده می‌گیرد و
کوکی‌ها را دارد. یک جفت به کار هر دو می‌آید:

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

## ۳. انتشار فرانت‌اند تازه

جای نگه داشتن توکن، هدر، interceptor تمدید و تلاش دوباره را حذف می‌کند - و کوکی‌ها را
می‌فرستد:

```js
// Once, when the new frontend loads: what the old one kept is no longer needed.
localStorage.removeItem('access')
localStorage.removeItem('refresh')

// Every request: the cookies, and nothing else.
const answer = await fetch('/api/me/', { credentials: 'include' })
```

کسی که با فرانت‌اند قدیمی وارد شده بود توکن‌های قدیمی‌اش را تا وقتی فرانت‌اند تازه بار
شود و پاکشان کند در `localStorage` دارد؛ یک بار دیگر وارد می‌شود. دوباره وارد شدن
هزینه‌ی مهاجرت است، و یک بار پرداخت می‌شود.

## ۴. دیگر توکن جواب ندادن

وقتی هیچ فرانت‌اند قدیمی نمانده، ورود فقط شخص را جواب می‌دهد:

```python
from httponly_jwt.sessions import start_session


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])
        return start_session(Response({'id': person.pk}), person, request=request)
```

هدر برای اپ‌ها و اسکریپت‌ها در فهرست می‌ماند. پروژه‌ای که هیچ‌کدام را ندارد می‌تواند
`HeaderAuthentication` را بردارد.

## آنچه باید بررسی کرد

* فرانت‌اند و API روی یک سایت باشند، وگرنه کوکی‌ها هیچ‌وقت به API نمی‌رسند -
  [فرانت‌اند](../guide.md) را در راهنما ببینید، بخش ۸.
* اگر API روی زیردامنه‌ی دیگری است، CORS باید origin فرانت‌اند را با credentials اجازه
  بدهد.
* هیچ چیزی روی سرور هنوز `Authorization` را برای مرورگر نخواند - viewی که این کار را
  بکند هدری را می‌خواند که فرانت‌اند تازه دیگر نمی‌فرستد.
