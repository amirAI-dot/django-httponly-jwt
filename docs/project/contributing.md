# Contributing

## Getting the code running

```bash
git clone https://github.com/amirAI-dot/django-httponly-jwt.git
cd django-httponly-jwt
uv tool install nox
```

Everything is run through nox, so every machine - and CI - runs the same
thing. With [uv](https://docs.astral.sh/uv/) installed, a Python that is
missing is fetched.

| session | what it holds |
|---|---|
| `nox -s lint` | ruff, the code and its formatting |
| `nox -s types` | mypy, strict |
| `nox -s tests` | the suite, on every supported Python and Django, with 100% coverage |
| `nox -s messages` | the Persian catalogue holds every marked string, and nothing more |
| `nox -s package` | the wheel builds and installs, and the suite and the example run on it |
| `nox -s docs` | this site builds, with no warning |

One combination of the suite, while working:

```bash
nox -s "tests(3.13-django6.1)"
```

## The conventions

* **English only in the code.** Every message a person reads is marked for
  translation; the Persian lives in the catalogue. A Persian string in a test
  is written as `\u` escapes.
* **A test is named after the behaviour it holds** - what would go wrong in
  the world if it failed, not which module it covers.
* **A test that fails first.** A fix comes with a test that fails without it.
* **Queries are counted.** A renewal costs two; a good session none. A change
  that adds one is a decision, written down, not an accident.
* **Every module's docstring says why it exists.**
* **The documentation is in English and Persian**, changed together. A page
  and its Persian twin have the same headings, the same tables and the same
  code.

## A change to what a person reads

After marking a string:

```bash
nox -s messages
```

The session extracts the strings again and fails on any difference - add the
Persian for what it added, then compile the catalogue with
`django-admin compilemessages` in `src/httponly_jwt`.

## A pull request

One change per pull request, with its tests, and its line in the changelog -
`CHANGELOG.md` and `CHANGELOG.fa.md`, under *Unreleased*. CI runs every
session above.
