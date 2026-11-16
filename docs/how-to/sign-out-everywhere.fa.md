# خارج کردن یک شخص از همه‌جا

`SignOutView` نشستی را که به آن داده شده تمام می‌کند - یک مرورگر، یک اپ. گوشی دزدیده‌شده،
رمز عوض‌شده یا حسابی که کس دیگری در دستش گرفته لازم دارد همه‌ی نشست‌های شخص با هم تمام
شوند.

## blacklist کردن همه‌ی توکن‌های refresh او

simplejwt هر توکن refreshی را که می‌دهد به شکل یک سطر `OutstandingToken` ثبت می‌کند.
blacklist کردن همه‌ی توکن‌های یک شخص هر نشستش را در تمدید بعدی تمام می‌کند:

```python
# accounts/sessions.py
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def sign_out_everywhere(person):
    """Every refresh token the person holds, blacklisted: no session of theirs renews again."""
    for token in OutstandingToken.objects.filter(user=person):
        BlacklistedToken.objects.get_or_create(token=token)
```

از آنجا، هر مرورگر و اپی که شخص در آن وارد بود دفعه‌ی بعد که توکن access آن تمام شود
توکن refresh خودش را blacklist‌شده می‌یابد: middleware کوکی‌هایش را پاک می‌کند و
`session_ended` با `token_unusable` فرستاده می‌شود.

## بعد از عوض کردن رمز

کسی که رمز را عوض می‌کند باید همان‌جا که هست وارد بماند:

```python
class ChangePassword(APIView):
    def post(self, request):
        person = request.user
        person.set_password(request.data['password'])
        person.save()
        sign_out_everywhere(person)
        # Signed in again here, with a session the blacklist did not reach.
        return start_session(Response(status=204), person, request=request)
```

## تمام کردنشان زودتر

توکن accessی که از قبل داده شده تا منقضی شدنش معتبر است - چند دقیقه، با
`ACCESS_TOKEN_LIFETIME` در simplejwt. blacklist توکن‌های refresh را تمام می‌کند، نه
توکن‌های access را. وقتی چند دقیقه زیاد است، طول عمر توکن access را کوتاه نگه دارید؛
این معامله‌ای است که هر نشست JWT می‌کند.

## غیرفعال کردن یک حساب

غیرفعال کردن یک حساب چیز دیگری لازم ندارد:

```python
person.is_active = False
person.save()
```

middleware در هر تمدید `is_active` را می‌پرسد، و view تمدید در هر تمدید دستی، پس
نشست‌های حساب در اولی از این دو تمام می‌شوند. `USER_CAN_SIGN_IN` همین کار را به
دلیل‌های خود پروژه می‌کند - حساب معلق، اشتراک پرداخت‌نشده.
