"""4.2 rc4 (MC 21/11, world_gplay_cupd2; Shaved's reading of the S7 path): gplay.c cd_rank at the Serie D file's league
end, built natively with GP_CD2=1 (S7 data). The Serie D file (144) is its own league struct: GP_IN holds its 9 groups
at LOCAL divisions 0..8, while CD_DT's head says df 5, dc 9 (the pack's numbering). Every group's clubs must be ranked
(CD_ST.ent[row] = 2 + place from the bottom, nrk = 162); pool rows (team FFFFh) and another file's rows are not.
Red twin: 173127a's cd_rank (pack numbering) ranks only local 5..8 = 72 clubs, groups A..E stay 0."""
import ctypes
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_cdkn as tk  # noqa: E402

TOOLS = tk.TOOLS
ENT, RANKED, NRK = 348, 609, 610                        # (struct cd_state offsets, as test_cdkn's)
LF, G, SZ = 144, 9, 18


def _lib(d, name, gsrc):
    gsrc += '\nvoid t_cdrank(void) { cd_rank(); }\n'
    old = tk.FLAGS
    tk.FLAGS = [f for f in old if not f.startswith('-DGP_CD2')] + ['-DGP_CD2=1']
    try:
        return tk._build(d, name, gsrc, False)
    finally:
        tk.FLAGS = old


def _run(L):
    cdt = bytes([0, 8, LF, 0]) + bytes(64)
    dt = bytes([5, 9]) + (192).to_bytes(2, 'little') + (2283).to_bytes(2, 'little') + (156).to_bytes(2, 'little') \
        + bytes(512)
    keep = {'GP_CDT': ctypes.create_string_buffer(cdt, len(cdt)), 'GP_CDD': ctypes.create_string_buffer(dt, len(dt))}
    for k, b in keep.items():
        ctypes.c_void_p.in_dll(L, k).value = ctypes.addressof(b)
    gin = (ctypes.c_uint8 * 22).in_dll(L, 'GP_IN')
    base = ctypes.addressof(gin)
    ctypes.memset(base, 0, 22 + 16 * 32 * 12)
    gin[0] = G
    want = {}
    for d in range(G):
        rows = SZ + (1 if d == 0 else 0)                # (group A: + one pool club, FFFFh, not ranked)
        gin[4 + d] = rows
        for k in range(rows):
            team = 0xFFFF if k == SZ else LF | (d * SZ + k) << 8
            ctypes.c_uint16.from_address(base + 22 + (d * 32 + k) * 12).value = team
            if team != 0xFFFF:
                want[d * SZ + k] = 2 + (rows - 1 - k)
    gin[4 + 9] = 2                                      # (a division of another file: never ranked)
    for k in range(2):
        ctypes.c_uint16.from_address(base + 22 + (9 * 32 + k) * 12).value = 102 | (200 + k) << 8
    st = (ctypes.c_uint8 * 1032).in_dll(L, 'CD_ST')
    for i in range(1032):
        st[i] = 0
    L.t_cdrank()
    got = {i: st[ENT + i] for i in range(256) if st[ENT + i]}
    return got, want, st[NRK], st[RANKED]


def test_cdrank_s7():
    src = open(os.path.join(TOOLS, 'gplay.c')).read()
    if 'df = 0; dc = GD;' not in src:
        return False, 'gplay.c: no rc4 cd_rank fix (GP_CD2: every captured division)'
    try:
        old = subprocess.run(['git', '-C', TOOLS, 'show', '173127a:tools/gplay.c'], capture_output=True,
                             text=True, check=True).stdout
    except Exception as e:
        return True, f'SKIP: no 173127a in this repo ({e})'
    with tempfile.TemporaryDirectory() as d:
        got, want, nrk, ranked = _run(_lib(d, 'cdr_new', src))
        bad = []
        if got != want or nrk != 162 or ranked != 1:
            miss = sorted(set(want) - set(got))
            bad.append(f'fix: {len(got)} rows ranked (want 162), nrk {nrk}, ranked {ranked}, missing rows '
                       f'{miss[:8]}{"..." if len(miss) > 8 else ""}, wrong '
                       f'{[(i, got[i], want.get(i)) for i in got if got[i] != want.get(i)][:5]}')
        got0, _, nrk0, _ = _run(_lib(d, 'cdr_old', old))
        if len(got0) != 72 or nrk0 != 72:
            bad.append(f'red twin (173127a): {len(got0)} rows ranked, nrk {nrk0} (want 72: local 5..8 only)')
    return not bad, '; '.join(bad) or 'S7: 9 local groups -> 162 ranked (pool + other file skipped); red twin 173127a: 72'
