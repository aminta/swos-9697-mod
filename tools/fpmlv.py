"""4.2 the fixture port's mini-league (the Supercoppa Serie C): its names, WINNERS line, management record line and
table view - lane 2 (design: internal/handoff/supercoppa-c-design-20261116.md (e); spec: supercoppa-c-spec.md).

GENERIC: one pack row of the league competition's 'mini_leagues' (lane 1 compiles it into FP_MLT, fpml.h) names
everything here:
    {"key": "supercoppa_c", "names": {"*": [long, calendar label]}, "entrants": [[div, place], ...],
     "record": {lang or "*": name}, ...}
'names' / 'record' missing: NAMES / the long name. Row i of the list: fp_mlrow.id = i + 1, .name = i, .rec = i,
.flags bit 0 (FP_MLF_RECORD) = the row has 'record' (indices(): the ONE place that numbers them - fpad.py's FP_MLT
compiler calls it).

What the exe gets (fpmlv.c, obj3; table(): FPV_TAB in the exe's language, every string checked - CONVENTIONS 1: font
characters only, each within its bar):
  nm[name]   the slot's long name (the title '<country> <long>': complist.TITLE_MAX / VC_PX) and the career calendar's
             label (complist.CAL_PX) - what gplay's ko_one copies; fpad.c's install took the national supercup's;
  rec[rec]   the management record's line (gplay.REC_PX);
  ttl[name]  the table view's title; leg: the 1st place's legend label (LEGEND, <= 5 characters, zones.LEG_W).
WINNERS (winners.py): win_sources() gives fmtgame.win_lines the line of every division with an entrant, source
'N' + id + '00' (wn_src's generic path: GP_WNSRC = 'N' | id << 8) -> fpv_wn_c through the dword WN_MLP.
FORMAT page: PROSE[key] = {lang: [paragraph, ...]} - EMPTY here (the prose is the translation task's; spec 3 has the
drafts, not approved); format_item() returns the page's titles and text once it is filled, None before.

    python3 tools/hosttest/run.py -k fpmlv      # the host tests (native fpmlv.c against stubs of fpml.h)
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'fpmlv.c')
LANGS = ('it', 'en', 'fr', 'de')
NN, NR = 4, 4                           # fpmlv.h FPV_NN / FPV_NR
TAB_SIZE = 4 + 8 + 8 * NN + 4 * NR + 4 * NN
RESERVE = 0x440                         # obj3 room claimed by reserve() (the release shape's size + slack, asserted by patch())
SLACK = 64
ROOTS = ['fpv_done', 'fpv_wn_c', 'fpv_rline_c', 'fpv_calnames', 'fpv_table', 'fpv_title', 'fpv_legend', 'FPV_TAB']
EXT_ML = ('fp_ml_get', 'fp_ml_row', 'fp_ml_table')      # lane 1's (fpml.h), from fpad.LABELS
EXT_GP = ('GP_SEAS', 'GP_MGR', 'GP_WNSRC', 'WN_ST')     # gplay.LABELS

# the names when the pack row gives none (spec: the Italian name in all four exes, as COPPA ITALIA SERIE C / COPPA SERIE C)
NAMES = {'supercoppa_c': {'*': ['SUPERCOPPA SERIE C', 'SUPERCOPPA C']}}
# the 1st place's legend label (spec 4: new labels, zones.LABELS has no title entry)
LEGEND = {'it': 'VINCE', 'en': 'WINS', 'fr': 'VAINQ', 'de': 'SIEG'}
ZONE = 0x0D                             # zones.LIGHT_BLUE: the best way, the title
PROSE = {}                              # key -> {lang: [paragraph, ...]}: the FORMAT page (the translation task fills it)
LABELS = {}


def on():
    """The builds with the fixture port (fpad.on())."""
    import fpad
    return fpad.on()


def rows(comp):
    """The league competition's mini-league rows, checked."""
    out = comp.get('mini_leagues') or []
    assert len(out) <= min(NN, NR, 9), ('mini_leagues: at most', min(NN, NR), len(out))   # (9: one digit in 'N<id>00')
    for r in out:
        assert r.get('key') and (r.get('names') or r['key'] in NAMES), ('mini_leagues: a row without key / names', r)
    return out


def indices(comp):
    """Per row (id, name, rec, flags) for FP_MLT: id = i + 1, name = rec = i, flags bit 0 = the record line."""
    return [(i + 1, i, i, 1 if r.get('record') else 0) for i, r in enumerate(rows(comp))]


def _pick(names, lang):
    v = names.get(lang) or names.get('*') or names.get('en') or next(iter(names.values()))
    v = v if isinstance(v, list) else [v]
    return [x.upper() for x in v]


def names(row, lang, country=''):
    """(long, calendar label, record line, view title) of a row in lang, each checked against its bar."""
    import complist
    import gplay
    nm = _pick(row.get('names') or NAMES[row['key']], lang)
    long_, short = nm[0], nm[1 if len(nm) > 1 else 0]
    what = f"mini_league {row['key']} {lang}"
    complist.cal_label(short, what)                     # (<= CAL_PX, font characters only)
    lo = long_
    if country:
        complist.LANG[:] = [lang]
        lo = complist._fit(country, long_, short)
    t = f'{country} {lo}'.strip()
    assert len(t) <= complist.TITLE_MAX and complist.px(t) <= complist.VC_PX and all(ch in complist.FONT for ch in t), \
        (what, 'title', t, len(t), complist.px(t))
    rec = _pick(row['record'], lang)[0] if row.get('record') else None
    if rec is not None and complist.px(rec) > gplay.REC_PX:
        rec = short
    assert rec is None or (complist.px(rec) <= gplay.REC_PX and all(ch in complist.FONT for ch in rec)), (what, 'record', rec)
    assert all(ch in complist.FONT for ch in long_), (what, 'view title', long_)
    return lo, short, rec, long_


def legend(lang):
    import complist
    import zones
    s = LEGEND[lang]
    assert len(s) <= 5 and complist.px(s) <= zones.LEG_W and all(ch in complist.FONT for ch in s), ('legend', lang, s)
    return s


def table(comp, lang, name_off, country=''):
    """FPV_TAB's bytes (struct fpv_tab). name_off(bytes) -> the string's STR_BASE-relative offset (gplay._sadd)."""
    rs = rows(comp)
    nm, rec, ttl = [], [], []
    for r in rs:
        lo, short, rc, view = names(r, lang, country)
        nm.append((name_off(lo.encode('latin-1')), name_off(short.encode('latin-1'))))
        rec.append(name_off(rc.encode('latin-1')) if rc else 0)
        ttl.append(name_off(view.encode('latin-1')))
    assert all(a and b for a, b in nm) and all(ttl), 'fpmlv: a name at STR_BASE itself (0 = none in FPV_TAB)'
    pad = lambda v, n, z: list(v) + [z] * (n - len(v))
    b = struct.pack('<4B8s', len(rs), len(rs), ZONE, 0, legend(lang).encode('latin-1'))
    b += b''.join(struct.pack('<II', *x) for x in pad(nm, NN, (0, 0)))
    b += struct.pack(f'<{NR}I', *pad(rec, NR, 0)) + struct.pack(f'<{NN}I', *pad(ttl, NN, 0))
    assert len(b) == TAB_SIZE
    return b


def win_sources(comp, k):
    """fmtgame.win_lines: [(names, source)] of the mini-leagues with an entrant from division k; none in a build
    without the port (gplay.c gp_wn_c does not know 'N')."""
    if not comp.get('mini_leagues') or not on():
        return []
    return [(r.get('names') or NAMES[r['key']], f'N{i + 1}00') for i, r in enumerate(rows(comp))
            if any(e[0] == k for e in r['entrants'])]


def format_item(row, countries):
    """The FORMAT page of a row: ({lang: the slot's title '<country> <long>' - fmtpage's key}, {lang: [paragraph]}),
    None while PROSE has no text for its key. countries: {lang: the pack's button name}."""
    text = PROSE.get(row['key'])
    if not text:
        return None
    assert all(text.get(lang) for lang in LANGS), ('fpmlv.PROSE: 4 languages', row['key'])
    titles = {lang: f"{countries.get(lang, '')} {names(row, lang, countries.get(lang, ''))[0]}".strip() for lang in LANGS}
    return titles, {lang: list(text[lang]) for lang in LANGS}


WN_ASM_CALL = """    cmp bl, 'N'                         ; 4.2 a mini-league (fpmlv.c fpv_wn_c, obj3: bound by fpmlv.patch;
    jne .mlc                            ; unbound - no producer in this build: nothing)
    mov eax, 0FFFEh
    cmp dword [wn_mlp], 0
    je .mlx
    call [wn_mlp]
    jmp .mlx
.mlc:
    call GP_WN_C
.mlx:
"""


def reserve(p, at):
    """Claims fpmlv.c's room in obj3's chain (patch.py, before the chain's end); patch() links there after fpad.patch
    (lane 1's fp_ml_* are obj4 symbols known only then). Returns the end."""
    if not on():
        return at
    at = (at + 15) & ~15
    assert not any(p.get(3, at, RESERVE)), 'fpmlv: obj3 room not free'
    LABELS['AT'] = at
    return at + RESERVE


def size(flags=('-Oz',)):
    """fpmlv.c's linked size in the exe's shape (a dry link: every extern at a dummy address)."""
    import cobj
    import collections
    import swefile

    class _Dry(swefile._Rec):
        recs = collections.defaultdict(list)

        def _page(self, *a):
            return 0, 0

        def _record(self, *a):
            return None
    obj = cobj.compile_c(SRC, tuple(flags), sections=True)
    ext = {k: (4, 0x100 + 16 * i) for i, k in enumerate(EXT_ML)}
    ext.update({k: (2, 0x100 + 16 * i) for i, k in enumerate(EXT_GP)})
    _, end, bss = cobj.link(_Dry(), obj, 0, (3, 0), externs=ext, text_obj=3, roots=ROOTS)
    assert not bss, 'fpmlv.c: no .bss'
    return end


def patch(p, comp, lang, area, country, fsyms, gsyms, mldone, wn_mlp=None):
    """Links fpmlv.c at reserve()'s room (obj3) against lane 1's fp_ml_* (fsyms: fpad.LABELS) and gplay's symbols, puts
    FPV_TAB, binds FP_MLDONE (mldone: (obj, offset) of lane 1's dword) to fpv_done and winners' dword WN_MLP to
    fpv_wn_c. Returns the code's end, None in a build without the port / the producer."""
    if not on() or 'AT' not in LABELS or not all(k in fsyms for k in EXT_ML):
        return None
    import cobj
    import gplay
    import sacups
    assert gplay.WN_SIZE == 4 + 4 * 40, 'fpmlv.c: struct wn_state (gplay.c WN_N 40)'
    at = LABELS['AT']
    ext = {k: fsyms[k] for k in EXT_ML}
    ext.update({k: gsyms[k] for k in EXT_GP})
    obj = cobj.compile_c(SRC, ('-Oz',), sections=True)
    syms, end, bss = cobj.link(p, obj, at, (3, 0), externs=ext, limit=at + RESERVE, text_obj=3, roots=ROOTS)
    assert not bss, 'fpmlv.c: no .bss (its state is the FP item\'s and WN_ST)'
    assert at + RESERVE - end >= SLACK, ('fpmlv: under 64 B left of its obj3 room', hex(end))
    p.put(*syms['FPV_TAB'], table(comp, lang, lambda x: gplay._sadd(area, x) - sacups.STR_BASE, country))
    cobj.add_ptr(p, mldone[1], *syms['fpv_done'][:2], mldone[0])
    if wn_mlp:
        cobj.add_ptr(p, wn_mlp[1], *syms['fpv_wn_c'][:2], wn_mlp[0])
    if 'FP_NAMES' in fsyms:                             # (fpad.c install: the fixture's own calendar names)
        cobj.add_ptr(p, fsyms['FP_NAMES'][1], *syms['fpv_calnames'][:2], fsyms['FP_NAMES'][0])
    LABELS.update(syms)
    print(f'exe: mini-league views (fpmlv.c) obj3+{at:#x}..{end:#x} of {at + RESERVE:#x} ({at + RESERVE - end} B left), '
          f'{len(rows(comp))} row(s), FP_MLDONE -> fpv_done' + (', winners N -> fpv_wn_c' if wn_mlp else ''))
    return end
