"""4.2 preseason friendlies, part (b): the player-facing texts (tools/frtext.py) - the calendar label, the season
record's line and the FORMAT page in IT / EN / FR / DE: widths against their bars, font glyphs only, AE / OE / UE in
the German small-font text, the record line = each exe's own string (orig/), every figure of the fee table told in
every language, and the page as fmtgame would write it (298 px lines, 14-line pages). Host only."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, TOOLS)
import complist  # noqa: E402
import fmtgame  # noqa: E402
import frtext  # noqa: E402

ORIG = os.path.join(os.path.dirname(TOOLS), 'orig')


def test_frtext_check():
    assert frtext.check(ORIG) > 0


def test_frtext_bars():
    for what, lang, s, w, bar, where in frtext.rows():
        assert w <= bar, (what, lang, s, w, bar)
    for lang in frtext.LANGS:
        assert complist.px(frtext.LABEL[lang]) <= complist.CAL_PX


def test_frtext_format_through_fmtgame():
    """The page through fmtgame.write() itself (the builder's path): one entry named as the label per language and
    world, its text = frtext.format_pages()."""
    with tempfile.TemporaryDirectory() as tmp:
        files = fmtgame.write(tmp, frtext.format_items((0, 5)))
        assert sorted(n for n, _ in files) == sorted(f'FMT{l.upper()}{w or ""}.DAT' for l in frtext.LANGS
                                                     for w in (0, 5))
        for lang in frtext.LANGS:
            d = open(os.path.join(tmp, f'FMT{lang.upper()}5.DAT'), 'rb').read()
            assert frtext.LABEL[lang].encode() + b'\0' in d
            want = '\f'.join('\n'.join(p) for p in frtext.format_pages(lang)).encode('latin-1')
            assert want in d, lang


def test_frtext_fees_match_handoff():
    """The fee table told by the prose = friendlies-pick.md's FINAL table (percent of G, home / away)."""
    assert frtext.FEES == {'far up': (120, 50), 'stronger': (100, 40), 'similar': (50, 20), 'weaker': (30, 10),
                           'far down': (20, 5)}
    assert sum((frtext.FEES['weaker'][0], frtext.FEES['similar'][0], frtext.FEES['similar'][1],
                frtext.FEES['stronger'][1])) == 140          # an all-automatic season
