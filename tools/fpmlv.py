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
FORMAT page: PROSE[key] = {lang: [paragraph, ...]} from tools/fpmlv_prose.json (Davide's decisions of 17/11: 3 / 1 / 0,
a draw stays a draw, the tie-break order, three matchdays in May); format_item() returns the page's titles and text
(fmtgame.from_pack adds it: the slot-4 contest's own page), None for a key without prose.
Match title (title B): rnd / ndays = rnames' ML_I and its matchdays - fpv_round gives fpad.c's install the round name
'GIORNATA n' of a fixture ('SUPERCOPPA SERIE C GIORNATA 2'; rnames.check_titles asserts each one).
Table view (screen 1, Davide 17/11): the game's own table screen in longtable's mode VIEW_MODE (lt_ov), opened from
STAT of a league table that holds one of the stage's clubs (fmtpage's entry 9, shown with the view's title while this
season's instance exists - also after a save + load: the rows are the saved instance's). GLUE (asm, after the C in
obj3): fv_title for fmtpage's entry, fv_show for lt_ov - fpv_rows' rows into gplay's GP_OV_ROWS / GP_OV_ORD, the
names of the clubs of other divisions from their team files (winners' wn_disk), the zone key (zones.stage_key(title,
ML_T): the 1st place light blue, the legend VINCE / WINS / VAINQ / SIEG), the title, and the view's flags: vflags
bit 0 (VF_NOSTAT, the pack row's "view": {"stat": false}, the default) hides the screen's STAT entry - per view,
table-driven (MC 17/11), no case of any one competition.

    python3 tools/hosttest/run.py -k fpmlv      # the host tests (native fpmlv.c against stubs of fpml.h)
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'fpmlv.c')
LANGS = ('it', 'en', 'fr', 'de')
NN, NR = 4, 4                           # fpmlv.h FPV_NN / FPV_NR
TAB_SIZE = 4 + 8 + 8 * NN + 4 * NR + 4 * NN + 4 + NN + NN
VF_NOSTAT = 1                           # fpmlv.h FPV_VF_NOSTAT: the view has no STAT button
VIEW_MODE = 3                           # longtable / fmtpage OV_FLAG: a mini-league's table view (0 the table, 1 the
                                        # overall one, 2 FASE 1, 4 + k an earlier stage's)
ML_T = VIEW_MODE - 4                    # its zone key's table number (zones.stage_key: 80h + t, as lt_ov's ZSTAGE)
STAT_E = 9                              # DIY_leagueTournamentMenu's STATS entry (ESCI the next one)
TF = 24                                 # fpmlv.h FPV_TF
RESERVE = 0x980                         # obj3 room claimed by reserve() (the release shape's size + slack, asserted by patch())
SLACK = 256                              # (MC 17/11: the 256 B floor of every band)
ROOTS = ['fpv_done', 'fpv_wn_c', 'fpv_rline_c', 'fpv_calnames', 'fpv_table', 'fpv_title', 'fpv_legend', 'FPV_TAB',
         'fpv_round', 'fpv_view', 'fpv_rows']
EXT_ML = ('fp_ml_get', 'fp_ml_row', 'fp_ml_table')      # lane 1's (fpml.h), from fpad.LABELS
EXT_GP = ('GP_SEAS', 'GP_MGR', 'GP_WNSRC', 'WN_ST')     # gplay.LABELS

# the names when the pack row gives none (spec: the Italian name in all four exes, as COPPA ITALIA SERIE C / COPPA SERIE C)
NAMES = {'supercoppa_c': {'*': ['SUPERCOPPA SERIE C', 'SUPERCOPPA C']}}
# the 1st place's legend label (spec 4: new labels, zones.LABELS has no title entry)
LEGEND = {'it': 'VINCE', 'en': 'WINS', 'fr': 'VAINQ', 'de': 'SIEG'}
ZONE = 0x0D                             # zones.LIGHT_BLUE: the best way, the title
PROSE_JSON = os.path.join(HERE, 'fpmlv_prose.json')


def _prose():
    """key -> {lang: [paragraph, ...]}: the FORMAT page's text (fpmlv_prose.json: {key: {LANG: [...]}} or, one key
    only, {LANG: [...]} = the Supercoppa Serie C's; language keys in any case)."""
    import json
    if not os.path.exists(PROSE_JSON):
        return {}
    j = json.load(open(PROSE_JSON, encoding='utf-8'))
    if all(k.lower() in LANGS for k in j):
        j = {'supercoppa_c': j}
    return {key: {lang.lower(): list(v) for lang, v in t.items()} for key, t in j.items()}


PROSE = _prose()                        # key -> {lang: [paragraph, ...]}: the FORMAT page
LABELS = {}


def on():
    """The builds with the fixture port (fpad.on())."""
    import fpad
    return fpad.on()


ML_MAXCLUBS = 22                        # rows the game's table screen lays out without scrolling (longtable.ROWS)


def rows(comp):
    """The league competition's mini-league rows, checked."""
    out = comp.get('mini_leagues') or []
    assert len(out) <= min(NN, NR, 9), ('mini_leagues: at most', min(NN, NR), len(out))   # (9: one digit in 'N<id>00')
    for r in out:
        assert r.get('key') and (r.get('names') or r['key'] in NAMES), ('mini_leagues: a row without key / names', r)
    if out:                                             # (MC 17/11: no silent behaviour: the view keeps the table screen's layout, which scrolls
        big = [(d.get('names') or {}).get('*', ['?'])[0] for d in comp.get('divisions') or []      # past 22 rows and has group headers)
               if int(d.get('teams') or 0) > ML_MAXCLUBS]
        assert not big, ('mini_leagues: a league with a division of more than', ML_MAXCLUBS,
                         'clubs keeps its scroll arrows in the mini-league view (not supported: parked); divisions', big)
        assert not (comp.get('groups') or any(st.get('groups') for st in comp.get('stages') or [])), \
            'mini_leagues: a league with group headers keeps its header rows in the mini-league view (not supported: parked)'
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


def prose_check():
    """The FORMAT prose as the page shows it: every language of every key, the game's font only, wrapped lines within
    the page's width; {(key, lang): lines}."""
    import fmtgame
    import fmtpage
    out = {}
    for key, text in PROSE.items():
        assert set(text) == set(LANGS), ('fpmlv prose: 4 languages', key, sorted(text))
        for lang in LANGS:
            n = 0
            for para in text[lang]:
                up = fmtgame.ascii_up(para, lang)
                assert up == ' '.join(up.split()) and ' ,' not in up and ' :' not in up and ' .' not in up, (key, lang, up)
                bad = set(up) - set(__import__('complist').FONT)
                assert not bad, ('fpmlv prose: not the font', key, lang, sorted(bad))
                ls = fmtgame.wrap_px(up)
                assert all(fmtgame.px(x) <= fmtgame.PX_MAX and len(x) < fmtpage.LINE_W for x in ls), (key, lang, ls)
                n += len(ls) + 1
            out[key, lang] = n - 1
            assert n - 1 <= 2 * fmtpage.LINES, ('fpmlv prose: over two pages', key, lang, n - 1)
    return out


def rounds():
    """(rnames' index of matchday 1's round name, the matchdays named) - (0, 0) before rnames.patch / without them."""
    import rnames
    return rnames.LABELS.get('ML_I', 0), rnames.LABELS.get('ML_DAYS', 0) if rnames.LABELS.get('ML_I') else 0


def vflags(row):
    """A row's table-view flags: VF_NOSTAT unless the pack row says "view": {"stat": true}."""
    return 0 if (row.get('view') or {}).get('stat') else VF_NOSTAT


def table(comp, lang, name_off, country=''):
    """FPV_TAB's bytes (struct fpv_tab). name_off(bytes) -> the string's STR_BASE-relative offset (gplay._sadd)."""
    rs = rows(comp)
    rnd, ndays = rounds()
    assert not rnd or all(len(r.get('units') or []) <= ndays for r in rs), ('fpmlv: matchdays without a round name', ndays)
    nm, rec, ttl = [], [], []
    for r in rs:
        lo, short, rc, view = names(r, lang, country)
        nm.append((name_off(lo.encode('latin-1')), name_off(short.encode('latin-1'))))
        rec.append(name_off(rc.encode('latin-1')) if rc else 0)
        ttl.append(name_off(view.encode('latin-1')))
    assert all(a and b for a, b in nm) and all(ttl), 'fpmlv: a name at STR_BASE itself (0 = none in FPV_TAB)'
    pad = lambda v, n, z: list(v) + [z] * (n - len(v))
    b = struct.pack('<4B8s', len(rs), len(rs), ZONE, rnd, legend(lang).encode('latin-1'))
    b += b''.join(struct.pack('<II', *x) for x in pad(nm, NN, (0, 0)))
    b += struct.pack(f'<{NR}I', *pad(rec, NR, 0)) + struct.pack(f'<{NN}I', *pad(ttl, NN, 0))
    b += struct.pack('<B3x', ndays) + bytes(pad([vflags(r) for r in rs], NN, 0))
    b += bytes(pad([int(comp['id'], 16) if comp.get('id') else 0] * len(rs), NN, 0))   # (vcid: the league's contest id)
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


GLUE = """
fv_stinit:                              ; the statistics menu's onInit / onReturn, after the chain's own (fmtpage's
    call PREV_INIT                      ; fp_ovinit, winners', ctview's): entry 9, when no earlier stage has it, is the
    pushad                              ; viewed league's mini-league table view - shown with its title, the column
    mov byte [FV_MLE], 0                ; re-spaced as fmtpage's fp_stpos does for a stage entry
    mov ebx, MENU_ + 16h
    cmp word [ebx + 9 * 38h + 4], 0
    je .r
    call fv_title
    test eax, eax
    jz .r
    mov [ebx + 9 * 38h + 26h], eax
    mov word [ebx + 9 * 38h + 4], 0
    mov byte [FV_MLE], 1
    mov edx, 30
    mov esi, fv_order
.l: movzx eax, byte [esi]
    inc esi
    cmp al, 0FFh
    je .r
    imul eax, eax, 38h
    cmp word [ebx + eax + 4], 0
    jne .l
    mov [ebx + eax + 16h], dx
    add edx, 19
    jmp .l
.r: popad
    ret
fv_order: db 1, 2, 3, 5, 6, 7, 8, 9, 0FFh
FV_MLE: db 0

fv_sel9:                                ; entry 9's select: the view's (the table screen's mode MLV_, out of STAT as
    cmp byte [FV_MLE], 0                ; its EXIT), else fmtpage's own fp_st9
    jne .v
    jmp FP_ST9
.v: mov byte [OV_FLAG], MLV_
    jmp EXIT_FN

fv_title:                               ; eax = the title of the viewed league's mini-league view
    push es                             ; (DIY_'s table), 0 = none now
    push ds
    pop es
    cld
    push dword FV_T
    push dword DIY_
    call FPV_VIEW
    add esp, 8
    pop es
    test eax, eax
    jz .r
    mov eax, [FV_T]
    add eax, STRB_
.r: ret

fv_show:                                ; longtable lt_ov, OV_FLAG = the view's mode (esi = the table shown): CF = 0 and
    pushad                              ; the view is up - its rows, names, zone key, title, flags; CF = 1: no view now
    push es
    push ds
    pop es
    cld
    push dword FV_TF
    push dword [SELTEAMS]
    push dword GP_OV_ORD
    push dword GP_OV_ROWS
    push esi
    call FPV_ROWS
    add esp, 20
    pop es
    test eax, eax
    jz .no
    mov [GP_OV_N], eax
    mov dword [GP_OV_ANNUAL], 0
    mov ebx, FV_TF                      ; a club of another division: its name from its team file (winners' wn_disk,
    mov ecx, 4                          ; as the WINNERS page names it)
.nm:
    cmp byte [ebx + 4], 0
    je .nx
    mov ax, [ebx]
    xor edx, edx
    call WN_DISK
    test edx, edx
    jz .nx
    xor edi, edi
.nc:
    mov al, [edx + edi]
    mov [ebx + 5 + edi], al
    inc edi
    cmp edi, 17
    jb .nc
.nx:
    add ebx, TF_
    dec ecx
    jnz .nm
    mov esi, [esp + 4]                  ; (pushad's esi)
    mov byte [OV_ON], 1
ZSTAGE
    push es
    push ds
    pop es
    cld
    push dword FV_T
    push esi
    call FPV_VIEW
    add esp, 8
    pop es
    test eax, eax
    jz .no
    mov edx, [FV_T]
    add edx, STRB_
    mov [MENU_ + 16h + 26h], edx        ; (entry 0's text: the unpacked menu's pointer only, as lt_ov's other titles)
    test al, VF_NOSTAT_                 ; the view's own flags: no STAT on this screen (the selection off it: the
    jz .st                              ; next entry, ESCI)
    mov ebx, MENU_ + 16h + STAT_E_ * 38h
    mov word [ebx + 4], 1
    cmp [MENU_ + 0Ch], ebx
    jne .st
    add ebx, 38h
    mov [MENU_ + 0Ch], ebx
.st:
    popad
    clc
    ret
.no:
    mov byte [OV_ON], 0
    popad
    stc
    ret
align 4
FV_T: dd 0
FV_TF: times 4 * TF_ db 0
"""


def glue(p, at, syms, lim):
    """The table view's asm (GLUE) at obj3+at: fv_show bound to longtable's LT_MLP (lt_ov's mode VIEW_MODE); the
    statistics menu's onInit / onReturn chained to fv_stinit and its entry 9's select to fv_sel9 (fmtpage.ML: pointers
    in obj2, no byte in fmtpage's code). Returns its end, at itself in a build without the table screen's modes."""
    import fmtpage
    import gplay
    import longtable
    import lp36
    import mkseason
    import nasmcave
    import sacups
    import winners
    import zones
    if 'LT_MLP' not in longtable.LABELS or 'sel9' not in fmtpage.ML or 'wn_disk' not in winners.LABELS:
        return at
    init = fmtpage.ML['init']
    prev = p.target(2, init)
    assert prev == p.target(2, init + 4) and p.target(2, fmtpage.ML['sel9']) == fmtpage.ML['st9'], \
        ('fpmlv: the statistics menu onInit / onReturn differ, or entry 9 select is not fp_st9', prev)
    sym = {'FPV_VIEW': syms['fpv_view'][:2], 'FPV_ROWS': syms['fpv_rows'][:2], 'DIY_': (2, lp36._sites(p)['DIY']),
           'STRB_': (2, sacups.STR_BASE), 'SELTEAMS': (2, mkseason._hook_sites(p)[3]), 'WN_DISK': winners.LABELS['wn_disk'],
           'OV_ON': (2, fmtpage.OV['on']), 'OV_FLAG': (2, fmtpage.OV['flag']), 'MENU_': zones._current_menu(p),
           'TF_': (0, TF), 'VF_NOSTAT_': (0, VF_NOSTAT), 'STAT_E_': (0, STAT_E), 'MLV_': (0, VIEW_MODE),
           'PREV_INIT': prev, 'FP_ST9': fmtpage.ML['st9'], 'EXIT_FN': fmtpage.ML['exit'],
           **{k: gplay.LABELS[k] for k in ('GP_OV_ORD', 'GP_OV_ROWS', 'GP_OV_N', 'GP_OV_ANNUAL')}}
    src = GLUE.replace('ZSTAGE\n', longtable.ZSTAGE_ASM if zones.STG else '')
    if zones.STG:
        sym.update({'ZSKEY': (2, zones.STG['key']), 'ZSTG': (2, zones.STG['flag']), 'ZNAME_': (0, zones.NAME)})
    at = (at + 15) & ~15
    code = zones._put_obj(p, src, at, sym, 3)
    assert at + len(code) <= lim, ('fpmlv: the view glue past its obj3 room', hex(at + len(code)), hex(lim))
    lab = nasmcave.labels(src, at, sym)
    import cobj
    cobj.add_ptr(p, longtable.LABELS['LT_MLP'], 3, lab['fv_show'], longtable.LABELS['LT_OBJ'])
    for off, t in ((init, 'fv_stinit'), (init + 4, 'fv_stinit'), (fmtpage.ML['sel9'], 'fv_sel9')):
        p.retarget(2, off, 3, lab[t])
        p.put(2, off, struct.pack('<I', lab[t]))
    LABELS.update({k: (3, lab[k]) for k in ('fv_title', 'fv_show', 'fv_stinit', 'fv_sel9', 'FV_TF')})
    print(f'exe: mini-league table view (screen 1): glue obj3+{at:#x}..{at + len(code):#x} ({len(code)} B), lt_ov mode '
          f'{VIEW_MODE} -> fv_show, STAT onInit / onReturn -> fv_stinit (then obj{prev[0]}+{prev[1]:#x}), entry 9 select '
          f'-> fv_sel9, STAT hidden per view (vflags)')
    return at + len(code)


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
    cend = end
    end = glue(p, end, syms, at + RESERVE)
    assert at + RESERVE - end >= SLACK, ('fpmlv: under 256 B left of its obj3 room', hex(end))
    p.put(*syms['FPV_TAB'], table(comp, lang, lambda x: gplay._sadd(area, x) - sacups.STR_BASE, country))
    cobj.add_ptr(p, mldone[1], *syms['fpv_done'][:2], mldone[0])
    if wn_mlp:
        cobj.add_ptr(p, wn_mlp[1], *syms['fpv_wn_c'][:2], wn_mlp[0])
    if 'FP_RND' in fsyms:                               # (fpad.c install: the fixture's round name - title B)
        cobj.add_ptr(p, fsyms['FP_RND'][1], *syms['fpv_round'][:2], fsyms['FP_RND'][0])
    if 'FP_NAMES' in fsyms:                             # (fpad.c install: the fixture's own calendar names)
        cobj.add_ptr(p, fsyms['FP_NAMES'][1], *syms['fpv_calnames'][:2], fsyms['FP_NAMES'][0])
    LABELS.update(syms)
    print(f'exe: mini-league views (fpmlv.c) obj3+{at:#x}..{cend:#x}, with the view glue ..{end:#x} of {at + RESERVE:#x} ({at + RESERVE - end} B left), '
          f'{len(rows(comp))} row(s), FP_MLDONE -> fpv_done' + (', winners N -> fpv_wn_c' if wn_mlp else ''))
    return end
