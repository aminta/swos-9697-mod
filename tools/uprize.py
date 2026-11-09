"""4.1 RC3 (Miguel via Davide, 09/11): UEFA prize money for the career club of a league-phase world - uprize.c in
obj4 after usmenu (swreg.USMENU_AT's page), its table first. Hooks: uesum's US_UP (us_hook, after every knockout
match) -> up_ko; lp36's lp_cb_res (chained before uefacoef's uc_res) -> up_res; cseg_5DEB9's euro-cup term (`mov eax,
[D8CB6]`) -> up_eur (0 in a league-phase world: no second payment next summer). The paid state: the engine item 'UP'
(UP_SIZE B, world only; up_new on a new career)."""
import os
import re
import struct

UP_SIZE = 8
# UEFA's distribution 2026/27 (UEFA circular No. 48/2026, 13 July 2026, sections 1.1.2.1-2, 1.2.1-2, 1.3.1-2; euros):
# participation (league-phase allocation), league-phase win, draw, qualification for the knockout play-offs, round of
# 16, quarter-finals, semi-finals, final, winner (extra)
EUROS = (
    (18_620_000, 2_100_000, 700_000, 1_000_000, 11_000_000, 12_500_000, 15_000_000, 18_500_000, 6_500_000),   # CL
    (4_310_000, 450_000, 150_000, 300_000, 1_750_000, 2_500_000, 4_200_000, 7_000_000, 6_000_000),            # EL
    (3_170_000, 400_000, 133_000, 200_000, 800_000, 1_300_000, 2_500_000, 4_000_000, 3_000_000))              # UECL
ROW = {'it': 'PREMI UEFA:', 'en': 'UEFA PRIZE MONEY:', 'fr': 'PRIMES UEFA:', 'de': 'UEFA-PRAEMIEN:'}  # (the statement)
STMT = r"""
up_stmt:                                ; finance's `call fi_stmt` (the in-season statement's total, D1) re-pointed here
    call FI_STMT
    call UP_SHOW
    test eax, eax
    jz .r
    push dword [D1]
    mov dword [D0], 2                   ; (the old balance's row: ours 15 px below it)
    call CALCMENU
    mov esi, [A0]
    mov bx, [esi + 22]
    add bx, 15
    mov dword [D0], 3                   ; the competition bonuses' row (label 3, value 13: the staying club's season-
    call CALCMENU                       ; start statement shows it; the in-season one hid it) with our label
    mov esi, [A0]
    mov word [esi + 4], 0
    mov [esi + 22], bx
    mov dword [esi + 38], UP_ROW
    mov dword [D0], 13
    call CALCMENU
    mov esi, [A0]
    mov word [esi + 4], 0
    mov [esi + 22], bx
    mov eax, [esi + 38]
    mov [A1], eax
    mov eax, [CBON]
    mov [D0], eax
    call WRITEBAL
    mov dword [D0], 4                   ; the rows below it 10 px down (labels 4..11, values 14..21), the total and the
    call .down                          ; new balance 5 / 10 px back up (their 20 px gaps: 15, as the other rows - the
    mov dword [D0], 14                  ; new balance's box stays above CONTINUA with finance's and FFP's rows too)
    call .down
    pop dword [D1]
.r:
    ret
.down:
    call CALCMENU
    mov esi, [A0]
    add word [esi + 22], 10
    add word [esi + 22 + 56], 10
    add word [esi + 22 + 2 * 56], 10
    add word [esi + 22 + 3 * 56], 10
    add word [esi + 22 + 4 * 56], 10
    add word [esi + 22 + 5 * 56], 10
    add word [esi + 22 + 6 * 56], 5
    ret
UP_ROW: ROW_DB
"""
# the league ranking pillar (the same circular, 1.1.2.2 / 1.2.2 / 1.3.2): one share (the 36th: 1, the 1st: 36),
# places 1-8 extra, places 9-16 extra
RANKING = ((275_000, 2_000_000, 1_000_000), (75_000, 600_000, 300_000), (28_000, 400_000, 200_000))
K = (1, 20)                     # the game's money per euro (placeholder until Davide's choice)
LABELS = {}


def amounts(k=K):
    """[cup][payment] in the game's money: euros x K, rounded to thousands (the statement's rows are); the ranking's
    share not rounded (uprize.c rounds shares x places)."""
    return [[(e * k[0] // k[1] + 500) // 1000 * 1000 for e in cup] + [rk[0] * k[0] // k[1]] +
            [(e * k[0] // k[1] + 500) // 1000 * 1000 for e in rk[1:]] for cup, rk in zip(EUROS, RANKING)]


def eur_site(p, d8cb6):
    """obj1: cseg_5DEB9's `mov eax, [D8CB6]; or eax, eax; jz` (the season start's euro-cup term)."""
    d = p.le.obj_bytes(1)
    key = b'\xa1' + struct.pack('<I', d8cb6) + b'\x0b\xc0\x0f\x84'
    hits = [m.start() for m in re.finditer(re.escape(key), d)]
    assert len(hits) == 1, ('uprize: the euro-cup term', [hex(h) for h in hits])
    assert p.get(1, hits[0], 5) == d[hits[0]:hits[0] + 5], 'uprize: the euro-cup term already patched'
    return hits[0]


def patch(p, at, ext, lang):
    """uprize.c + its table at obj4:at (usmenu's end); ext: uesum's symbols (UC, UD, SEASONP, W_LPW, US_UP).
    Returns the end."""
    import cobj
    import finance
    import kitcolors
    import lp36
    import sacups
    import swe
    room = 0x1000 * swe.OBJ4_PAGES
    t0 = at = (at + 3) & ~3
    tab = b''.join(struct.pack('<12I', *c) for c in amounts())
    p.put(4, at, tab)
    tab_at, at = at, at + len(tab)
    s = finance.SITES
    d8cb6 = sacups.COMP_SLOTS[0] + 0xC
    a0 = sacups.regs(p.le.obj_bytes(1))['A0']
    cs = kitcolors._career_syms(p)
    if lp36.LABELS:
        assert (2, lp36._sites(p)['DIY']) == ext['UD'], ('uprize: lp36 DIY = uesum UD', ext['UD'])
    ext = dict(ext, CTEAM=cs['CAREER_TEAM'], GAMETYPE=cs['GAMETYPE'], NEWBAL=s['NEWBAL'],
               CBON=(2, s['D6B88'][1] + 4), FF_INC=(3, finance.LABELS['FF_INC']), D8CB6=(2, d8cb6),
               A3R=(2, a0 + 12), A4R=(2, a0 + 16), D1R=(2, a0 - 28), D2R=(2, a0 - 24), UP_TAB=(4, tab_at))
    res = lp36.LABELS.get('lp_cb_res')                  # (uefacoef's jmp uc_res, else its ret; none: no league phase
    chain = res is not None and p.get(1, res, 1)[0] == 0xE9     # in this exe, up_res never called)
    assert res is None or chain or p.get(1, res, 1)[0] == 0xC3, ('lp_cb_res', bytes(p.get(1, res, 5)).hex())
    if chain:
        ext['RESOLD'] = (1, res + 5 + struct.unpack('<i', bytes(p.get(1, res + 1, 4)))[0])
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uprize.c'),
                         ['-Oz', '-fno-zero-initialized-in-bss', f'-DRES_CHAIN={int(chain)}'])
    syms, end, bss = cobj.link(p, obj, at, (4, 0), externs=ext, limit=room, text_obj=4)
    assert bss == 0, ('uprize.c: no .bss', bss)
    import complist
    import nasmcave
    assert all(ch in complist.FONT for ch in ROW[lang]) and complist.px(ROW[lang]) <= complist.px(finance.ROW[lang]) + 8, \
        ('uprize: the statement label', lang, ROW[lang])
    gat = (end + 3) & ~3
    sym = {k: s[k] for k in ('D0', 'D1', 'A0', 'A1', 'CALCMENU', 'WRITEBAL')}
    sym.update(FI_STMT=(3, finance.LABELS['fi_stmt']), UP_SHOW=syms['up_show'][:2], CBON=ext['CBON'])
    db = lambda t: 'db ' + ', '.join(str(c) for c in t.encode('ascii') + b'\0')
    src = nasmcave.sub(STMT, 'ROW_DB', db(ROW[lang]))
    code, fix, rel = nasmcave.assemble_obj(src, gat, sym, 4)
    lab = nasmcave.labels(src, gat, sym)
    assert not any(p.get(4, gat, len(code)))
    p.put(4, gat, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, gat + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, gat + o, t_obj, t_off)
    end = gat + len(code)
    assert end <= room, ('uprize past obj4', hex(end))
    assert p.rel_target(1, s['stmt'] + 1) == (3, finance.LABELS['fi_stmt']), 'uprize: finance\'s statement call'
    p.branch(1, s['stmt'], 0xE8, 4, lab['up_stmt'], 5)
    for pt, fn in (('US_UP', 'up_ko'), ('US_UP2', 'up_lp')):     # uesum's pointers: after a knockout match, the
        up = ext[pt]                                                # league phase's end
        p.put(up[0], up[1], struct.pack('<I', syms[fn][1]))
        p.add_ptr(up[0], up[1], *syms[fn][:2])
    if res is not None:
        p.branch(1, res, 0xE9, *syms['up_resg'][:2], n=5)
    es = eur_site(p, d8cb6)
    p.remove(1, es + 1)
    p.branch(1, es, 0xE8, *syms['up_eur'][:2], n=5)
    LABELS.clear()
    LABELS.update(syms)
    LABELS['UP_ST'] = (4, syms['UP'][1] + 4)
    LABELS.update({k: (4, v) for k, v in lab.items()})
    print(f'exe: UEFA prizes (uprize, 4.1 RC3): obj4+{t0:#x}..{end:#x} ({end - t0} B: table {len(tab)}, statement '
          f'{len(code)}); obj4 left '
          f'{room - end} B; K {K[0]}/{K[1]}')
    return end
