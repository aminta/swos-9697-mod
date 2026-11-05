"""The competition engine's object, obj4 (engine step O, PLAN §19; CONVENTIONS 23bis). obj4 is the engine's alone: the
4.0.x minors keep obj3 (rule 23), so the engine's layout never races their chain.

    obj4+0     header: 'SWOS-ENG', u32 version, u32 -> obj4+0 (a self pointer: the harness finds obj4 in memory by
               the magic and checks it), u32 -> swe_init, u32 -> the arena, u32 the .bss size, u32 -> SWE_STATE
    obj4+0x40  swe.c's code + data (OBJ4_PAGES file pages)
    +32        (step W) u32 -> the world registry (swreg.py, obj4+REG_AT), u32 -> reg_enter, u32 -> reg_leave,
               u32 -> SEL_MODE, u32 -> REG_PREV; (W-modes M2) u32 -> SWE_CWORLD (the last contest's world), u32 -> SEL_CW
    tail       swe.c's .bss (the arena): zero-filled vsize; DOS/4GW does not zero it, swe_init does

patch.py adds the object (lepatch.add_object + OBJ4_PAGES pages) after obj3's; patch(p) links swe.c, sizes obj4 and
puts its base above obj3's end.

Step W: the game's first call into the engine. GoGetTeamsForPlay (FRIENDLY and the 3 DIY editors: one picker) calls
SelectTeamsFinalMenu; that call (chained: whatever it reaches now) goes to swe_sel_tramp in obj4, which calls
swe_sel_pre(M_FRIENDLY), the picker, swe_sel_post. In step W they only keep competitionsTable[254] as it was: the
picker lists what it listed before (W-modes adds World 2026-27). obj1 changes by that call's rel32 only."""
import os
import struct

LANG = ['it']                  # (patch.py: the exe's language, for LOCK_LINE)
LOCK_LINE = {'it': 'UN SOLO MONDO PER COMPETIZIONE', 'en': 'ONE WORLD PER COMPETITION',   # W-modes M2's lock line
             'fr': 'UN SEUL MONDE PAR COMPETITION', 'de': 'NUR EINE WELT PRO WETTBEWERB'}  # (Davide 2026-11-04)
AV_LINES = {        # step 2.5 (texts frozen, Davide 2026-11-05): [NATIONAL, PRESET, SEASON], split into 2 rows by av_rows
    'it': ('NAZIONALI NON ANCORA DISPONIBILI PER QUESTO MONDO', 'AL MOMENTO NON CI SONO COMPETIZIONI PREDEFINITE PER QUESTO MONDO',
           'AL MOMENTO NON CI SONO STAGIONI PER QUESTO MONDO'),
    'en': ('NATIONAL TEAMS NOT YET AVAILABLE FOR THIS WORLD', 'NO PRESET COMPETITIONS FOR THIS WORLD AT THE MOMENT',
           'NO SEASONS FOR THIS WORLD AT THE MOMENT'),
    'fr': ('EQUIPES NATIONALES PAS ENCORE DISPONIBLES POUR CE MONDE',
           'AUCUNE COMPETITION PREDEFINIE POUR CE MONDE POUR LE MOMENT', 'AUCUNE SAISON POUR CE MONDE POUR LE MOMENT'),
    'de': ('NATIONALMANNSCHAFTEN F\x9aR DIESE WELT NOCH NICHT VERF\x9aGBAR', 'ZURZEIT KEINE STANDARDWETTBEWERBE F\x9aR DIESE WELT',
           'ZURZEIT KEINE SAISONS F\x9aR DIESE WELT')}
AV_KINDS = (1, 2, 0)           # swe.c AV_TXT[kind - 1] order: PRESET, SEASON, NATIONAL -> AV_LINES' index
AV_LEN, AV_WIDTH = 40, 300     # (swe.c AV_LEN; the rows' width = the list area's)
UE = '\x9a'                    # (the exe's own U-umlaut glyph, as titlelegs' R\x9aCKSP.)


def av_rows(text):
    """the message's 2 rows: the word break with the most even widths (complist.px), each within AV_WIDTH"""
    import complist
    w = text.split(' ')
    cuts = [(' '.join(w[:k]), ' '.join(w[k:])) for k in range(1, len(w))]
    a, b = min(cuts, key=lambda c: abs(complist.px(c[0]) - complist.px(c[1])))
    for r in (a, b):
        assert set(r) <= complist.FONT | {UE} and complist.px(r) <= AV_WIDTH and len(r) < AV_LEN, ('step 2.5 row', r, complist.px(r))
    return a, b


OBJ4_PAGES = 2                 # (M2: 2 pages, the registry moved to swreg.REG_AT = 0x1800)
MAGIC = b'SWOS-ENG'
VERSION = 3                    # (swe.c SWE_VERSION; 2 = step W, the registry; 3 = W-modes M2, the pickers' worlds)
CODE_AT = 0x40
ARENA = 0x8000                 # (swe.c SWE_ARENA)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swe.c')
LABELS = {}


def pick_site(p):
    """obj1 offset of GoGetTeamsForPlay's `call SelectTeamsFinalMenu`: `mov byte [D0], 255; call ...; mov dword [A0], 0;
    call SetZeroFlag` (the one picker of FRIENDLY and the DIY tournament / cup / league editors)"""
    import re
    import sacups
    d1 = p.le.obj_bytes(1)
    rg = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    ms = [m.start() + 7 for m in re.finditer(rb'\xc6\x05' + pk(rg['D7'] - 28) + rb'\xff\xe8.{4}\xc7\x05' + pk(rg['A0'])
                                             + rb'\x00\x00\x00\x00\xe8', d1, re.S)]
    assert len(ms) == 1, ms
    return ms[0]


def m2_sites(p, site):
    """W-modes M2's game addresses and call sites: {extern: (obj, off)} and [(obj1 call offset, tramp)]"""
    import re
    import sacups
    import careerworld
    import countries
    d1 = p.le.obj_bytes(1)
    rg = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d0, a0 = rg['D7'] - 28, rg['A0']
    ext = {'SWE_D0': p.target(1, site - 5)}          # (`mov byte [D0], 255` before the picker call)
    tt = [m.start() for m in re.finditer(rb'\x66\xa1.{4}\x66[\x09\x0b]\xc0\x78', d1[site - 0x80:site], re.S)]
    assert len(tt) == 1, tt                         # GoGetTeamsForPlay: mov ax, [teamsType]; or ax, ax; js out
    ext['SWE_TTYPE'] = p.target(1, site - 0x80 + tt[0] + 2)
    # SaveDIYFile: call nullsub; mov [D1], offset g_numSelectedTeams; mov ax, [numDiyTeams]; mov [D0], ax ..
    # (SavePresetCompetitionFile has the same body: SaveDIYFile = the one SaveContest calls after `mov [D0], '.DIY'`)
    sv = [m.start() for m in re.finditer(rb'\xe8.{4}\xc7\x05' + pk(d0 + 4) + rb'.{4}\x66\xa1.{4}\x66\xa3' + pk(d0), d1, re.S)]
    diy = [m.start() for m in re.finditer(rb'\xc7\x05' + pk(d0) + rb'YID\.', d1)]
    sv = [x for x in sv if any(re.search(rb'\xff\x35' + pk(a0) + rb'\xe8', d1[q:q + 0x40]) and
                               p.call_target(1, q + re.search(rb'\xff\x35' + pk(a0) + rb'\xe8', d1[q:q + 0x40]).start() + 6)
                               == (1, x) for q in diy)]
    assert len(sv) == 1, sv
    sv = sv[0]
    ext['SWE_NUMSEL'] = p.target(1, sv + 11)
    ext['SWE_NDIY'] = p.target(1, sv + 17)
    cf = [m.start() for m in re.finditer(rb'\xc7\x05' + pk(a0 + 4) + rb'.{4}', d1[sv:sv + 0x60], re.S)]
    assert cf, 'SaveDIYFile: mov [A1], offset competitionFileBuffer'
    ext['SWE_CFB'] = p.target(1, sv + cf[0] + 6)
    # LoadDIYFile: push [A0]; call SaveOptions; pop [A0]; mov [A1], offset competitionFileBuffer; call LoadFile
    ld = [m.start() for m in re.finditer(rb'\xff\x35' + pk(a0) + rb'\xe8.{4}\x8f\x05' + pk(a0) + rb'\xc7\x05' + pk(a0 + 4)
                                         + rb'.{4}\xe8', d1, re.S) if p.target(1, m.start() + 23) == ext['SWE_CFB']]
    tg = []                                         # LoadOldCompetitionMenu: cmp [D1], '.DIY'; jz diy; .. diy: push
    for m in re.finditer(rb'\x81\x3d' + pk(d0 + 4) + rb'YID\.(\x74.|\x0f\x84.{4})', d1, re.S):   # [A0]; call LoadDIYFile
        j = m.start(1)                              # (LoadPresetFile has the same body: the one that branch calls)
        j = j + 2 + d1[j + 1] if d1[j] == 0x74 else j + 6 + struct.unpack_from('<i', d1, j + 2)[0]
        if d1[j:j + 2] == b'\xff\x35' and d1[j + 6] == 0xE8:
            tg.append(p.call_target(1, j + 6))
    ld = [x for x in ld if (1, x) in tg]
    assert len(ld) == 1, ld
    ld = ld[0]
    ext['SWE_A0'] = p.target(1, ld + 2)
    calls = []                                      # their callers: push [A0]; call ..; pop [A0]; jnz
    for fn, tr in ((sv, 'swe_diy_save_tramp'), (ld, 'swe_diy_load_tramp')):
        cs = [m.start() + 6 for m in re.finditer(rb'\xff\x35' + pk(a0) + rb'\xe8.{4}\x8f\x05' + pk(a0) + rb'\x0f\x85', d1, re.S)
              if p.call_target(1, m.start() + 6) == (1, fn)]
        assert len(cs) == 1, (tr, cs)
        calls.append((cs[0], tr))
    if 'gametype' in careerworld.SITES and 'w_ns_menu' in careerworld.LABELS:
        ext['SWE_GTYPE'] = careerworld.SITES['gametype']
        stfm = p.call_target(1, site)               # SelectTeamsFinalMenu's entry: an earlier patch's jmp (chained)
        assert p.get(*stfm, 1) == b'\xe9' and stfm[0] == 1, ('SelectTeamsFinalMenu entry', stfm, p.get(*stfm, 5))
        calls.append((stfm[1], 'swe_stfm_tramp'))
    import mainbtn                                  # (M3) the career's team choice: ChooseTeamsDialog's picker call
    if mainbtn.CHOOSE[0]:                           # after mb_d0 (a build with the main menu's world switch)
        ch = mainbtn.CHOOSE[0]
        assert p.get(1, ch['site'], 1) == b'\xe8', ('ChooseTeamsDialog picker call', hex(ch['site']))
        ext['MB_HDR'], ext['MB_STR'] = ch['HDR'], ch['STR']
        calls.append((ch['site'], 'swe_car_tramp'))
        nat = careerworld.SITES.get('nat')
        if nat:                                     # (M3: the coach nationality list after the team choice)
            ext.update({'CW_' + k: v for k, v in nat.items()})
    import historic                                 # SelectTeamsReinit's names call (historic's hist_names, chained)
    ext['SWE_CT'] = (2, countries.CT[0])
    if 'EF_VARS' in historic.LBL:                   # (hist_names: the first entry in EF_VARS; host tests: no build)
        ext['SWE_EFV'] = (1, historic.LBL['EF_VARS'])
    calls.append((historic._names_call(p)[0], 'swe_names_tramp'))
    if 'w_ns_menu' in careerworld.LABELS:           # careerworld w_ns_menu: mov eax, ecx; call w_ns_set
        wm = careerworld.LABELS['w_ns_menu']
        code = p.get(1, wm, 0x80)                   # (the mod's code: the patched bytes)
        ns = [wm + k + 2 for k in range(0x7d) if code[k:k + 3] == b'\x89\xc8\xe8'
              and p.call_target(1, wm + k + 2) == (1, careerworld.LABELS['w_ns_set'])]
        assert len(ns) == 1, ns
        calls.append((ns[0], 'swe_ns_tramp'))
    return ext, calls


def w0_proxies(p, at):
    """W-modes M2: the 1996-97 world's continent proxies (mkseason.W0_IDS) = copies of the game's continent records
    as the build left them (their cups' pointers dd .., -1 with their fixups, then the country ids .. FF), in obj4 after
    the registry. Returns the end."""
    import countries
    import mkseason
    comp = countries.COMP[0]
    for cid, c in mkseason.W0_IDS:
        sobj, src = p.target(2, comp + 4 * c)
        k = 0
        while struct.unpack('<i', p.get(sobj, src + k, 4))[0] != -1:
            try:
                p.add_ptr(4, at + k, *p.target(sobj, src + k))
            except AssertionError:
                p.put(4, at + k, p.get(sobj, src + k, 4))
            k += 4
        e = k + 4
        while p.get(sobj, src + e, 1) != b'\xff':
            e += 1
        assert at + e + 1 <= 0x1000 * OBJ4_PAGES, 'world 0 proxies: past obj4'
        p.put(4, at + k, p.get(sobj, src + k, e + 1 - k))
        p.add_ptr(2, comp + 4 * cid, 4, at)
        at = (at + e + 1 + 3) & ~3
    if mkseason.W0_IDS:
        print(f'exe: world 0 (the 1996-97 game) continent proxies {[x for x, _ in mkseason.W0_IDS]} in obj4 up to {at:#x}')
    return at


def patch(p):
    """links swe.c into obj4 (after obj3's vsize / base are final), the world registry (swreg.py) and the picker's
    trampoline; returns the code's end"""
    import cobj
    import careerworld
    import swreg
    assert len(p.le.objs) == 4 and p.le.obj(4).npages == OBJ4_PAGES, 'obj4 not added (patch.py)'
    room = 0x1000 * OBJ4_PAGES
    assert room == swreg.OBJ4_END
    site = pick_site(p)
    pick = p.call_target(1, site)                   # (chained: the picker call as earlier patches left it)
    ns = 'w_ns_set' in careerworld.LABELS and careerworld.NS.get('info')
    ext = {'SWE_REG': (4, swreg.REG_AT), 'SWE_PICK': pick}
    if ns:
        ext['w_ns_set'] = (1, careerworld.LABELS['w_ns_set'])
    m2, calls = m2_sites(p, site)                   # (W-modes M2: chained, as the picker call)
    ext.update(m2)
    chain = {'swe_diy_save_tramp': 'SWE_SAVEDIY', 'swe_diy_load_tramp': 'SWE_LOADDIY', 'swe_ns_tramp': 'SWE_NSSET',
             'swe_stfm_tramp': 'SWE_STFM', 'swe_names_tramp': 'SWE_NAMES', 'swe_car_tramp': 'SWE_CARPICK'}
    import historic
    if historic.CALLS:                              # step 2.5: the preset / season selectors' picker calls
        calls += [(historic.CALLS[0], 'swe_pre_tramp'), (historic.CALLS[1], 'swe_sea_tramp')]
        chain.update(swe_pre_tramp='SWE_PREPICK', swe_sea_tramp='SWE_SEAPICK')
    for cs, tr in calls:
        ext[chain[tr]] = p.call_target(1, cs)
    if not ns:
        calls = [c for c in calls if c[1] not in ('swe_ns_tramp', 'swe_stfm_tramp')]
    if 'W_FNAT' in careerworld.LABELS:              # step 2.5: the friendly / DIY nationals' world (w_tmap)
        ext['CW_FNAT'] = (1, careerworld.LABELS['W_FNAT'])
    flags = (('-DNS',) if ns else ()) + (('-DNAT',) if 'CW_PLNAT' in ext else ()) + (('-DFNAT',) if 'CW_FNAT' in ext else ())
    syms, end, bss = cobj.link(p, cobj.compile_c(SRC, flags), CODE_AT, (4, room), externs=ext, limit=swreg.REG_AT,
                               text_obj=4)
    arena = syms['SWE_ARENA_AT']
    if 'NAT_X' in syms:                             # M3: careerworld.NAT_ERA's pairs for the two lists
        import careerworld
        code = careerworld.nat_codes(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orig',
                                                  'ENGLISH.EXE'))
        era, today = (set(bytes(p.get(*ext[k], 256)).split(b'\xff')[0]) for k in ('CW_NATORD', 'CW_NATORD27'))
        to27, toera = careerworld.nat_maps(code, era, today)
        for nm, pairs, cap in (('NATMAP27', to27, 32), ('NATMAPERA', toera, 64)):
            assert 2 * len(pairs) + 1 <= cap, (nm, pairs)
            p.put(*syms[nm], bytes(x for pr in pairs for x in pr) + b'\xff')
        cobj.add_ptr(p, 60, *syms['NAT_X'], 4)
    import complist
    lk = LOCK_LINE[LANG[0]]
    assert set(lk) <= complist.FONT and complist.px(lk) <= 280 and len(lk) < 48, ('lock line', lk, complist.px(lk))
    p.put(*syms['LOCK_TXT'], lk.encode('latin-1') + b'\0')
    if 'AV_TXT' in syms:                            # step 2.5: the messages' rows, the exe's language
        lines = AV_LINES[LANG[0]]
        buf = b''.join((r.encode('latin-1') + b'\0').ljust(AV_LEN, b'\0') for k in AV_KINDS for r in av_rows(lines[k]))
        p.put(*syms['AV_TXT'], buf)
    assert arena[0] == 4 and bss >= ARENA
    p.put(4, 0, MAGIC + struct.pack('<I', VERSION))
    cobj.add_ptr(p, 12, 4, 0, 4)
    cobj.add_ptr(p, 16, *syms['swe_init'], 4)
    cobj.add_ptr(p, 20, *arena, 4)
    p.put(4, 24, struct.pack('<I', bss))
    cobj.add_ptr(p, 28, *syms['SWE_STATE'], 4)
    cobj.add_ptr(p, 32, 4, swreg.REG_AT, 4)
    for k, nm in enumerate(('reg_enter', 'reg_leave', 'SEL_MODE', 'REG_PREV', 'SWE_CWORLD', 'SEL_CW')):
        cobj.add_ptr(p, 36 + 4 * k, *syms[nm], 4)
    rend = swreg.patch(p, lambda off, tobj, toff: cobj.add_ptr(p, off, tobj, toff, 4))
    w0_proxies(p, rend)
    for cs, tr in [(site, 'swe_sel_tramp')] + calls:
        if p.rel_target(1, cs + 1):
            p.remove(1, cs + 1)
        p.add_rel(1, cs + 1, *syms[tr])
    p.set_vsize(4, room + bss, bss=bss)
    p.set_base_after(4)
    LABELS.clear()
    LABELS.update({k: v for k, v in syms.items()})
    print(f'exe: obj4 (engine) code obj4+{CODE_AT:#x}..{end:#x} of {swreg.REG_AT:#x}, arena {bss:#x} B; the picker '
          f'call obj1+{site:#x} -> swe_sel_tramp obj4+{syms["swe_sel_tramp"][1]:#x} -> {pick[0]}:{pick[1]:#x}; M2 calls '
          + ', '.join(f'{cs:#x} -> {tr}' for cs, tr in calls))
    return end
