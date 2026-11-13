"""4.2 S7 WSITES K keys (MC 13/11): saved states KEYED over team words are not WSITES rows - after a season's swaps the key
no longer matches, the consumer DISCARDS the state and rebuilds it (never a trap, never a wrong display). One test per key,
each poking a mismatch into the exe's own code (HT_S7_EXE, else c/S7W-p6: a shaped IT build with HOSTTEST_SYMS=1):

- test_k_f1 (F1_ST.key = the first team word of the league's DIY list): f1_valid / f1_auto / f1_build return 0 on a
  different first word (no overlay: the table is shown as the game has it), f1_capture rewrites the state under the new key
  and the three accept it again."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_registry as tr  # noqa: E402
import test_s7swap as t7  # noqa: E402
import test_swc1 as ts  # noqa: E402

EXE = t7.EXE
DIY = ts.BUF + 0x2000                                   # (a DIY league buffer stand-in: 0x600 bytes)
SEASON = 9


def _diy(m, first, n=4, played=3):
    b = bytearray(0x600)
    struct.pack_into('<H', b, 0x31, n)
    for i in range(n):
        struct.pack_into('<H', b, 0x12D + 2 * i, first + (i << 8) if i else first)      # (the list: words)
        struct.pack_into('<H', b, 0x6D + 2 * i, 18 * i)                                  # (place i -> row offset)
        struct.pack_into('<H', b, 0x2B3 + 18 * i + 4, played)                            # (played)
    m.w(DIY, bytes(b))


def test_k_f1():
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    if 'f1_valid' not in sy.get('gplay', {}):
        return True, f'SKIP: {EXE}: no F1 (gplay.f1_valid)'
    m = t7.M(EXE)
    errs = []
    mgr = 0x0166
    _diy(m, 0x0166)
    m.call('gplay', 'f1_capture', DIY, SEASON, mgr)
    ok1 = [m.call('gplay', k, DIY, SEASON) for k in ('f1_valid', 'f1_auto')]
    if ok1 != [1, 1]:
        errs.append(f'capture: f1_valid / f1_auto {ok1}, want 1 1')
    _diy(m, 0x0266)                                     # (a crossed club first in the list now: another key)
    bad = [m.call('gplay', k, DIY, SEASON) for k in ('f1_valid', 'f1_auto', 'f1_build')]
    if bad != [0, 0, 0]:
        errs.append(f'mismatched key: f1_valid / f1_auto / f1_build {bad}, want 0 0 0 (discard)')
    if m.call('gplay', 'f1_capture', DIY, SEASON, 0x0266) is not None:
        pass
    ok2 = [m.call('gplay', k, DIY, SEASON) for k in ('f1_valid', 'f1_auto')]
    if ok2 != [1, 1]:
        errs.append(f'rebuilt (f1_capture): f1_valid / f1_auto {ok2}, want 1 1')
    return not errs, '; '.join(errs) or ('F1_ST: a different first team word -> f1_valid / f1_auto / f1_build 0 (no overlay, no '
                                         'trap); f1_capture rewrites it under the new key and they accept again')


def test_k_unconsumed():
    """ST and SS have no consumer of their key in the shaped build (audit, MC 13/11): sr_st_check / sr_st_begin are linked
    nowhere in tools/ (the 'ST' item is only a ledger reservation) and the default gplay build has SS_NB == 1 (ss_set a
    no-op, ss_view ignoring the key). This pins it: a build that starts consuming either must come with its own test
    (and a decision: re-key, or discard-on-mismatch with a poked mismatch), so it fails here until it does."""
    if not os.path.exists(EXE) or not os.path.exists(EXE[:-4] + '.syms.json'):
        return True, f'SKIP: {EXE} (a shaped HOSTTEST_SYMS=1 build) missing'
    sy = json.load(open(EXE[:-4] + '.syms.json'))
    have = [(m, k) for m in sy for k in sy[m] if k in ('sr_st_check', 'sr_st_begin', 'sr_st_group', 'sr_st_record',
                                                       'ss_view', 'ss_set')]
    return not have, (f'a consumer appeared: {have} (needs its own K test)' if have else
                      'no sr_st_* / ss_set / ss_view in the exe: ST and SS keys unconsumed')
