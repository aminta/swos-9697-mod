"""4.1 gp_champ (gplay.c; Davide 06/11 B: Malta's 11th-placed club won the Final Four): a title play-off's winner
becomes first of the season end's top-9 list (GP_TOPW / GP_TOPR, which the qualifiers read for the champion place),
on the static image of HT_CHAMP_EXE (else c/HTMC: a release-recipe exe with HOSTTEST_SYMS=1). gp_champ is found from
its glue (`mov eax, gp_champ; call gp_c; movzx ecx, byte [GP_OUT]`).

- the winner 4th of the list: it moves first, the three above one place down, the rest unchanged (as before 4.1);
- the winner outside the top 9 and in the game's team cache (FindTeamInCache, as chained in the exe: here the
  currentTeam slot): first, with its 684-byte record from the cache, the others one place down, the 9th gone; the
  game's pseudo registers D0 / D1 / A0 as they were;
- the winner outside the top 9 and in no cache: the list unchanged (the table's 1st stays);
- the winner already first, or no title result: unchanged."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_CHAMP_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTMC', 'SWOS', 'ITALIAN.EXE')
REC = 684


def static_machine(exe):
    """obj1..obj4 of exe relocated (test_registry's bases), their BSS mapped, flat selectors; (uc, le, rd)"""
    import emu
    from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_CS
    tr.EXE, keep = exe, tr.EXE
    try:
        uc, le, sizes, _ = tr._machine()
    finally:
        tr.EXE = keep
    for b, k, n in ((tr.B1, 1, sizes[0]), (tr.B2, 2, sizes[1])):
        top, end = (n + 0xfff) & ~0xfff, (le.obj(k).vsize + 0xfff) & ~0xfff
        if end > top:
            uc.mem_map(b + top, end - top)
    gdt = bytearray(8 * 64)
    gdt[emu.CODE_SEL:emu.CODE_SEL + 8] = emu._desc(0, 0xFFFFF, 0x9A)
    gdt[emu.DATA_SEL:emu.DATA_SEL + 8] = emu._desc(0, 0xFFFFF, 0x92)
    uc.mem_map(0x6000000, 0x1000)
    uc.mem_write(0x6000000, bytes(gdt))
    uc.reg_write(UC_X86_REG_GDTR, (0, 0x6000000, len(gdt) - 1, 0))
    for r in (UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES):
        uc.reg_write(r, emu.DATA_SEL)
    uc.reg_write(UC_X86_REG_CS, emu.CODE_SEL)
    return uc, le, lambda a, n: bytes(uc.mem_read(a, n))


def test_champ():
    syms = EXE[:-4] + '.syms.json'
    if not os.path.exists(EXE) or not os.path.exists(syms):
        return False, f'{EXE} / its .syms.json missing (HT_CHAMP_EXE)'
    g = json.load(open(syms))['gplay']
    uc, le, rd = static_machine(EXE)
    base = {0: tr.B1, 1: tr.B1, 2: tr.B2}
    at = lambda k: base[g[k][0]] + g[k][1]
    gp_out, topw = at('GP_OUT'), at('GP_TOPW')
    img = rd(tr.B1, le.obj(1).vsize)
    k = img.find(b'\x0f\xb6\x0d' + struct.pack('<I', gp_out))
    while k >= 0 and not (img[k - 10] == 0xB8 and img[k - 5] == 0xE8):
        k = img.find(b'\x0f\xb6\x0d' + struct.pack('<I', gp_out), k + 1)
    if k < 0:
        return False, 'gp_champ glue not found'
    champ = struct.unpack_from('<I', img, k - 9)[0]
    # GP_TOPR: the record copy's source in the shift loop is past our reach by pattern; use cseg_927A2's own
    # (gplay._top9: mov [A1], offset records; mov [A3], offset team words)
    import re
    import sacups
    from le import LE
    o1 = LE(open(os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)   # (the original's
    rg = sacups.regs(o1)                                                                              # code: patterns)
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(rg['A0'] + 4) + rb'.{4}\xc7\x05' + pk(rg['A0'] + 12)
                                        + rb'.{4}\xc7\x05' + pk(rg['A0'] + 8), o1, re.S)]
    import lepatch
    lp = lepatch.LEPatch(EXE)                                        # (the targets through the exe's fixups)
    ab = lambda off: (lambda t: base[t[0]] + t[1])(lp.target(1, off))
    topr = ab(m[0] + 6)
    if ab(m[0] + 16) != topw:
        return False, f'top-9 words {ab(m[0] + 16):#x} != GP_TOPW {topw:#x}'
    # the original FindTeamInCache's currentTeam path, wherever the chain starts (careerworld may hook it first)
    ov = re.search(rb'\xe8(.{4})\x75\x01\xc3\xcc\xe8.{4}\xe8.{4}\xcc', o1, re.S)
    of = ov.start() + 5 + struct.unpack('<i', ov.group(1))[0]
    ctn = ab(of + 2)                                                 # mov ax, [currentTeamNumber]
    cm = re.search(rb'\xc7\x05(.{4})(.{4})', o1[of:of + 0x40], re.S)   # mov [A0], offset currentTeam
    a0, cur = ab(of + cm.start() + 2), ab(of + cm.start() + 6)
    d0 = rg['D7'] - 28 + tr.B2
    errs = []
    words = [0x1000 + 0x100 * i for i in range(9)]

    def setup(win, cache=None):
        uc.mem_write(gp_out, bytes([0, 1, 0, 0]))
        uc.mem_write(gp_out + 4 + 8 * 32, struct.pack('<BBHHHH', 5, 0, win, 0xFFFF, 0, 0))
        uc.mem_write(topw, struct.pack('<9H', *words))
        uc.mem_write(topr, b''.join(struct.pack('<H', w) + bytes([i + 1]) * (REC - 2) for i, w in enumerate(words)))
        uc.mem_write(ctn, struct.pack('<H', cache[0] if cache else 0xFFFE))
        if cache:
            uc.mem_write(cur, struct.pack('<H', cache[0]) + b'\xAB' * (REC - 2))
        uc.mem_write(d0, struct.pack('<III', 0x11111111, 0x22222222, 0x33333333)[:8])
        uc.mem_write(a0, struct.pack('<I', 0x44444444))

    def run():
        tr._call(uc, champ)
        w = list(struct.unpack('<9H', rd(topw, 18)))
        recs = [rd(topr + REC * i, REC) for i in range(9)]
        return w, recs

    rec = lambda i, w: struct.pack('<H', w) + bytes([i + 1]) * (REC - 2)
    setup(words[3])
    w, r = run()
    if w != [words[3]] + words[:3] + words[4:] or r[0] != rec(3, words[3]) or r[1] != rec(0, words[0]):
        errs.append(f'4th wins: {[hex(x) for x in w]}')
    out = 0x7B8C
    setup(out, (out,))
    w, r = run()
    if w != [out] + words[:8] or r[0] != struct.pack('<H', out) + b'\xAB' * (REC - 2) or r[8] != rec(7, words[7]):
        errs.append(f'outside, cached: {[hex(x) for x in w]} rec0 {r[0][:4].hex()}')
    regs = rd(d0, 8) + rd(a0, 4)
    if regs != struct.pack('<III', 0x11111111, 0x22222222, 0x44444444):
        errs.append(f'D0 / D1 / A0 not kept: {regs.hex()}')
    setup(out)
    w, r = run()
    if w != words or r[0] != rec(0, words[0]):
        errs.append(f'outside, not cached: {[hex(x) for x in w]}')
    setup(words[0])
    if run()[0] != words:
        errs.append('first already: changed')
    return not errs, '; '.join(errs) or (f'gp_champ {champ - tr.B1:#x}: 4th -> first; outside the top 9 + cached -> '
                                         'first with its record, the 9th out, D0/D1/A0 kept; not cached / already '
                                         'first -> unchanged')
