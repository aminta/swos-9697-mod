"""4.2 S7 / bteam (Panchina 13/11, the S7 audit's 'bteam: BAGE by [SEL]'; MC rule: identity data by the HOME word):
bt_team (bteam.py) finds a club's B team row in DATA\\BAGE.nnn, whose parent words are the shipped (home) ones. After a
season-end swap a club that crossed sits at another word; bt_team maps the word it is given through s7swap.c's
s7_home_word (ripool's S7_HPTR) first. On HT_BT_EXE (else c/S7W-ws4c: a shaped IT build - the S7 test pack - with
HOSTTEST_SYMS=1), the registry after test_s7swap's 9 swaps, a poked BAGE buffer {row0: parent = a crosser's home word,
row1: parent = a club that stays}:
- bt_team(the crosser's NEW word) = row0 (found through its home word); the crosser's OLD word (now another club's) = no
  row; a staying club's word = row1; a word of no registry club (0, FFFFh, another file) = itself, no row;
- before the swaps (no crossing): the same lookups by the shipped word hit the same rows (no change for an uncrossed club);
- S7_HPTR = 0 (a build/state without the helper): the word itself (a plain lookup)."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_s7swap as t7  # noqa: E402
import test_registry as tr  # noqa: E402
import test_swc1 as ts  # noqa: E402

HOME = os.path.expanduser('~')
EXE = os.environ.get('HT_BT_EXE') or os.path.join(HOME, 'swos-mod', 'c', 'S7W-ws4c', 'SWOS', 'ITALIAN.EXE')


def test_bteam_s7():
    import json
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (shaped, HOSTTEST_SYMS=1) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'S7_HPTR' not in sy.get('ripool', {}) or 'bt_team' not in sy.get('bteam', {}):
        return False, f'{EXE}: no S7_HPTR / bt_team in the syms (S7 + XTRA + B teams build)'
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESI
    m = t7.M(EXE)
    errs = []
    m.fresh()
    fs, word, at, rdiv, rows = t7.reg_parse(m.regb())
    down, up = t7.crossings(fs, m.gb)
    cross, stay = down[0][1], t7.FA | 10 << 8
    b3 = lambda k: tr.B3 + sy['bteam'][k][1]          # (asm labels of the obj3 modules: bare obj3 offsets)
    buf = b3('btbuf')
    rowsb = b''.join(struct.pack('<HHBB', b, par, 0, 0) for b, par in ((0x1111, cross), (0x2222, stay)))
    m.w(buf, b'\0\0\0' + bytes([2]) + rowsb)
    r0, r1 = buf + 4, buf + 4 + 6

    def team(w):
        ts._run(m.uc, b3('bt_team'), tr.RET, {UC_X86_REG_EAX: w})
        return m.uc.reg_read(UC_X86_REG_ESI)
    hp = m.at('ripool', 'S7_HPTR')
    if not struct.unpack('<I', m.rd(hp, 4))[0]:
        return False, 'S7_HPTR not bound to s7_home_word in the image'
    for w, want, why in ((cross, r0, 'before: the crosser'), (stay, r1, 'before: the staying club')):
        if team(w) != want:
            errs.append(f'{why}: {team(w):#x} (want {want:#x})')
    stt, nsw, ncr, slt = t7.run(m, down, up)
    if stt != t7.OK:
        return False, f'season status {stt}'
    fs1, word1, _, _, _ = t7.reg_parse(m.regb())
    ident = {w: i for i, w in enumerate(word)}
    new = word1[ident[cross]]
    if new == cross:
        errs.append('the crosser did not move')
    else:
        got = team(new)
        if got != r0:
            errs.append(f'the crosser at its new word {new:#x}: {got:#x} (want row0 {r0:#x})')
    if team(cross) != 0:                                # (its old word now holds the club that took its row)
        errs.append(f'the crosser\'s old word {cross:#x} found a row ({team(cross):#x}): looked up by the CURRENT word')
    if team(stay) != r1:
        errs.append(f'the staying club after the swaps: {team(stay):#x} (want {r1:#x})')
    for w in (0, 0xFFFF, 0x3F00 | 0x55):
        if team(w) != 0:
            errs.append(f'word {w:#x} (no registry club) found a row')
    saved = m.rd(hp, 4)                                 # no helper: a plain lookup by the word given
    m.w(hp, b'\0\0\0\0')
    if team(cross) != r0 or team(new) != 0:
        errs.append('S7_HPTR = 0: not a plain lookup')
    m.w(hp, saved)
    return not errs, '; '.join(errs[:5]) or ('bt_team: a crosser found by its new word through its home word, not by '
                                             'its old one; staying club, unknown words and S7_HPTR = 0 as a plain lookup')
