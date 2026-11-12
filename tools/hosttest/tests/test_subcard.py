"""4.2 subcard.py (Marco's bug: a player booked on a carried yellow cannot be substituted): the game's own
IsPlayerOkToSubstitute and FindInitialPlayerToBeSubstituted run in Unicorn from the relocated exe (no snapshot: their
inputs are a handful of variables and one in-match team), the original and the patched exe of every language.
- IsPlayerOkToSubstitute, the player to take off with cards 0..4 (g_subsState 1 and 3): the original refuses 2..4,
  the patched one refuses only 3..4 (really sent off); disallowSubs (state 3) still refuses.
- FindInitialPlayerToBeSubstituted: the entering attacker's exact match on the pitch has cards 2 -> the original skips
  him (the first available, place 0), the patched one picks him; with cards 3 both skip him.
- BumpPlayerLastPlayedHalfAtHalfStart / End (both copies, 4 routines): a pitch player on cards 2 gets his half
  counted (halfPlayed 0 -> 1 at a half's start, 1 -> 2 at its end) on the patched exe, not on the original; 3 / 4 never.
- The patch is those 7 bytes and nothing else: obj1 differs from the original at the 7 imm8s only, the other 3
  `cmp byte [esi+34h], 2` (bench players) untouched, obj2 (the booking tables) identical."""
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', '..')
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(HERE, '..'))
import subcard                                                  # noqa: E402

ORIG = os.path.join(TOOLS, '..', 'orig')
LANGS = ('ENGLISH', 'ITALIAN', 'FRENCH', 'GERMAN')
BASE1, SCRATCH = 0x100000, 0x1F00000
POS_GK, POS_ATT = 0, 7
OK_PAT = rb'\x66\x83\x3d(....)\x04\x75.\x66\xa1(....)\x66\x0b\xc0\x0f\x84....\xeb.\x90\x90\x90\xa1(....)\xa3(....)\xc7\x05(....)(....)\x66\xa1(....)'
FI_PAT = rb'\xa1(....)\xa3....\xc7\x05....(....)\x66\xa1(....)\x66\xa3'
FI_END = rb'\x66\xa1....\x66\xa3....\x66\xa1....\x66\xa3(....)\xe8....\x66\xa1....\x66\xa3(....)\xc3'


def _patched(lang):
    import lepatch
    p = lepatch.LEPatch(os.path.join(ORIG, f'{lang}.EXE'))
    subcard.patch(p)
    out = os.path.join(tempfile.mkdtemp(prefix='subcard_'), f'{lang}.EXE')
    p.save(out)
    return out


class Exe:
    """The exe's obj1 / obj2 relocated at BASE1 / after it in a Unicorn machine, an in-match team at SCRATCH."""

    def __init__(self, path, orig):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        import emu
        from le import LE
        le = LE(open(path, 'rb').read())
        self.base2 = (BASE1 + le.obj(1).vsize + 0xFFFF) & ~0xFFFF
        self.img1, self.img2, _ = emu.relocate(path, BASE1, self.base2)
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(0, 0x2000000)
        self.uc.mem_write(BASE1, self.img1)
        self.uc.mem_write(self.base2, self.img2)
        self.d = le.obj_bytes(1)
        self.site = subcard.sites(LE(open(orig, 'rb').read()).obj_bytes(1))   # (the original's: the same places)
        self.emu = emu

    def addr(self, b):
        return struct.unpack('<I', b)[0]

    def w16(self, a, v=None):
        if v is None:
            return struct.unpack('<H', self.uc.mem_read(a, 2))[0]
        self.uc.mem_write(a, struct.pack('<H', v & 0xFFFF))

    def call(self, off):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
        ret = 0x1FF0000
        self.uc.mem_write(ret, b'\xf4')
        self.uc.mem_write(0x1FE0000 - 4, struct.pack('<I', ret))
        self.uc.reg_write(UC_X86_REG_ESP, 0x1FE0000 - 4)
        self.uc.emu_start(BASE1 + off, ret, count=100000)
        assert self.uc.reg_read(UC_X86_REG_EIP) == ret, 'no return'

    def team(self, offs, players):
        """players: {in-match place: (position, cards, disallowSubs)} at SCRATCH + inGameTeamPlayerOffsets[place]"""
        self.uc.mem_write(SCRATCH, b'\0' * 0x1000)
        for i, (pos, cards, dis) in players.items():
            at = SCRATCH + self.w16(offs + 2 * i)
            self.uc.mem_write(at + 46, bytes([pos & 0xFF]))
            self.uc.mem_write(at + 52, bytes([cards, dis]))


def _ok_sub(x, cards, state, dis=0):
    """IsPlayerOkToSubstitute with the player to take off (place 3 of the in-match team) on `cards`: 0 = ok"""
    a = x.site['IsPlayerOkToSubstitute']
    start = a - 123
    m = re.match(OK_PAT, x.img1[start:start + 64], re.S)
    assert m, 'IsPlayerOkToSubstitute: not at its place'
    sub_st, ordv, btg, _a0, _a1, offs, pos = (x.addr(m.group(k)) for k in range(1, 8))
    x.w16(sub_st, state)
    x.w16(ordv, 3)
    x.uc.mem_write(btg, struct.pack('<I', SCRATCH))
    x.w16(pos, 3)
    x.team(offs, {3: (POS_ATT, cards, 0x80 if dis else 0)})
    x.call(start)
    from unicorn.x86_const import UC_X86_REG_EAX
    return x.uc.reg_read(UC_X86_REG_EAX) & 0xFFFF


def _first_choice(x, cards):
    """FindInitialPlayerToBeSubstituted: the entering attacker (place 11); on the pitch every place a goalkeeper on 0
    but menu index 9's, an attacker on `cards`. Returns (plToBeSubstitutedOrd = the menu index chosen,
    plToBeSubstitutedPos, the in-match place of index 9)"""
    f = x.site['FindInitialPlayerToBeSubstituted']
    start = f - 230
    m = re.match(FI_PAT, x.img1[start:start + 40], re.S)
    e = re.search(FI_END, x.img1[f:f + 400], re.S)
    assert m and e, 'FindInitialPlayerToBeSubstituted: not at its place'
    btg, offs, enter = (x.addr(m.group(k)) for k in range(1, 4))
    ordv, posv = x.addr(e.group(1)), x.addr(e.group(2))
    call_at = f - 3 - 6 - 5                                     # `call GetBenchPlayerPointer / mov esi, [A0]`
    g = call_at + 5 + struct.unpack('<i', x.img1[call_at + 1:call_at + 5])[0]
    gm = re.match(rb'\x66\xff\x35....\x66\xa1(....)\x66\xa3....\xa1(....)', x.img1[g:g + 24], re.S)
    assert gm, 'GetBenchPlayerPointer: not at its place'
    tac, bteam = x.addr(gm.group(1)), x.addr(gm.group(2))
    x.w16(tac, 0)                                               # pl1Tactics 0; benchTeam -> a TeamGeneralInfo of
    x.uc.mem_write(SCRATCH + 0x1800, b'\0' * 0x40)              # team number (+12h) 1
    x.w16(SCRATCH + 0x1800 + 0x12, 1)
    x.uc.mem_write(bteam, struct.pack('<I', SCRATCH + 0x1800))
    x.uc.mem_write(btg, struct.pack('<I', SCRATCH))
    x.w16(enter, 11)
    pitch = {i: (POS_GK, 0, 0) for i in range(11)}
    pitch[11] = (POS_ATT, 0, 0)
    x.team(offs, pitch)
    tgt = _place_of(x, g, offs, 9)
    pitch[tgt] = (POS_ATT, cards, 0)
    x.team(offs, pitch)
    x.w16(ordv, 0xEEEE)
    x.call(start)
    return x.w16(ordv), x.w16(posv), tgt


def _place_of(x, g, offs, index):
    """GetBenchPlayerPointer(D0 = index): the in-match place its A0 points at"""
    gm = re.search(rb'\xa1(....)\xa3(....)\x8b\x35', x.img1[g:g + 40], re.S)
    a0 = x.addr(gm.group(2))
    s = x.site['IsPlayerOkToSubstitute'] - 123               # D0: IsPlayerOkToSubstitute's `mov ax, [plToBeSubstitutedPos]
    d0 = x.addr(re.search(rb'\x66\xa1....\x66\xa3(....)\x66\xd1\x25', x.img1[s:s + 80], re.S).group(1))  # / mov [D0], ax`
    x.w16(d0, index)
    x.call(g)
    p = struct.unpack('<I', x.uc.mem_read(a0, 4))[0] - SCRATCH
    return next(i for i in range(16) if x.w16(offs + 2 * i) == p)


def _halves(x, i):
    """BumpPlayerLastPlayedHalf copy i (subcard.sites' order) on a pitch player with cards 0..4: [half counted]"""
    at = x.site[f'BumpPlayerLastPlayedHalf{i}']
    start = at - 3 - 6                                          # `mov esi, [A0] / cmp byte [esi+34h], 2`
    assert x.img1[start:start + 2] == b'\x8b\x35', 'BumpPlayerLastPlayedHalf: not at its place'
    a0 = x.addr(x.img1[start + 2:start + 6])
    half_start = x.img1[at + 12:at + 14] == b'\x02\x74'      # (Start: 0 -> 1 unless 2; End: 1 -> 2)
    out = []
    for cards in range(5):
        x.uc.mem_write(SCRATCH, b'\0' * 0x100)
        x.uc.mem_write(SCRATCH + 52, bytes([cards]))
        x.uc.mem_write(SCRATCH + 0x4E, bytes([0 if half_start else 1]))
        x.uc.mem_write(a0, struct.pack('<I', SCRATCH))
        x.call(start)
        out.append(int(x.uc.mem_read(SCRATCH + 0x4E, 1)[0] == (1 if half_start else 2)))
    return out


def test_subcard():
    errs = []
    for lang in LANGS:
        o, n = os.path.join(ORIG, f'{lang}.EXE'), _patched(lang)
        xo, xn = Exe(o, o), Exe(n, o)
        d1o, d1n = xo.d, xn.d
        diff = [i for i in range(len(d1o)) if d1o[i] != d1n[i]]
        want = sorted(xo.site.values())
        if diff != want or any(d1n[i] != 3 for i in diff):
            errs.append(f'{lang}: obj1 differs at {[hex(i) for i in diff]} (want the 7 imm8s {[hex(i) for i in want]})')
        from le import LE
        if LE(open(o, 'rb').read()).obj_bytes(2) != LE(open(n, 'rb').read()).obj_bytes(2):
            errs.append(f'{lang}: obj2 changed')
        left = [m.start() for m in re.finditer(rb'\x80\x7e\x34\x02', d1n)]
        if len(left) != 3:
            errs.append(f'{lang}: {len(left)} cmp [esi+34h], 2 left (want the 3 bench ones)')
        for i in range(4):
            got_o, got_n = _halves(xo, i), _halves(xn, i)
            if got_o != [1, 1, 0, 0, 0] or got_n != [1, 1, 1, 0, 0]:
                errs.append(f'{lang} Bump {i}: half counted for cards 0..4 -> orig {got_o}, fix {got_n}')
        for state in (1, 3):
            got_o = [_ok_sub(xo, c, state) for c in range(5)]
            got_n = [_ok_sub(xn, c, state) for c in range(5)]
            if got_o != [0, 0, 1, 1, 1] or got_n != [0, 0, 0, 1, 1]:
                errs.append(f'{lang} state {state}: IsPlayerOkToSubstitute cards 0..4 -> orig {got_o}, fix {got_n}')
        if (_ok_sub(xo, 1, 3, dis=1), _ok_sub(xn, 2, 3, dis=1)) != (1, 1):
            errs.append(f'{lang}: disallowSubs no longer refuses')
        fo2, fn2, fo3, fn3 = (_first_choice(x, c) for x, c in ((xo, 2), (xn, 2), (xo, 3), (xn, 3)))
        if fo2[0] != 0 or fn2[0] != 9 or fo3[0] != 0 or fn3[0] != 0:
            errs.append(f'{lang}: FindInitial (ord, pos, place of index 9) cards 2 orig {fo2} fix {fn2}, '
                        f'cards 3 orig {fo3} fix {fn3}')
    return not errs, '; '.join(errs) or f'{len(LANGS)} languages: IsPlayerOkToSubstitute cards 2 allowed, 3/4 '\
        f'refused; FindInitial picks the booked exact match; his halves counted (4 Bump routines); 7 bytes, obj2 identical'
