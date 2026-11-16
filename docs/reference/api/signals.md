# Signals

Every change to a session, announced once the answer is decided. Each is a
Django `Signal`, sent with `person` and `request`; `session_ended` also
carries `reason`.

| signal | sent when | carries |
|---|---|---|
| `session_started` | `start_session` or `issue_tokens` signed somebody in | `person`, `request` |
| `session_renewed` | the middleware renewed the access token, and the renewal reached the answer | `person`, `request` |
| `session_refreshed` | `RefreshView` rotated the refresh token | `person`, `request` |
| `session_ended` | a sign-out, or a session found over | `person`, `request`, `reason` |

```python
from httponly_jwt.signals import session_ended
```

`person` is `None` when the token named nobody the library could load, and
`request` is `None` when `start_session` or `issue_tokens` was not given one.
Under ASGI the middleware sends with `asend`.

::: httponly_jwt.signals.Ended
