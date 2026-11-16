"""
The library ships Persian: every string it marks is translated, and the
compiled catalogue says what the source says.

If these fail, a Persian frontend shows an English sentence when a session
ends, a schema read in Persian documents the sign-out in English, or a
catalogue edited and not compiled serves the old translation - which looks
right to whoever reads the ``.po`` and is wrong on every screen.

That every marked string is in the catalogue at all is held by ``nox -s
messages``, which extracts them again and finds nothing new.
"""

import ast
import gettext
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from django.test import override_settings
from django.utils import translation
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

SOURCE = Path(__file__).resolve().parent.parent / 'src' / 'httponly_jwt'
CATALOGUE = SOURCE / 'locale' / 'fa' / 'LC_MESSAGES' / 'django.po'
PLACEHOLDER = re.compile(r'%\((\w+)\)[sdr]')

#: "Your session has ended. Please sign in again." and "Sign out", in Persian -
#: written as escapes: the code is English only.
ENDED_FA = (
    '\u0646\u0634\u0633\u062a \u0634\u0645\u0627 \u062a\u0645\u0627\u0645'
    ' \u0634\u062f\u0647. \u0644\u0637\u0641\u0627\u064b'
    ' \u062f\u0648\u0628\u0627\u0631\u0647 \u0648\u0627\u0631\u062f'
    ' \u0634\u0648\u06cc\u062f.'
)
SIGN_OUT_FA = '\u062e\u0631\u0648\u062c'


@dataclass
class Entry:
    msgid: str = ''
    msgstr: str = ''
    flags: set[str] = field(default_factory=set)


def entries(path: Path) -> list[Entry]:
    """The entries of a ``.po`` file, the header left out."""
    found: list[Entry] = []
    current, key = Entry(), ''

    for line in [*path.read_text(encoding='utf-8').splitlines(), '']:
        if not line.strip():
            if current.msgid:
                found.append(current)
            current = Entry()
        elif line.startswith('#,'):
            current.flags |= {flag.strip() for flag in line[2:].split(',')}
        elif line.startswith('#'):
            continue
        elif line.startswith('"'):
            setattr(current, key, getattr(current, key) + ast.literal_eval(line))
        else:
            key, _, rest = line.partition(' ')
            setattr(current, key, ast.literal_eval(rest))

    return found


def test_every_entry_is_translated_and_keeps_its_placeholders() -> None:
    problems = []

    for entry in entries(CATALOGUE):
        if 'fuzzy' in entry.flags:
            problems.append(f'{entry.msgid!r} is fuzzy')
        if not entry.msgstr:
            problems.append(f'{entry.msgid!r} has no translation')
        elif set(PLACEHOLDER.findall(entry.msgstr)) != set(PLACEHOLDER.findall(entry.msgid)):
            problems.append(f'{entry.msgid!r} loses or adds a placeholder')

    assert entries(CATALOGUE), 'the catalogue is read'
    assert not problems, '\n'.join(problems)


def test_the_compiled_catalogue_says_what_the_source_says() -> None:
    with CATALOGUE.with_suffix('.mo').open('rb') as compiled:
        catalogue = gettext.GNUTranslations(compiled)

    stale = [e.msgid for e in entries(CATALOGUE) if catalogue.gettext(e.msgid) != e.msgstr]

    assert not stale, f'compile the catalogue again: {stale}'


@pytest.mark.django_db
@override_settings(LANGUAGE_CODE='fa')
def test_a_session_that_has_ended_is_said_in_persian() -> None:
    answer = APIClient().post('/auth/refresh/', {'refresh': 'not.a.token'}, format='json')

    assert answer.json()['detail'] == ENDED_FA


def test_the_schema_reads_in_persian() -> None:
    with translation.override('fa'):
        generated = SchemaGenerator().get_schema(request=None, public=True)

    assert generated['paths']['/auth/sign-out/']['post']['summary'] == SIGN_OUT_FA
