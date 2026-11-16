"""4.2 typofix.py (Davide 16/11: PAREGGI): the original exes' typos fixed in place. On the original exes (CD and GOG,
orig/): every hit of a misspelt stem (typofix.FIND) in an exe of its language is one of FIXES' strings and no DATA
file has it (a new hit fails here instead of shipping unfixed); patch() on a real LEPatch rewrites every copy, the
patched exe has no stem left, the new string is NUL-padded in the old one's bytes; other languages untouched.
Host only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)
import complist  # noqa: E402
import lepatch  # noqa: E402
import typofix  # noqa: E402

ORIG = os.path.join(os.path.dirname(TOOLS), 'orig')
EXE = {'it': 'ITALIAN.EXE', 'en': 'ENGLISH.EXE', 'fr': 'FRENCH.EXE', 'de': 'GERMAN.EXE'}


def _exes(lang):
    return [x for x in (os.path.join(ORIG, EXE[lang]), os.path.join(ORIG, 'gog', EXE[lang])) if os.path.isfile(x)]


def test_typofix_all_found():
    if not _exes('it'):
        return True, 'SKIP: orig/ exes missing'
    hits = []
    for lang, stems in typofix.FIND.items():
        olds = [o for o, _ in typofix.FIXES.get(lang, ())]
        for exe in _exes(lang):
            d = open(exe, 'rb').read()
            for st in stems:
                i = d.find(st)
                while i >= 0:
                    s0 = d.rfind(b'\0', 0, i) + 1
                    s = d[s0:d.index(b'\0', i)]
                    assert s in olds, f'{os.path.relpath(exe, ORIG)}: {s!r} has {st!r} and no typofix entry'
                    hits.append(s)
                    i = d.find(st, i + 1)
        dd = os.path.join(ORIG, 'DATA')
        for n in sorted(os.listdir(dd)) if os.path.isdir(dd) else ():
            b = open(os.path.join(dd, n), 'rb').read()
            assert not any(st in b for st in stems), f'DATA/{n} has a typo stem: not an exe string, fix it there'
    for lang, fx in typofix.FIXES.items():
        for old, new in fx:
            t = new.decode('latin-1')
            for k in ('%0', '%1', '%2'):                    # (the game's number fields: digits on screen)
                t = t.replace(k, '4')
            assert len(new) <= len(old) and all(c in complist.FONT for c in t), (old, new)
    return True, f'{len(hits)} hits, all in FIXES: {sorted(set(hits))}'


def test_typofix_patch():
    if not _exes('it'):
        return True, 'SKIP: orig/ exes missing'
    out = []
    for lang in EXE:
        for exe in _exes(lang):
            p = lepatch.LEPatch(exe)
            d2 = p.le.obj_bytes(2)
            n = typofix.patch(p, lang)
            want = sum(d2.count(o + b'\0') for o, _ in typofix.FIXES.get(lang, ()))
            assert n == want and (n >= 1) == (lang in typofix.FIXES), (exe, n, want)
            for st in typofix.FIND.get(lang, ()):
                assert st not in bytes(p.out), f'{exe}: {st!r} left after the patch'
            for old, new in typofix.FIXES.get(lang, ()):
                i = d2.find(old + b'\0')
                assert p.get(2, i, len(old) + 1) == new + bytes(len(old) + 1 - len(new)), (exe, old)
                assert typofix.fixed(lang, old.decode('latin-1')) == new.decode('latin-1')
            out.append(f'{os.path.relpath(exe, ORIG)} {n}')
    return True, ', '.join(out)
