"""W-modes M2: the friendly / DIY picker's worlds (swe.c swe_sel_pre / swe_sel_ns / swe_sel_post, the mixing-A lock) and
the DIY contest's world block 'WM' (swe_diy_save_tramp / swe_diy_load_tramp around the game's own SaveDIYFile /
LoadDIYFile, over a fake DOS). On the static image of HT_WM_EXE (else HT_REG_EXE, else c/HTW): a release-recipe exe
with worlds 0 / 4 / 5 and the 1996-97 world entry (WMENU + 0). No snapshot.

- default world 2026-27 (SETUP.DAT +105 = 0): the picker opens on world 5's list (D0 = 205) = its continents + STORICO
  (98); STORICO = 1996-97 (200) + Europe 1984-85 (204). A club picked under 2026-27 locks 1984-85 out of STORICO; one
  picked under 1984-85 locks 2026-27's continents out (its list = STORICO alone); NUMSEL 0 frees the lock;
- default 1996-97 (+105 = 1): the game's top list (D0 255, COMP254 = the careers' world table) and STORICO = 1984-85
  + 2026-27, no 200; default 1984-85 (2): D0 = 204, its countries + STORICO, STORICO = 200 + 205;
- national / custom teams: nothing changes; post: competitionsTable, D0 aside, obj1 / obj2 as before the picker;
- the 1996-97 entry: 200 lists 6 proxies whose records equal the game's continents 80..85 byte for byte (pointers too);
- DIY: a contest with a career world saves the game's file + 'WM' 1 world; one of 1996-97 clubs alone, the game's file
  only; loading reads the world back, and reads 0 from a file without the block, or of another size."""
import os
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'hosttest'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swe  # noqa: E402
import swreg  # noqa: E402
import test_registry as tr  # noqa: E402

B1, B2, B4 = tr.B1, tr.B2, tr.B4


def _exe():
    return os.environ.get('HT_WM_EXE') or tr.EXE


class _Dos:
    """int 21h: create / open / read / write / lseek / close on in-memory files (enough for WriteFile / LoadFile)"""
    def __init__(self, uc):
        self.files, self.h, self.uc = {}, {}, uc

    def name(self, a):
        b = bytes(self.uc.mem_read(a, 80))
        return b[:b.index(0)].decode('latin-1').upper()

    def __call__(self, uc, intno, _):
        from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                                       UC_X86_REG_EFLAGS)
        r = lambda x: uc.reg_read(x)
        eax, ebx, ecx, edx = (r(x) for x in (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX))
        ah, al, ok, out = (eax >> 8) & 0xFF, eax & 0xFF, True, {}
        if intno != 0x21:
            ok = False
        elif ah == 0x3C:
            n = self.name(edx)
            self.files[n] = bytearray()
            k = 5 + len(self.h)
            self.h[k] = [n, 0]
            out[UC_X86_REG_EAX] = k
        elif ah == 0x3D:
            n = self.name(edx)
            if n in self.files:
                k = 5 + len(self.h)
                self.h[k] = [n, 0]
                out[UC_X86_REG_EAX] = k
            else:
                ok = False
                out[UC_X86_REG_EAX] = 2
        elif ah in (0x3F, 0x40, 0x42, 0x3E):
            k = ebx & 0xFFFF
            if k not in self.h:
                ok = False
            else:
                n, pos = self.h[k]
                f = self.files[n]
                if ah == 0x3F:
                    b = bytes(f[pos:pos + ecx])
                    uc.mem_write(edx, b)
                    self.h[k][1] += len(b)
                    out[UC_X86_REG_EAX] = len(b)
                elif ah == 0x40:
                    b = bytes(uc.mem_read(edx, ecx))
                    f[pos:pos + len(b)] = b
                    self.h[k][1] += len(b)
                    out[UC_X86_REG_EAX] = len(b)
                elif ah == 0x42:
                    off = ((ecx & 0xFFFF) << 16) | (edx & 0xFFFF)
                    self.h[k][1] = (0, pos, len(f))[al] + off
                    out[UC_X86_REG_EAX] = self.h[k][1] & 0xFFFF
                    out[UC_X86_REG_EDX] = self.h[k][1] >> 16
                else:
                    del self.h[k]
        for x, v in out.items():
            uc.reg_write(x, v)
        fl = r(UC_X86_REG_EFLAGS)
        uc.reg_write(UC_X86_REG_EFLAGS, fl & ~1 if ok else fl | 1)


def _e8(rd, a):
    return a + 5 + struct.unpack('<i', rd(a + 1, 4))[0]


def test_wmodes():
    exe = _exe()
    if not os.path.exists(exe):
        return False, f'{exe} missing (HT_WM_EXE: a release-recipe exe of W-modes M2)'
    tr.EXE = exe
    uc, le, sizes, (ct, comp, tcn) = tr._machine()
    from unicorn import UC_HOOK_INTR
    from le import LE
    import lepatch
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    u32 = lambda a: struct.unpack('<I', rd(a, 4))[0]
    u16 = lambda a: struct.unpack('<H', rd(a, 2))[0]
    w16 = lambda a, v: uc.mem_write(a, struct.pack('<H', v))
    hdr = rd(B4, 0x40)
    if hdr[:8] != swe.MAGIC or struct.unpack_from('<I', hdr, 8)[0] != swe.VERSION:
        return False, f'obj4 header {hdr[:12]!r} (want version {swe.VERSION})'
    reg, _, _, selmode, _, cworld_p, selcw_p = struct.unpack_from('<7I', hdr, 32)
    wcur, c254, cwt, _, _, wdef = struct.unpack_from('<6I', rd(reg + 8, 24))
    errs = []
    o = lepatch.LEPatch(tr.ORIG)                    # (the game's addresses: the original exe of the same language)
    site = swe.pick_site(o)
    ext, calls = swe.m2_sites(o, site)
    va = lambda k: (B1 if ext[k][0] == 1 else B2) + ext[k][1]
    D0, NUMSEL, TTYPE, A0, NDIY, CFB = (va(k) for k in ('SWE_D0', 'SWE_NUMSEL', 'SWE_TTYPE', 'SWE_A0', 'SWE_NDIY',
                                                         'SWE_CFB'))
    seltr = _e8(rd, B1 + site)
    cs = [a for a in range(seltr, seltr + 48) if rd(a, 1) == b'\xe8']
    pre, post = _e8(rd, cs[0]), _e8(rd, cs[2])
    into4 = [a for a in range(B1, B1 + sizes[0] - 5) if rd(a, 1) == b'\xe8' and B4 <= _e8(rd, a) < B4 + swreg.REG_AT]
    nstr = [_e8(rd, a) for a in into4 if a - B1 not in (site,) + tuple(c for c, _ in calls)]
    if len(nstr) != 1 or rd(nstr[0] + 1, 3) != b'\x0f\xb6\xc0':
        return False, f'obj1 calls into obj4: {[hex(a - B1) for a in into4]} (the picker, DIY save / load, w_ns_menu)'
    ns = _e8(rd, nstr[0] + 4 + 1)
    import re
    import sacups                                 # (careerworld's gametype site: the career menu's `cmp [g_gameType], 4`)
    d1o = o.le.obj_bytes(1)
    gt = {o.target(1, x.start() + 14) for x in re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d.{4}\x04\x75',
                                                           d1o, re.S)}
    assert len(gt) == 1, gt
    GTYPE = (B1 if list(gt)[0][0] == 1 else B2) + list(gt)[0][1]
    entry = _e8(rd, cs[1])                        # (the picker's own: SelectTeamsFinalMenu, its entry a jmp -> obj4)
    stfm = _e8(rd, entry) if rd(entry, 1) == b'\xe9' else 0
    guard = _e8(rd, stfm + 2) if stfm and B4 <= stfm < B4 + swreg.REG_AT and rd(stfm + 2, 1) == b'\xe8' else 0
    if not guard:
        return False, f'SelectTeamsFinalMenu\'s entry does not reach obj4\'s guard ({stfm:#x})'
    slot = lambda i: B2 + comp + 4 * i

    def ids(lp):                                  # a list's menu ids (after its dd entries, -1)
        k = 0
        while u32(lp + k) != 0xFFFFFFFF:
            k += 4
        b = rd(lp + k + 4, 100)
        return list(b[:b.index(0xFF)])

    o205, o204, o98 = ids(u32(slot(205))), ids(u32(slot(204))), ids(u32(slot(98)))
    if o98 != [204, 205]:
        return False, f'the careers list 98 = {o98}'
    # the 1996-97 world entry: proxies = the game's continents
    w0 = ids(u32(slot(200)))
    top = ids(u32(c254))
    if len(w0) != 6 or len(top) != 6:
        errs.append(f'200 lists {w0}, the top list {top}')

    def rec(lp):
        k, out = 0, []
        while u32(lp + k) != 0xFFFFFFFF:
            out.append(u32(lp + k))
            k += 4
        return out, ids(lp)
    bad = [(c, x) for c, x in zip(top, w0) if rec(u32(slot(c))) != rec(u32(slot(x))) or
           u32(B2 + ct + 4 * c) != u32(B2 + ct + 4 * x)]
    if bad:
        errs.append(f'proxies differing from the game continents {bad}')
    boot = tr._snap(uc, sizes)

    def run(setting, ttype, steps, career=False):
        """steps = [(NUMSEL, the path's world)]: lists after each; returns (D0, [(hist, def)], SWE_CWORLD, mem ok)"""
        uc.mem_write(wdef, bytes((setting,)))
        w16(TTYPE, ttype)
        uc.mem_write(D0, b'\xff')
        w16(NUMSEL, 0)
        before = tr._snap(uc, sizes)
        tr._call(uc, pre, swreg.M_FRIENDLY)
        d0 = rd(D0, 1)[0]
        seen = [(ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt), u32(c254) == cwt)]
        for n, w in steps:
            w16(NUMSEL, n)
            tr._call(uc, ns, w)
            seen.append((ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt), u32(selcw_p)))
        tr._call(uc, post)
        cw = u32(cworld_p)
        ns_after = rd(wcur, 1)[0]
        w16(GTYPE, 4 if career else 0)            # (the next team picker: in a career the namespace is kept, else
        tr._call(uc, guard)                       # the base one is back)
        seen.append(('ns', ns_after, rd(wcur, 1)[0]))
        w16(GTYPE, 0)
        uc.mem_write(D0, b'\xff')
        last = steps[-1][0] if steps else 0
        w16(NUMSEL, 0)
        after = tr._snap(uc, sizes)
        w16(NUMSEL, last)
        a1 = bytearray(after[0])                  # (careerworld XNAMEW keeps a tmwN world's digit after the base
        xw = before[0].find(b'data\\xtw0.000\0')  # namespace is back: harmless, test_registry's whitelist too)
        if xw >= 0 and a1[xw + 8] == ord('5'):
            a1[xw + 8] = ord('0')
        same = (bytes(a1), after[1]) == before and u32(selmode) == 0xFFFFFFFF
        return d0, seen, cw, same

    d0, seen, cw, same = run(0, 1, [(1, 5), (2, 0), (0, 0), (1, 4), (2, 5)])
    want = [([200, 204], o205 + [98], True), ([200], o205 + [98], 5), ([200], o205 + [98], 5),
            ([200, 204], o205 + [98], 0), ([200, 204], [98], 4), ([200, 204], [98], 4), ('ns', 4, 4)]
    if d0 != 205 or seen != want or cw != 4 or not same:
        errs.append(f'default 2026-27: D0 {d0}, lists {seen}, contest world {cw}, memory restored {same}')
    # Q1 (b): MONDO 2026-27 never in STORICO; under another default its own entry next to the box (the 1996-97
    # default: the top list = CAREER_WORLD, its spare byte), the box left out when the lock empties it
    ctop = top                                    # (the game's continents, as CAREER_WORLD lists them)
    d0, seen, cw, same = run(1, 1, [(1, 0), (2, 5), (0, 0), (1, 4)])
    want = [([204], ctop + [205, 98], True), ([204], ctop + [205, 98], 0), ([], ctop + [205], 5),
            ([204], ctop + [205, 98], 0), ([204], ctop + [98], 4), ('ns', 4, 4)]
    if d0 != 255 or seen != want or cw != 4 or not same:
        errs.append(f'default 1996-97: D0 {d0}, lists {seen}, contest world {cw}, memory restored {same}')
    if ids(cwt) != ctop + [98] or rd(cwt + 8 + len(ctop), 3) != b'\x62\xff\xff':
        errs.append(f'CAREER_WORLD after the picker {ids(cwt)} {rd(cwt + 8 + len(ctop), 3).hex()}')
    d0, seen, cw, same = run(2, 1, [(1, 5)])
    if d0 != 204 or seen != [([200], o204 + [205, 98], True), ([200], [205, 98], 5), ('ns', 5, 4)] or \
            cw != 5 or not same:   # (a 2026-27 club: its namespace kept after the picker, the base one at the next)
        errs.append(f'default 1984-85: D0 {d0}, lists {seen}, contest world {cw}, memory restored {same}')
    d0, seen, cw, same = run(2, 1, [(1, 4)])
    if seen[:2] != [([200], o204 + [205, 98], True), ([200], o204 + [98], 4)] or cw != 4 or not same:
        errs.append(f'default 1984-85, a 1984-85 club: lists {seen}, contest world {cw}, memory restored {same}')
    d0, seen, cw, same = run(2, 1, [(1, 5)], career=True)
    if seen[-1] != ('ns', 5, 5):
        errs.append(f'a career\'s picker after a 2026-27 contest: namespace {seen[-1]} (kept 5)')
    run(0, 1, [(1, 0)])                           # (a 1996-97 contest: the base namespace again)
    if rd(wcur, 1)[0] != 4:
        errs.append(f'a 1996-97 contest left namespace {rd(wcur, 1)[0]}')
    for tt in (0, 2, 3):
        d0, seen, cw, same = run(0, tt, [])
        if d0 != 255 or seen[0][0] != o98 or seen[0][2] or seen[-1] != ('ns', 4, 4) or not same:
            errs.append(f'teams type {tt}: D0 {d0}, 98 {seen[0][0]}, COMP254 swapped {seen[0][2]}, restored {same}')

    # DIY: the game's own SaveDIYFile / LoadDIYFile through the tramps, a fake DOS
    dos = _Dos(uc)
    hk = uc.hook_add(UC_HOOK_INTR, dos)
    sv_tr = _e8(rd, B1 + [c for c, t in calls if t == 'swe_diy_save_tramp'][0])
    ld_tr = _e8(rd, B1 + [c for c, t in calls if t == 'swe_diy_load_tramp'][0])
    name = B2 + 0x100                               # (a scratch name in obj2's first page)
    keep = rd(name, 16)
    uc.mem_write(name, b'TEST.DIY\0')
    n = 3
    w16(NDIY, n)
    game = NUMSEL + 2 + 684 * n - CFB
    pattern = bytes((i * 7 + 3) & 0xFF for i in range(game))
    res = {}
    for w in (5, 4, 0):
        uc.mem_write(CFB, pattern)
        w16(NDIY, n)
        uc.mem_write(cworld_p, struct.pack('<I', w))
        uc.mem_write(A0, struct.pack('<I', name))
        tr._call(uc, sv_tr)
        f = bytes(dos.files.get('TEST.DIY', b''))
        uc.mem_write(CFB, bytes(game + 4))
        uc.mem_write(cworld_p, struct.pack('<I', 77))
        uc.mem_write(A0, struct.pack('<I', name))
        tr._call(uc, ld_tr)
        exp = bytearray(pattern)                    # (numDiyTeams lives inside the file's part: 3)
        exp[NDIY - CFB:NDIY - CFB + 2] = struct.pack('<H', n)
        back = rd(CFB, game)                        # (LoadDIYFile's own after-load code writes a dword of its state)
        moved = [i for i in range(game) if back[i] != exp[i]]
        res[w] = (len(f) - game, f[game:], f[:game] == exp, u32(cworld_p), len(moved) <= 4)
    dos.files['TEST.DIY'] += b'\0'                    # (another size: a block that does not count)
    uc.mem_write(A0, struct.pack('<I', name))
    tr._call(uc, ld_tr)
    odd = u32(cworld_p)
    uc.hook_del(hk)
    uc.mem_write(name, keep)
    want = {5: (4, b'WM\x01\x05', True, 5, True), 4: (4, b'WM\x01\x04', True, 4, True), 0: (0, b'', True, 0, True)}
    if res != want or odd != 0:
        errs.append(f'DIY save / load {res} (want {want}), a file of another size -> {odd}')
    return not errs, '; '.join(errs) or (
        f'default 2026-27 / 1996-97 / 1984-85 lists, lock both ways, national / custom untouched, memory restored; '
        f'200 = 6 proxies = the game continents; DIY: WM 5 / 4 round trip, 1996-97 alone = the game file '
        f'({game} B), other size -> 0')
