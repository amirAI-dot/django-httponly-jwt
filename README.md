# django-httponly-jwt

JWT sessions for Django in HttpOnly cookies, renewed by the server so quietly
that the frontend never holds a token.

**Not released yet.** The design is in [`docs/design.md`](docs/design.md)
([Persian](docs/design.fa.md)); the code follows it stage by stage, and the
[changelog](CHANGELOG.md) says what each has added.

## Working on it

Every check runs through [nox](https://nox.thea.codes), the same sessions
locally and in CI. With [uv](https://docs.astral.sh/uv/) installed, a Python
that is missing is fetched for you.

```bash
uv tool install nox
```

```bash
nox -s lint
```

```bash
nox -s types
```

```bash
nox -s tests
```

`tests` runs every supported Python and Django, with 100% coverage; one
combination is `nox -s "tests(3.13-django6.1)"`, and `nox -l` lists them all.
`package` builds the wheel and runs the suite against it.

## Licence

BSD 3-Clause - see [`LICENSE`](LICENSE).
