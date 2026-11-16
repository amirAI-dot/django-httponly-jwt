# نسخه‌ها و سازگاری

## روی چه چیزی اجرا می‌شود

| | پشتیبانی‌شده | تست‌شده در CI |
|---|---|---|
| Python | 3.11 - 3.14 | همه |
| Django | 5.2 LTS، 6.0، 6.1 | هر کدام با همه‌ی Pythonهایی که پشتیبانی می‌کند |
| Django REST framework | 3.16 به بعد | آخرین نسخه |
| djangorestframework-simplejwt | 5.5 به بعد | آخرین نسخه |
| drf-spectacular | 0.28 به بعد، اختیاری | آخرین نسخه |

## نسخه‌ها

کتابخانه جوان است: **آلفا**، `0.x`، و API آن ممکن است پیش از `1.0` عوض شود. انتشاری
که کاری را که انتشار قبلی می‌کرد طوری عوض کند که پروژه متوجه شود، یک نسخه‌ی minor تازه
است - `0.1` به `0.2` - و [تغییرات](../changelog.md) می‌گوید چه عوض شده و چه باید کرد.

## به‌روزرسانی

```bash
pip install --upgrade django-httponly-jwt
python manage.py migrate
python manage.py check --deploy
```

`migrate` اگر نسخه‌ای از simplejwt جدولی به blacklist اضافه کند آن را اعمال می‌کند.
`check --deploy` می‌گوید انتشار تازه چه ایرادی در پیکربندی می‌بیند. اول تغییرات را
بخوانید: یک رفع امنیتی ممکن است قدم خودش را داشته باشد، همان‌طور که 0.1.1 داشت.

## کجا منتشر می‌شود

* بسته - [PyPI](https://pypi.org/project/django-httponly-jwt/)، که از یک tag با
  GitHub Actions منتشر می‌شود، بدون اینکه هیچ توکنی جایی نگه داشته شود؛
* کد - [GitHub](https://github.com/amirAI-dot/django-httponly-jwt)؛
* همین سایت - که با هر تغییر از `main` ساخته می‌شود.

## مجوز

BSD 3-Clause.
