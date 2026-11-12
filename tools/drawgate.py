"""4.2 AFC mode: the build's group-draw gate (MC 11/11, option 2 + proposal b; CONVENTIONS 14a: always on, never a
switch). For every conti group stage drawn with an association rule (conti.c draw_groups -> ctdraw.c ct_place, ED_S):

- its reachable association multisets, from draw_bound's fixed point (conti.BOUND_CNT: each association's most clubs
  in the round, its direct places): EXHAUSTIVE when the round has <= 4096 of them; above that the SATURATED ones
  (associations at their bound, in up to 4096 orders - every association with a bound reaches it in at least one,
  else the gate refuses) + 4096 RANDOM ones (a fixed seed);
- per multiset 1024 seeds through ct_place natively (ctdraw.c ct_gate, conti's native library): the first <= 64 the
  game's own (the edition rng at that round over 64 native seasons: CT_PSEED), the rest an LCG; each seed its own
  seeding order. FAIL: a budget hit (sr_gdraw_hits) or a refusal;
- per multiset the seed with the most library steps replayed under Unicorn on ctband.c as the exe compiles it
  (cobj flags, cobj.link; the engine's C stack stubbed to a direct call): <= 20 M i486 instructions, else FAIL.

A FAIL names the pack (confederation), cup, round, multiset and seed, and fails the build. The result is cached by
content in internal/drawgate/<key>.json, key = sha1 of the gate's inputs (every round's rule / groups / size / region
flag, fixed places, bounds, regions) + the draw code (ctdraw.c, ctband.c, swce/sr_stage.c,
swce/swosrules.h, cobj's flags) + this file: one run serves every build until data or engine change.

    python3 tools/drawgate.py            # the gate on the world's data (the build's call: gate())
"""
import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '..', 'internal', 'drawgate')
if not os.path.isdir(os.path.dirname(CACHE)):
    CACHE = os.path.expanduser('~/swos-mod/internal/drawgate')
VENV = os.path.expanduser('~/swos-mod/internal/hosttest/.venv/bin/python')
EXHAUST, NSAT, NRND, NSEED, NGAME = 4096, 4096, 4096, 1024, 64
I486_MAX = 20_000_000
FLAGS = ['-Oz', '-fno-zero-initialized-in-bss']        # (lrank.ct_patch's)
SRCS = ('ctdraw.c', 'ctband.c', 'swce/sr_stage.c', 'swce/swosrules.h', 'drawgate.py',
        'conti.c', 'conti.h')                           # (conti.c: the game seeds' derivation - MC 11/11)
A_ANY, A_NO, A_NOVIA, A_NO2, A_MIN = 0, 1, 2, 3, 4


def count(avail, n):
    """multisets of n over the associations, each <= avail[i]"""
    dp = [1] + [0] * n
    for a in avail:
        nd = [0] * (n + 1)
        for s in range(n + 1):
            if dp[s]:
                for x in range(min(a, n - s) + 1):
                    nd[s + x] += dp[s]
        dp = nd
    return dp[n]


def every(avail, n):
    """all of them (count() <= EXHAUST): tuples of counts"""
    out, cur = [], [0] * len(avail)
    suf = [0] * (len(avail) + 1)
    for i in range(len(avail) - 1, -1, -1):
        suf[i] = suf[i + 1] + avail[i]

    def rec(i, left):
        if i == len(avail):
            if not left:
                out.append(tuple(cur))
            return
        for x in range(max(0, left - suf[i + 1]), min(avail[i], left) + 1):
            cur[i] = x
            rec(i + 1, left - x)
        cur[i] = 0
    rec(0, n)
    return out


def saturated(avail, n, rnd):
    """associations at their bound in turn (an order each), the last one the rest: up to NSAT distinct, the first
    len(avail) orders each start with another association (so each reaches its bound)"""
    k = len(avail)
    seen, out = set(), []
    orders = [[i] + [j for j in range(k) if j != i] for i in range(k)]
    for _ in range(NSAT * 4):
        if len(orders) >= NSAT * 4:
            break
        o = list(range(k))
        rnd.shuffle(o)
        orders.append(o)
    for o in orders:
        cur, left = [0] * k, n
        for i in o:
            x = min(avail[i], left)
            cur[i], left = x, left - x
            if not left:
                break
        t = tuple(cur)
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= NSAT:
            break
    hit = [any(t[i] == avail[i] for t in out) for i in range(k)]
    assert all(hit[i] or not avail[i] for i in range(k)), 'drawgate: the saturated set misses a bound'
    return out


def randoms(avail, n, rnd):
    out = []
    for _ in range(NRND):
        cur, left = [0] * len(avail), n
        while left:
            w = [avail[i] - cur[i] for i in range(len(avail))]
            i = rnd.choices(range(len(avail)), w)[0]
            cur[i] += 1
            left -= 1
        out.append(tuple(cur))
    return out


def rounds(confs):
    """the gate's inputs: [{cup, conf, round, rule, ng, gs, pr, direct {assoc: n}, avail {assoc: n}, nvar, via,
    region {assoc: 0/1}}] from conti's last load (BOUND_IN / BOUND_CNT / AREG)"""
    import conti
    body, access, holders, gl, assocs, clubs = conti.BOUND_IN[0]
    cnt, direct, short, hold, cap = conti.BOUND_CNT[0]
    areg = conti.AREG[0]
    R, off, ci = {}, 0, 0
    while off < len(body):
        for j in range(body[off]):
            R[(ci, j)] = body[off + 4 + conti.RB * j:off + 4 + conti.RB * (j + 1)]
        off += 4 + conti.RB * body[off]
        ci += 1
    fed = {}                                            # (a round's routes in: [(source, winners 0 / losers 1 / other 2, n)])
    for (c, j), b in R.items():
        outs = [(b[10], 0, (b[18] + 1) // 2), (b[11], 1, b[18] // 2)] if b[0] == conti.K['ko'] else \
            [(b[12 + q], 2, b[6]) for q in range(4)] + ([(b[20], 2, b[6] * b[19])] if b[19] else [])
        for t, kind, n in outs:
            if t not in (conti.OUT, conti.CHAMP) and n:
                fed.setdefault((t >> 4, t & 15), []).append(((c, j), kind, n))

    places = {}                                         # (each association's direct places, all cups)
    for (c, j), d in direct.items():
        for a, x in d.items():
            places[a] = places.get(a, 0) + x
    hcup = {}                                           # (holder slots by cup, the UEFA holder's too: hold lacks it)
    for si, c, jf, _ in holders:
        hcup.setdefault(c, []).append(jf)

    def exact(src, kind):
        """a same_assoc_pairs knockout round fed by direct places only: its winners (losers) are exactly half of
        each association's clubs (every tie two of one association, conti.c draw_ko D_SAMEPAIRS) -> ({assoc: n},
        None), else (None, why): the loose bound. The precondition (MC 11/11 check 2; access() in conti.c):
        winners / losers routes only; no route in; no holder slot in the round, no CAF own-place holder in the cup
        (its league place skipped, not refilled), no vacant holder place there; every direct place filled
        (no association with more places than clubs: next_club() 0, a bye); even counts summing to the round's
        size. (Test builds' CONTI_FORCE '!' place may swap an entrant: CT_SDRAW_HIT is the harness backstop.)"""
        b = R[src]
        if b[0] != conti.K['ko'] or b[4] != conti.DRAW['same_assoc_pairs']:
            return None, 'not a same_assoc_pairs knockout'
        if kind > 1:
            return None, 'not a winners / losers route'
        if fed.get(src):
            return None, 'routes in'
        if any((jf & 0x1F) == src[1] or jf & 0x80 for jf in hcup.get(src[0], ())):
            return None, 'holder slot'
        d = direct.get(src, {})
        if any(places[a] > cap.get(a, places[a]) for a in d):
            return None, 'association short of clubs'
        if any(x % 2 for x in d.values()):
            return None, 'odd association count'
        if sum(d.values()) != b[18]:
            return None, 'direct places != round size'
        return {a: x // 2 for a, x in d.items()}, None

    out = []
    for (c, j), b in sorted(R.items()):
        if b[0] != conti.K['groups'] or b[19] or b[5] == A_ANY:
            continue
        ng, gs, rule, pr = b[6], b[7], b[5], bool(b[16] & 2)
        d = dict(direct.get((c, j), {}))
        var, ok, loose = {}, [], []                     # (the variable clubs' bound: draw_bound's flows for this
        for src, kind, n in fed.get((c, j), ()):         #  round, an exact source's clubs fixed instead)
            ex, why = exact(src, kind)
            if ex is not None:
                assert sum(ex.values()) == n, ('drawgate: exact source != places sent', src, kind, ex, n)
                for a, x in ex.items():
                    d[a] = d.get(a, 0) + x
                ok.append(f'{src[0]}.{src[1]}{"wl"[kind]}')
                continue
            if R[src][4] == conti.DRAW['same_assoc_pairs'] and R[src][0] == conti.K['ko']:
                loose.append(f'{src[0]}.{src[1]}: {why}')
            for a, x in cnt.get(src, {}).items():
                var[a] = var.get(a, 0) + min(n, x)
        for si in hold.get((c, j), ()):
            for a in {a for (cc, _), dd in cnt.items() if cc == si for a, x in dd.items() if x}:
                var[a] = var.get(a, 0) + 1
        if not b[23] and short:
            for a in set(cap) | set(var) | set(d):
                var[a] = var.get(a, 0) + short
        wvar = None                                     # (4.2 AFC mode, per region: the variable clubs' West count
        if pr and not hold.get((c, j)) and not (not b[23] and short):   # when every loose source is region-closed -
            wvar = 0                                    #  an 'order' knockout of direct places only, West then East
            for src, kind, n in fed.get((c, j), ()):    #  (conti.py), each region even: its winners / losers half
                if exact(src, kind)[0] is not None:     #  of each region's clubs; else None: no region filter)
                    continue
                sb, sd = R[src], direct.get(src, {})
                if (sb[0] != conti.K['ko'] or sb[4] != conti.DRAW['order'] or kind > 1 or fed.get(src)
                        or any((jf & 0x1F) == src[1] or jf & 0x80 for jf in hcup.get(src[0], ()))
                        or any(places[a] > cap.get(a, places[a]) for a in sd) or sum(sd.values()) != sb[18]
                        or any(sum(x for a, x in sd.items() if areg[a] & 1 == z) % 2 for z in (0, 1))):
                    wvar = None
                    break
                wvar += sum(x for a, x in sd.items() if not areg[a] & 1) // 2
        nd = sum(d.values())
        size = ng * gs
        assert nd <= size, ('drawgate: more fixed places than the round', c, j)
        top = cnt.get((c, j), {})
        av = {a: min(x, top.get(a, x) - d.get(a, 0), b[18]) for a, x in var.items()}
        av = {a: x for a, x in av.items() if x > 0}
        nvar = min(size - nd, sum(av.values()))
        out.append(dict(c=c, j=j, rule=rule, ng=ng, gs=gs, pr=pr, direct=d, avail=av, nvar=nvar,
                        via=rule == A_NOVIA, region={a: areg[a] & 1 for a in set(d) | set(av)} if pr else {},
                        exact=ok, loose=loose, wvar=wvar))
    return out


def game_seeds(confs, nseasons=NGAME):
    """(cup, round) -> the edition rng at that round's ct_place, over nseasons native seasons (conti.test's world)"""
    import ctypes
    import contextlib
    import io
    import conti
    L = conti._native()
    got = {}

    def hook(L_, names, step):
        if 'start' in step:
            ps = (ctypes.c_uint32 * 256).in_dll(L_, 'CT_PSEED')
            for t in range(256):
                if ps[t]:
                    got.setdefault((t >> 4, t & 15), []).append(ps[t])
                ps[t] = 0
    with contextlib.redirect_stdout(io.StringIO()):
        conti.test(list(confs), seasons=nseasons, seed=11, L=L, hook=hook)
    return got, L


def key(rs):
    h = hashlib.sha1()
    for f in SRCS:
        h.update(open(os.path.join(HERE, f), 'rb').read())
    import cobj
    import conti
    h.update(json.dumps([cobj.CFLAGS, FLAGS, list(conti.NATIVE_FLAGS)]).encode())   # (+ the native build's flags)
    h.update(json.dumps([{k: (sorted(v.items()) if isinstance(v, dict) else v) for k, v in r.items()} for r in rs]).encode())
    return h.hexdigest()[:16]


def multisets(r, rnd):
    """(kind, [counts tuples over r's association order]) and that order"""
    names = sorted(r['avail'])
    av = [r['avail'][a] for a in names]
    n = r['nvar']
    if r['via']:                                        # (A_NOVIA: routed clubs exempt - their own values)
        return 'exhaustive', [()], names
    tot = count(av, n)
    w = r.get('wvar')
    if w is not None:                                   # (per region, region-closed sources: only the multisets
        west = [not r['region'][a] for a in names]      #  with that West count - the others unreachable)
        keep = lambda t: sum(x for x, z in zip(t, west) if z) == w
        if tot <= EXHAUST:
            return 'exhaustive', [t for t in every(av, n) if keep(t)], names
        return 'saturated+random', [('s', t) for t in saturated(av, n, rnd) if keep(t)] + \
            [('r', t) for t in randoms(av, n, rnd) if keep(t)], names
    if tot <= EXHAUST:
        return 'exhaustive', every(av, n), names
    return 'saturated+random', [('s', t) for t in saturated(av, n, rnd)] + [('r', t) for t in randoms(av, n, rnd)], names


def clubs_of(r, names, t):
    """the multiset's clubs: association bytes (region bit 7) and via flags"""
    asb, v = [], []
    for a, x in sorted(r['direct'].items()):
        asb += [a] * x
        v += [0] * x
    if r['via']:
        asb += [0] * r['nvar']
        v += [1] * r['nvar']
    else:
        for a, x in zip(names, t):
            asb += [a] * x
            v += [0] * x
    if r['pr']:
        asb = [a | (r['region'][a] << 7) for a in asb]
    return bytes(asb), bytes(v)


def gate(confs, cups, assocs, quiet=False):
    """the gate (the build: conti.patch after load); returns the result dict, raises AssertionError on a FAIL"""
    import ctypes
    rs = rounds(confs)
    k = key(rs)                                         # (not the game seeds: derived from the same data and code -
                                                        #  and from conti's module state, the build's season 1)
    path = os.path.join(CACHE, k + '.json')
    if os.path.exists(path):
        res = json.load(open(path))
        assert res['result'] == 'PASS', f'drawgate: cached FAIL {path}: {res.get("fail")}'
        print(f'exe: conti draw gate PASS (cached {k}): {res["summary"]}')
        return res
    t0 = time.time()
    seeds, L = game_seeds(confs)
    L.ct_gate.restype = ctypes.c_int
    rnd = random.Random(0x4A2)
    res = dict(key=k, rounds=[], result='PASS')
    worst_all, jobs = None, []
    for r in rs:
        kind, ms, names = multisets(r, rnd)
        gs_ = seeds.get((r['c'], r['j']), [])[:NGAME]
        s0 = (ctypes.c_uint32 * max(1, len(gs_)))(*gs_)
        mode = r['rule'] | 0x20 | (0x40 if r['pr'] else 0) | 1 << 8
        out = (ctypes.c_uint32 * 5)()
        wo, wv, ws = (ctypes.c_uint8 * 64)(), (ctypes.c_uint8 * 64)(), ctypes.c_uint32()
        nsat = sum(1 for t in ms if isinstance(t, tuple) and t and t[0] == 's')
        rw, fails = None, []
        for mi, t in enumerate(ms):
            tt = t[1] if t and t[0] in ('s', 'r') else t
            asb, v = clubs_of(r, names, tt)
            m = len(asb)
            ab, vb = (ctypes.c_uint8 * 64)(*asb), (ctypes.c_uint8 * 64)(*v)
            L.ct_gate(m, r['ng'], r['gs'], mode, ab, vb, s0, len(gs_), NSEED, 0x9E37 + 7919 * mi + 31 * r['c'] + r['j'],
                      out, wo, wv, ctypes.byref(ws))
            ms_txt = ' '.join(f'{assocs[a]}x{x}' for a, x in sorted(_mset(asb).items()))
            if out[2] or out[3]:
                fails.append(f'{cups[r["c"]][0]}:{cups[r["c"]][1]} round {r["j"]} multiset [{ms_txt}]: '
                             f'{out[2]} budget hit(s), {out[3]} refusal(s) (first at seed #{out[4] - 1})')
            jobs.append(dict(r=len(res['rounds']), m=m, ng=r['ng'], gs=r['gs'], mode=mode, steps=out[0],
                             seed=ws.value, order=list(wo[:m]), v=list(wv[:m]), ms=ms_txt))
            if rw is None or out[0] > rw[0]:
                rw = (out[0], ms_txt, ws.value)
        res['rounds'].append(dict(cup=f'{cups[r["c"]][0]}:{cups[r["c"]][1]}', round=r['j'], kind=kind,
                                  multisets=len(ms), saturated=nsat, random=len(ms) - nsat if kind != 'exhaustive' else 0,
                                  game_seeds=len(gs_), worst_steps=rw[0], worst=rw[1], fails=fails[:8], nfail=len(fails),
                                  exact_src=r['exact'], loose_sap=r['loose']))
        if fails:
            res['result'] = 'FAIL'
            res.setdefault('fail', fails[0])
        if not quiet:
            print(f'drawgate: {res["rounds"][-1]["cup"]} r{r["j"]} {kind} {len(ms)} multisets x {NSEED} seeds '
                  f'({len(gs_)} game): worst {rw[0]} steps [{rw[1]}], {len(fails)} FAIL ({time.time() - t0:.0f} s)',
                  flush=True)
        if r['loose'] and not quiet:                    # (MC 11/11: a same_assoc_pairs source on the loose bound)
            print(f'drawgate:   loose same_assoc_pairs source(s): {"; ".join(r["loose"])}', flush=True)
    for ri in range(len(res['rounds'])):                # (the exact count: each round's most-steps job - steps and
        js = [jb for jb in jobs if jb['r'] == ri]        #  instructions go together; the rest: under the cap or not)
        if js:
            max(js, key=lambda jb: jb['steps'])['exact'] = True
    i486 = run_i486(jobs)                               # (every multiset's worst seed under Unicorn)
    for rr in res['rounds']:
        rr['i486_worst'] = 0
    over = []
    for jb, n in zip(jobs, i486):
        rr = res['rounds'][jb['r']]
        if n > rr['i486_worst']:
            rr['i486_worst'], rr['i486_worst_ms'] = n, jb['ms']
        if n > I486_MAX:
            over.append(f'{rr["cup"]} round {rr["round"]} multiset [{jb["ms"]}] seed {jb["seed"]:#x}: {n} i486 insns')
    if over:
        res['result'] = 'FAIL'
        res.setdefault('fail', over[0])
        res['i486_over'] = over[:16]
    w = max(res['rounds'], key=lambda x: x['i486_worst'])
    res['summary'] = (f'{len(rs)} rounds, {sum(x["multisets"] for x in res["rounds"])} multisets x {NSEED} seeds; '
                      f'worst i486 {w["i486_worst"]} insns ({w["cup"]} r{w["round"]} [{w.get("i486_worst_ms", "")}])')
    res['seconds'] = round(time.time() - t0)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(res, open(path, 'w'), indent=1)
    print(f'exe: conti draw gate {res["result"]} ({k}, {res["seconds"]} s): {res["summary"]}')
    assert res['result'] == 'PASS', f'drawgate FAIL ({path}): {res["fail"]}'
    return res


def _mset(asb):
    d = {}
    for a in asb:
        d[a & 0x7F] = d.get(a & 0x7F, 0) + 1
    return d


def run_i486(jobs):
    """the jobs' worst seeds under Unicorn (the venv's python, this file --i486): insns each"""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        jf = os.path.join(t, 'jobs.json')
        json.dump(jobs, open(jf, 'w'))
        r = subprocess.run([VENV, '-I', os.path.abspath(__file__), '--i486', jf], capture_output=True, text=True)
        assert r.returncode == 0, ('drawgate: the i486 run', r.stderr[-2000:])
        return json.load(open(jf + '.out'))


def i486_main(jf):
    """ctband.c compiled as the exe compiles it, linked by cobj at obj4+0x100 (the C stack's calls stubbed), each job's
    ct_place under Unicorn with a 20 M + 1 instruction cap: its count (exact under the cap: emu_start's count)"""
    sys.path.insert(0, HERE)
    import cobj
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP

    class Rec:
        class le:
            page_size = 0x100000

        def __init__(self):
            self.mem, self.ptrs = {}, []

        def put(self, o, off, data):
            for i, b in enumerate(data):
                self.mem[off + i] = b

        def add_ptr(self, o, off, to, toff):
            self.ptrs.append((off, toff))

        def add_rel(self, *a):
            raise AssertionError('drawgate i486: a cross-object call')

        def get(self, o, off, n):
            return bytes(self.mem.get(off + i, 0) for i in range(n))
    BASE = 0x400000
    stub = bytes.fromhex('ff742408ff54240883c404c3') + b'\xc3'   # cstack_call(fn, arg): fn(arg); swe_ready: ret
    p = Rec()
    p.put(4, 0, stub)
    ext = {'cstack_call': (4, 0), 'swe_ready': (4, len(stub) - 1)}
    obj = cobj.compile_c(os.path.join(HERE, 'ctband.c'), FLAGS, sections=True)
    import lrank
    syms, end, bss = cobj.link(p, obj, 0x100, (4, 0), externs=ext, limit=0x10000, text_obj=4, roots=lrank.CT_ROOTS)
    img = bytearray(end + 16)
    for a, b in p.mem.items():
        img[a] = b
    for off, toff in p.ptrs:
        struct.pack_into('<I', img, off, struct.unpack_from('<I', img, off)[0] + BASE)
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, 0x400000)
    uc.mem_write(BASE, bytes(img))
    ct = BASE + syms['ct_place'][1]
    sent, buf, top = BASE + 0x300000, BASE + 0x200000, BASE + 0x3F0000
    uc.mem_write(sent, b'\xf4')
    jobs = json.load(open(jf))
    out = []
    for jb in jobs:
        m = jb['m']
        uc.mem_write(buf, struct.pack('<64H', *(list(range(1, m + 1)) + [0] * (64 - m))))
        uc.mem_write(buf + 0x100, bytes(jb['v']).ljust(64, b'\0'))
        uc.mem_write(buf + 0x200, bytes(64))
        uc.mem_write(buf + 0x300, bytes(jb['order']).ljust(64, b'\0'))
        uc.mem_write(buf + 0x400, struct.pack('<I', jb['seed']))
        args = [m, jb['ng'], jb['gs'], jb['mode'], buf, buf + 0x100, buf + 0x200, buf + 0x300, buf + 0x400, 0]
        sp = top - 64
        uc.mem_write(sp, struct.pack('<11I', sent, *args))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.emu_start(ct, sent, count=I486_MAX + 1)
        if uc.reg_read(UC_X86_REG_EIP) != sent:
            out.append(I486_MAX + 1)                    # (over the cap)
            continue
        out.append(count_insns(uc, ct, sent, sp, args, buf, jb) if jb.get('exact') else 1)   # (1: under the cap)
    json.dump(out, open(jf + '.out', 'w'))


def count_insns(uc, ct, sent, sp, args, buf, jb):
    """the exact count, by bisection on emu_start's count (the run restarted each time, same inputs)"""
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP
    lo, hi = 0, I486_MAX + 1

    def run(c):
        m = jb['m']
        uc.mem_write(buf, struct.pack('<64H', *(list(range(1, m + 1)) + [0] * (64 - m))))
        uc.mem_write(buf + 0x100, bytes(jb['v']).ljust(64, b'\0'))
        uc.mem_write(buf + 0x200, bytes(64))
        uc.mem_write(buf + 0x300, bytes(jb['order']).ljust(64, b'\0'))
        uc.mem_write(buf + 0x400, struct.pack('<I', jb['seed']))
        uc.mem_write(sp, struct.pack('<11I', sent, *args))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.emu_start(ct, sent, count=c)
        return uc.reg_read(UC_X86_REG_EIP) == sent
    while hi - lo > max(1, hi // 1000):                 # (to 0.1 %)
        mid = (lo + hi) // 2
        if run(mid):
            hi = mid
        else:
            lo = mid
    return hi


if __name__ == '__main__':
    if sys.argv[1:2] == ['--i486']:
        i486_main(sys.argv[2])
    else:
        sys.path.insert(0, HERE)
        import conti
        if os.environ.get('DRAWGATE_DATA'):            # (a data copy: the gate on data not yet live)
            conti.DATA = os.environ['DRAWGATE_DATA']
        confs = conti.ready()
        files, words = conti._world_maps(confs)
        spec, assocs, cups = conti.load(confs, files, words)
        gate(confs, cups, assocs)
