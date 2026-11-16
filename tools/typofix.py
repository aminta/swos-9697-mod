"""4.2 (Davide 16/11, via MC): typos in the original exes' own strings, fixed once at the root - in place in the exe, so
every screen that shows the string (and the mod's texts that reuse it, frtext.REC_LINE) reads the corrected one; never a
second string. Same scheme as uefaname.py (4.1.2, EUFA -> UEFA).

FIXES[lang] = [(old, new)]: old is the exe's whole string (a string start: the byte before it is 0), new is never
longer; it is written in place, NUL-padded to old's length (so the terminator is where the game's code expects at most).
Every copy in obj2 whose bytes in the patched exe still read old is rewritten (strpool may have placed a pool string
over a freed copy: those bytes are no longer the string and are left alone, as uefaname). The original's bytes are
asserted (p.get) before the write; at least one copy per fix, in both the CD and the GOG exes.

The search for every other copy of a typo (MC's rule 0: grep first): FIND[lang] = the misspelt stem, searched in every
original exe of the language (CD + GOG) and the original DATA; each hit must be one of FIXES' strings
(test_typofix_all_found asserts it, so a new hit fails the host suite instead of shipping unfixed).
  - IT 'PARREGG' (PAREGGI, draws): one string in ITALIAN.EXE, the management record's line for a national-team coach
    (cseg_3892C, 'VINCITE %0 PARREGGI %1 SCON %2'; the friendlies' season record reuses it, frtext.REC_LINE). The
    other IT strings with the stem are spelt right: 'SPAREGGIO 3 POSTO', '3 SPAREGGIO', 'SPAREGGI**' (play-off)."""

FIXES = {
    'it': [(b'VINCITE %0 PARREGGI %1 SCON %2', b'VINCITE %0 PAREGGI %1 SCON %2')],
}
FIND = {'it': [b'PARREGG']}


def fixed(lang, s):
    """s (str or bytes) as the patched exe has it: frtext's texts quote the exe's own strings."""
    b = s.encode('latin-1') if isinstance(s, str) else s
    for old, new in FIXES.get(lang, ()):
        if b == old:
            b = new
    return b.decode('latin-1') if isinstance(s, str) else b


def patch(p, lang):
    """-> the number of strings rewritten (0 for a language with no fix)."""
    d2 = p.le.obj_bytes(2)                  # (the original exe: where the strings were)
    n = 0
    for old, new in FIXES.get(lang, ()):
        assert len(new) <= len(old) and b'\0' not in new, (old, new)
        key, k = old + b'\0', 0
        i = d2.find(key)
        while i >= 0:
            if (i == 0 or d2[i - 1] == 0) and p.get(2, i, len(key)) == key:   # (a string start; still the string)
                p.put(2, i, new + bytes(len(key) - len(new)))
                k += 1
            i = d2.find(key, i + 1)
        assert k >= 1, f'typofix: {old!r} not found in the {lang} exe'
        n += k
    return n
