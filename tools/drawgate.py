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

Root fix G (MC 12/11) adds, in the same cached result:
- POTS (item 1): per round its NPM hardest multisets in up to NPOT pot compositions by club ranking each
  (compositions(): an association's clubs together from every pot, the associations grouped / interleaved in many
  orders, random rankings), NPS seeds each through ct_place in that FIXED seeding order;
- FILL (items 2 + 3, its own process: run_fill): conti.c natively on the world's club counts, every association
  with places in turn short of clubs (places - 1, half, 10 = a career country's top 9 + the club, as before
  2c352da): the group fills' associations within the round's rule (9b14728), no refusal, ctfield clean.
And by hand / the gate scripts: `drawgate.py --field <run dir | .CAR>` replays a harness run's dumped edition (or a
career save's) over 64 seeds - exit 1 on a refusal or a ctfield violation; `--pots`, `--fill` alone
(DRAWGATE_CONTI_C=<a conti.c>: another revision, the negative tests). Host tests: hosttest/tests/test_drawgate_g.py.

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
        'conti.c', 'conti.h', 'ctfield.py')             # (ctfield: the fill sweep's checks - root fix G)                           # (conti.c: the game seeds' derivation - MC 11/11)
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
    if conti.BOUND_CNT[0]:                              # (root fix G: the fill sweep's club counts, per association)
        h.update(json.dumps(sorted(conti.BOUND_CNT[0][4].items())).encode())
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
    res['pots'] = pot_sweep(rs, L, cups, assocs, quiet=quiet)   # (root fix G item 1: pot compositions by ranking)
    for rr in res['pots']:
        if rr['nfail']:
            res['result'] = 'FAIL'
            res.setdefault('fail', rr['fails'][0])
    fl = run_fill()                                     # (root fix G items 2 + 3: the fills, a short association)
    res['fill'] = dict(runs=fl['runs'], nfail=len(fl['fails']), fails=fl['fails'][:8])
    if fl['fails']:
        res['result'] = 'FAIL'
        res.setdefault('fail', 'fill sweep: ' + ' '.join(map(str, fl['fails'][0])))
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
                      f'pots {sum(x["compositions"] for x in res["pots"])} compositions x {NPS}; '
                      f'fill {res["fill"]["runs"]} short-association runs; '
                      f'worst i486 {w["i486_worst"]} insns ({w["cup"]} r{w["round"]} [{w.get("i486_worst_ms", "")}])')
    res['seconds'] = round(time.time() - t0)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(res, open(path, 'w'), indent=1)
    print(f'exe: conti draw gate {res["result"]} ({k}, {res["seconds"]} s): {res["summary"]}')
    assert res['result'] == 'PASS', f'drawgate FAIL ({path}): {res["fail"]}'
    return res


def run_fill():
    """the fill sweep in its own process (conti.test / load would overwrite the build's conti state): this
    process's SEASON_PACKS (the build's world) -> fill_sweep's result"""
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--fill-json'], capture_output=True, text=True,
                         env=dict(os.environ))
    line = [x for x in out.stdout.splitlines() if x.startswith('{')]
    assert out.returncode == 0 and line, ('drawgate: the fill sweep did not run', out.stderr[-2000:])
    r = json.loads(line[-1])
    r['fails'] = [tuple(x) for x in r['fails']]
    return r


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


NPM, NPOT, NPS = 48, 256, 16          # (root fix G item 1: multisets per round, pot compositions each, seeds each)


def compositions(asb, ng, gs, rnd, cap=NPOT):
    """root fix G item 1 (MC 12/11): seeding orders of one multiset's clubs (asb: association bytes) that differ in
    their POT composition (pot p = positions p*ng ..: conti.c draw_groups sorts by ranking, so any order is a
    ranking): each association's clubs together from each pot in turn (the others grouped by association, or
    interleaved), the associations grouped in up to 32 orders (and reversed), then random ones; distinct by pot
    contents, at most cap. -> [list of club indices in seeding order]"""
    m = len(asb)
    idx = {}
    for i, a in enumerate(asb):
        idx.setdefault(a, []).append(i)
    al = sorted(idx)
    out, seen = [], set()

    def add(o):
        k = tuple(tuple(sorted(asb[i] for i in o[p * ng:(p + 1) * ng])) for p in range(gs))
        if len(o) == m and k not in seen and len(out) < cap:
            seen.add(k)
            out.append(list(o))

    def interleave(groups):
        o, gs_ = [], [list(g) for g in groups]
        while any(gs_):
            for g in gs_:
                if g:
                    o.append(g.pop(0))
        return o
    for a in al:                                        # (a's clubs from pot p on, the rest grouped / interleaved)
        rest = [b for b in al if b != a]
        for style in (0, 1):
            others = [i for b in rest for i in idx[b]] if style == 0 else interleave(idx[b] for b in rest)
            for p in range(gs):
                o = list(others)
                at = min(p * ng, len(o))
                add(o[:at] + idx[a] + o[at:])
    orders = [al, al[::-1]] + [rnd.sample(al, len(al)) for _ in range(30)]
    for ao in orders:                                   # (associations grouped, in an order)
        add([i for b in ao for i in idx[b]])
        add(interleave(idx[b] for b in ao))
    for _ in range(4 * cap):                            # (random rankings)
        if len(out) >= cap:
            break
        add(rnd.sample(range(m), m))
    return out


def pot_sweep(rs, L, cups, assocs, quiet=False):
    """root fix G item 1: per group round, its NPM hardest multisets (the most clubs of one association first) in
    up to NPOT pot compositions each (compositions()), NPS seeds each, through ct_place in that fixed seeding order
    (ct_gate shuffles: a random composition per seed). FAIL: a refusal, a half over size / 2, a budget hit.
    -> [{cup, round, multisets, compositions, draws, fails}]"""
    import ctypes
    rnd = random.Random(0x6A7E)
    hit = ctypes.c_uint32.in_dll(L, 'CT_SDRAW_HIT')
    err = ctypes.c_uint32.in_dll(L, 'CT_SDRAW_ERR')
    L.ct_place.restype = ctypes.c_int
    x, v, k, a_ = (ctypes.c_uint16 * 64)(), (ctypes.c_uint8 * 64)(), (ctypes.c_uint8 * 64)(), (ctypes.c_uint8 * 64)()
    rng = ctypes.c_uint32()
    out = []
    for r in rs:
        kind, ms, names = multisets(r, rnd)
        tl = [t[1] if t and t[0] in ('s', 'r') else t for t in ms]
        sets = [clubs_of(r, names, t) for t in tl]
        sets.sort(key=lambda sv: (-max(_mset(sv[0]).values() or [0]), -sum(n * n for n in _mset(sv[0]).values())))
        mode = r['rule'] | 0x20 | (0x40 if r['pr'] else 0) | 1 << 8
        if os.environ.get('DRAWGATE_POTS_411'):         # (the negative test: 4.1.1's draw, not the library's -
            mode = r['rule'] | 16 << 8                  #  it may refuse a composition a draw exists for)
        nc = nd = 0
        fails = []
        for asb, vb in sets[:NPM]:
            m = len(asb)
            for o in compositions(asb, r['ng'], r['gs'], rnd):
                nc += 1
                lcg = 0x2545F491 ^ (nc * 2654435761 & 0xFFFFFFFF)
                for _ in range(NPS):
                    lcg = (lcg * 1664525 + 1013904223) & 0xFFFFFFFF
                    for i, j in enumerate(o):
                        x[i], v[i], k[i], a_[i] = i + 1, vb[j], 0, asb[j]
                    rng.value = lcg
                    h0, e0 = hit.value, err.value
                    err.value = 0
                    rc = L.ct_place(m, r['ng'], r['gs'], mode, x, v, k, a_, ctypes.byref(rng), 0)
                    halves = (err.value & 0xFF) == 5
                    err.value = e0
                    nd += 1
                    if rc < 0 or halves or hit.value != h0:
                        pots = [' '.join(assocs[asb[j] & 0x7F] for j in o[p * r['ng']:(p + 1) * r['ng']])
                                for p in range(r['gs'])]
                        fails.append(f'{cups[r["c"]][0]}:{cups[r["c"]][1]} round {r["j"]} rc {rc}'
                                     f'{" halves" if halves else ""}{" budget" if hit.value != h0 else ""} '
                                     f'seed {lcg:#x} pots {pots}')
        rr = dict(cup=f'{cups[r["c"]][0]}:{cups[r["c"]][1]}', round=r['j'], multisets=min(NPM, len(sets)),
                  compositions=nc, draws=nd, nfail=len(fails), fails=fails[:8])
        out.append(rr)
        if not quiet:
            print(f'drawgate pots: {rr["cup"]} r{r["j"]}: {rr["multisets"]} multisets, {nc} pot compositions, '
                  f'{nd} draws, {len(fails)} FAIL', flush=True)
    return out


def native(conti_c=None):
    """conti's native library: this checkout's, or conti_c (another conti.c - a git revision's copy, the negative
    tests) compiled with this checkout's conti.h / ctdraw.c"""
    import ctypes
    import shutil
    import tempfile
    import conti
    if not conti_c:
        return conti._native()
    t = tempfile.mkdtemp()
    shutil.copy(conti_c, os.path.join(t, 'conti.c'))
    for f in ('conti.h', 'ctdraw.c'):
        shutil.copy(os.path.join(HERE, f), t)
    if os.path.isdir(os.path.join(HERE, 'swce')):
        shutil.copytree(os.path.join(HERE, 'swce'), os.path.join(t, 'swce'))
    lib = os.path.join(t, 'conti.dylib')
    subprocess.run(['clang', '-O1', '-shared', '-fPIC', '-DNATIVE', *conti.NATIVE_FLAGS, '-I', HERE, '-o', lib,
                    os.path.join(t, 'conti.c'), os.path.join(t, 'ctdraw.c')], check=True, capture_output=True)
    return ctypes.CDLL(lib)


def _cups():
    """the loaded world's cups, in spec order"""
    import contextlib
    import io
    import conti
    with contextlib.redirect_stdout(io.StringIO()):
        files, words = conti._world_maps(conti.ready())
        _, _, cups = conti.load(conti.ready(), files, words)
    return cups


def world_spec():
    """conti's spec for the world data in W2627REL_DATA (the build's packs list, as buildrel), the build's load"""
    import contextlib
    import io
    import conti
    w = os.environ.get('W2627REL_DATA') or os.path.expanduser('~/swos-mod/internal/world2526/world5tm-h2')
    if not os.environ.get('SEASON_PACKS'):
        os.environ['SEASON_PACKS'] = ','.join(os.path.join(w, ln.split()[0].lower()) for ln in open(w + '.txt')
                                              if ' file ' in ln)
    confs = conti.ready()
    with contextlib.redirect_stdout(io.StringIO()):
        files, words = conti._world_maps(confs)
        spec, _, _ = conti.load(confs, files, words)
    return spec


def fill_sweep(confs=None, seasons=2, seeds=(7, 3, 11, 19, 23, 31), L=None, quiet=False):
    """root fix G (MC 12/11) items 2 + 3: the group fills' associations and a career country's table, on conti.c
    itself (native seasons, conti.test's world with each association's real club count from the world data - the
    build's load: BOUND_CNT's cap). Every association with places in a confederation whose group stages fill (R[23]
    0) in turn SHORT of clubs: one fewer than its places, half of them, and 10 (its top 9 records + the career club:
    a career country before 2c352da) - so its places pass to the fills, any association's, which conti.c draw_groups
    must keep within the round's rule (9b14728: ng clubs, A_NO2 2 ng). FAIL: a refused draw (CT_SDRAW_ERR), a budget
    hit, or a ctfield violation (the shortened association's own check 4 excepted - that one is the case itself).
    -> {'runs', 'fails': [(conf, assoc, n, seed, why)]}"""
    import contextlib
    import ctypes
    import io
    import conti
    import ctfield
    world_spec()                                        # (the world's load: BOUND_CNT's cap, the club counts)
    cnt, direct, short, hold, cap = conti.BOUND_CNT[0]
    _, _, _, _, assocs, _ = conti.BOUND_IN[0]
    places = {}
    for d in direct.values():
        for a, x in d.items():
            places[assocs[a]] = places.get(assocs[a], 0) + x
    caps = {assocs[a]: n for a, n in cap.items() if a < len(assocs)}
    L = L or conti._native()
    fails, runs = [], 0
    for conf in confs or conti.ready():
        with contextlib.redirect_stdout(io.StringIO()):
            spec, ca, cups = conti.load([conf])
        fill = any(conti.rbytes(spec, ci, j)[0] == conti.K['groups'] and not conti.rbytes(spec, ci, j)[23]
                   for ci in range(len(cups)) for j in range(8) if conti.rbytes(spec, ci, j))
        if not fill:
            continue
        base = {a: min(caps.get(a, 18), 24) for a in ca if not a.startswith('g:')}   # (conti.test's strengths stay > 0)
        for a in sorted(x for x in base if places.get(x)):
            n = places[a]
            for k in sorted({n - 1, max(1, n // 2)} | ({10} if n > 10 else set())):
                for sd in seeds:
                    env = dict(base, **{a: k})
                    os.environ['CONTI_TEST_SHORT'] = ','.join(f'{x}:{y}' for x, y in env.items())
                    bad = []

                    def hook(L_, names, step):
                        lay = (ctypes.c_uint32 * 22).in_dll(L_, 'CT_LAYOUT')
                        g = lambda nm, i: bytes((ctypes.c_ubyte * lay[i]).in_dll(L_, nm))
                        for x in ctfield.check(g('CT_IN', 0), g('CT_OUT', 2), lay, g('CT_ST', 1), confs=(conf,)):
                            if not x.startswith(f'{a}: ') and x not in bad:
                                bad.append(x)
                    why = None
                    lay0 = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')    # (a fresh career each run: no
                    for nm, i in (('CT_IN', 0), ('CT_ST', 1), ('CT_OUT', 2), ('CT_ED', 20)):   # holders, season, pad[1]
                        ctypes.memset((ctypes.c_ubyte * lay0[i]).in_dll(L, nm), 0, lay0[i])  # of the run before)
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            conti.test([conf], seasons=seasons, seed=sd, L=L, hook=hook)
                    except AssertionError as e:
                        why = str(e)
                    finally:
                        os.environ.pop('CONTI_TEST_SHORT', None)
                    runs += 1
                    if why or bad:
                        fails.append((conf, a, k, sd, why or bad[0]))
                        if not quiet:
                            print(f'drawgate fill: FAIL {conf} {a} short to {k} (places {n}) seed {sd}: {why or bad[:2]}',
                                  flush=True)
    if not quiet:
        print(f'drawgate fill: {runs} runs, {len(fails)} FAIL')
    return dict(runs=runs, fails=fails)


def field(run, nseeds=64, conti_c=None, quiet=False):
    """root fix G (MC 12/11): replay a dumped edition (a harness run dir's ctsd_dump/: CT_ED - the season end's
    entrants by cup and round + the reserve clubs the group fills take -, CT_ST, the exe's CT_SPEC) through conti.c
    natively: ct_finish's run(0), every round and draw as the exe plays them, over nseeds edition seeds (the dump's
    own first). conti_c: another conti.c (a git revision's copy: the negative test, e.g. before 9b14728's fill rule).
    run: the dump's dir, or a .CAR (a run's career save: no dump needed - its 'CE' / 'CT' items, the spec rebuilt
    from W2627REL_DATA). -> {'seeds', 'refused': [(seed, CT_SDRAW_ERR)], 'field': [ctfield violations]}; FAIL = any."""
    import ctypes
    import conti
    import ctfield
    if run.upper().endswith('.CAR'):                    # (a career save: its items 'CE' / 'CT'; the spec from the
        import engine                                   #  world data - W2627REL_DATA, as the scenario build's)
        car = open(run, 'rb').read()

        def item(name, size):
            k = car.find(struct.pack('<HH', engine.item_id(name), size))
            assert k >= 0, ('drawgate field: no item', name, run)
            return car[k + 4:k + 4 + size]
        items = {'CT_ED': item('CE', conti.ED_SIZE), 'CT_ST': item('CT', conti.ST_SIZE), 'CT_SPEC': world_spec()}
        d = run
        rd = items.__getitem__
    else:
        d = run if os.path.isdir(os.path.join(run, 'ctsd_dump')) else os.path.dirname(run)
        rd = lambda k: open(os.path.join(d, 'ctsd_dump', k + '.bin'), 'rb').read()
    L = native(conti_c)
    lay = (ctypes.c_uint32 * 22).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out, s_ed = lay[0], lay[1], lay[2], lay[20]
    ed0, st0, spec = bytearray(rd('CT_ED')[:s_ed]), rd('CT_ST')[:s_st], rd('CT_SPEC')
    assert ed0[:2] == b'CE', ('drawgate field: no edition in the dump', d)
    seed0 = struct.unpack_from('<I', ed0, 4)[0]
    buf = ctypes.create_string_buffer(spec, len(spec))
    IN = (ctypes.c_ubyte * s_in).in_dll(L, 'CT_IN')
    ST = (ctypes.c_ubyte * s_st).in_dll(L, 'CT_ST')
    ED = (ctypes.c_ubyte * s_ed).in_dll(L, 'CT_ED')
    OUTB = (ctypes.c_ubyte * s_out).in_dll(L, 'CT_OUT')
    err = ctypes.c_uint32.in_dll(L, 'CT_SDRAW_ERR')
    refused, bad = [], []
    lcg = seed0 or 1
    for s in range(nseeds):
        sd = seed0 if s == 0 else (lcg := (lcg * 1664525 + 1013904223) & 0xFFFFFFFF)
        e = bytearray(ed0)
        struct.pack_into('<I', e, 4, sd)
        ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
        ctypes.memmove(ST, st0, s_st)
        ctypes.memmove(ED, bytes(e), s_ed)
        ctypes.memset(IN, 0, s_in)
        err.value = 0
        L.ct_finish()
        if err.value:
            refused.append((sd, err.value))
        for x in ctfield.check(bytes(IN), bytes(OUTB), tuple(lay), st0):
            if x not in bad:
                bad.append(x)
    res = dict(run=d, seeds=nseeds, refused=refused, field=bad)
    if not quiet:
        print(f'drawgate field {d}: {nseeds} seeds: {len(refused)} refused'
              + (f' (first seed {refused[0][0]:#x}, CT_SDRAW_ERR {refused[0][1]:#x})' if refused else '')
              + f', {len(bad)} field violation(s) {bad[:3]}')
    return res


if __name__ == '__main__':
    if sys.argv[1:2] == ['--i486']:
        i486_main(sys.argv[2])
    elif sys.argv[1:2] == ['--fill-json']:          # (run_fill's child: the result as one JSON line)
        sys.path.insert(0, HERE)
        r = fill_sweep(quiet=True)
        print(json.dumps(r))
    elif sys.argv[1:2] == ['--pots']:               # (root fix G item 1: pot compositions by ranking)
        sys.path.insert(0, HERE)
        import conti
        world_spec()
        cc = os.environ.get('DRAWGATE_CONTI_C')
        _, _, _, _, an, _ = conti.BOUND_IN[0]
        cu = [x for x in conti.LOADED_CUPS] if hasattr(conti, 'LOADED_CUPS') else None
        res = pot_sweep(rounds(conti.ready()), native(cc), cu or _cups(), an)
        sys.exit(1 if any(r['nfail'] for r in res) else 0)
    elif sys.argv[1:2] == ['--fill']:               # (root fix G items 2 + 3: every association short in turn)
        sys.path.insert(0, HERE)
        cc = os.environ.get('DRAWGATE_CONTI_C')      # (another conti.c: the negative test)
        sys.exit(1 if fill_sweep(sys.argv[2:] or None, L=native(cc) if cc else None)['fails'] else 0)
    elif sys.argv[1:2] == ['--field']:              # (root fix G: a dumped field, PASS / FAIL by exit code)
        sys.path.insert(0, HERE)
        r = field(sys.argv[2], conti_c=sys.argv[3] if len(sys.argv) > 3 else None)
        sys.exit(1 if r['refused'] or r['field'] else 0)
    else:
        sys.path.insert(0, HERE)
        import conti
        if os.environ.get('DRAWGATE_DATA'):            # (a data copy: the gate on data not yet live)
            conti.DATA = os.environ['DRAWGATE_DATA']
        confs = conti.ready()
        files, words = conti._world_maps(confs)
        spec, assocs, cups = conti.load(confs, files, words)
        gate(confs, cups, assocs)
