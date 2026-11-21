"""4.2 team cache, step 1b (careerworld / trailer; design internal/handoff/teamcache-fable-design.md 1.4-1.6, MC 16/11),
on the static image of HT_TC_EXE (else c/HTTC1: a release-recipe exe built with HOSTTEST_SYMS=1). No snapshot: the
routines are called with the cache pointers and the stage poked.

- w_switch: every new career takes the big cache (SELBASEV = selTeamsPtr = NEWSEL, ROOMV = SEL_ROOM);
- w_loadcopy checks a .CAR in the stage BEFORE touching memory: N > SEL_CAP -> TC_LOADERR 3, a file shorter than its
  records -> 1, longer than the fixed part + SEL_ROOM -> 2; each refusal leaves careerFileBuffer and SELBASEV as they
  were. A good file: TC_LOADERR 0, the fixed part copied, the big cache (any .CAR). A .SEA (SWSEA): not checked, the
  game's cache;
- load_trailer: a refusal returns to LoadCareerFile's own failure path (`mov ax, 1; or ax, ax; ret` after its message);
- w_save_tail, a 1996-97 career in the big cache: the file from the stage in CANONICAL form - selTeamsPtr = the game's
  cache, every competition dword careerTeam - NEWSEL -> careerTeam - OLDSEL, other dwords (a record offset) kept, the
  records after the fixed part, A1 = the stage;
- the season-end parking (ws0 / wl0): keyed on selTeamsPtr == NEWSEL (all records: SEL_CAP * 684), flags kept."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixroot  # noqa: E402
import test_registry as tr  # noqa: E402
import test_swc1 as ts  # noqa: E402

EXE = os.environ.get('HT_TC_EXE') or fixroot.fx('HTTC1', 'SWOS', 'ITALIAN.EXE')
CT = 0xDB80                                     # careerTeam in careerFileBuffer
NUMSEL_OFF = 0x173AF                            # g_numSelectedTeams in the fixed part
SELPTR_OFF = 0x1739C                            # selTeamsPtr in the fixed part
COMP = (0xF77E, 0x16ABC)                        # the competition buffers


class M:
    def __init__(self):
        self.uc, self.le, self.rd = ts.static_machine(EXE)
        sy = json.load(open(EXE[:-4] + '.syms.json'))
        cw, self.trl = sy['careerworld'], sy['trailer']
        self.code = {k[6:]: v for k, v in cw.items() if k.startswith('tails.')}
        self.code.update({k: cw[k] for k in ('ws0', 'wl0') if k in cw})
        self.s = {k[5:]: v for k, v in cw.items() if k.startswith('tsym.')}

    def lin(self, v):
        o, off = v
        return {0: off, 1: tr.B1, 2: tr.B2, 3: tr.B3, 4: tr.B4}[o] + (off if o else 0)

    def a(self, name):                          # an address symbol
        return self.lin(self.s[name])

    def k(self, name):                          # a constant
        assert self.s[name][0] == 0, name
        return self.s[name][1]

    def w8(self, a, v):
        self.uc.mem_write(a, bytes([v]))

    def w16(self, a, v):
        self.uc.mem_write(a, struct.pack('<H', v))

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack('<I', v & 0xffffffff))

    def u32(self, a):
        return struct.unpack('<I', self.rd(a, 4))[0]

    def call(self, name, stop=None, regs=None):
        """run obj1 code `name` (tails / stubs) until it returns (or reaches stop); (eax, eflags)"""
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EFLAGS
        sp = tr.STACK - 0x100
        self.uc.mem_write(sp, struct.pack('<I', tr.RET))
        self.uc.reg_write(UC_X86_REG_ESP, sp)
        for r, v in (regs or {}).items():
            self.uc.reg_write(r, v)
        hs = [self.uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=x, end=x)
              for x in [tr.RET] + ([stop] if stop else [])]
        self.uc.emu_start(tr.B1 + self.code[name][1], tr.RET, count=20_000_000)
        for h in hs:
            self.uc.hook_del(h)
        return self.uc.reg_read(UC_X86_REG_EAX), self.uc.reg_read(UC_X86_REG_EFLAGS)


def test_tc1b():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (release recipe + HOSTTEST_SYMS=1) missing'
    m = M()
    if 'w_loadcopy' not in m.code or 'TC_LOADERR' not in m.s:
        return False, f'{EXE}: no team cache 1b (careerworld tails / TC_LOADERR not in the syms)'
    bad, notes = [], []
    car, stage, new, old = m.a('CAREER'), m.a('STAGE'), m.a('NEWSEL'), m.a('OLDSEL')
    sbv, room, sptr, err, d1, a1 = (m.a(x) for x in ('SELBASEV', 'ROOMV', 'SELPTR', 'TC_LOADERR', 'D1R', 'A1R'))
    fixed, selroom, cap = m.k('FIXED'), m.k('SEL_ROOM'), m.k('SEL_CAP')
    sea = tr.B1 + m.code['SWSEA'][1]
    # w_switch
    m.w32(sbv, old)
    m.w32(sptr, old)
    m.call('w_switch')
    if (m.u32(sbv), m.u32(sptr), m.u32(room)) != (new, new, selroom):
        bad.append(f'w_switch: SELBASEV {m.u32(sbv):#x} selTeamsPtr {m.u32(sptr):#x} ROOMV {m.u32(room)} (want NEWSEL / SEL_ROOM)')

    # w_loadcopy: refusals leave memory as it was
    def load(n, length, is_sea=0):
        m.w8(sea, is_sea)
        m.w8(err, 0xEE)
        m.w32(sbv, old)
        m.w8(car, 0xAA)
        m.w8(stage, 0x55)
        m.w16(stage + NUMSEL_OFF, n)
        m.w32(stage + SELPTR_OFF, old)
        m.w32(d1, length)
        m.call('w_loadcopy')
        return m.rd(err, 1)[0], m.rd(car, 1)[0], m.u32(sbv)
    for n, length, want in ((cap + 1, fixed + (cap + 1) * 684, 3), (10, fixed + 9 * 684, 1),
                            (10, fixed + selroom + 1, 2)):
        e, c0, base = load(n, length)
        if (e, c0, base) != (want, 0xAA, old):
            bad.append(f'w_loadcopy N {n} length {length}: TC_LOADERR {e} (want {want}), careerFileBuffer[0] {c0:#x} '
                       f'(want untouched 0xaa), SELBASEV {base:#x} (want unchanged)')
    e, c0, base = load(10, fixed + 10 * 684 + 948)
    if (e, c0, base) != (0, 0x55, new):
        bad.append(f'w_loadcopy good 1996-97 .CAR: TC_LOADERR {e}, careerFileBuffer[0] {c0:#x} (want the stage 0x55), '
                   f'SELBASEV {base:#x} (want NEWSEL)')
    e, c0, base = load(cap + 1, fixed + (cap + 1) * 684, 1)
    if base != old or e not in (0, 0xEE):
        bad.append(f'w_loadcopy .SEA: TC_LOADERR {e}, SELBASEV {base:#x} (want the game\'s cache, no check)')
    m.w8(sea, 0)

    # 1b+ (MC 16/11): w_lsize - the .CAR's size from DOS before LoadFile (int 21h emulated: open / seek end / close);
    # longer than FIXED + SEL_ROOM -> TC_LONG + CF, the stage not read; w_loadcopy then refuses it (2) untouched
    if 'w_lsize' in m.code:
        from unicorn import UC_HOOK_INTR
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_EFLAGS
        size = [0]
        calls = []

        def intr(u, n, _):
            ah = (u.reg_read(UC_X86_REG_EAX) >> 8) & 0xff
            calls.append(ah)
            fl = u.reg_read(UC_X86_REG_EFLAGS) & ~1
            if ah == 0x42:
                u.reg_write(UC_X86_REG_EAX, size[0] & 0xffff)
                u.reg_write(UC_X86_REG_EDX, size[0] >> 16)
            elif ah == 0x3D:
                u.reg_write(UC_X86_REG_EAX, 7)
            u.reg_write(UC_X86_REG_EFLAGS, fl)
        h = m.uc.hook_add(UC_HOOK_INTR, intr)
        tl = tr.B1 + m.code['TC_LONG'][1]
        for n_, is_sea, want in ((fixed + selroom, 0, 0), (fixed + selroom + 1, 0, 1), (fixed + selroom + 4096, 0, 1),
                                 (fixed + selroom + 4096, 1, 0)):
            size[0] = n_
            del calls[:]
            m.w8(sea, is_sea)
            m.w8(tl, 0xEE)
            _, fl = m.call('w_lsize')
            if (m.rd(tl, 1)[0], fl & 1) != ((want, want) if not is_sea else (0, 0)) or (not is_sea and calls != [0x3D, 0x42, 0x3E]):
                bad.append(f'w_lsize size {n_} .SEA {is_sea}: TC_LONG {m.rd(tl, 1)[0]} CF {fl & 1} (want {want}), int 21h {calls}')
        m.uc.hook_del(h)
        m.w8(sea, 0)
        m.w8(tl, 1)                             # w_loadcopy after a too long file: 2, nothing copied (the stage stale)
        e, c0, base = load(10, fixed + 10 * 684 + 948)
        if (e, c0, base) != (2, 0xAA, old):
            bad.append(f'w_loadcopy after TC_LONG: TC_LOADERR {e} (want 2), careerFileBuffer[0] {c0:#x}, SELBASEV {base:#x}')
        m.w8(tl, 0)
        notes.append('w_lsize 4 cases + TC_LONG refusal')
    else:
        bad.append('no w_lsize (team cache 1b+: the length check before LoadFile)')

    # the refusal: load_trailer processes nothing; tc_lchk (LoadCareerFile's call after it, in its own frame) takes the
    # game's failure path
    o1 = m.rd(tr.B1, m.le.obj(1).vsize)
    lc = m.trl.get('tc_lchk', [0, 0])[1]
    calls = [i for i in range(len(o1) - 5) if o1[i] == 0xE8 and lc and i + 5 + struct.unpack_from('<i', o1, i + 1)[0] == lc]
    seg = o1[lc:lc + 32]
    k = seg.find(b'\x83\xc4\x04\xe9')
    if len(calls) != 1 or k < 0:
        bad.append(f'tc_lchk: {len(calls)} callers, add esp / jmp at {k}')
    else:
        tgt = lc + k + 8 + struct.unpack_from('<i', seg, k + 4)[0]
        if b'\x66\xb8\x01\x00\x66\x0b\xc0\xc3' not in o1[tgt:tgt + 48]:
            bad.append(f'tc_lchk refusal -> obj1+{tgt:#x}: not the failure path ({o1[tgt:tgt + 24].hex()})')
        elif o1[calls[0] + 5:calls[0] + 8] != b'\x66\xc7\x05':
            bad.append(f'tc_lchk called from obj1+{calls[0]:#x}: not LoadCareerFile\'s call after ProcessCareerFile')
        else:
            notes.append(f'refusal obj1+{calls[0]:#x} -> obj1+{tgt:#x}')

    # 4.2 rc3 (MC 21/11, Saric's STK84.CAR): a save written with obj2 at an address that is NOT page-aligned relative
    # to this run's (his DOSBox: obj2 at 0x2CEEB6) - its careerTeam dwords must still move to the big cache. (a) a
    # game-cache save (careerTeam - g_selectedTeams), (b) a 4.x big-cache save (careerTeam - NEWSEL); a record offset
    # stays. Before rc3 the .ct page test left them -> team 0 -> FindTeamInCache's int 3 (obj1+0x17064)
    ctv = car + CT
    spots = [COMP[0] + 0x387, COMP[0] + 0x171B, COMP[0] + 0x6BBF]       # STK84: fixed+0xFB05 / 0x10E99 / 0x1633D
    recat = COMP[0] + 0x1787                                             # STK84: fixed+0x10F05 = record 90 (Sparta)
    for label, saved_sel, ctval in (('game-cache save', old - 0xA114A, ctv - old),
                                    ('4.x big-cache save', new - 0xA114A, ctv - new)):
        m.w8(sea, 0)
        m.w8(tr.B1 + m.code['TC_LONG'][1], 0)
        m.uc.mem_write(stage, bytes(fixed))
        for o in spots:
            m.w32(stage + o, ctval)
        m.w32(stage + recat, 90 * 684)
        m.w16(stage + NUMSEL_OFF, 95)
        m.w32(stage + SELPTR_OFF, saved_sel)
        m.w32(d1, fixed + 95 * 684)
        m.w32(sbv, old)
        m.call('w_loadcopy')
        got = [m.u32(car + o) for o in spots] + [m.u32(car + recat)]
        want = [(ctv - new) & 0xffffffff] * 3 + [90 * 684]
        if got != want or m.u32(sbv) != new:
            bad.append(f'w_loadcopy {label} from a non-page-aligned obj2 (selTeamsPtr {saved_sel:#x}): careerTeam dwords '
                       f'+ record 90 = {[hex(x) for x in got]} want {[hex(x) for x in want]}, SELBASEV {m.u32(sbv):#x}')
    stk = os.environ.get('HT_STK84', os.path.expanduser('~/swos-mod/internal/user-reports/ante-20261120/STK84.CAR'))
    if os.path.exists(stk):                     # the real file, as Saric's DOSBox wrote it
        f = open(stk, 'rb').read()
        m.uc.mem_write(stage, f)
        m.w32(d1, len(f))
        m.w32(sbv, old)
        m.call('w_loadcopy')
        got = [m.u32(car + o) for o in (0xFB05, 0x10E99, 0x1633D, 0x10F05)]
        want = [(ctv - new) & 0xffffffff] * 3 + [90 * 684]
        if m.rd(err, 1)[0] or got != want:
            bad.append(f'w_loadcopy STK84.CAR: TC_LOADERR {m.rd(err, 1)[0]}, dwords {[hex(x) for x in got]} want '
                       f'{[hex(x) for x in want]}')
        else:
            notes.append('STK84.CAR relocated')
    notes.append('non-aligned obj2 saves (game cache + 4.x big cache)')

    # w_save_tail: a 1996-97 career (world 0: w_big ZF = 1) in the big cache -> the canonical file from the stage
    m.w32(sbv, new)
    m.w32(sptr, new)
    ctv = car + CT
    a, b, rec = car + COMP[0] + 0x100, car + COMP[0] + 0x205, car + COMP[0] + 0x300
    m.w32(a, ctv - new)
    m.w32(b, ctv - new)
    m.w32(rec, 3 * 684)
    m.uc.mem_write(new, bytes(range(256)) * 6)
    m.w32(d1, fixed + 2 * 684)
    m.w32(a1, car)
    m.call('w_save_tail', stop=m.a('WRITEFILE'))
    so = lambda x: stage + (x - car)
    got = (m.u32(stage + SELPTR_OFF), m.u32(so(a)), m.u32(so(b)), m.u32(so(rec)), m.u32(a1))
    want = (old, (ctv - old) & 0xffffffff, (ctv - old) & 0xffffffff, 3 * 684, stage)
    if got != want:
        bad.append('w_save_tail canonical: selTeamsPtr / 2 careerTeam dwords / a record offset / A1 = '
                   f'{[hex(x) for x in got]} want {[hex(x) for x in want]}')
    if m.rd(stage + fixed, 2 * 684) != (bytes(range(256)) * 6)[:2 * 684]:
        bad.append('w_save_tail: the records after the fixed part are not the big cache\'s')

    # parking: ws0 / wl0 keyed on selTeamsPtr
    if 'ws0' in m.code:
        from unicorn.x86_const import UC_X86_REG_EFLAGS
        res = {}
        for p in (new, old):
            m.w32(sptr, p)
            eax, fl = m.call('ws0', regs={UC_X86_REG_EFLAGS: 0x203})
            res[p] = (eax, fl & 1)
        if res[new][0] == res[old][0] or not res[new][1] or not res[old][1]:
            bad.append(f'ws0: eax {res[new][0]:#x} (big) / {res[old][0]:#x} (game\'s), CF kept {res[new][1]} {res[old][1]}')
    else:
        notes.append('no parking stubs (no big world)')
    return not bad, '; '.join(bad) or f'switch, 3 refusals + good + .SEA, canonical save, parking; {", ".join(notes)}'
