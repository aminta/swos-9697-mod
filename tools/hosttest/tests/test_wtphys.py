"""careerworld's team-file cache test (4.0.6 WTPHYS, audit-stale-406 #5): the game skips LoadTeamFile when
lastLoadedExtNumber is the file asked for; w_tcache turns a cached national 80..85 into a miss (0FEh) unless the
physical file in teamFileBuffer (WTPHYS, written by w_tfile) is the one this world wants (w_tmap). On the static image
of HT_WT_EXE (else c/HTOMM: a release-recipe exe built with HOSTTEST_SYMS=1, whose ITALIAN.syms.json names the
careerworld labels). No snapshot.

- outside a career (GAMETYPE != 4) w_tmap follows W_FNAT (the friendly / DIY nationals' world); in a career, the career
  slot's world byte;
- w_tfile(80) under a world with its own nationals: D0 and WTPHYS = that world's file; w_tcache(80) in the same world
  = a hit (LASTEXT back), under 1996-97 = a miss (0FEh), and the reverse after w_tfile(80) under 1996-97;
- a namespace change (reg_enter / reg_leave -> w_ns_set) leaves WTPHYS 0FFh: the next 80..85 always reloads;
- a club file (not 80..85) is never touched: w_tcache returns LASTEXT whatever WTPHYS holds."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402

HOME = os.path.expanduser('~')
GDT_AT = 0x6000000
EXE = os.environ.get('HT_WT_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTOMM', 'SWOS', 'ITALIAN.EXE')


def _find(rd, start, n, pat):
    """the absolute address after the first `pat` in [start, start + n) (an instruction's disp32)"""
    code = rd(start, n)
    i = code.find(pat)
    assert i >= 0, f'{pat.hex()} not in {start:#x}+{n}'
    return struct.unpack_from('<I', code, i + len(pat))[0]


def _reg_call(uc, fn, eax=0):
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    sp = tr.STACK - 0x100
    uc.mem_write(sp, struct.pack('<I', tr.RET))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.reg_write(UC_X86_REG_EAX, eax)
    h = uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=tr.RET, end=tr.RET)
    uc.emu_start(fn, tr.RET, count=200_000)
    uc.hook_del(h)
    return uc.reg_read(UC_X86_REG_EAX)


def test_wtphys():
    syms = EXE[:-4] + '.syms.json'
    if not os.path.exists(EXE) or not os.path.exists(syms):
        return False, f'{EXE} / its .syms.json missing (HT_WT_EXE: a release-recipe exe built with HOSTTEST_SYMS=1)'
    cw = json.load(open(syms))['careerworld']
    if any(cw[k][0] != 0 for k in ('w_tmap', 'w_tfile', 'w_tcache', 'WTPHYS')):
        return False, 'careerworld labels not in obj1'
    tr.EXE, keep = EXE, tr.EXE
    try:
        uc, le, sizes, _ = tr._machine()
    finally:
        tr.EXE = keep
    for b, k, n in ((tr.B1, 1, sizes[0]), (tr.B2, 2, sizes[1])):    # (the objects' BSS: w_guest clears a guest
        top, end = (n + 0xfff) & ~0xfff, (le.obj(k).vsize + 0xfff) & ~0xfff   # file's clubs in someLeaguesTable)
        if end > top:
            uc.mem_map(b + top, end - top)
    import emu                                                   # (w_guest's push ds / pop es: flat selectors)
    from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_CS
    gdt = bytearray(8 * 64)
    gdt[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
    gdt[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
    uc.mem_map(GDT_AT, 0x1000)
    uc.mem_write(GDT_AT, bytes(gdt))
    uc.reg_write(UC_X86_REG_GDTR, (0, GDT_AT, len(gdt) - 1, 0))
    for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
        uc.reg_write(r, emu.DATA_SEL)
    uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    a = {k: tr.B1 + cw[k][1] for k in ('w_tmap', 'w_tfile', 'w_tcache', 'WTPHYS')}
    wfnat = a['WTPHYS'] + 1                                     # (W_FNAT: the byte after WTPHYS)
    gametype = _find(rd, a['w_tmap'], 64, b'\x66\x83\x3d')      # cmp word [GAMETYPE], 4
    if _find(rd, a['w_tmap'], 64, b'\x0f\xb6\x1d') != wfnat:     # movzx ebx, byte [W_FNAT]
        return False, 'w_tmap: W_FNAT is not the byte after WTPHYS'
    at = rd(a['w_tmap'], 64).find(b'\x66\x83\x3d')
    slotw = _find(rd, a['w_tmap'] + at, 64, b'\x0f\xb6\x1d')    # movzx ebx, byte [SLT + WORLD_BYTE] (after the cmp)
    wnat = _find(rd, a['w_tmap'], 64, b'\x0f\xb6\x9b')          # movzx ebx, byte [WNAT + ebx]
    d0 = _find(rd, a['w_tfile'], 16, b'\x81\x25')               # and dword [D0R], 0FFh
    lastext = _find(rd, a['w_tcache'], 8, b'\xa0')              # mov al, [LASTEXT]
    nat = {w: rd(wnat + w, 1)[0] for w in range(8)}
    own = [w for w in nat if nat[w]]
    if nat[0] or not own:
        return False, f'WNAT {nat} (the base world maps 80..85 to themselves; a world with its own nationals needed)'
    w = own[0]
    phys = nat[w]                                              # (lea eax, [eax + ebx - 80]: the file for 80)
    wb = lambda ad, v: uc.mem_write(ad, bytes([v]))
    u8 = lambda ad: rd(ad, 1)[0]
    errs = []

    def tfile(n):
        uc.mem_write(d0, struct.pack('<I', n | 0xAB00))         # (the high bytes: and 0FFh clears them)
        _reg_call(uc, a['w_tfile'])
        return struct.unpack('<I', rd(d0, 4))[0], u8(a['WTPHYS'])

    def tcache(n, last):
        uc.mem_write(d0, struct.pack('<I', n))
        wb(lastext, last)
        return _reg_call(uc, a['w_tcache'], 0x12345600) & 0xFF

    uc.mem_write(gametype, struct.pack('<H', 1))                # (a friendly: W_FNAT decides)
    wb(wfnat, w)
    got = tfile(80)
    if got != (phys, phys):
        errs.append(f'w_tfile(80) world {w}: D0 / WTPHYS {got}, want {phys}')
    if tcache(80, 80) != 80:
        errs.append(f'world {w} after its own 80: a miss')
    if tcache(83, 80) != 0xFE:
        errs.append('80 loaded, 83 asked: not a miss')
    wb(wfnat, 0)
    if tcache(80, 80) != 0xFE:
        errs.append(f'world {w}\'s 80 cached, 1996-97 asks 80: a hit (the stale cross-world file)')
    if tfile(80) != (80, 80) or tcache(80, 80) != 80:
        errs.append('1996-97 after its own 80: D0 / WTPHYS or a miss')
    wb(wfnat, w)
    if tcache(80, 80) != 0xFE:
        errs.append(f'1996-97\'s 80 cached, world {w} asks 80: a hit')
    if tcache(12, 12) != 12 or tcache(200, 200) != 200:
        errs.append('a club file was not a plain cache test')

    uc.mem_write(gametype, struct.pack('<H', 4))                # a career: the slot's world byte, not W_FNAT
    wb(wfnat, 0)
    keep_slot = u8(slotw)
    wb(slotw, w)
    if tfile(81) != (phys + 1, phys + 1) or tcache(81, 81) != 81:
        errs.append(f'career world {w}: w_tfile(81) / cache')
    wb(slotw, 0)
    if tcache(81, 81) != 0xFE:
        errs.append('career slot world changed: a hit')
    wb(slotw, keep_slot)

    hdr = rd(tr.B4, 0x40)                                       # a namespace change: reg_enter(5) / reg_leave
    _, enter, leave, _, _ = struct.unpack_from('<5I', hdr, 32)
    uc.mem_write(gametype, struct.pack('<H', 1))
    wb(wfnat, 0)
    tfile(80)
    seen = []
    for f, args in ((enter, (5,)), (leave, ())):
        wb(a['WTPHYS'], 80)
        tr._call(uc, f, *args)
        seen.append(u8(a['WTPHYS']))
    if seen != [0xFF, 0xFF] or tcache(80, 80) != 0xFE:
        errs.append(f'after reg_enter / reg_leave WTPHYS {seen}, w_tcache(80) {tcache(80, 80):#x}')
    return not errs, '; '.join(errs) or (f'world {w} nationals = files {phys}..{phys + 5}: w_tfile / w_tcache hit '
                                         f'only on the same world (friendly W_FNAT and career slot), a namespace '
                                         f'change = 0FFh = reload, club files untouched')
