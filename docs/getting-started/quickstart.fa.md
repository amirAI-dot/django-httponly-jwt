# شروع سریع

پروژه‌ای که آدم‌ها را با نام کاربری و رمز عبور وارد می‌کند، از
[نصب](installation.md) به بعد. ورود مال پروژه است - اینجا `authenticate` خود Django؛
[پروژه‌ی نمونه](https://github.com/amirAI-dot/django-httponly-jwt/tree/main/example)
این کار را با کد یک‌بارمصرف می‌کند. هر چه بعد از آن است مال کتابخانه است.

## ورود، و صفحه‌ای برای خواندن

```python
# accounts/views.py
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from httponly_jwt.sessions import start_session


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = authenticate(
            request,
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if person is None:
            return Response({'detail': 'Wrong username or password.'}, status=400)
        return start_session(Response({'id': person.pk}), person, request=request)


class Me(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'username': request.user.get_username()})
```

`start_session` یک جفت برای شخص می‌سازد و هر دو کوکی را روی پاسخ می‌گذارد. بدنه هیچ
چیزی درباره‌ی توکن‌ها نمی‌گوید.

```python
# urls.py
from django.urls import path

from accounts.views import Me, SignIn
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    path('auth/sign-in/', SignIn.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
    path('me/', Me.as_view()),
]
```

## امتحان کردن

```bash
python manage.py createsuperuser --username ana
```

وارد شوید. جواب `{"id": 1}` است و دو خط `Set-Cookie`، هر دو `HttpOnly`:

```bash
curl -i -c jar -X POST localhost:8000/auth/sign-in/ -d username=ana -d password=...
```

کوکی‌ها خود نشست‌اند:

```bash
curl -b jar localhost:8000/me/
```

وقتی توکن access تمام شده، همان درخواست باز هم جواب می‌گیرد: middleware سر راه
تمدیدش می‌کند، و جواب توکن تازه را می‌گذارد. خروج توکن refresh را blacklist می‌کند و
هر دو کوکی را پاک می‌کند:

```bash
curl -b jar -c jar -X POST localhost:8000/auth/sign-out/
```

## فرانت‌اند

```js
const answer = await fetch('/me/', { credentials: 'include' })

if (answer.status === 401) location.assign('/sign-in')
```

همه‌اش همین است: کوکی‌ها را بفرست، و با 401 به صفحه‌ی ورود برو. فرانت‌اند هیچ‌وقت توکنی
نمی‌خواند، نگه نمی‌دارد یا تمدید نمی‌کند. برای فرانت‌اندی روی سایت دیگر، برای اپ‌ها و
برای بقیه، [راهنما](../guide.md) را ببینید.
