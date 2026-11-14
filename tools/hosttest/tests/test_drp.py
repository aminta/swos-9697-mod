"""42-drp DRIBBLING PERSONALIZZATO (difficulty.py dp_build / df_blk, buildup.py bu_opp) in Unicorn, every language.
- dp_fmt: every value row at every step: its 'step/max' text.
- dp_build: for every row at every step (the others at their defaults) and mixed settings, BLK_CU / BLK_CO = BLK_U /
  BLK_O with the rows' values at their fields (the host model below); the default settings = BLK_U / BLK_O exactly.
- df_blk with DRIBBLING 2: the human's side BLK_CU, the opposition BLK_CO, every other pairing BLK_N; with 0 / 1 as
  before (BLK_N; BLK_U / BLK_O).
- bu_opp: DRIBBLING 2 acts on the opposition only while the CPU BUILD UP row is ON (DP_K[7] 0).
Exes built here with DIFF_TEST=3 (the beta's shape) - labels from the in-process build."""
import itertools
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_difficulty as td                                    # noqa: E402

RET = 0x1D00000


def _build(lang):
    import patch
    import buildup
    import difficulty
    out = tempfile.mkdtemp(prefix=f'drp_{lang}_')
    os.makedirs(os.path.join(out, 'DATA'))
    keep = {k: os.environ.get(k) for k in ('DIFF_TEST', 'DIFF_DRIB', 'MODVER_TAG', 'DIFF_MARGIN_BETA')}
    os.environ.update(DIFF_TEST='3', MODVER_TAG='DRIBBLING TEST', DIFF_MARGIN_BETA='384')   # (the beta's recipe)
    os.environ.pop('DIFF_DRIB', None)
    try:
        r = patch.patch_teams(os.path.join(td.ORIG, 'DATA/TEAM.020'), os.path.join(out, 'DATA/TEAM.020'))
        patch.write_new_teams(os.path.join(td.ORIG, 'DATA'), os.path.join(out, 'DATA'))
        patch.patch_exe(os.path.join(td.ORIG, f'{td.LANGS[lang]}.EXE'), os.path.join(out, 'ITALIAN.EXE'), r, lang)
    finally:
        for k, v in keep.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    return os.path.join(out, 'ITALIAN.EXE'), dict(difficulty.LABELS), dict(buildup.LABELS)


def model(k):
    """DP_K -> (BLK_CU, BLK_CO) bytes."""
    import difficulty as df
    cu, co = bytearray(df._blk(df.USER)), bytearray(df._blk(df.OPP))
    for i, (_, blk, field, size, vals) in enumerate(df.DP_ROWS):
        if blk:
            struct.pack_into('<I' if size == 4 else '<H', cu if blk == 'U' else co, field, vals[k[i]])
    return bytes(cu), bytes(co)


def _call(uc, at, ebx=0):
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS, UC_X86_REG_EBX
    uc.reg_write(UC_X86_REG_ESP, td.STACK - 4)
    uc.mem_write(td.STACK - 4, struct.pack('<I', RET))
    uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
    uc.reg_write(UC_X86_REG_EBX, ebx)
    uc.emu_start(at, RET, count=5000)
    return uc.reg_read(UC_X86_REG_EBX), uc.reg_read(UC_X86_REG_EFLAGS)


def test_drp():
    import difficulty as df
    import lepatch
    errs, n = [], 0
    nr = len(df.DP_ROWS)
    sets = [list(df.DP_DEFAULT)]
    for i, r in enumerate(df.DP_ROWS):
        for st in range(len(r[4])):
            k = list(df.DP_DEFAULT)
            k[i] = st
            sets.append(k)
    sets += [[2, 2, 2, 2, 2, 2, 1, 1, 1], [0] * 9, [0, 2, 1, 2, 0, 1, 1, 0, 0], [2, 0, 2, 0, 2, 0, 0, 1, 1],
             [len(r[4]) - 1 for r in df.DP_ROWS], [len(r[4]) // 2 for r in df.DP_ROWS]]
    for lang, name in td.LANGS.items():
        p = lepatch.LEPatch(os.path.join(td.ORIG, f'{name}.EXE'))
        s, sym = df.find(p)
        exe, ld, lb = _build(lang)
        un, sn, b2n, B4 = td._load(exe)
        a4 = lambda k: B4 + k
        un.mem_write(0, sn)
        u0, o0 = bytes(un.mem_read(a4(ld['BLK_U']), 32)), bytes(un.mem_read(a4(ld['BLK_O']), 32))
        for k in sets:
            un.mem_write(0, sn)
            un.mem_write(a4(ld['DP_K']), struct.pack(f'<{nr}H', *k))
            _call(un, a4(ld['dp_build']))
            n += 1
            cu, co = bytes(un.mem_read(a4(ld['BLK_CU']), 32)), bytes(un.mem_read(a4(ld['BLK_CO']), 32))
            if (cu, co) != model(k):
                errs.append(f'{lang} dp_build {k}: CU {cu.hex()} CO {co.hex()}, want {model(k)[0].hex()} / '
                            f'{model(k)[1].hex()}')
            if k == list(df.DP_DEFAULT) and (cu, co) != (u0, o0):
                errs.append(f'{lang} dp_build defaults: not BLK_U / BLK_O')
        # dp_fmt: every value row at every step -> DP_S + 6 * row = 'step/max' (0 = CLASSICO)
        for row in range(df.DP_NNUM):
            for st in range(len(df.DP_ROWS[row][4])):
                un.mem_write(0, sn)
                un.mem_write(a4(ld['DP_K']) + 2 * row, struct.pack('<H', st))
                _call(un, a4(ld['dp_fmt']), row)
                n += 1
                want = f'{st}/{len(df.DP_ROWS[row][4]) - 1}'.encode() + b'\0'
                got = bytes(un.mem_read(a4(ld['DP_S']) + 6 * row, len(want)))
                if got != want:
                    errs.append(f'{lang} dp_fmt row {row} step {st}: {got!r}, want {want!r}')
        # df_blk / bu_opp: (pa, pb) controls of TA / TB; ebx = TA or TB
        for (pa, pb), team, dact, mix in itertools.product(((1, 0), (1, 1), (0, 0)), (td.TA, td.TB), (0, 1, 2),
                                                           (0, 1)):
            un.mem_write(0, sn)
            td._setup(un, sym, dict(pa=pa, pb=pb, a6=team), b2n)
            un.mem_write(a4(ld['DF_DACT']), bytes([dact]))
            k = list(df.DP_DEFAULT)
            k[nr - 1] = mix
            un.mem_write(a4(ld['DP_K']), struct.pack(f'<{nr}H', *k))
            side = None if (pa, pb) != (1, 0) else ('U' if team == td.TA else 'O')
            want = {None: 'BLK_N', 'U': ('BLK_N', 'BLK_U', 'BLK_CU')[dact], 'O': ('BLK_N', 'BLK_O', 'BLK_CO')[dact]}[side]
            got, _ = _call(un, a4(ld['df_blk']), team)
            n += 1
            if got != a4(ld[want]):
                errs.append(f'{lang} df_blk pa {pa} pb {pb} team {"TB" if team == td.TB else "TA"} DF_DACT {dact}: '
                            f'{got:#x}, want {want}')
            _, fl = _call(un, a4(lb['bu_opp']))
            act = bool(fl & 0x40)
            want_act = side == 'O' and dact != 0 and not (dact == 2 and mix)
            n += 1
            if act != want_act:
                errs.append(f'{lang} bu_opp pa {pa} pb {pb} DF_DACT {dact} mix {mix}: acts {act}, want {want_act}')
        # the 'DF' byte: df_load (DF_SV) -> DF_W / DF_DR, then df_pack back into DF_SV / DF_SH
        for v in range(64):
            un.mem_write(0, sn)
            un.mem_write(a4(ld['DF_SV']), bytes([v]))
            _call(un, a4(ld['df_load']))
            n += 1
            w = struct.unpack('<H', bytes(un.mem_read(a4(ld['DF_W']), 2)))[0]
            dr = struct.unpack('<H', bytes(un.mem_read(a4(ld['DF_DR']), 2)))[0]
            sv, sh = bytes(un.mem_read(a4(ld['DF_SV']), 1))[0], bytes(un.mem_read(a4(ld['DF_SH']), 1))[0]
            ww = v & 15 if v & 15 <= 4 else 0
            wd = (v >> 4) & 3 if (v >> 4) & 3 <= 2 else 0
            if (w, dr, sv, sh) != (ww, wd, ww | wd << 4, ww | wd << 4):
                errs.append(f'{lang} df_load {v:#x}: W {w} DR {dr} SV {sv:#x} SH {sh:#x}, want {ww} {wd}')
    return not errs, '; '.join(errs[:10]) + (f' (+{len(errs) - 10})' if len(errs) > 10 else '') or \
        f'4 languages, {n} cases: dp_build = the host model (defaults = BLK_U / BLK_O), dp_fmt texts, df_blk and bu_opp per DRIBBLING'


if __name__ == '__main__':
    ok, msg = test_drp()
    print('PASS' if ok else 'FAIL', msg)
