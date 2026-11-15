"""4.2 GAMEPLAY page P1 (host side): the row table, the strings in 4 languages (font-safe: gameplay.py's own guard runs on import),
room for the 2 rows that come after the freeze, the GM item's constants."""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')))
import gameplay  # noqa: E402


def test_present_rows_are_the_six_switches_in_order():
    assert [r[0] for r in gameplay.present()] == ['difficulty', 'dribbling', 'setpieces', 'cpucards', 'cpuinj', 'gkinj']


def test_absent_rows_leave_no_line():
    for lang in ('it', 'en', 'fr', 'de'):
        labels = [x[0] for x in gameplay.page(lang)]
        assert len(labels) == 6 and gameplay.TAKERS[lang] not in labels and gameplay.ROLES[lang] not in labels


def test_room_for_two_more_rows():
    assert len(gameplay.present()) + 2 <= gameplay.PAGE_MAX_ROWS


def test_gm_item_default_is_personalizzato():
    assert gameplay.GM_SIZE == 1 and gameplay.GM_PERSONALIZZATO == 0 and gameplay.GM_ORIGINALE == 1
    for lang in ('it', 'en', 'fr', 'de'):
        assert gameplay.VALUES[lang][0] != gameplay.VALUES[lang][1]


def test_texts_fit_a_row():
    for lang in ('it', 'en', 'fr', 'de'):                  # (the longest label + value of a page row: the dribbling page's own widths)
        for lab, vals in gameplay.page(lang):
            assert len(lab) + max(map(len, vals)) <= 40, (lang, lab, vals)
        assert len(gameplay.TITLE[lang]) <= 34


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
            print('ok', k)
