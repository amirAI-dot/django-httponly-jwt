"""
Every check the project runs, defined once - locally and in CI alike.

    nox -l                                   list the sessions
    nox -s lint                              lint and formatting
    nox -s types                             mypy
    nox -s tests                             every supported Python and Django
    nox -s "tests(3.13-django6.1)"           one combination
    nox -s package                           the wheel installs; the suite and example run on it
    nox -s messages                          the Persian catalogue holds every marked string
    nox -s docs                              the documentation site builds, every link found

CI runs these same sessions, built from the same table, so a check that
passes here passes there and a supported version cannot be left out of one.
Pythons that are not installed are fetched by uv.
"""

import os

import nox

nox.needs_version = '>=2025.2.9'
nox.options.default_venv_backend = 'uv|virtualenv'
nox.options.sessions = ['lint', 'types', 'tests']

#: Every supported Django release, and the Pythons that release supports.
#: Adding a release, or dropping one, is a change to this table only.
SUPPORTED: dict[str, tuple[str, ...]] = {
    '5.2': ('3.11', '3.12', '3.13', '3.14'),
    '6.0': ('3.12', '3.13', '3.14'),
    '6.1': ('3.12', '3.13', '3.14'),
}

NEWEST_DJANGO = max(SUPPORTED, key=lambda release: tuple(map(int, release.split('.'))))
NEWEST_PYTHON = SUPPORTED[NEWEST_DJANGO][-1]

MATRIX = [(python, django) for django, pythons in SUPPORTED.items() for python in pythons]


def django_release(release: str) -> str:
    """The requirement that installs the newest patch of one Django release."""
    return f'django~={release}.0'


@nox.session(python=NEWEST_PYTHON)
def lint(session: nox.Session) -> None:
    """Lint and formatting."""
    session.install('--group', 'lint')
    session.run('ruff', 'check', '.')
    session.run('ruff', 'format', '--check', '.')


@nox.session(python=NEWEST_PYTHON)
def types(session: nox.Session) -> None:
    """mypy, strict, over the library's source."""
    session.install('-e', '.', '--group', 'types', django_release(NEWEST_DJANGO))
    session.run('mypy')


@nox.session
@nox.parametrize(
    'python,django',
    MATRIX,
    ids=[f'{python}-django{django}' for python, django in MATRIX],
)
def tests(session: nox.Session, django: str) -> None:
    """The suite, against one Python and one Django release, with 100% coverage."""
    session.install('-e', '.', '--group', 'test', django_release(django))
    session.run('pytest', '--cov', '--cov-report=term', *session.posargs)


@nox.session(python=NEWEST_PYTHON)
def messages(session: nox.Session) -> None:
    """
    The catalogue holds every string the library marks, and nothing it no
    longer marks: the strings are extracted again, and git finds no change.

    Needs gettext installed. After marking a string, run this, translate what
    it added, and compile: ``django-admin compilemessages`` in ``src/httponly_jwt``.
    """
    session.install('-e', '.', '--group', 'test', django_release(NEWEST_DJANGO))
    root = os.getcwd()

    with session.chdir('src/httponly_jwt'):
        session.run(
            'python',
            '-m',
            'django',
            'makemessages',
            '--locale=fa',
            '--no-location',
            '--no-obsolete',
            '--ignore=__pycache__',
            '--settings=tests.project.settings',
            env={'PYTHONPATH': root},
        )

    session.run(
        'git',
        'diff',
        '--exit-code',
        '--ignore-matching-lines=POT-Creation-Date',
        '--',
        '*.po',
        external=True,
    )


@nox.session(python=NEWEST_PYTHON)
def docs(session: nox.Session) -> None:
    """
    The documentation site builds with no warning - a link, an anchor or a
    page it cannot find fails it. ``nox -s docs -- serve`` shows it at
    http://127.0.0.1:8000 while it is written.
    """
    session.install('--group', 'docs')
    session.env['NO_MKDOCS_2_WARNING'] = '1'

    if session.posargs[:1] == ['serve']:
        session.run('mkdocs', 'serve', *session.posargs[1:])
    else:
        session.run('mkdocs', 'build', '--strict', *session.posargs)


@nox.session(python=NEWEST_PYTHON)
def package(session: nox.Session) -> None:
    """
    What is published works: the wheel is built and installed alone - not the
    source tree - and the suite and the example project run against it, so a
    file left out of the package fails here.
    """
    session.install('build')
    out = session.create_tmp()
    session.run('python', '-m', 'build', '--outdir', out)
    wheel = next(name for name in os.listdir(out) if name.endswith('.whl'))
    session.install(os.path.join(out, wheel), '--group', 'test', django_release(NEWEST_DJANGO))

    # The package installed, not the source tree beside it.
    installed = 'import httponly_jwt, sys; sys.exit("site-packages" not in httponly_jwt.__file__)'
    session.run('python', '-c', installed)
    session.run('pytest', '-p', 'no:cacheprovider')

    with session.chdir('example'):
        session.run('python', 'manage.py', 'test', '--noinput')
