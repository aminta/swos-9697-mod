"""4.2 GAMEPLAY = ORIGINALE / PERSONALIZZATO (Davide 15/11; design internal/handoff/gameplay-menu-design.md, MC). Host-side part P1:
the row table, the strings (4 languages, font-safe) and the save item's constants. No exe code yet (the page code goes into
the GAMEPLAY reserve of obj4pack, 0x400, after Shaved's commit is in 42-int).

OPTIONS gets ONE row GAMEPLAY (ORIGINALE / PERSONALIZZATO; FIRE on PERSONALIZZATO opens the page). The page holds the mod's
match-play switches as a TABLE of rows, each with a 'present' flag: a row that is not in yet (TIRATORI, RUOLI: after the
freeze) is simply absent - no empty line, no placeholder text; adding one later = one table entry + its module's mask hook,
inside the reserve (asserted: room for 2 more rows).
ORIGINALE is a MASK applied at kick-off (every switch acts as its original value; the sub-values are kept). GM_W, the engine
item 'GM' (1 B): 0 = PERSONALIZZATO (default, today's defaults), 1 = ORIGINALE; a save without GM loads PERSONALIZZATO.
SWOS++: the row is hidden and everything original (as every other row of ours)."""
import cpucards
import difficulty
import gkinj
import setpieces

GM_TAG = 'GM'
GM_SIZE = 1                             # engine item 'GM': 0 = PERSONALIZZATO (default), 1 = ORIGINALE
GM_PERSONALIZZATO, GM_ORIGINALE = 0, 1

LABEL = {'it': 'GAMEPLAY', 'en': 'GAMEPLAY', 'fr': 'GAMEPLAY', 'de': 'SPIELWEISE'}
VALUES = {'it': ('PERSONALIZZATO', 'ORIGINALE'), 'en': ('CUSTOM', 'ORIGINAL'),          # (value 0 first = GM_W's 0)
          'fr': ('PERSONNALISE', 'ORIGINAL'), 'de': ('INDIVIDUELL', 'ORIGINAL')}
TITLE = {'it': 'GAMEPLAY PERSONALIZZATO', 'en': 'CUSTOM GAMEPLAY', 'fr': 'GAMEPLAY PERSONNALISE', 'de': 'INDIVIDUELLE SPIELWEISE'}
YESNO = {'it': ('SI', 'NO'), 'en': ('YES', 'NO'), 'fr': ('OUI', 'NON'), 'de': ('JA', 'NEIN')}     # (the CPU rows: 0 = SI, today's default)
PRACTICE = {'it': 'GAMEPLAY: ORIGINALE', 'en': 'GAMEPLAY: ORIGINAL', 'fr': 'GAMEPLAY: ORIGINAL', 'de': 'SPIELWEISE: ORIGINAL'}
LEG = {'it': 'SINISTRA/DESTRA CAMBIA  FUOCO: AVANTI', 'en': 'LEFT/RIGHT CHANGE  FIRE: NEXT',
       'fr': 'GAUCHE/DROITE CHANGE  FEU: SUITE', 'de': 'LINKS/RECHTS AENDERT  FEUER: WEITER'}
# rows not in yet (after the freeze: takers, Marco's traits) - their texts are ready, the 'present' flag off
TAKERS = {'it': 'TIRATORI', 'en': 'TAKERS', 'fr': 'TIREURS', 'de': 'SCHUETZEN'}
TAKERS_V = {'it': ('AUTOMATICI', 'SCELTI'), 'en': ('AUTO', 'CHOSEN'), 'fr': ('AUTO', 'CHOISIS'), 'de': ('AUTO', 'GEWAEHLT')}
ROLES = {'it': 'RUOLI', 'en': 'ROLES', 'fr': 'ROLES', 'de': 'ROLLEN'}      # (Marco's position traits; fr / de to be confirmed)

# the page's rows in order: (key, present, label, values, module whose mask hook reads GM_W at kick-off)
ROWS = (
    ('difficulty', True, difficulty.LABEL, difficulty.VALUES, 'difficulty'),
    ('dribbling', True, difficulty.DRLABEL, difficulty.DRVALUES, 'difficulty'),      # (PERSONALIZZATO opens the dribbling page: nested)
    ('setpieces', True, setpieces.LABEL, setpieces.VALUES, 'setpieces'),
    ('takers', False, TAKERS, TAKERS_V, 'setpieces'),
    ('cpucards', True, cpucards.LABEL, YESNO, 'cpucards'),
    ('cpuinj', True, cpucards.LABEL_I, YESNO, 'cpucards'),
    ('gkinj', True, gkinj.LABEL, YESNO, 'gkinj'),
    ('roles', False, ROLES, YESNO, 'traits'),
)
PAGE_MAX_ROWS = len(difficulty.DP_ROWS)  # the dribbling page's 8 rows: the same page code (title, rows, legend, PREDEFINITI / INDIETRO)


def present():
    return [r for r in ROWS if r[1]]


def page(lang):
    """[(label, values)] of the present rows, in order, for a language."""
    return [(r[2][lang], tuple(r[3][lang])) for r in present()]


difficulty._font_guard(LABEL, VALUES, TITLE, YESNO, PRACTICE, LEG, TAKERS, TAKERS_V, ROLES)
assert len(present()) + 2 <= PAGE_MAX_ROWS, 'gameplay: no room for takers + roles on the page'
assert len({r[0] for r in ROWS}) == len(ROWS)
assert all(set(r[2]) == set(r[3]) == {'it', 'en', 'fr', 'de'} for r in ROWS), 'gameplay: a row misses a language'
assert all(len(VALUES[k]) == 2 and VALUES[k][GM_PERSONALIZZATO] and VALUES[k][GM_ORIGINALE] for k in LABEL)
