"""4.2 backlog-42 row 153 (Gianfranco 17/11, Android DOSBox Pure / RetroArch touch overlay): joyname's letter picker
(InputTextKeyLoop's FilterKeys call, jn_filt) one loop at a time in Unicorn (test_lrank's Exe: the build's objects
relocated; FilterKeys and Joy1SetStatus stubbed, the stick's flags written straight into player 1's control flags).
The build: HT_JOY_BUILD (default: the current fixture, HOSTTEST_SYMS=1).

- FIRE + LEFT deletes with FIRE held all along: no ESC, however long FIRE is held (up to 4.1: the long-FIRE count ran
  on through the deletes, the 2nd-3rd delete ended in ESC and the edit was lost); FIRE alone held JN_LONG loops: ESC;
- DOWN at the name's end (cursor on the terminator) = BACKSPACE (8), no chord; held = repeated; on an empty name:
  nothing; the keyboard's DOWN arrow the same; UP at the end appends 'A' (up to 4.1 DOWN appended too);
- DOWN on a character still cycles it (A -> space)."""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import fixroot  # noqa: E402

BUILD = fixroot.build_dir('HT_JOY_BUILD')
UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 0x20
ESC, BS, ENTER = 1, 8, 13


class J:
    def __init__(self):
        fixroot.need(BUILD, 'test_joyname', 'ITALIAN.syms.json')
        import test_lrank
        test_lrank.BUILD = BUILD
        self.e = test_lrank.Exe()
        self.s = json.load(open(os.path.join(BUILD, 'ITALIAN.syms.json')))['joyname']
        from unicorn import UC_HOOK_CODE
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
        stubs = {self.lin('FILT'), self.lin('JOY1')}

        def hook(uc, addr, size, _):
            if addr in stubs:
                sp = uc.reg_read(UC_X86_REG_ESP)
                uc.reg_write(UC_X86_REG_ESP, sp + 4)
                uc.reg_write(UC_X86_REG_EIP, struct.unpack('<I', bytes(uc.mem_read(sp, 4)))[0])
        for a in stubs:
            self.e.uc.hook_add(UC_HOOK_CODE, hook, begin=a, end=a)
        self.e.wr(self.lin('SWOSPP'), b'\xff')           # (the game's own keyboard, not SWOS++)
        self.w16('CTL', 0)                               # (not KEYBOARD ONLY: the stick is read)
        self.w16('KCF', 0)
        self.w16('ALLOWX', 0)                            # (a name, not a file name)
        self.w16('D7', 21)                               # (the field: 22 bytes)

    def lin(self, n):
        o, a = self.s[n]
        return self.e.base[o] + a

    def w16(self, n, v):
        self.e.wr(self.lin(n), struct.pack('<H', v))

    def r16(self, n):
        return struct.unpack('<H', self.e.rd(self.lin(n), 2))[0]

    def field(self, name, cur=None):
        """a new field holding name, the cursor at cur (default: its end)"""
        buf = self.lin('BUF')
        self.e.wr(buf, name.encode('latin-1') + bytes(24 - len(name)))
        self.e.wr(self.lin('A0'), struct.pack('<I', buf + (len(name) if cur is None else cur)))
        self.w16('DEAD', 0)

    def name(self):
        return self.e.rd(self.lin('BUF'), 24).split(b'\0')[0].decode('latin-1')

    def loop(self, stick=0, key=0):
        """one InputTextKeyLoop pass: the code jn_filt leaves in D1 (0: none); 8 applied as the game does"""
        self.w16('D1', 0)
        self.w16('LASTKEY', key)
        self.w16('PL1CF', stick)
        self.e.call(self.lin('jn_filt'))
        d1 = self.r16('D1')
        if d1 == BS:                                     # (InputTextKeyLoop: delete left of the cursor)
            a0 = struct.unpack('<I', self.e.rd(self.lin('A0'), 4))[0]
            buf = self.lin('BUF')
            if a0 > buf:
                t = self.e.rd(a0, 24 - (a0 - buf))
                self.e.wr(a0 - 1, t + b'\0')
                self.e.wr(self.lin('A0'), struct.pack('<I', a0 - 1))
        return d1

    def arm(self):
        """the FIRE that opened the field released (the picker armed)"""
        assert self.loop(0) == 0


def test_joyname_fire_left_deletes_never_cancel():
    """5 FIRE + LEFT deletes, FIRE held all along for far more than JN_LONG loops: 5 BACKSPACEs, no ESC"""
    j = J()
    j.field('ROBERTO BAGGIO')
    j.arm()
    codes = []
    codes.append(j.loop(FIRE))
    for _ in range(5):
        for _ in range(12):                              # (LEFT held 12 loops: one edge, one delete)
            codes.append(j.loop(FIRE | LEFT))
        for _ in range(12):
            codes.append(j.loop(FIRE))
    assert ESC not in codes, ('ESC during the deletes', codes)
    assert codes.count(BS) == 5, codes
    assert j.name() == 'ROBERTO B', j.name()
    assert j.loop(0) == 0 and j.name() == 'ROBERTO B'    # (released after a delete: no confirm)
    assert j.loop(FIRE) == 0 and j.loop(0) == ENTER      # (then a FIRE tap confirms)


def test_joyname_long_fire_still_cancels():
    """FIRE alone held: ESC within JN_LONG + 1 loops (and only then)"""
    j = J()
    j.field('PAOLO MALDINI')
    j.arm()
    codes = [j.loop(FIRE) for _ in range(45)]
    assert ESC in codes and codes.index(ESC) >= 30, codes
    assert BS not in codes and j.name() == 'PAOLO MALDINI'


def test_joyname_down_at_end_deletes():
    """DOWN at the end: BACKSPACE, held = repeated; empty name: nothing; the keyboard's DOWN arrow too"""
    j = J()
    j.field('ZOLA')
    j.arm()
    assert j.loop(DOWN) == BS and j.name() == 'ZOL', j.name()
    assert j.loop(0) == 0
    assert j.loop(DOWN) == BS and j.name() == 'ZO'
    codes = [j.loop(DOWN) for _ in range(40)]            # (held: the repeat deletes the rest, then nothing)
    assert j.name() == '' and codes.count(BS) == 2, (j.name(), codes)
    assert j.loop(0) == 0
    assert j.loop(DOWN) == 0 and j.name() == ''          # (empty: nothing to delete)
    j.field('DEL PIERO')
    j.arm()
    assert j.loop(0, key=0x50) == BS and j.name() == 'DEL PIER', j.name()   # (the keyboard's DOWN arrow)


def test_joyname_up_appends_down_cycles():
    """UP at the end appends 'A' (cursor on it); DOWN on that character cycles it to a space (not a delete)"""
    j = J()
    j.field('VIERI')
    j.arm()
    assert j.loop(UP) == 0 and j.name() == 'VIERIA', j.name()
    assert j.loop(0) == 0
    assert j.loop(DOWN) == 0 and j.name() == 'VIERI ', repr(j.name())
    assert j.loop(0) == 0
    assert j.loop(RIGHT) == 22                           # (the game's cursor right: onto the terminator)
