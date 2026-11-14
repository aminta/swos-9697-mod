"""4.2 S2 knockouts (MC 14/11, 42-cdkn): gplay.c's cd_make with cdkn.c (the engine's sr_kn) behind GP_CDKN, built natively.
Random later seasons of a 9 x 18 Serie D (CD_DT one run, the arrivals / places in CD_ST.ent as cd_season leaves them):
- dormant: GP_CDKN = 0 -> CD_ST's gen / np byte-equal to the reference gplay.c (today's file with 42-cdkn's hunk taken
  out) over 2000 seasons; the reference's object (the exe's flags) = gplay.c before 42-cdkn;
- on: every season drawn by the engine (CDKN_OK, no log entry); the bracket's invariants: every Serie D club once (2p in the
  preliminary, the rest at round 1: a bye), each preliminary tie's winner once in round 1 (CD_REF); the preliminary =
  the arrivals, then the lowest placed (PLACE_DESC: 200 - ent), unknown last; neighbours meet (round 0: most ties in
  one girone, none across the country); control: the old cd_make fails the bracket equality;
- fallback (never silent): CDKN_TFALL = 1 and a shape the form cannot express (128 clubs: no preliminary) -> gen / np =
  the dormant run's, CDKN_LOG = season << 8 | reason (9 / 1), CDKN_NLOG counts."""
import ctypes
import os
import random
import re
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, TOOLS)
FLAGS = ['-DGP_S7=0', '-DSS_NB=1', '-DGP_FORCE=0', '-DGP_SPST=0', '-DGP_SPGRP=0', '-DGP_SPPRE=0', '-DGP_SPMAGIC=0',
         '-DGP_DATA_SECTION=', '-DGP_CD2=0']
G, SZ, LF, NR = 9, 18, 144, 8                          # (9 gironi of 18, the Serie D file, 8 rounds: n1 = 64)
ENT, EFRESH, GENON, NP, GEN = 348, 604, 605, 606, 612   # (struct cd_state offsets: the scenario's)
DECL = re.compile(r'#ifndef GP_DATA_SECTION\n#define GP_DATA_SECTION [^\n]*\n#endif\n/\* 4\.2 S2 knockouts \(MC 14/11, 42-cdkn\).*?int n\) GP_DATA_SECTION;\n', re.S)
HOOK = re.compile(r'    if \(GP_CDKN && GP_CDKN\(ord, grp, key, n\)\) return;[^\n]*\n[^\n]*\n')


def _build(d, name, gsrc, with_cdkn):
    wrap = os.path.join(d, name + '.c')
    open(wrap, 'w').write('#include <stdint.h>\n' + gsrc + ('\nunsigned char CDKN_WORK[0x4400] __attribute__((aligned(16)));\n'
                                                            'void t_wire(int on) { extern int cdkn_make(); GP_CDKN = on ? (void *)cdkn_make : 0; }\n'
                                                            if with_cdkn else ''))
    lib = os.path.join(d, name + '.dylib')
    srcs = [wrap] + ([os.path.join(TOOLS, 'cdkn.c')] if with_cdkn else [])
    cmd = ['cc', '-shared', '-fPIC', '-O1', '-w', '-I', TOOLS, '-DDATA='] + FLAGS + ['-o', lib] + srcs
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        und = sorted(set(re.findall(r'"_(\w+)", referenced from', r.stderr)))
        if not und:
            raise RuntimeError(r.stderr[-600:])
        stub = os.path.join(d, name + '_stub.c')
        open(stub, 'w').write(''.join(f'unsigned char {n}[65536];\n' for n in und))
        r = subprocess.run(cmd + [stub], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[-600:])
    return ctypes.CDLL(lib)


class Season:
    """One later season's inputs: girone of each of the 162 ordinals, ent per ordinal (1 arrival, 2 + place from the
    bottom, 40h unknown)."""
    def __init__(self, seed, n=162):
        r = random.Random(seed)
        self.seas = 2 + seed % 200
        self.n = n
        self.grp = [i * G // n for i in range(n)]           # (ordinal i in girone grp[i])
        self.ent = [0] * 256
        for i in range(n):
            x = r.random()
            self.ent[i] = 1 if x < 0.17 else 0x40 if x < 0.20 else 2 + r.randrange(SZ)


def _run(L, s, tfall=0):
    dt = bytes((5, G)) + struct.pack('<H', 0) + bytes([5 + s.grp[i] if i < s.n else 0xFF for i in range(256)])
    cdt = bytearray(4 + 8 * NR)
    cdt[0], cdt[1], cdt[2] = 5, NR, LF
    for r in range(NR):
        cdt[4 + 8 * r] = 60                               # (every round's week far ahead: cd_step_c stops after cd_make)
    bufs = {'GP_CDT': ctypes.create_string_buffer(bytes(cdt), len(cdt)), 'GP_CDD': ctypes.create_string_buffer(dt, len(dt)),
            'GP_SLT': ctypes.create_string_buffer(bytes(2400), 2400)}
    for k, b in bufs.items():
        ctypes.c_void_p.in_dll(L, k).value = ctypes.addressof(b)
    ctypes.c_uint8.in_dll(L, 'GP_SEAS').value = s.seas
    ctypes.c_uint32.in_dll(L, 'GP_WK').value = 0
    ctypes.c_uint32.in_dll(L, 'GP_CDFIRST').value = 0
    st = (ctypes.c_uint8 * 1032).in_dll(L, 'CD_ST')
    for i in range(1032):
        st[i] = 0
    st[0], st[1] = 0x43, 0x44                              # (magic 'CD', another season: cd_step_c's new-season branch)
    st[2] = (s.seas + 1) & 0xFF
    for i in range(256):
        st[ENT + i] = s.ent[i]
    st[EFRESH] = 1
    if hasattr(L, 't_wire'):
        ctypes.c_uint8.in_dll(L, 'CDKN_TFALL').value = tfall
    L.cd_step_c.restype = ctypes.c_uint32
    L.cd_step_c()
    b = bytes(st)
    np_ = b[NP]
    return b[GENON], np_, struct.unpack_from(f'<{2 * (41 + 64)}H', b, GEN)


def _check_bracket(s, np_, gen):
    """The invariants of an engine draw; [] = all hold."""
    e = []
    n1 = 64
    p = s.n - 2 * n1
    if np_ != p:
        return [f'np {np_} != {p}']
    pre = [w >> 8 for w in gen[:2 * p]]
    r1 = gen[2 * p:2 * (p + n1)]
    refs = sorted(w >> 8 for w in r1 if w & 0xFF == 0xFF)
    clubs = [w >> 8 for w in r1 if w & 0xFF == LF]
    if refs != list(range(p)):
        e.append(f'round 1 refs {refs[:6]}..')
    if sorted(pre + clubs) != list(range(s.n)):
        e.append('not every club once')
    key = lambda i: (0 if s.ent[i] == 1 else 1, -(200 - s.ent[i]) if 2 <= s.ent[i] < 0x40 else 0, s.ent[i] == 0x40)
    worst_in = max(key(i) for i in pre)
    best_out = min(key(i) for i in clubs)
    if worst_in[:2] > best_out[:2] and not (worst_in[2] and best_out[2]):
        e.append(f'preliminary not the arrivals then the lowest placed ({worst_in} > {best_out})')
    same = sum(s.grp[gen[2 * t] >> 8] == s.grp[gen[2 * t + 1] >> 8] for t in range(p))
    far = [t for t in range(p) if abs(s.grp[gen[2 * t] >> 8] - s.grp[gen[2 * t + 1] >> 8]) > 4]
    if same * 2 < p or far:
        e.append(f'round 0 not neighbours: {same}/{p} in one girone, far {far[:4]}')
    return e


def test_cdkn():
    errs, notes = [], []
    gsrc = open(os.path.join(TOOLS, 'gplay.c')).read()
    ref = gsrc
    for a, b in ((HOOK, ''), (DECL, '')):
        ref = a.sub(b, ref, count=1)
    if ref.count('GP_CDKN') or gsrc.count('GP_CDKN') < 2:
        return False, 'the reference gplay.c still has GP_CDKN (the hunk pattern moved)'
    d = tempfile.mkdtemp(prefix='cdkn')
    git = subprocess.run(['git', '-C', TOOLS, 'show', '447be28:tools/gplay.c'], capture_output=True, text=True).stdout
    notes.append('reference = 447be28\'s gplay.c' if ref == git else '(reference = today\'s gplay.c less the 42-cdkn hunks)')
    Lref = _build(d, 'ref', ref, False)
    L = _build(d, 'new', gsrc, True)
    # dormant
    L.t_wire(0)
    bad = 0
    for k in range(2000):
        s = Season(k)
        a, b = _run(Lref, s), _run(L, s)
        bad += a != b
    check = lambda c, m: c or errs.append(m)
    check(not bad, f'dormant: {bad} of 2000 seasons differ from the reference')
    notes.append(f'dormant 2000 seasons equal' if not bad else f'dormant {bad} differ')
    # on
    import cdkn
    ctr = (ctypes.c_int16 * 32).in_dll(L, 'CDKN_CTR')
    for i, (la, lo) in enumerate(cdkn.CENTRES):
        ctr[2 * i], ctr[2 * i + 1] = la, lo
    ctypes.c_uint8.in_dll(L, 'CDKN_NCTR').value = len(cdkn.CENTRES)
    L.t_wire(1)
    nlog = ctypes.c_uint32.in_dll(L, 'CDKN_NLOG')
    okc = ctypes.c_uint32.in_dll(L, 'CDKN_OK')
    nlog.value = okc.value = 0
    bad, ex, oldbad = 0, None, 0
    for k in range(2000):
        s = Season(k)
        on, np_, gen = _run(L, s)
        e = _check_bracket(s, np_, gen) if on else ['gen_on 0']
        if e:
            bad += 1
            ex = ex or (k, e)
        if k < 200:
            _, onp, ogen = _run(Lref, s)
            oldbad += _check_bracket(s, onp, ogen) == [] and ogen == gen
    check(not bad and okc.value == 2000 and nlog.value == 0,
          f'on: {bad} seasons break the invariants (first {ex}), OK {okc.value}, log {nlog.value}')
    check(oldbad == 0, f'control: the old cd_make gave the engine\'s bracket in {oldbad} of 200 seasons')
    notes.append(f'on: 2000 seasons by the engine (OK {okc.value}, log {nlog.value}); control: old cd_make differs')
    # fallback: forced, and a shape with no preliminary
    for tf, s, why in ((1, Season(7), 9), (0, Season(8, n=128), 1)):
        n0 = nlog.value
        a = _run(L, s, tfall=tf)
        L.t_wire(0)
        b = _run(L, s)
        L.t_wire(1)
        lg = (ctypes.c_uint32 * 8).in_dll(L, 'CDKN_LOG')[n0 & 7]
        check(a == b and nlog.value == n0 + 1 and lg == (s.seas << 8 | why),
              f'fallback {why}: gen equal {a == b}, log {nlog.value - n0} entry {lg:#x} (want {s.seas << 8 | why:#x})')
    notes.append('fallback: TFALL (9) and 128 clubs (1) logged, gen = today\'s')
    return not errs, '; '.join(errs) or '; '.join(notes)
