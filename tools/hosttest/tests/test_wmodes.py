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
    car = [t for t in nstr if rd(t, 2) == b'\x60\xe8']       # (M3: the career's team choice, swe_car_tramp)
    av = [t for t in nstr if t not in car and rd(t + 1, 3) != b'\x0f\xb6\xc0']   # (step 2.5: the preset / season
    nstr = [t for t in nstr if t not in car and t not in av]                     # selectors' tramps, -DAV builds)
    if len(nstr) != 1 or len(car) != 1 or len(av) not in (0, 2):
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
    def ctrec(i):                                 # countriesTable record: continent byte, NAME, ADJ (+ a proxy's NAME + year)
        b = rd(u32(B2 + ct + 4 * i), 64)
        return b[:1], b[1:].split(b'\0')[:3]
    bad = []
    for c, x in zip(top, w0):                     # 4.1 (6940ecd): a proxy's record is its own copy, 'NAME 96-97' after it
        (gc, (gn, ga, _)), (pc, (pn, pa, py)) = ctrec(c), ctrec(x)
        if rec(u32(slot(c))) != rec(u32(slot(x))) or (gc, gn, ga) != (pc, pn, pa) or py != pn + swe.W0_YEAR:
            bad.append((c, x))
    if bad:
        errs.append(f'proxies differing from the game continents {bad}')
    boot = tr._snap(uc, sizes)

    def run(setting, ttype, steps, career=False, tail=None):
        """steps = [(NUMSEL, the path's world)]: list w shown at the count so far (swe_sel_ns), the picks in it, then w
        shown again (ee6117b: swe_sel_ns credits the picks to the list shown last, SEL_LW); lists after each. tail = a
        last list shown at the count so far and NUMSEL picks in it with no list after them (swe_sel_post credits them).
        Returns (D0, [(hist, def)], SWE_CWORLD, mem ok)"""
        uc.mem_write(wdef, bytes((setting,)))
        w16(TTYPE, ttype)
        uc.mem_write(D0, b'\xff')
        w16(NUMSEL, 0)
        before = tr._snap(uc, sizes)
        tr._call(uc, pre, swreg.M_FRIENDLY)
        d0 = rd(D0, 1)[0]
        seen = [(ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt), u32(c254) == cwt)]
        k = 0
        for n, w in steps:
            w16(NUMSEL, k)
            tr._call(uc, ns, w)
            w16(NUMSEL, k := n)
            tr._call(uc, ns, w)
            seen.append((ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt), u32(selcw_p)))
        if tail:
            w16(NUMSEL, k)
            tr._call(uc, ns, tail[1])
            w16(NUMSEL, tail[0])
        tr._call(uc, post)
        cw = u32(cworld_p)
        ns_after = rd(wcur, 1)[0]
        w16(GTYPE, 4 if career else 0)            # (the next team picker: in a career the namespace is kept, else
        tr._call(uc, guard)                       # the base one is back)
        seen.append(('ns', ns_after, rd(wcur, 1)[0]))
        w16(GTYPE, 0)
        uc.mem_write(D0, b'\xff')
        last = tail[0] if tail else steps[-1][0] if steps else 0
        w16(NUMSEL, 0)
        after = tr._snap(uc, sizes)
        w16(NUMSEL, last)
        a1 = bytearray(after[0])                  # (careerworld XNAMEW keeps a tmwN world's digit after the base
        xw = before[0].find(b'data\\xtw0.000\0')  # namespace is back: harmless, test_registry's whitelist too)
        if xw >= 0 and a1[xw + 8] == ord('5'):
            a1[xw + 8] = ord('0')
        tr.unset_wtphys(a1, before[0])
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
    # ee6117b: the picks made in the list shown last, with no list change before the picker's end (INTER + MILAN in one
    # 2026-27 list): swe_sel_post gives the contest that list's world
    d0, seen, cw, same = run(0, 1, [], tail=(2, 5))
    if cw != 5 or seen[-1] != ('ns', 5, 4) or not same:
        errs.append(f'picks in the last list only: contest world {cw}, {seen[-1]}, memory restored {same}')
    # M3: the career's picker (swe_car_tramp -> swe_sel_pre(M_CAREER)): the same lists, whatever teamsType, no lock
    def run_car(setting, steps):
        uc.mem_write(wdef, bytes((setting,)))
        w16(TTYPE, 0)
        uc.mem_write(D0, b'\xff')
        w16(NUMSEL, 0)
        before = tr._snap(uc, sizes)
        tr._call(uc, pre, swreg.M_CAREER)
        d0 = rd(D0, 1)[0]
        seen = [(ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt))]
        for n, w in steps:
            w16(NUMSEL, n)
            tr._call(uc, ns, w)
            seen.append((ids(u32(slot(98))), ids(u32(slot(d0))) if d0 != 255 else ids(cwt), u32(selcw_p)))
        return d0, seen, before
    for setting, d0w, want in ((0, 205, [([200, 204], o205 + [98]), ([200, 204], o205 + [98], 0)]),
                               (1, 255, [([204], ctop + [205, 98]), ([204], ctop + [205, 98], 0)]),
                               (2, 204, [([200], o204 + [205, 98]), ([200], o204 + [205, 98], 0)])):
        d0, seen, before = run_car(setting, [(1, 5)])
        tr._call(uc, post)                        # (the lists back; the friendly's post: the namespace is the test's)
        uc.mem_write(D0, b'\xff')
        if d0 != d0w or seen != want:
            errs.append(f'career picker, setting {setting}: D0 {d0}, lists {seen}')
        if ids(cwt) != ctop + [98] or ids(u32(slot(98))) != o98:
            errs.append(f'career picker, setting {setting}: lists not restored {ids(cwt)} {ids(u32(slot(98)))}')
    tr._call(uc, guard)
    # M3: swe_car_tramp's own pre / post (its calls: pushal; call pre; popal; call the picker; ..; call post): only for
    # SELECT TEAM TO MANAGE (mainbtn mb_d0's check: the title pointer = its string); after it the namespace stays
    import mainbtn
    _, hdr_s, str_s = mainbtn.choose_sites(o)
    HDR, STR = ((B1 if x[0] == 1 else B2) + x[1] for x in (hdr_s, str_s))
    cc = [a for a in range(car[0], car[0] + 40) if rd(a, 1) == b'\xe8']
    cpre, cpost = _e8(rd, cc[0]), _e8(rd, cc[2])
    uc.mem_write(wdef, b'\x00')
    keep_hdr = rd(HDR, 4)
    for title, on in ((STR + 1, False), (STR, True)):
        uc.mem_write(HDR, struct.pack('<I', title))
        uc.mem_write(D0, b'\xcd')                # (mb_d0's: World 2026-27's list)
        tr._call(uc, cpre)
        got = (ids(u32(slot(98))), u32(selmode), rd(D0, 1)[0])
        want = ([200, 204], swreg.M_CAREER, 205) if on else (o98, 0xFFFFFFFF, 0xCD)
        uc.mem_write(wcur, b'\x05')              # (the path's namespace, as the picker left it)
        tr._call(uc, cpost)
        if got != want or ids(u32(slot(98))) != o98 or u32(selmode) != 0xFFFFFFFF or rd(wcur, 1)[0] != 5:
            errs.append(f'career tramp ({"SELECT TEAM TO MANAGE" if on else "another team choice"}): {got} want '
                        f'{want}; after: 98 {ids(u32(slot(98)))} SEL_MODE {u32(selmode):#x} WCUR {rd(wcur, 1)[0]}')
    uc.mem_write(HDR, keep_hdr)
    uc.mem_write(D0, b'\xff')
    w16(GTYPE, 0)
    tr._call(uc, guard)
    run(0, 1, [(1, 0)])                           # (the base namespace back for the cases below)
    # M3: the coach nationality after the team choice (swe_nat_fix, careerworld.NAT_ERA): every pair, both ways
    natx = u32(B4 + 60)
    if not natx:
        errs.append('obj4 header +60: no NAT_X (the coach nationality fix)')
    else:
        import careerworld
        fix, plnat, m27, mera, lera, l27 = struct.unpack('<6I', rd(natx, 24))
        code = careerworld.nat_codes(os.path.join(os.path.dirname(TOOLS), 'orig', 'ENGLISH.EXE'))
        name = {v: k for k, v in code.items()}
        lst = lambda a: list(rd(a, 256)[:rd(a, 256).index(0xFF)])
        era, today = lst(lera), lst(l27)
        keep = rd(plnat, 1)
        bad = []

        def got(c, t):
            uc.mem_write(plnat, bytes((c,)))
            tr._call(uc, fix, t)
            return rd(plnat, 1)[0]
        want = {}                                 # (from, to today?) -> expected, from the table itself
        for e, (succ, states) in careerworld.NAT_ERA.items():
            want[(code[e], 1)] = code[e] if code[e] in today else (code[succ] if succ else careerworld.NAT_ENG)
            for st in states:
                want.setdefault((code[st], 0), code[st] if code[st] in era else code[e])
        for (c, t), w in want.items():
            if got(c, t) != w:
                bad.append(f'{name[c]} -> {"today" if t else "era"}: {name.get(got(c, t))} (want {name[w]})')
        for t, l in ((1, today), (0, era)):       # (a nationality in the list is kept; FF = OTHER too)
            bad += [f'{name.get(c, c)} not kept ({"today" if t else "era"})' for c in l + [0xFF] if got(c, t) != c]
        for c, t, w in ((code['GDR'], 1, code['GER']), (code['FRG'], 1, code['GER']), (code['URS'], 1, code['RUS']),
                        (code['UKR'], 0, code['UKR']), (code['KAZ'], 0, code['URS']), (code['MNE'], 0, code['YUG']),
                        (code['BOS'], 0, code['YUG']), (code['YUG'], 1, code['YUG']),   # (NAT_TODAY: 37 = SERBIA today)
                        (code['USA'], 0, careerworld.NAT_ENG)):   # (hand-written: GDR -> GER ... USA -> ENG)
            if got(c, t) != w:
                bad.append(f'{name[c]}: {name.get(got(c, t))} want {name[w]}')
        uc.mem_write(plnat, keep)
        if bad:
            errs.append(f'coach nationality: {bad[:8]}')
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
        f'default 2026-27 / 1996-97 / 1984-85 lists, lock both ways, national / custom untouched, memory restored; career picker (M3): the same lists, no lock, only for SELECT TEAM TO MANAGE, namespace kept; '
        f'200 = 6 proxies = the game continents (own records, NAME 96-97); picks in the last list = its world; DIY: WM 5 / 4 round trip, 1996-97 alone = the game file '
        f'({game} B), other size -> 0; coach nationality: kept in the list, era <-> today pairs both ways, ENG last')
