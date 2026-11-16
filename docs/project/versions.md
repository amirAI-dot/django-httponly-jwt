# Versions and compatibility

## What it runs on

| | supported | tested in CI |
|---|---|---|
| Python | 3.11 - 3.14 | every one |
| Django | 5.2 LTS, 6.0, 6.1 | each with every Python it supports |
| Django REST framework | 3.16 and later | the latest |
| djangorestframework-simplejwt | 5.5 and later | the latest |
| drf-spectacular | 0.28 and later, optional | the latest |

## Versions

The library is young: **alpha**, `0.x`, and its API may change before `1.0`.
A release that changes what an earlier one did, in a way a project may
notice, is a new minor version - `0.1` to `0.2` - and the
[changelog](../changelog.md) says what changed and what to do.

## Upgrading

```bash
pip install --upgrade django-httponly-jwt
python manage.py migrate
python manage.py check --deploy
```

`migrate` applies simplejwt's blacklist tables if a release of simplejwt adds
any. `check --deploy` says what the new release finds wrong with the
configuration. Read the changelog first: a security fix may come with a step
of its own, as 0.1.1's did.

## Where it is published

* the package - [PyPI](https://pypi.org/project/django-httponly-jwt/), released
  from a tag by GitHub Actions, with no token kept anywhere;
* the code - [GitHub](https://github.com/amirAI-dot/django-httponly-jwt);
* this site - built from `main` on every change.

## Licence

BSD 3-Clause.
