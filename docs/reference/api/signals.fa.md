# سیگنال‌ها

هر تغییر در یک نشست، وقتی جواب معلوم شد اعلام می‌شود. هر کدام یک `Signal` در Django
است که با `person` و `request` فرستاده می‌شود؛ `session_ended` یک `reason` هم دارد.

| سیگنال | کی فرستاده می‌شود | چه دارد |
|---|---|---|
| `session_started` | `start_session` یا `issue_tokens` کسی را وارد کرد | `person`، `request` |
| `session_renewed` | middleware توکن access را تمدید کرد، و تمدید به جواب رسید | `person`، `request` |
| `session_refreshed` | `RefreshView` توکن refresh را چرخاند | `person`، `request` |
| `session_ended` | یک خروج، یا نشستی که تمام‌شده یافت شد | `person`، `request`، `reason` |

```python
from httponly_jwt.signals import session_ended
```

وقتی توکن کسی را نام می‌برد که کتابخانه نتوانست بارش کند `person` برابر `None` است، و
وقتی به `start_session` یا `issue_tokens` درخواستی داده نشده `request` برابر `None`
است. زیر ASGI، middleware با `asend` می‌فرستد.

::: httponly_jwt.signals.Ended
