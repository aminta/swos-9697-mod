"""Global team numbers up to LIMIT - 1 (World 5.0: about 1840 clubs, more than the game's 2000 numbers allow).

The game keeps a byte per global team number in someLeaguesTable (the club's league / division delta, inside the
.CAR fixed part) and its mirror leaguesTableCopy (not saved), 2000 bytes each; currentTeam follows the first one, so a
club numbered 2000+ wrote over live career state. In a build whose career worlds need more (bigtables.needed()):
- both tables move to LIMIT-byte copies in obj2 (retarget(): the 5 code references to someLeaguesTable and the 6
  `mov [Ax], offset leaguesTableCopy` move; UnpackMenu's 4 references stay: there `offset leaguesTableCopy` is only
  the end of the menu buffer g_currentMenu); the 4 loops over them (InitCareer's clear, cseg_8CC0A / cseg_8CC4E's
  copies, cseg_9487A's sum check: `mov word [D0], 1999`) run over LIMIT bytes;
- world 0 (4.0: euro97 / counts97 / seriec files above 2000) turns it on too (needed()); its bytes 2000..LIMIT-1 go
  into the .CAR's engine block 'EN' (engine.save_item 'BT_EXT', trailer.py), in a big world's save as well;
- the .CAR keeps its layout: the old 2000 bytes in the fixed part are written from the new table before a save
  (bt_save, in front of trailer's save_trailer) and read back after a load (bt_load, after w_loadcopy's copy of the
  fixed part from its stage, before it reads the world byte); bytes 2000..LIMIT-1 go to the 80-record area of the
  fixed part (tmdFileBuffer + ext_off(): under the BIGC mark, after the W1 block, the UEFA coefficients, uefaq's and
  dplay's states) when the career's world
  is big (careerworld.w_big), else they are cleared. Old saves load unchanged (their numbers are < 2000).
The mod's own code finds both tables through the retargeted fixups (careerworld.sites, worldpool, benchnum: p.target)
or through sacups.TABLES (moved()); globals 1730..1849 stay reserved (career marks, world byte).
"""
import re
import struct

LIMIT = 2400                    # global numbers 0..2399: what the 80-record area of a big world's save holds (W1 block,
                                # UEFA coefficients for LIMIT clubs, uefaq's state, dplay's state, these 400 bytes)


def ext_off():
    """tmdFileBuffer + ext_off(): table[2000..LIMIT) in a big world's save, right under careerworld's BIGC mark."""
    import careerworld
    return (careerworld.BIGC_AT - (LIMIT - 2000)) & ~3
ON = [False]
MOVED = {}                      # old obj2 offset -> new obj2 offset (someLeaguesTable, leaguesTableCopy)
SITES = {}


def world_maxg(n):
    """The highest global number + 1 of world n's team files (packs and national pack)."""
    import mkseason
    out = 0
    for pk in mkseason.packs() + mkseason.nationals():
        if pk.world == n:
            for key, (f, base) in pk.files.items():
                out = max(out, base + pk.count.get(key, 0))
    return out


def world0_bases():
    """Global bases of world 0's own team files (4.0: counts97, euro97, seriec with SERIEC=1, brstates96; none elsewhere)."""
    import importlib
    out = []
    for name in ('counts97', 'euro97', 'seriec', 'brstates96'):   # (4.0 packages 3, 5, 2, 6)
        try:
            m = importlib.import_module(name)
        except ImportError:                     # (a branch without the 4.0 modules: world-2025-26)
            continue
        if name == 'seriec':
            out += list(m.BASES_40.values()) if m.ON else []
        else:
            out += list(m.BASES.values())
    return out


def needed():
    """A career world, or world 0 (4.0's moved files), numbers clubs 2000+."""
    import mkseason
    return any(world_maxg(n) > 2000 for n in mkseason.worlds()) or any(b >= 2000 for b in world0_bases())


def moved(off):
    return MOVED.get(off, off)


def _find(p):
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0, d0 = r['A0'], r['D7'] - 28
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'(.{4})\x66\xc7\x05' + pk(d0) + rb'\xcf\x07', d1, re.S)]
    assert len(m) == 1, len(m)
    table = p.target(1, m[0].start(1))
    def tg(off):
        try:
            return p.target(1, off)
        except AssertionError:                  # (no fixup there: not an address)
            return None
    m = [x for x in re.finditer(rb'\xc7\x05' + pk(a0) + rb'.{4}\xc7\x05' + pk(a0 + 4) + rb'(.{4})', d1, re.S)
         if tg(x.start() + 6) == table]
    copy = {p.target(1, x.start(1)) for x in m}
    assert len(copy) == 1, copy
    return d1, a0, d0, table, copy.pop()


def retarget(p, area):
    """Early in patch_exe (before every user of the tables): new tables in obj2 (area), fixups and loops moved."""
    d1, a0, d0, table, copy = _find(p)
    new_t = (area.add(bytes(LIMIT + 4)) + 3) & ~3
    new_c = (area.add(bytes(LIMIT + 4)) + 3) & ~3
    fx = [f for f in p.le.fixups() if f[0] == 1 and f[3] == 2 and f[4] in (table[1], copy[1])]
    regs = [struct.pack('<I', a0 + 4 * k) for k in range(4)]        # A0..A3
    nt = nc = 0
    for f in fx:
        src = f[1]
        if f[4] == table[1]:
            p.retarget(1, src, 2, new_t)
            nt += 1
        elif d1[src - 6:src - 4] == b'\xc7\x05' and d1[src - 4:src] in regs:   # mov [Ax], offset leaguesTableCopy
            p.retarget(1, src, 2, new_c)
            nc += 1
    assert nt == 5 and nc == 6, (nt, nc)
    loops = [m.start() + 7 for m in re.finditer(rb'\x66\xc7\x05' + re.escape(struct.pack('<I', d0)) + rb'\xcf\x07', d1)]
    loops = [k for k in loops if any(abs(f[1] - k) < 24 for f in fx)]
    assert len(loops) == 4, [hex(k) for k in loops]
    MOVED.update({table[1]: new_t, copy[1]: new_c})
    import engine                               # world 0 (not a big world): numbers 2000+ in the .CAR engine block;
    engine.save_item('BT_EXT', LIMIT - 2000, clear=False)   # a big world keeps them in its 80-record area too, and
    engine.ITEM_AT['BT_EXT'] = (2, new_t + 2000)            # bt_load already set them (no 'EN': left as loaded)
    SITES.update(old=table, new=(2, new_t), newcopy=(2, new_c), loops=loops)   # (the loops' 1999 -> LIMIT - 1 in
                                                # hooks(): careerworld / worldpool / benchnum find the tables by them)
    print(f'exe: global numbers up to {LIMIT - 1}: someLeaguesTable obj2+{table[1]:#x} -> +{new_t:#x}, '
          f'leaguesTableCopy obj2+{copy[1]:#x} -> +{new_c:#x}, {len(loops)} loops of {LIMIT}')


ASM = '''
bt_save:                                ; in front of save_trailer: the fixed part's 2000 bytes from the new table,
    pushad                              ; numbers 2000+ into the 80-record area (a big world's career)
    mov esi, NEWT
    mov edi, OLDT
    mov ecx, 2000
    call bt_copy
    call W_BIG
    jz .r
    mov esi, NEWT + 2000
    mov edi, EXT
    mov ecx, LIMIT - 2000
    call bt_copy
.r:
    popad
    jmp [BT_SAVE_NEXT]

bt_load:                                ; replaces w_loadcopy's first `call w_copy` (the fixed part out of its stage):
    call W_COPY                         ; then the new table from the save, before anything reads the world byte
    pushad
    mov esi, OLDT
    mov edi, NEWT
    mov ecx, 2000
    call bt_copy
    call W_BIG
    jz .z
    mov esi, EXT
    mov edi, NEWT + 2000
    mov ecx, LIMIT - 2000
    call bt_copy
    jmp .r
.z:
    mov edi, NEWT + 2000                ; no numbers 2000+ in this career
    mov ecx, LIMIT - 2000
.c:
    mov byte [edi], 0
    inc edi
    dec ecx
    jnz .c
.r:
    popad
    ret

bt_copy:                                ; ecx bytes esi -> edi (no string instructions: ES may differ from DS)
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz bt_copy
    ret
align 4
BT_SAVE_NEXT: dd 0
'''


def hooks(p, at):
    """Late in patch_exe (after trailer, careerworld.patch_tails): bt_save in front of the save chain, bt_load in
    w_loadcopy. Returns the cave end."""
    import nasmcave
    import careerworld
    import trailer
    d1 = p.le.obj_bytes(1)
    import sacups
    r = sacups.regs(d1)
    A1 = re.escape(struct.pack('<I', r['A1']))
    D1 = re.escape(struct.pack('<I', r['D7'] - 24))
    career = trailer.INFO['CAREER'][1]
    m = [x for x in re.finditer(rb'\xc7\x05' + A1 + re.escape(struct.pack('<I', career)) + rb'\xa1' + A1 +
                                rb'\x29\x05' + D1 + rb'\xe8', d1, re.S)]
    assert len(m) == 1, len(m)
    save_call = m[0].end() - 1
    nxt = save_call + 5 + struct.unpack('<i', bytes(p.get(1, save_call + 1, 4)))[0]
    lc = p.target(1, trailer.INFO['loadcopy'])[1]              # w_loadcopy (careerworld.patch_tails)
    cur = bytes(p.get(1, lc, 0x40))
    k = cur.index(b'\xe8')                                     # its first call: w_copy (stage -> fixed part)
    w_copy = lc + k + 5 + struct.unpack_from('<i', cur, k + 1)[0]
    assert w_copy == careerworld.LABELS['w_copy'], (hex(w_copy), hex(careerworld.LABELS['w_copy']))
    tmd = careerworld.LABELS['sites']['tmd']
    sym = {'NEWT': SITES['new'], 'OLDT': SITES['old'], 'EXT': (2, tmd + ext_off()), 'LIMIT': (0, LIMIT),
           'W_BIG': (1, careerworld.LABELS['w_big']), 'W_COPY': (1, w_copy)}
    code, fix = nasmcave.assemble(ASM, at, sym)
    lab = nasmcave.labels(ASM, at, sym)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.add_ptr(1, lab['BT_SAVE_NEXT'], 1, nxt)
    for lp in SITES['loops']:
        assert bytes(p.get(1, lp, 2)) == b'\xcf\x07'
        p.put(1, lp, struct.pack('<H', LIMIT - 1))
    p.put(1, save_call + 1, struct.pack('<i', lab['bt_save'] - (save_call + 5)))
    p.put(1, lc + k + 1, struct.pack('<i', lab['bt_load'] - (lc + k + 5)))
    print(f'exe: global numbers: save obj1+{save_call:#x} -> bt_save -> obj1+{nxt:#x}; w_loadcopy obj1+{lc + k:#x} '
          f'-> bt_load; numbers 2000+ at tmdFileBuffer+{ext_off():#x} ({LIMIT - 2000} B)')
    return (at + len(code) + 3) & ~3
