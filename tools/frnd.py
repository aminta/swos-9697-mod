"""4.2 preseason friendlies (a), the engine (Motore): tools/frstep.c (+ frnd.c, frpick.c) linked into the obj4 band
FRND (swreg FRND_AT). Dormant unless on(): no byte of it (gplay.c GP_FRND 0; frtext / frstr gate FRSS.DAT and the
FORMAT page on it). Design: internal/handoff/motore-frnd-engine.md + motore-frnd-fable-review.md."""
import os


def on():
    """FRND=1 builds only until the engine's gates pass (then every career world)"""
    return os.environ.get('FRND') == '1'

import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'frstep.c')
BUFSZ = 4864                            # FR_BUF (swe.c .bss): the largest slice is World 2026-27's 4804 B (frdata) + room
SLACK = 256                             # (MC: >= 256 B left in the band, release shape)
LABELS = {}

ASM = r"""
fr_seasg:                               ; InitializeNewSeason's `call cseg_3D204` (careers only, never on a load): the
    call F3D204                         ; call first, then the friendlies' season step (frstep.c fr_season)
    pushad
    push es
    push ds
    pop es
    cld
    push dword [D0R]                    ; (the game's D0 / A0 kept: gp_mgr and FindTeamInCache use them)
    push dword [A0R]
    call GP_MGRF
    movzx eax, ax
    push eax
    call fr_season
    add esp, 4
    pop dword [A0R]
    pop dword [D0R]
    pop es
    popad
    ret

fr_cached_asm:                          ; cdecl u32 (u32 word): 1 = the club is in the team cache (FindTeamInCache, the
    pushad                              ; non-trapping one; D0 / A0 kept)
    push dword [D0R]
    push dword [A0R]
    mov eax, [esp + 44]
    mov [D0R], ax
    call FTIC
    setz al
    movzx eax, al
    mov [esp + 36], eax                 ; (popad's eax)
    pop dword [A0R]
    pop dword [D0R]
    popad
    ret
"""


def call_site(p):
    """InitializeNewSeason's `call cseg_3D204` (ffp.find: cseg_5DEB9's call + 5) and cseg_3D204"""
    import ffp
    site = ffp.LABELS['SEASON_SITE'] + 5              # (ffp.find ran on the unpatched exe: its sites kept)
    d = p.le.obj_bytes(1)
    assert d[site] == 0xE8
    return site, (1, site + 5 + struct.unpack_from('<i', d, site + 1)[0])


def patch(p, ssyms, gsyms):
    """links frstep.c (+ frnd.c, frpick.c) at obj4 + swreg.FRND_AT, after fpad.patch (its hooks chained) and finance
    (FI_FRGATE); returns the end, or None (dormant)"""
    if not on():
        return None
    import cobj
    import finance
    import fpad
    import nasmcave
    import sacups
    import swefile
    import swreg
    import tcache
    import careerworld
    need = ('GP_PAPI', 'GP_PSTEP', 'GP_PLEG', 'GP_WK', 'GP_MGR', 'GP_ST', 'GP_SEAS', 'GP_K', 'D1R', 'A1R', 'CAL_CUR',
            'GP_CFLAGS', 'FR_NAMEB', 'SC_ST', 'CAL', 'SEASONPLAYING', 'gp_mgr')
    if 'GP_PAPI' not in gsyms:          # (a build without gplay - no World 2026-27 packs: no fixture port, friendlies
        LABELS.clear()                  #  dormant, Chooser 16/11; fi_gate's FI_FRGATE stays 0 = skipped)
        print('exe: friendlies dormant (no gplay fixture port in this build)')
        return None
    for k in need:
        assert k in gsyms, ('frnd: gplay without', k)
    assert 'FR_BUF' in ssyms, 'frnd: swe.c without FR_BUF (swe.py -DFRND_BUF)'
    assert sacups.COMP_SLOTS[0] is not None, 'frnd: sacups without dseg_D8CAA (COMP_SLOTS)'
    assert 'FI_FRGATE' in finance.LABELS, 'frnd: finance.py without the FR_GATE chain'
    assert not any(p.get(4, swreg.FRND_AT, swreg.FRND_END - swreg.FRND_AT)), 'frnd: obj4+FRND_AT not free'
    off = fpad.gp_offsets(gsyms['GP_CFLAGS'])
    flags = ['-Oz', f'-DFR_BUFSZ={BUFSZ}'] + [f'-D{k}={off[k]}' for k in ('O_KO', 'O_SEASON', 'O_KIND', 'O_TW', 'O_D1',
                                                                          'O_PTS', 'C_MAGIC', 'C_NOC', 'C_KFR', 'C_LVBETTER')]
    regs = sacups.regs(p.le.obj_bytes(1))
    fs = finance.SITES
    so, soff = careerworld.SITES['slt']
    cal = gsyms['CAL']
    sct = gsyms['SC_ST']
    ext = {'GP_PAPI': gsyms['GP_PAPI'], 'GP_GST': gsyms['GP_ST'], 'GP_SEAS': gsyms['GP_SEAS'], 'GP_WK': gsyms['GP_WK'],
           'GP_MGR': gsyms['GP_MGR'], 'GP_K': gsyms['GP_K'], 'FR_D1R': gsyms['D1R'], 'FR_A1R': gsyms['A1R'],
           'FR_CAL': cal, 'FR_CALCUR': gsyms['CAL_CUR'], 'FR_SEASON': gsyms['SEASONPLAYING'],
           'FR_CWB': (so, soff + careerworld.WORLD_BYTE), 'FR_ST': (sct[0], sct[1] + 180), 'FR_BUF': ssyms['FR_BUF'],
           'FR_SLOT4': (2, sacups.COMP_SLOTS[0] + 16), 'FR_D6BA2': (2, fs['D6B9E'][1] + 4), 'FR_D6C4E': (2, fs['D6B9E'][1] + 0xB0),
           'tc_room': tcache.LABELS['tc_room'], **{k: swefile.LABELS[k] for k in ('swe_fopen_r', 'swe_fread', 'swe_fclose')}}
    site, f3d = call_site(p)
    assert p.call_target(1, site) == f3d, ('frnd: InitializeNewSeason\'s call cseg_3D204 already hooked', p.call_target(1, site))
    roots = ['fr_season', 'fr_step', 'fr_row', 'fr_leg', 'fr_gate', 'fr_pick', 'fr_given', 'fr_level', 'FR_NSTEP', 'FR_NLEG',
             'FR_CHOOSE', 'FR_AFTER4', 'FR_NAMES']
    test = os.environ.get('HOSTTEST_SYMS') == '1'     # (test builds: FR_TRACE, FR_GIVENW, FR_FEE, FR_G, FR_FB, FR_ROWC)
    if test:
        flags.append('-DFR_TEST')
        roots += ['FR_TRACE', 'FR_GIVENW', 'FR_FEE', 'FR_G', 'FR_FB', 'FR_ROWC']
    obj = cobj.compile_c(SRC, tuple(flags), sections=True)
    # (the glue first, its labels as the C's externs: its size from a dry assembly at the band's start)
    at = swreg.FRND_AT
    gsym = {'F3D204': f3d, 'D0R': (2, regs['A0'] - 32), 'A0R': (2, regs['A0']), 'GP_MGRF': (1, gsyms['gp_mgr']), 'FTIC': tcache.LABELS['sym']['FTIC'],
            'fr_season': (4, at)}
    code0, _, _ = nasmcave.assemble_obj(ASM, at, gsym, 4)
    c_at = (at + len(code0) + 15) & ~15
    ext['fr_cached_asm'] = (4, nasmcave.labels(ASM, at, gsym)['fr_cached_asm'])
    syms, end, bss = cobj.link(p, obj, c_at, (4, 0), externs=ext, limit=swreg.FRND_END, text_obj=4, roots=roots)
    assert not bss, ('frstep.c: no .bss in the band (FR_BUF is swe.c\'s)', bss)
    left = swreg.FRND_END - end         # (the band from swreg only: MC 16/11, no test override)
    assert left >= SLACK, ('frnd: the FRND band has under 256 B left - stop and report to MC', left)
    gsym['fr_season'] = syms['fr_season']
    code, fix, rel = nasmcave.assemble_obj(ASM, at, gsym, 4)
    assert len(code) == len(code0)
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    lab = nasmcave.labels(ASM, at, gsym)
    p.put(*syms['FR_NAMES'], gsyms['FR_NAMEB'])
    # the hooks: FRND first, what they held before (fpad's) chained through FR_NSTEP / FR_NLEG
    for hook, f, nxt in (('GP_PSTEP', 'fr_step', 'FR_NSTEP'), ('GP_PLEG', 'fr_leg', 'FR_NLEG')):
        prev = p.target(*gsyms[hook]) if any(p.get(*gsyms[hook], 4)) else None
        if prev:                        # (FPORT=1: fpad's pointer and its fixup sit in the slot - retargeted, never added
            cobj.add_ptr(p, syms[nxt][1], *prev, syms[nxt][0])        #  twice: Shaved 17/11, lepatch's add_ptr assert)
            p.retarget(gsyms[hook][0], gsyms[hook][1], *syms[f])
            p.put(gsyms[hook][0], gsyms[hook][1], struct.pack('<I', syms[f][1]))
            assert p.target(*gsyms[hook]) == syms[f], ('frnd: hook not retargeted', hook)
        else:
            cobj.add_ptr(p, gsyms[hook][1], *syms[f], gsyms[hook][0])
    assert 'GP_PROW' in gsyms, 'frnd: gplay without GP_PROW (gp_scrow_c\'s hook, GP_FRND)'
    cobj.add_ptr(p, gsyms['GP_PROW'][1], *syms['fr_row'], gsyms['GP_PROW'][0])   # (played friendlies' rows keep their name)
    cobj.add_ptr(p, finance.LABELS['FI_FRGATE'], *syms['fr_gate'], 3)
    try:
        import frchoose
        if frchoose.on():               # (the chooser page: its fixed slot, FRCH_AT + 8)
            cobj.add_ptr(p, syms['FR_CHOOSE'][1], 4, swreg.FRCH_AT + 8, syms['FR_CHOOSE'][0])
    except ImportError:
        pass
    p.branch(1, site, 0xE8, 4, lab['fr_seasg'])
    LABELS.clear()
    LABELS.update(syms, **{k: (4, v) for k, v in lab.items()}, FR_ST=ext['FR_ST'], FR_BUF=ssyms['FR_BUF'], site=site,
                  END=(4, end))
    print(f'exe: friendlies (frstep.c + frnd.c + frpick.c) obj4+{at:#x}..{end:#x} of {swreg.FRND_END:#x} ({left} B left), '
          f'season hook obj1+{site:#x}, hooks GP_PSTEP / GP_PLEG first (chained), fi_gate FI_FRGATE')
    return end


def check(p):
    """(patch.py, at the end) the season hook, the two gplay hooks and fi_gate's dword still lead here"""
    if not LABELS:                      # (dormant: nothing linked)
        return
    import finance
    import gplay
    g = gplay.LABELS
    assert p.call_target(1, LABELS['site']) == LABELS['fr_seasg'], 'frnd: season hook'
    assert p.target(*g['GP_PSTEP']) == LABELS['fr_step'] and p.target(*g['GP_PLEG']) == LABELS['fr_leg'], 'frnd: hooks'
    assert p.target(3, finance.LABELS['FI_FRGATE']) == LABELS['fr_gate'], 'frnd: fi_gate'
    assert p.target(*g['GP_PROW']) == LABELS['fr_row'], 'frnd: GP_PROW'
