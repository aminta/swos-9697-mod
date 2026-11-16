"""4.2 team cache bound, step 1a (tools/tcache.py; MC 16/11, design internal/handoff/teamcache-fable-design.md), on the
static image of HT_TC_EXE (else c/HTTC1: a release-recipe exe built with HOSTTEST_SYMS=1). No snapshot: the routines
are called with NUMSEL / selTeamsPtr / SELBASEV poked; tc_full is seen at its first DOS call (int 10h AX=2), the
message at int 21h AH=9.

- the 6 inserts: 5 `call tc_chk_n` (+4 nops) and 1 `call tc_chk_add` (+3 nops) in obj1, nothing else calls them;
- tc_chk_n: the game's cache 99 -> D0 = 155h, the high-water mark 100; 100 -> the stop with "TEAM CACHE FULL (100)";
  the big cache (selTeamsPtr = NEWSEL) 159 passes, 160 stops; flags and eax kept;
- tc_chk_add: 50 -> 51, the HWM not lowered;
- tc_clamp: the cache in use's cap (100 passes, 101 stops), flags kept; tc_clamp_sel by SELBASEV: a big career's 124
  restored while selTeamsPtr is the game's cache (main menu -> FRIENDLY) passes, the same count on the game's cache stops;
- tc_room: budget - NUMSEL (the game's cache: trailer nmax; the big one: TC_CAP), never below 0;
- tc_reserve: the list's clubs not cached, each once, 0xFFFF skipped, vs tc_room; the pseudo registers and
  ebx / esi / edi / ebp kept."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixroot  # noqa: E402
import test_registry as tr  # noqa: E402
import test_swc1 as ts  # noqa: E402

EXE = os.environ.get('HT_TC_EXE') or fixroot.fx('HTTC1', 'SWOS', 'ITALIAN.EXE')
BUF = 0x6200000                                  # (a stand-in cache: 170 records)


class Stop(Exception):
    pass


class T:
    def __init__(self):
        from unicorn import UC_HOOK_INTR
        self.uc, self.le, self.rd = ts.static_machine(EXE)
        self.uc.mem_map(BUF, 0x20000 * 2)
        sy = json.load(open(EXE[:-4] + '.syms.json'))['tcache']
        self.lab = {k: v[1] for k, v in sy.items() if not k.startswith(('sym.', 'caps.'))}
        self.sym = {k[4:]: self.lin(v) for k, v in sy.items() if k.startswith('sym.')}
        self.caps = {k[5:]: v[1] for k, v in sy.items() if k.startswith('caps.')}
        self.big = self.caps['tc_cap'] > 0
        self.ints = []
        self.uc.hook_add(UC_HOOK_INTR, self._intr)

    def lin(self, v):
        o, off = v
        return {0: off, 1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}[o] + (off if o else 0)

    def at(self, name):
        return tr.B4 + self.lab[name]

    def _intr(self, uc, intno, data):
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX
        eax, edx = uc.reg_read(UC_X86_REG_EAX), uc.reg_read(UC_X86_REG_EDX)
        msg = None
        if intno == 0x21 and eax >> 8 & 0xff == 9:
            b = bytes(uc.mem_read(edx, 80))
            msg = b[:b.index(b'$')].decode('latin-1').strip()
        self.ints.append((intno, eax & 0xffff, msg))
        if msg is not None:
            uc.emu_stop()

    def w16(self, a, v):
        self.uc.mem_write(a, struct.pack('<H', v))

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack('<I', v))

    def u16(self, a):
        return struct.unpack('<H', self.rd(a, 2))[0]

    def u32(self, a):
        return struct.unpack('<I', self.rd(a, 4))[0]

    def setup(self, n, big=False, base=None):
        self.w16(self.sym['NUMSEL'], n)
        cache = self.sym['NEWSEL'] if big else self.sym['NUMSEL'] + 2
        self.w32(self.sym['SELPTR'], cache)
        self.w32(self.sym['SELBASEV'], cache if base is None else base)
        self.ints = []

    def call(self, name, *args, regs=None):
        """(eax, eflags, stopped message or None)"""
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EFLAGS
        sp = tr.STACK - 0x100
        self.uc.mem_write(sp, struct.pack('<I', tr.RET) + b''.join(struct.pack('<I', a) for a in args))
        self.uc.reg_write(UC_X86_REG_ESP, sp)
        for r, v in (regs or {}).items():
            self.uc.reg_write(r, v)
        h = self.uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=tr.RET, end=tr.RET)
        self.uc.emu_start(self.at(name), tr.RET, count=5_000_000)
        self.uc.hook_del(h)
        msg = next((m for _, _, m in self.ints if m), None)
        return self.uc.reg_read(UC_X86_REG_EAX), self.uc.reg_read(UC_X86_REG_EFLAGS), msg


def test_tcache():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (release recipe + HOSTTEST_SYMS=1) missing'
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EFLAGS, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI,
                                   UC_X86_REG_EBP)
    t = T()
    bad, notes = [], []
    # the hooks: calls into tc_chk_n / tc_chk_add from obj1
    o1 = t.rd(tr.B1, t.le.obj(1).vsize)
    calls = {}
    for i in range(len(o1) - 5):
        if o1[i] == 0xE8:
            tg = (tr.B1 + i + 5 + struct.unpack_from('<i', o1, i + 1)[0]) & 0xffffffff
            for k in ('tc_chk_n', 'tc_chk_add'):
                if tg == t.at(k):
                    calls.setdefault(k, []).append(i)
    if (len(calls.get('tc_chk_n', [])), len(calls.get('tc_chk_add', []))) != (5, 1):
        bad.append(f'hooks: {({k: len(v) for k, v in calls.items()})} (want 5 tc_chk_n, 1 tc_chk_add)')
    for k, n in (('tc_chk_n', 4), ('tc_chk_add', 3)):
        for i in calls.get(k, []):
            if o1[i + 5:i + 5 + n] != b'\x90' * n:
                bad.append(f'{k} at obj1+{i:#x}: not followed by {n} nops')
    d0, numsel, hwm = t.sym['D0'], t.sym['NUMSEL'], t.at('TC_HWM')
    CF = 1
    # tc_chk_n
    t.w16(hwm, 0)
    t.setup(99)
    t.w16(d0, 0)
    eax, fl, msg = t.call('tc_chk_n', regs={UC_X86_REG_EAX: 0x12345678, UC_X86_REG_EFLAGS: 0x202 | CF})
    if msg or t.u16(d0) != 0x155 or t.u16(hwm) != 100 or eax != 0x12345678 or not fl & CF:
        bad.append(f'tc_chk_n 99: msg {msg} D0 {t.u16(d0):#x} HWM {t.u16(hwm)} eax {eax:#x} CF {fl & CF}')
    t.setup(100)
    _, _, msg = t.call('tc_chk_n')
    if msg != 'TEAM CACHE FULL (100) - PLEASE REPORT' or t.ints[0][:2] != (0x10, 2):
        bad.append(f'tc_chk_n 100: {t.ints}')
    else:
        notes.append(msg)
    if t.big:
        t.setup(159, big=True)
        _, _, msg = t.call('tc_chk_n')
        if msg or t.u16(hwm) != 160:
            bad.append(f'big tc_chk_n 159: {msg} HWM {t.u16(hwm)}')
        t.setup(160, big=True)
        _, _, msg = t.call('tc_chk_n')
        if msg != 'TEAM CACHE FULL (160) - PLEASE REPORT':
            bad.append(f'big tc_chk_n 160: {t.ints}')
    # tc_chk_add
    t.setup(50)
    _, _, msg = t.call('tc_chk_add')
    if msg or t.u16(numsel) != 51 or t.u16(hwm) != (160 if t.big else 100):
        bad.append(f'tc_chk_add 50: {msg} NUMSEL {t.u16(numsel)} HWM {t.u16(hwm)}')
    # tc_clamp / tc_clamp_sel
    for n, want in ((100, None), (101, 'TEAM CACHE FULL (101) - PLEASE REPORT')):
        t.setup(n)
        eax, fl, msg = t.call('tc_clamp', regs={UC_X86_REG_EAX: 7, UC_X86_REG_EFLAGS: 0x202 | CF})
        if msg != want or (want is None and (eax != 7 or not fl & CF)):
            bad.append(f'tc_clamp {n}: {msg} eax {eax} CF {fl & CF}')
    if t.big:
        t.setup(124, base=t.sym['NEWSEL'])               # (selTeamsPtr = the game's cache, the career's at NEWSEL)
        _, _, msg = t.call('tc_clamp_sel')
        if msg:
            bad.append(f'tc_clamp_sel 124 (big career, main menu): {msg}')
        t.setup(161, base=t.sym['NEWSEL'])
        _, _, msg = t.call('tc_clamp_sel')
        if msg != 'TEAM CACHE FULL (161) - PLEASE REPORT':
            bad.append(f'tc_clamp_sel 161 big: {t.ints}')
    t.setup(124)
    _, _, msg = t.call('tc_clamp_sel')
    if msg != 'TEAM CACHE FULL (124) - PLEASE REPORT':
        bad.append(f'tc_clamp_sel 124 game cache: {t.ints}')
    # tc_room
    nm, tcap = t.caps['nmax'], t.caps['tc_cap']
    cases = [(0, False, nm), (nm - 6, False, 6), (nm, False, 0), (100, False, 0)]
    if t.big:
        cases += [(150, True, tcap - 150), (tcap, True, 0), (160, True, 0)]
    for n, big, want in cases:
        t.setup(n, big=big)
        eax, _, msg = t.call('tc_room')
        if eax != want or msg:
            bad.append(f'tc_room {n} {"big" if big else "game"}: {eax} want {want}')
    # tc_reserve: a stand-in cache at BUF (selTeamsPtr = BUF: the game's budget)
    words = [0x7E00 | k for k in range(nm)]
    for k, w in enumerate(words):
        t.w16(BUF + 684 * k, w)
    lst = BUF + 0x30000
    new = [0x7D01, 0x7D02, 0x7D02, 0xFFFF, words[3]]     # (2 new: 7D01, 7D02 once; FFFF skipped; one cached)
    t.uc.mem_write(lst, b''.join(struct.pack('<H', w) for w in new))
    for n, want in ((nm - 2, 1), (nm - 1, 0)):
        t.w16(numsel, n)
        t.w32(t.sym['SELPTR'], BUF)
        t.w32(t.sym['SELBASEV'], BUF)
        for a, v in ((d0, 0x11111111), (t.sym['D1'], 0x22222222), (t.sym['A0'], 0x33333333)):
            t.w32(a, v)
        regs = {UC_X86_REG_EBX: 0xB, UC_X86_REG_ESI: 0x51, UC_X86_REG_EDI: 0xD1, UC_X86_REG_EBP: 0xBB}
        eax, _, msg = t.call('tc_reserve', lst, len(new), regs=regs)
        kept = [t.uc.reg_read(r) for r in regs] == list(regs.values()) and \
            [t.u32(a) for a in (d0, t.sym['D1'], t.sym['A0'])] == [0x11111111, 0x22222222, 0x33333333]
        if eax != want or msg or not kept:
            bad.append(f'tc_reserve at {n}: {eax} want {want}, registers kept {kept}')
    notes.append(f'budgets {nm} / {tcap or "-"}, 6 hooks')
    return not bad, '; '.join(bad) if bad else ', '.join(notes)
