"""4.2 set-piece practice, step 2 (MC 14/11 gate 4: practice off = the match byte-identical): the release exe's
GameLoop per-pass call (practice.hook_site's site, now `call pr_frame`) run in a bare Unicorn machine - the exe
(HT_PRACTICE_EXE, else c/HTO4/SWOS/ITALIAN.EXE) relocated (emu.relocate: obj1 / obj2 / obj4 at bases of their own),
the game state zero but for what each case sets, the obj2 offsets from practice.find_game on the original exe:
- practice off (PR_KIND 0): the call returns having written nothing but its own stack - not a byte of the game;
- PR_KIND set outside the training game (g_trainingGame 0): the same;
- (playGame 0 - the match left this pass, ESC - is skipped the same way: the case below sets it 1);
- CORNER practice (PR_KIND 3, ATTACK, the top team human, play live): WAITF frames write only PR_WORK (the idle
  count; step 3: and gameTime, held at 0), the next frame forces the corner for the top team (it attacks the bottom goal): the ball at x 150, y 778,
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
    gt = {B2 + g['GT_O'] + i for i in range(4)}                     # (step 3: gameTime held at 0 - no clock)
    uc.mem_write(B2 + g['GT_O'], struct.pack('<I', 1234))
    pw = set(range(work, work + practice.WORK_SZ)) | gt
    for f in range(practice.WAITF - 1):
        w = [x for x in _frame(uc, writes, hk) if x[0] not in pw]
        if w:
            errs.append(f'idle frame {f}: writes outside PR_WORK {[hex(a) for a, _ in w[:4]]}')
            break
    ball = B2 + g['BALL_O']
    allowed = pw | {B2 + g['LTP_O'] + i for i in range(4)} | {ball + o + i for o in (0x1E, 0x22, 0x26, 0x2E, 0x32,
                                                                                         0x36) for i in range(4)} \
        | {ball + 0x2C, ball + 0x2D}
    w = [x for x in _frame(uc, writes, hk) if x[0] not in allowed]
    if w:
        errs.append(f'forcing frame: writes outside PR_WORK / the ball / lastTeamPlayed {[hex(a) for a, _ in w[:4]]}')
    rd = lambda a, n: bytes(uc.mem_read(a, n))
    if rd(B2 + g['GT_O'], 4) != bytes(4):
        errs.append(f"gameTime {rd(B2 + g['GT_O'], 4).hex()} (want held at 0)")
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


REF = os.environ.get('HT_PRACTICE_REF') or os.path.join(HOME, 'swos-mod', 'c', 'RELpr5', 'SWOS', 'ITALIAN.EXE')
# (15/11 pr_rbar's reference: an exe with step 3's sites but not the score bar hook - 42-int 1856968's release build)
REF_RBAR = os.environ.get('HT_PRACTICE_RBAR_REF') or os.path.join(HOME, 'swos-mod', 'c', 'REL42i53', 'SWOS',
                                                                    'ITALIAN.EXE')


def _run_site(exe, site, n, skip, kind=None):
    """obj1+site run with practice off (PR_KIND 0: a zeroed .bss) until the first instruction outside the site's n bytes
    and the `skip` range (the practice band): (that instruction's address, the return address on the stack, the writes
    outside the stack as {address: bytes})"""
    from emu import relocate
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP
    i1, i2, le = relocate(exe, B1, B2, base4=B4)
    uc, writes = _machine((i1, i2, le.img4))
    if kind is not None:                    # (PR_KIND set: the PRWK tag's PR_WORK pointer in the relocated band)
        import practice
        import swreg
        band = le.img4[swreg.PRACTICE_AT:swreg.PRACTICE_END]
        k = band.find(practice.TAG.encode())
        uc.mem_write(struct.unpack_from('<I', band, k + 4)[0] + practice.WK['KIND'], bytes([kind]))
    out = []

    def hook(u, a, sz, d):
        if not (B1 + site <= a < B1 + site + n or skip[0] <= a < skip[1]):
            out.append((a, struct.unpack('<I', bytes(u.mem_read(u.reg_read(UC_X86_REG_ESP), 4)))[0]))
            u.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(UC_X86_REG_ESP, STACK)
    uc.emu_start(B1 + site, B1 + site + n, count=10_000)
    w = {}
    for a, k in writes:
        if not STACK - 0x1000 <= a < STACK + 16:
            w[a] = bytes(uc.mem_read(a, k))
    img = {B1: i1, B4: le.img4}
    pc, ret = out[0] if out else (B1 + site + n, None)     # (no instruction outside: the site's end reached)
    while ret is not None and ret < B1 + len(i1) and i1[ret - B1] == 0x90:     # (the branch's nop padding)
        ret += 1
    code = None
    if pc is not None:
        base = B1 if pc < B2 else B4
        code = bytes(img[base][pc - base:pc - base + 48])
    return pc, ret, w, code


def test_practice_off_sites():
    """MC 15/11 (step 3's obj1 sites): with practice off, ShowPlayMatchMenu's call pr_pmm and UpdateTime's call
    pr_time (and 15/11 the restart's call pr_rbar) reach the very code the exe without them runs (HT_PRACTICE_REF, else c/RELpr5: 4.2 with practice step 2):
    the same next instruction (kitcolors' pm_show chain / InitDisplaySprites) and its 48 code bytes, the same return
    address, the same writes ([A6] = playMatchMenu / currentTimeSprite.visible = 1) - nothing else."""
    for f in (EXE, REF, REF_RBAR, ORIG):
        if not os.path.exists(f):
            return False, f'{f} missing'
    import lepatch
    import practice
    import bteam
    import swreg
    o = lepatch.LEPatch(ORIG)
    pm = practice.pm_site(o, bteam.ui_sites(o)['a6'])[0]
    tm = practice.time_site(o)[0]
    rb, rtim = practice.rbar_site(o)
    band = (B4 + swreg.PRACTICE_AT, B4 + swreg.PRACTICE_END)
    errs, info = [], []
    for name, site, n, rf in (('ShowPlayMatchMenu', pm, 15, REF), ('UpdateTime', tm, 14, REF),
                              ('restart score bar', rb, 9, REF_RBAR)):
        new = _run_site(EXE, site, n, band)
        ref = _run_site(rf, site, n, (0, 0))
        if new[0] is None or new != ref:
            errs.append(f'{name} obj1+{site:#x}: practice off {new[:3]} vs the reference {ref[:3]}'
                        + ('' if new[3] == ref[3] else ' (code differs)'))
        else:
            info.append(f'{name} obj1+{site:#x} -> {new[0]:#x} (ret {new[1] and hex(new[1])}, writes '
                        f'{ {hex(a): v.hex() for a, v in new[2].items()} })')
    on = _run_site(EXE, rb, 9, band, kind=3)                # (Davide 15/11: a practice - CORNER - no score bar)
    if on[0] != B1 + rb + 9 or on[2]:
        errs.append(f'restart score bar, PR_KIND 3: next {on[0] and hex(on[0])} (want {B1 + rb + 9:#x}), writes '
                    f'{ {hex(a): v.hex() for a, v in on[2].items()} } (want none)')
    else:
        info.append(f'PR_KIND 3: obj1+{rb:#x} -> its retn, nothing written (resultTimer obj2+{rtim:#x} untouched)')
    return not errs, '; '.join(errs) or 'practice off = the exe without the sites: ' + '; '.join(info)
