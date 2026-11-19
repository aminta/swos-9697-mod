"""4.2 backlog-42 row 154 (MC must-fix): the Intercontinental has ONE owner per career world, and sacups' slot-4
Intercontinental is built AS slot 4. Tier B without a snapshot (test_lrank's Exe: the build's objects relocated into
Unicorn, the game's routines the glue calls stubbed and recorded). The build: HT_INT_BUILD (default: the current
fixture, HOSTTEST_SYMS=1).

- tables: INT_OWN[w] = 0 exactly for the World 2026-27 world (its year byte in careerworld's WTAB = 126, conti linked:
  conti plays its Intercontinental), 1 elsewhere; INT_S1[0] = the build's default INTLIST (JUVENTUS / ARG), every
  world's pair 0xFFFF 0xFFFF (before 4.2: 1996-97's pair in every world - the phantom);
- sa_int_new (engine after_new) per world byte: INTLIST = that world's season-1 pair;
- int_step (slot 2): the club in INTLIST in a world sacups owns reaches cseg_8B2D3 (the probe's red twin), in the
  2026-27 world it does not;
- int4_step (slot 4, a club with a league cup): cseg_8B2D3 with D0 = 4 and A0 = the Intercontinental (its days written
  as slot 4; up to 4.1 D0 = 2 and a buffer swap: the days kept slot 2), then cseg_8ECAE's tail with LIST4 = the pair,
  A4 = slot 4, D7 = 0; dseg_D8CBA = INT after it, the no-sacking flag unchanged; in the 2026-27 world: nothing."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import fixroot  # noqa: E402

BUILD = fixroot.build_dir('HT_INT_BUILD')
NONE = 0xFFFFFFFF


class X:
    def __init__(self):
        fixroot.need(BUILD, 'test_intworld', 'ITALIAN.syms.json')
        import test_lrank
        test_lrank.BUILD = BUILD
        self.e = test_lrank.Exe()
        allsyms = json.load(open(os.path.join(BUILD, 'ITALIAN.syms.json')))
        self.s = allsyms['sacups']
        self.cw = allsyms['careerworld']
        self.conti = 'conti' in allsyms
        self.hits = []
        from unicorn import UC_HOOK_CODE
        stubs = {self.lin('CSEG_8B2D3'): '8b2d3', self.lin('CSEG_8DAC3'): '8dac3', self.lin('PO_TAIL'): 'tail',
                 self.lin('GET_SEASON'): 'season'}
        self.stubs = stubs

        def hook(uc, addr, size, _):
            k = stubs.get(addr)
            if k is None:
                return
            self.hits.append((k, self.w16('D0'), self.w32('A0'), self.w32('A4'), self.w16('D7'), self.w32('LIST4')))
            if k == 'tail':                    # (the tail sets the no-sacking flag: the caller must restore it)
                self.e.wr(self.lin('NOSACK'), b'\1\0')
            from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
            sp = uc.reg_read(UC_X86_REG_ESP)
            ret = struct.unpack('<I', bytes(uc.mem_read(sp, 4)))[0]
            uc.reg_write(UC_X86_REG_ESP, sp + 4)
            uc.reg_write(UC_X86_REG_EIP, ret)
        for a in stubs:
            self.e.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)

    def lin(self, name, mod=None):
        o, a = (mod or self.s)[name]
        return self.e.base[o or 1] + a

    def w16(self, n):
        return struct.unpack('<H', self.e.rd(self.lin(n), 2))[0]

    def w32(self, n):
        return struct.unpack('<I', self.e.rd(self.lin(n), 4))[0]

    def put(self, n, v, size=4):
        self.e.wr(self.lin(n), struct.pack('<I' if size == 4 else '<H', v))

    def world(self, w):
        if 'INT_WB' in self.s:
            self.e.wr(self.lin('INT_WB'), bytes([w]))
        else:
            assert w == 0


def _tables(x):
    n = x.s['INT_NW'][1] + 1                             # (the worlds 0..n-2 + the out-of-table entry)
    own = list(x.e.rd(x.lin('INT_OWN'), n))
    s1 = list(struct.unpack(f'<{n}I', x.e.rd(x.lin('INT_S1'), 4 * n)))
    return own, s1


def _year(x, w):
    wtab = x.lin('WTAB', x.cw)
    return x.e.rd(wtab + 52 * (w - 1) + 42, 1)[0]


def _want(x, w):
    """1 when sacups must play world w's Intercontinental: not the World 2026-27 world when conti is linked (from the
    world data - WTAB's year byte -, not from INT_OWN: the slot tests stay independent of the table they check)"""
    return 0 if (w > 0 and x.conti and _year(x, w) == 126) else 1


def test_intworld_tables():
    """INT_OWN / INT_S1 per world from the world data"""
    x = X()
    own, s1 = _tables(x)
    assert own and own[-1] == 1 and s1[-1] == NONE, (own, s1)
    default = x.w32('INTLIST')
    assert s1[0] == default and default != NONE, (hex(s1[0]), hex(default))
    bad = []
    for w in range(len(own) - 1):
        want = _want(x, w)
        if own[w] != want:
            bad.append(f'world {w}: own {own[w]} want {want}')
        if w > 0 and s1[w] != NONE:
            bad.append(f'world {w}: season-1 pair {s1[w]:#x}')
    assert not bad, bad
    conti_w = [w for w in range(len(own) - 1) if own[w] == 0]
    assert not x.conti or conti_w, 'conti linked but no world without a sacups Intercontinental'
    return True, f'{len(own) - 1} worlds, conti owns {conti_w}, season 1: world 0 {s1[0]:#010x}, others none'


def test_intworld_new_career():
    """sa_int_new: INTLIST = the world's season-1 pair"""
    x = X()
    own, s1 = _tables(x)
    default = x.w32('INTLIST')
    out = []
    for w in range(len(own) - 1) if 'INT_WB' in x.s else (0,):
        x.put('INTLIST', 0x00200014)                     # (a stale pair: the 1996-97 one, whatever the world)
        x.world(w)
        x.e.call(x.lin('sa_int_new'))
        got = x.w32('INTLIST')
        assert got == (default if w == 0 else NONE), (w, hex(got))
        out.append(f'{w}:{got:#x}')
    return True, 'INTLIST after a new career per world ' + ' '.join(out)


def _setup(x, w, sel_holder=True):
    x.hits.clear()
    x.world(w)
    x.put('INTLIST', 0x00210014)                         # two clubs: (20, 0) and (33, 0)
    x.e.wr(x.lin('SEL'), struct.pack('<H', 0x0014 if sel_holder else 0x0115))


def test_intworld_slot2():
    """int_step: the gate (2026-27 world: no slot-2 Intercontinental; a sacups world: built - the red twin)"""
    x = X()
    own, _ = _tables(x)
    res = []
    for w in range(len(own) - 1) if 'INT_WB' in x.s else (0,):
        for holder in (True, False):
            _setup(x, w, holder)
            x.put('PLAYER_CUP2', 0)
            x.e.call(x.lin('int_step'))
            built = any(h[0] == '8b2d3' for h in x.hits)
            assert [h[0] for h in x.hits] in ([], ['8b2d3', 'season']), x.hits
            want = holder and _want(x, w) == 1
            assert built == want, (w, holder, x.hits)
            if built:
                h = [h for h in x.hits if h[0] == '8b2d3'][0]
                assert h[1] == 2 and h[2] == x.lin('INT'), h
        res.append(f'{w}:{"built" if _want(x, w) else "gated"}')
    return True, 'slot 2 per world ' + ' '.join(res)


def test_intworld_slot4():
    """int4_step: built AS slot 4 (D0 = 4), clubs through cseg_8ECAE's tail; gated in the 2026-27 world"""
    x = X()
    own, _ = _tables(x)
    res = []
    for w in range(len(own) - 1) if 'INT_WB' in x.s else (0,):
        _setup(x, w)
        x.put('SLOT4_CUP', 0)
        x.put('PLAYER_CUP2', 0x12345)                    # (the league cup's contest in slot 2)
        x.e.wr(x.lin('NOSACK'), b'\0\0')
        x.e.call(x.lin('int4_step'))
        kinds = [h[0] for h in x.hits]
        if _want(x, w) == 0:
            assert kinds == ['8dac3'] and x.w32('SLOT4_CUP') == 0, (w, x.hits)
            res.append(f'{w}:gated')
            continue
        assert kinds == ['8dac3', '8b2d3', 'tail'], (w, kinds)
        b, t = x.hits[1], x.hits[2]
        assert b[1] == 4 and b[2] == x.lin('INT'), ('cseg_8B2D3 not as slot 4', b)
        assert t[3] == x.lin('SLOT4') and t[4] == 0 and t[5] == 0x00210014, ('tail', t)
        assert x.w32('SLOT4_CUP') == x.lin('INT'), hex(x.w32('SLOT4_CUP'))
        assert x.w32('PLAYER_CUP2') == 0x12345
        assert x.e.rd(x.lin('NOSACK'), 2) == b'\0\0', 'the no-sacking flag left set for the season'
        res.append(f'{w}:slot4')
    _setup(x, 0, sel_holder=False)                       # (not a holder: only the native play-off builder)
    x.put('SLOT4_CUP', 0)
    x.e.call(x.lin('int4_step'))
    assert [h[0] for h in x.hits] == ['8dac3'], x.hits
    return True, 'slot 4 per world ' + ' '.join(res) + '; a non-holder: cseg_8DAC3 only'


def test_intworld_red_twins():
    """R4: the probes fail on mutants - int4_step's D0 = 2 (the 4.1 build as slot 2), INT_OWN all 1 (no gate)"""
    import test_intworld as me
    x = X()
    d0 = struct.pack('<I', x.lin('D0'))
    at = x.lin('int4_step')
    code = x.e.rd(at, 0x100)
    k = code.find(b'\x66\xc7\x05' + d0 + b'\x04\x00')
    assert k > 0, 'int4_step: mov word [D0], 4 not found'
    caught = []
    orig_x = me.X

    def mutant(fn, patch):
        def mk():
            y = orig_x()
            patch(y)
            return y
        me.X = mk
        try:
            fn()
        except AssertionError:
            caught.append(fn.__name__)
        finally:
            me.X = orig_x

    mutant(test_intworld_slot4, lambda y: y.e.wr(at + k + 7, b'\x02'))
    own, _ = _tables(x)
    if 0 in own:
        mutant(test_intworld_slot2, lambda y: y.e.wr(y.lin('INT_OWN'), bytes([1] * len(own))))
        mutant(test_intworld_tables, lambda y: y.e.wr(y.lin('INT_OWN'), bytes([1] * len(own))))
    want = 3 if 0 in own else 1
    assert len(caught) == want, ('PROBE-ERROR: a mutant passed', caught)
    return True, f'{len(caught)} mutants caught: {", ".join(caught)}'
