# راهنما

> English: [`guide.md`](https://github.com/amirAI-dot/django-httponly-jwt/blob/main/docs/guide.md).

هر کاری که django-httponly-jwt می‌کند، و اینکه یک پروژه چطور از آن استفاده می‌کند.
اینکه چرا این‌طور ساخته شده در [طراحی](design.fa.md) آمده؛ پروژه‌ای که همه‌اش سر جایش
است در [`example/`](https://github.com/amirAI-dot/django-httponly-jwt/tree/main/example) است.

## ۱. برای چیست

فرانت‌اندی که JWT را در `localStorage` نگه می‌دارد آن را به همه‌ی اسکریپت‌های صفحه
می‌دهد، و فرانت‌اندی که توکن refresh نگه می‌دارد باید 401 را تشخیص بدهد، endpoint
تمدید را صدا بزند، درخواست را دوباره بفرستد - و همه‌ی این‌ها را در همه‌ی تب‌ها با هم
درست انجام بدهد. این کتابخانه هر دو را از دوش فرانت‌اند برمی‌دارد:

* **توکن‌ها فقط در کوکی‌های HttpOnly هستند** - هیچ اسکریپتی نمی‌تواند بخواندشان؛
* **سرور توکن access را سر راه تمدید می‌کند** - درخواستی که آن را منقضی یافت جواب
  می‌گیرد، و جواب توکن تازه را با خودش دارد؛
* **فرانت‌اند هیچ‌وقت توکنی نگه نمی‌دارد**: درخواست‌ها را با کوکی‌ها می‌فرستد و وقتی
  درخواستی 401 جواب داد به صفحه‌ی ورود می‌رود.

لایه‌ای است روی [djangorestframework-simplejwt](https://github.com/jazzband/djangorestframework-simplejwt):
simplejwt توکن‌ها را می‌سازد و بررسی می‌کند، و تنظیماتش مثل همیشه سر جایش است. اینکه
شخص چطور ثابت می‌کند کیست - رمز عبور، کد یک‌بارمصرف، حساب اجتماعی - مال خود پروژه
می‌ماند.

## ۲. نصب

```bash
pip install django-httponly-jwt
```

با توصیف schema در drf-spectacular (بخش ۱۲):

```bash
pip install "django-httponly-jwt[spectacular]"
```

Django نسخه‌ی 5.2 تا 6.1، Python نسخه‌ی 3.11 تا 3.14، DRF نسخه‌ی 3.16 و simplejwt نسخه‌ی
5.5 یا جدیدتر.

## ۳. راه‌اندازی

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'rest_framework_simplejwt.token_blacklist',
    'httponly_jwt',
]

MIDDLEWARE = [
    ...,
    'httponly_jwt.middleware.RenewalMiddleware',
    ...,
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'httponly_jwt.authentication.CookieAuthentication',
        'httponly_jwt.authentication.HeaderAuthentication',
    ],
}
```

```python
# urls.py
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    ...,
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
```

```bash
python manage.py migrate
```

`migrate` جدول‌های blacklist در simplejwt را می‌سازد. چیز دیگری لازم نیست:
`HTTPONLY_JWT` فقط برای عوض کردن یک پیش‌فرض لازم است (بخش ۱۳)، و هر اشتباهی در آن
موقع بالا آمدن پروژه رد می‌شود (بخش ۱۴).

`RenewalMiddleware` را پیش از هر چیزی بگذارید که می‌خواند چه کسی درخواست داده -
جای معمولش بعد از `SecurityMiddleware` و `CommonMiddleware` خود Django است.

## ۴. ورود

پروژه به روش خودش بررسی می‌کند شخص کیست، بعد او را می‌سپارد:

```python
from httponly_jwt.sessions import start_session

class SignInView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        person = verify_code(request.data['phone'], request.data['code'])   # the project's
        return start_session(Response({'id': person.pk}), person, request=request)
```

`start_session` یک جفت می‌سازد - با claimها و طول عمر آن شخص (بخش ۷) - هر دو کوکی را
روی پاسخ می‌گذارد و آن را برمی‌گرداند. `request=` به `session_started` (بخش ۱۱)
رسانده می‌شود و می‌شود ننوشتش.

هر دو کوکی HttpOnly، `Secure`، `SameSite=Lax` و `Path=/` هستند، و هر دو به اندازه‌ی
توکن refresh عمر می‌کنند: کوکی access عمداً از توکنش بیشتر می‌ماند، تا middleware
توکنی کهنه پیدا کند نه هیچ چیز.

کلاینت موبایل توکن‌هایش را خودش نگه می‌دارد. `issue_tokens` همان جفت را می‌سازد و
چیزی نمی‌گذارد:

```python
from httponly_jwt.sessions import issue_tokens

tokens = issue_tokens(person, request=request)
return Response({'access': tokens.access, 'refresh': tokens.refresh})
```

## ۵. تمدید

وقتی کوکی access نیست یا دیگر معتبر نیست و کوکی refresh هست، `RenewalMiddleware`
توکن access تازه‌ای می‌سازد، آن را برای همین درخواست به کار می‌برد، و روی جواب
می‌گذارد. view هیچ‌وقت نمی‌فهمد این اتفاق افتاده.

* **وقتی مرورگر کوکی access را از قبل پاک کرده هم تمدید می‌کند**، نه فقط وقتی کوکی
  توکنی منقضی دارد.
* **می‌پرسد شخص هنوز اجازه‌ی ورود دارد یا نه** - `is_active`، و `USER_CAN_SIGN_IN`
  (بخش ۷). غیرفعال کردن یک حساب نشست‌هایش را در تمدید بعدی تمام می‌کند، نه وقتی توکن
  refresh منقضی شود.
* **claimها را دوباره می‌خواند**، پس نقشی که امروز عوض شده در توکن access بعدی هست.
* **توکن refresh را هیچ‌وقت نمی‌چرخاند.** دو تبی که با هم تمدید می‌کنند هر کدام توکن
  دیگری را blacklist می‌کرد، و شخص با تب دوم خودش خارج می‌شد.
* **پاسخی را که خودش نشست را گذاشته یا پاک کرده دست نمی‌زند** - ورود، خروج.

نشستی که تمام شده - توکن refresh منقضی، blacklist شده یا ناخوانا، شخص حذف شده یا
بدون اجازه‌ی ورود - هر دو کوکی‌اش پاک می‌شود، و درخواست به نام هیچ کس ادامه پیدا
می‌کند.

درخواستی با توکن access معتبر یک بررسی امضا هزینه دارد و هیچ کوئری. تمدید دو کوئری
دارد: اینکه توکن refresh در blacklist هست یا نه، و بار کردن شخص. زیر WSGI و ASGI
کار می‌کند.

کلاینتی که با هدر وارد شده و کوکی refresh ندارد دست نخورده می‌ماند: هیچ کوکی‌ای
برایش گذاشته یا پاک نمی‌شود.

## ۶. تمدید دستی و خروج

هر دو view توکن refresh را اول از کوکی‌اش و بعد از بدنه به شکل `{"refresh": "..."}`
می‌خوانند، و همان‌طور جواب می‌دهند که آمده.

**`RefreshView`** (`POST`) می‌چرخاند: توکنی که ارائه شده blacklist می‌شود و جفت تازه
داده می‌شود، با claimها و طول عمر شخص که دوباره خوانده می‌شوند - پس نشست را هم یک
طول عمر کامل طولانی‌تر می‌کند. بنابراین هر توکن refresh یک بار به کار می‌رود.

| توکن آمد | جواب |
|---|---|
| در کوکی | `204`، هر دو کوکی گذاشته می‌شوند؛ هیچ‌وقت توکنی در بدنه نیست |
| در بدنه | `200`، `{"access": "...", "refresh": "..."}`؛ بدون کوکی |
| و نمی‌شود انجامش داد | `401`، `{"detail": "...", "code": "session_ended"}`؛ وقتی در کوکی آمده بود کوکی‌ها پاک می‌شوند |

مرورگر کمتر به آن نیاز دارد - middleware بدون آن تمدید می‌کند. برای کلاینت موبایل
است، و برای فرانت‌اندی که می‌خواهد عمداً نشستی را طولانی‌تر کند.

**`SignOutView`** (`POST`) توکن refresh را blacklist می‌کند، پس هیچ نسخه‌ای از آن
جایی تمدید نمی‌کند، هر دو کوکی را پاک می‌کند، و هر چه به آن داده شود `204` جواب
می‌دهد: کسی که خواسته خارج شود در هر صورت خارج شده.

هیچ‌کدام احراز هویت نمی‌خواهند - توکن refresh خودش مدرک است، و خروج باید وقتی توکن
access تمام شده هم کار کند. هر دو viewهای معمولی DRF هستند که پروژه می‌تواند از
آن‌ها ارث ببرد، برایشان محدودیت نرخ بگذارد و هر جا خواست نصبشان کند.

## ۷. نشست هر نفر

سه تنظیم تابعی از شخص را با مسیر نقطه‌دار نام می‌برند:

```python
HTTPONLY_JWT = {
    'REFRESH_LIFETIME': 'myproject.auth.session_length',
    'CLAIMS': 'myproject.auth.claims',
    'USER_CAN_SIGN_IN': 'myproject.auth.may_sign_in',
}
```

```python
# myproject/auth.py
def session_length(person):
    """Staff for a working day; everybody else simplejwt's REFRESH_TOKEN_LIFETIME."""
    return timedelta(hours=8) if person.is_staff else None


def claims(person):
    """What both tokens carry beyond who the person is."""
    return {'role': person.role}


def may_sign_in(person):
    """Asked beside is_active, at every renewal and refresh."""
    return not person.is_suspended
```

* **`REFRESH_LIFETIME`** یک `timedelta` جواب می‌دهد، یا `None` برای
  `REFRESH_TOKEN_LIFETIME` در simplejwt. کوکی‌ها هم همان‌قدر می‌مانند.
* **`CLAIMS`** یک دیکشنری جواب می‌دهد. موقع ورود، در هر تمدید و در هر تمدید دستی
  پرسیده می‌شود. نمی‌تواند claimهای خود simplejwt را بگذارد - اینکه توکن مال کیست،
  نوعش، `jti`، `exp`، `iat` - و تابعی که این کار را بکند `ImproperlyConfigured`
  است، نه توکنی برای کس دیگر.
* **`USER_CAN_SIGN_IN`** جواب می‌دهد که شخص هنوز می‌تواند نشستی داشته باشد یا نه.

view claimها را از `request.auth` می‌خواند:

```python
role = request.auth['role']
```

## ۸. فرانت‌اند

فرانت‌اند و API باید روی **یک سایت** باشند - `example.com` و `api.example.com` یک
سایت‌اند - تا مرورگر کوکی‌ها را به درخواست‌های API بچسباند و به درخواست هیچ کس دیگر
نه. بعد:

```js
// Every request sends the cookies.
const answer = await fetch('https://api.example.com/me/', { credentials: 'include' })

if (answer.status === 401) {
  // The session is over: the middleware has already cleared the cookies.
  location.assign('/sign-in')
}
```

* هیچ‌وقت توکنی نمی‌خواند، نگه نمی‌دارد یا نمی‌فرستد. نمی‌تواند - کوکی‌ها HttpOnly
  هستند - و لازم هم ندارد.
* هیچ‌وقت برای زنده نگه داشتن نشست endpoint تمدید را صدا نمی‌زند: تمدید سر راه انجام
  می‌شود.
* خروج یک `POST` به view خروج است.
* زیردامنه‌ی جدا برای API وقتی فرانت‌اند روی سرور خودش هم نشست را می‌خواند به
  `COOKIE_DOMAIN` نیاز دارد، مثلاً `'.example.com'`؛ و تنظیمات CORS در API باید
  origin فرانت‌اند را با credentials اجازه بدهد.

وقتی فرانت‌اند روی سرور رندر می‌شود (مثلاً Next.js)، سرور هدر `Cookie` مرورگر را به API
می‌فرستد و هر `Set-Cookie` در جواب را به مرورگر برمی‌گرداند - وگرنه توکن تمدیدشده
در راه گم می‌شود.

## ۹. فرانت‌اند روی سایت دیگر

وقتی فرانت‌اند روی سایتی غیر از API است، مرورگر فقط وقتی کوکی‌ها را می‌فرستد که
`SameSite=None` باشند - و آن وقت آن‌ها را با درخواستی هم می‌فرستد که هر سایتی ساخته.
این بررسی CSRF خود Django را لازم دارد:

```python
HTTPONLY_JWT = {'COOKIE_SAMESITE': 'None', 'CSRF': True}

CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = ['https://app.example.org']
```

```python
from httponly_jwt.views import CsrfTokenView

urlpatterns += [path('auth/csrf/', CsrfTokenView.as_view())]
```

* فرانت‌اند توکن را از `auth/csrf/` می‌گیرد - صفحه‌ای روی سایت دیگر نمی‌تواند کوکی
  API را بخواند - و در هر نوشتن آن را در `X-CSRFToken` می‌فرستد.
* درخواست ناامنی که کوکی احراز هویتش می‌کند و توکن ندارد با 403 رد می‌شود.
* از درخواستی که با هدر آمده هیچ‌وقت پرسیده نمی‌شود: سایت دیگر نمی‌تواند هدر بگذارد.
  کوکی کهنه هم همچنان «هیچ کس» است، نه خطای CSRF.
* viewهای تمدید و خروج هم وقتی توکن refresh در کوکی آمده می‌پرسند، پس سایت دیگر نه
  می‌تواند نشستی را بچرخاند و نه تمامش کند.
* `OptionalAuthentication` نوشتنی با کوکی و بدون توکن را مثل درخواست یک مهمان جواب
  می‌دهد.

`SameSite=None` بدون این بررسی موقع بالا آمدن رد می‌شود (E001)، و `SameSite=None`
بدون `Secure` هم (E005). W002 تنظیمی از CSRF در Django را نام می‌برد که هر نوشتن
فرانت‌اند را رد می‌کرد.

## ۱۰. اپ‌ها، اسکریپت‌ها و ورود اختیاری

**`HeaderAuthentication`** همان `Authorization: Bearer` در simplejwt است به نام
کتابخانه. اپ موبایل یا اسکریپت با `issue_tokens` وارد می‌شود (بخش ۴)، با بدنه تمدید
می‌کند و خارج می‌شود (بخش ۶)، و هیچ‌وقت کوکی‌ای برایش فرستاده نمی‌شود. هدر نادرست با
401 رد می‌شود - عمداً فرستاده شده بود.

**`CookieAuthentication`** کوکی‌ای را که منقضی، ناخوانا یا توکن refresh است، یا حسابی
را نام می‌برد که حذف یا غیرفعال شده، به جای خطا **هیچ کس** می‌داند: صفحه‌ای که کسی
را لازم دارد 401 جواب می‌دهد، و صفحه‌ای که برای همه باز است به یک مهمان جواب می‌دهد.

**`OptionalAuthentication`** برای endpointی است که هر کسی می‌تواند صدا بزند و برای
کسی که وارد شده کار بیشتری می‌کند: کوکی، بعد هدر، و هیچ‌وقت رد نمی‌کند - مهمان به
خاطر توکن کهنه‌ای که نمی‌خواست بفرستد رد نمی‌شود.

```python
from httponly_jwt.authentication import OptionalAuthentication

class Catalogue(APIView):
    authentication_classes = (OptionalAuthentication,)
    permission_classes = (AllowAny,)
```

## ۱۱. سیگنال‌ها

وقتی جواب معلوم شد فرستاده می‌شوند، هر کدام با `person` و `request`، برای سابقه‌ای که
خود پروژه نگه می‌دارد:

| سیگنال | کی |
|---|---|
| `session_started` | `start_session` یا `issue_tokens` کسی را وارد کرد |
| `session_renewed` | middleware توکن access را تمدید کرد، و تمدید به جواب رسید |
| `session_refreshed` | `RefreshView` توکن refresh را چرخاند |
| `session_ended` | با `reason`: `signed_out`، `token_unusable` یا `not_allowed` |

```python
from django.dispatch import receiver
from httponly_jwt.signals import Ended, session_ended

@receiver(session_ended)
def note_it(sender, person, request, reason, **kwargs):
    if reason == Ended.NOT_ALLOWED:
        AuditEntry.objects.create(person=person, what='refused at renewal')
```

وقتی توکن کسی را نام می‌برد که کتابخانه نتوانست بارش کند، `person` برابر `None` است.
زیر ASGI، middleware با `asend` می‌فرستد، پس گیرنده‌ای که در پایگاه داده می‌نویسد جایی
اجرا می‌شود که اجازه دارد.

## ۱۲. schema

با extraی `spectacular` نصب‌شده، drf-spectacular این‌ها را توصیف می‌کند:

* `CookieAuthentication` به شکل یک `apiKey` در کوکی، با همان نامی که پروژه انتخاب کرده
  (`httponlyJwtCookie`)؛
* `HeaderAuthentication` به شکل scheme از نوع bearer در simplejwt (`jwtAuth`)، پس
  آوردن کلاس خود simplejwt کنارش یک scheme است؛
* `OptionalAuthentication` به شکل هر کدام؛
* viewهای تمدید، خروج و توکن CSRF، با همه‌ی جواب‌ها.

چیزی برای تنظیم نیست: توصیف‌ها وقتی drf-spectacular نصب است بار می‌شوند، و schema
بدون هیچ هشداری درباره‌ی کتابخانه ساخته می‌شود.

## ۱۳. تنظیمات

همه زیر `HTTPONLY_JWT`؛ پیش‌فرض به هیچ‌کدام نیاز ندارد.

| کلید | پیش‌فرض | |
|---|---|---|
| `ACCESS_COOKIE` | `'access_token'` | نام کوکی access |
| `REFRESH_COOKIE` | `'refresh_token'` | نام کوکی refresh |
| `COOKIE_DOMAIN` | `None` | |
| `COOKIE_PATH` | `'/'` | |
| `COOKIE_SAMESITE` | `'Lax'` | `Lax`، `Strict` یا `None` |
| `COOKIE_SECURE` | `True` | |
| `CSRF` | `False` | توکن CSRF خود Django را روی نوشتن‌هایی که با کوکی احراز هویت شده‌اند لازم می‌کند |
| `REFRESH_LIFETIME` | `None` | یک مسیر نقطه‌دار: `(person) -> timedelta \| None` |
| `CLAIMS` | `None` | یک مسیر نقطه‌دار: `(person) -> dict` |
| `USER_CAN_SIGN_IN` | `None` | یک مسیر نقطه‌دار: `(person) -> bool`، کنار `is_active` پرسیده می‌شود |
| `ALLOW_WITHOUT_BLACKLIST` | `False` | اجرا بدون blacklist در simplejwt، با پذیرفتن اینکه توکنی را نمی‌شود تمام کرد |

طول عمر توکن‌ها، کلید امضا و claim شناسه‌ی کاربر تنظیمات خود simplejwt هستند، در
`SIMPLE_JWT`.

## ۱۴. آنچه موقع بالا آمدن رد می‌شود

`manage.py check`، و در نتیجه `runserver` و `migrate`، آنچه را که نمی‌تواند کار کند رد
می‌کنند:

| شناسه | کی | سطح |
|---|---|---|
| `httponly_jwt.E001` | `COOKIE_SAMESITE` برابر `None` است و `CSRF` خاموش | خطا |
| `httponly_jwt.E002` | کوکی احراز هویت می‌کند و `RenewalMiddleware` نصب نیست | خطا |
| `httponly_jwt.E003` | کلیدی که کتابخانه نمی‌شناسد، یا مقداری که نمی‌تواند به کار ببرد | خطا |
| `httponly_jwt.E004` | `token_blacklist` نصب نیست | خطا، مگر `ALLOW_WITHOUT_BLACKLIST` |
| `httponly_jwt.E005` | `COOKIE_SAMESITE` برابر `None` است و `COOKIE_SECURE` خاموش | خطا |
| `httponly_jwt.W001` | `COOKIE_SECURE` خاموش است (`check --deploy`) | هشدار |
| `httponly_jwt.W002` | بررسی CSRF برای سایت دیگر روشن است، و تنظیمات CSRF در Django نوشتن‌هایش را رد می‌کردند | هشدار |

## ۱۵. زبان‌ها

کلمه‌های خود کتابخانه - پیام رد وقتی نشستی تمام شده، توصیف‌های schema - به انگلیسی
و فارسی هستند، و مثل بقیه‌ی Django از زبان درخواست پیروی می‌کنند.
