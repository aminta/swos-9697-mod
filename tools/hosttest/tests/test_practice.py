"""4.2 set-piece practice, step 2 (MC 14/11 gate 4: practice off = the match byte-identical): the release exe's
GameLoop per-pass call (practice.hook_site's site, now `call pr_frame`) run in a bare Unicorn machine - the exe
(HT_PRACTICE_EXE, else c/HTO4/SWOS/ITALIAN.EXE) relocated (emu.relocate: obj1 / obj2 / obj4 at bases of their own),
the game state zero but for what each case sets, the obj2 offsets from practice.find_game on the original exe:
- practice off (PR_KIND 0): the call returns having written nothing but its own stack - not a byte of the game;
- PR_KIND set outside the training game (g_trainingGame 0): the same;
- (playGame 0 - the match left this pass, ESC - is skipped the same way: the case below sets it 1);
- CORNER practice (PR_KIND 3, ATTACK, the top team human, play live): WAITF frames write only PR_WORK (the idle
  count), the next frame forces the corner for the top team (it attacks the bottom goal): the ball at x 150, y 778,
  z / speed / deltas 0, lastTeamPlayed = bottomTeamData, ST 1 - and nothing else in the game is written."""
import os
import re
import struct
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_PRACTICE_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'HTO4', 'SWOS', 'ITALIAN.EXE')
ORIG = os.path.join(HOME, 'swos-mod', 'orig', 'ITALIAN.EXE')
B1, B2, B4 = 0x100000, 0x400000, 0x1000000
STACK, RET, MEM = 0x3F0000, 0x3E0000, 0x4000000


def _setup():
    from emu import relocate
    import lepatch
    import practice
    import swreg
    import bteam
    p = lepatch.LEPatch(EXE)
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\xe8....\xe8....\xe8....\xe8....\x66\xa1....\x66\x0b\xc0\x0f\x84....'
                                        rb'\x66\xa1....\x66\x0b\xc0\x74.\xe8', d1, re.S)]
    assert len(m) == 1, ('GameLoop site', m)
    hk = m[0] + 15
    tgt = p.call_target(1, hk)
    o = lepatch.LEPatch(ORIG)
    pt = [x.start() for x in re.finditer(rb'\x66\xc7\x05....\x01\x00\xc7\x05........\x66\xc7\x05....\x01\x00\x66\xc7\x05'
                                         rb'....\x02\x00\xe8', o.le.obj_bytes(1), re.S)]
    assert len(pt) == 1, ('PlayTrainingGame', pt)
    g = practice.find_game(o, bteam.ui_sites(o)['a6'], pt[0])
    i1, i2, le = relocate(EXE, B1, B2, base4=B4)
    band = le.img4[swreg.PRACTICE_AT:swreg.PRACTICE_END]
    k = band.find(practice.TAG.encode())
    assert k >= 0, 'no PRWK tag in the PRACTICE band (an exe without practice step 2?)'
    work = struct.unpack_from('<I', band, k + 4)[0]
    g['PLAYG_O'] = practice._t(p, hk + 7)[1]                          # playGame (the site's own `mov ax, [playGame]`)
    return hk, tgt, g, (i1, i2, le.img4), work


def _machine(imgs):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0, MEM)
    for b, img in zip((B1, B2, B4), imgs):
        uc.mem_write(b, img)
    uc.hook_add(UC_HOOK_CODE, lambda u, a, n, d: u.emu_stop(), begin=RET, end=RET)
    writes = []
    uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, acc, a, n, v, d: writes.append((a, n)))
    return uc, writes


def _frame(uc, writes, hk):
    """GameLoop's site once: `call pr_frame` run from the site to the next instruction; the writes outside the stack"""
    from unicorn.x86_const import UC_X86_REG_ESP
    writes.clear()
    uc.reg_write(UC_X86_REG_ESP, STACK)
    uc.emu_start(B1 + hk, B1 + hk + 5, count=200_000)
    return [(a, n) for a, n in writes if not STACK - 0x1000 <= a < STACK + 16]


def test_practice_off():
    if not os.path.exists(EXE):
        return False, f'{EXE} missing (HT_PRACTICE_EXE: a 4.2 exe with practice step 2)'
    import practice
    hk, tgt, g, imgs, work = _setup()
    errs, info = [], []
    if tgt[0] != 4:
        return False, f'GameLoop obj1+{hk:#x} calls {tgt}: not the practice engine (obj4)'
    uc, writes = _machine(imgs)
    kind = work + practice.WK['KIND']
    w = _frame(uc, writes, hk)                                       # practice off
    if w:
        errs.append(f'PR_KIND 0: {len(w)} writes ({[hex(a) for a, _ in w[:4]]})')
    uc.mem_write(kind, b'\x01')                                      # PR_KIND set, no training game
    w = _frame(uc, writes, hk)
    if w:
        errs.append(f'PR_KIND 1, g_trainingGame 0: {len(w)} writes ({[hex(a) for a, _ in w[:4]]})')
    info.append('practice off / outside the training game: nothing written')
    uc.mem_write(kind, b'\x03')                                      # CORNER, ATTACK, the top team human, live play
    uc.mem_write(B2 + g['GTR_O'], b'\x01\x00')
    uc.mem_write(B2 + g['PLAYG_O'], b'\x01\x00')                     # the match running (playGame 0 = left: skipped)
    uc.mem_write(B2 + g['GSP_O'], struct.pack('<H', 100))
    uc.mem_write(B2 + g['GS_O'], struct.pack('<H', 100))
    uc.mem_write(B2 + g['TOPT_O'] + 4, b'\x01\x00')
    pw = range(work, work + practice.WORK_SZ)
    for f in range(practice.WAITF - 1):
        w = [x for x in _frame(uc, writes, hk) if x[0] not in pw]
        if w:
            errs.append(f'idle frame {f}: writes outside PR_WORK {[hex(a) for a, _ in w[:4]]}')
            break
    ball = B2 + g['BALL_O']
    allowed = set(pw) | {B2 + g['LTP_O'] + i for i in range(4)} | {ball + o + i for o in (0x1E, 0x22, 0x26, 0x2E, 0x32,
                                                                                         0x36) for i in range(4)} \
        | {ball + 0x2C, ball + 0x2D}
    w = [x for x in _frame(uc, writes, hk) if x[0] not in allowed]
    if w:
        errs.append(f'forcing frame: writes outside PR_WORK / the ball / lastTeamPlayed {[hex(a) for a, _ in w[:4]]}')
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    bx, by = (struct.unpack('<i', rd(ball + o, 4))[0] >> 16 for o in (0x1E, 0x22))
    ltp = struct.unpack('<I', rd(B2 + g['LTP_O'], 4))[0]
    st, atk, hum = rd(work + practice.WK['ST'], 1)[0], rd(work + practice.WK['ATK'], 1)[0], rd(work + practice.WK['HUM'], 1)[0]
    got = (bx, by, ltp - B2 == g['BOTT_O'], st, atk, hum)
    if got != (150, 778, True, 1, 1, 0):
        errs.append(f'corner forced: ball x/y {bx}/{by}, lastTeamPlayed bottom {got[2]}, ST {st}, ATK {atk}, HUM {hum} '
                    f'(want 150/778, True, 1, 1, 0)')
    info.append(f'corner practice: {practice.WAITF - 1} idle frames write PR_WORK only; frame {practice.WAITF}: '
                f'ball {bx}/{by}, lastTeamPlayed = bottomTeamData, ATTACK by the top (human) team')
    return not errs, '; '.join(errs) or f'GameLoop obj1+{hk:#x} -> obj4+{tgt[1]:#x}: ' + '; '.join(info)
