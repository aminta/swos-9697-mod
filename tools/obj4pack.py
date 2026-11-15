"""obj4 freeze layout proposer (MC 15/11, the 4.2 rc freeze: obj1-room.md "Release order rule"). Read-only: it never
writes swreg.py and builds nothing.

    python3 tools/obj4pack.py c/RELxx [--out DIR] [--map obj1-room.md] [--ship NAME,...] [--test NAME,...]
    python3 tools/obj4pack.py --verify c/RELyy DIR/obj4pack.json [--allow NAME,...]

Proposal (a release build dir: its 8 exes + build.log, measured on this checkout's swreg):
 - the bands and their classes come from obj1-room.md's obj4 map only (its table order = the map order; obj4check's
   parser): '(test)' rows are test-only, '(4.3)' rows the 4.3 reservations, the rest release. A map test-only band
   with bytes in a release exe is a FAIL of the proposal (MC 15/11: a test switch leaking into a release; MC reclasses
   the band in the map, or the recipe stops linking it) - never packed;
 - each band's used bytes = max over the 8 exes of obj4check's used end - AT (non-zero bytes + build.log extents;
   a band holding others owns up to the first of them);
 (a) the release map bands are packed in map order from the first of them (no holes): each sized to its used bytes +
     its floor (obj4check: 256 B, 128 B for SETPIECE / DIFF2 / SPX), rounded up to 0x100 - so a band under its floor
     (KITS) grows and an oversized one shrinks. Bands that are not map bands (REG, SLOW + its inner bands, T3, ...) and
     map bands nested inside one stay where they are; the packing jumps over them. A release map band with no byte in
     any of the 8 exes (not linked in this release build) is NOT packed: it goes to the test region with the
     test-only bands and the report names it (--ship NAME packs it anyway at its current size);
 (b) the test-only bands (and the unlinked ones) keep their sizes and go from 0x30000 (after the bands already there);
 (c) OBJ4_PAGES = ceil(the last packed release band's END / 0x1000); the 4.3 reservations follow the last release band
     in map order, sizes kept (unlinked: no file page in a release);
 (d) a swreg.py patch (unified diff, AT / END literals only, plus the band's own inner constants NAME_* moved with it,
     e.g. OBJ1MV_CC) for the Integratore to review and apply, and the swreg asserts that fail with the new values
     (chain asserts to rewrite by hand). obj4pack.json keeps the plan and the per-exe used bytes for --verify.

--verify (after the Integratore applied the patch and rebuilt): this checkout's swreg must give the planned addresses
for every band of the plan, obj4check's release check must have 0 findings on the new build, and every band's used
bytes must equal the proposal's per exe (only addresses moved)."""
import ast
import difflib
import json
import math
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import obj4check as oc  # noqa: E402

ALIGN = 0x100
TEST_BASE = 0x30000
# non-map bands that go to the test region when no release exe links them (MC 15/11: shape-only bands addressed
# through swreg only), with their alignment there: SREG2 = the old-save import's page (sreg.py: exactly one page,
# obj4_pages floors SREG2_END, SREG2_AT >= lrank's LR_TAB end)
EXTRA_MOVABLE = {'SREG2': 0x1000}
MAP_DEFAULT = oc.MAP_DEFAULT


read_map = oc.read_map            # (one parser: the obj4 map is the single source of band classes, MC 15/11)


def floor(name):
    return 128 if name in oc.FLOOR_128 else oc.FLOOR


def up(x, a=ALIGN):
    return -(-x // a) * a


def measure(rel, bl):
    """{exe: {band: used bytes (used end - AT) or None}} over the release dir's 8 exes."""
    import le
    logp = os.path.join(rel, 'build.log')
    lt = open(logp, errors='replace').read() if os.path.exists(logp) else ''
    ext, its = oc.log_extents(lt), oc.log_items(lt)
    out = {}
    for x in oc.EXES:
        p = os.path.join(rel, x)
        if not os.path.exists(p):
            raise SystemExit(f'obj4pack: {p} missing')
        rows = oc.check_obj4(le.LE(p).obj_bytes(4), bl, ext.get(x, []), items=its.get(x, ()))[2]
        out[x] = {n: (None if u is None else u - a) for n, k, a, e, u, fr in rows}
    return out


def nested(bl):
    """{band: outer band} for the bands lying inside another one (SLOW's NAMEFIT / TRIAL / BOX)."""
    out = {}
    for n, a, e in bl:
        for n2, a2, e2 in bl:
            if n2 != n and a2 <= a and e <= e2 and (a2, e2) != (a, e):
                out[n] = n2
    return out


def pack(bl, mp, used, ship=(), test=()):
    """-> (plan, notes, obj4_pages, fails). plan: [{name, cls, old_at, old_end, at, end, used, floor, why}] in placement
    order. bl: swreg bands [(name, at, end)]; mp: read_map(); used: measure()."""
    B = {n: (a, e) for n, a, e in bl}
    inner = nested(bl)
    mx = {n: max([u[n] for u in used.values() if u.get(n) is not None], default=None) for n in B}
    cls = {n: c for n, c in mp}
    notes, fails = [], []
    for n in test:
        cls[n] = 'test'
    rel_order = [n for n, c in mp if c == 'release' and n in B and n not in test]
    packed, totest = [], []
    for n in rel_order:
        if n in inner:
            notes.append(f'{n}: inside {inner[n]} - stays with it')
        elif mx[n] is None and n not in ship:
            totest.append(n)
            notes.append(f'{n}: release map band with no byte in any of the 8 exes (not linked in this release build) '
                         f'- moved to the test region with its size; --ship {n} packs it')
        else:
            packed.append(n)
    for n, al in EXTRA_MOVABLE.items():
        if n in B and n not in cls and mx[n] is None and n not in ship:
            totest.append(n)
            notes.append(f'{n}: shape-only band with no byte in any of the 8 exes - moved to the test region '
                         f'({al:#x}-aligned); --ship {n} keeps it in place')
    moving = set(packed) | set(totest) | {n for n, c in cls.items() if c in ('test', '4.3') and n in B}
    fixed = sorted([(a, e, n) for n, a, e in bl if n not in moving and a < TEST_BASE], key=lambda f: f[0])
    plan, cur = [], (B[packed[0]][0] if packed else None)
    for n in packed:
        a0, e0 = B[n]
        u = mx[n] if mx[n] is not None else e0 - a0 - floor(n)
        size = up(max(u, 0) + floor(n))
        why = 'used + floor' if mx[n] is not None else '--ship: current size'
        if mx[n] is None:
            size = e0 - a0
        moved = True
        while moved:
            moved = False
            for fa, fe, fn in fixed:
                if cur < fe and fa < cur + size:
                    notes.append(f'{n}: jumps over fixed band {fn} {fa:#x}..{fe:#x}')
                    cur, moved = up(fe), True
        plan.append(dict(name=n, cls='release', old_at=a0, old_end=e0, at=cur, end=cur + size, used=mx[n],
                         floor=floor(n), why=why))
        cur += size
    rel_end = cur if packed else 0
    pages = math.ceil(rel_end / oc.PAGE) if packed else None
    mk = rel_end
    for n, c in mp:
        if c == '4.3' and n in B:
            a0, e0 = B[n]
            plan.append(dict(name=n, cls='4.3', old_at=a0, old_end=e0, at=mk, end=mk + (e0 - a0), used=mx[n],
                             floor=None, why='4.3 reservation: after the release bands, size kept'))
            mk += e0 - a0
    t = max([e for n, a, e in bl if a >= TEST_BASE] + [TEST_BASE])        # (after the bands already there)
    for n in [n for n, c in mp if c == 'test' and n in B] + totest:
        a0, e0 = B[n]
        if a0 >= TEST_BASE:
            plan.append(dict(name=n, cls='test', old_at=a0, old_end=e0, at=a0, end=e0, used=mx[n], floor=None,
                             why='already in the test region'))
            continue
        t = up(t, EXTRA_MOVABLE.get(n, ALIGN))
        plan.append(dict(name=n, cls='test' if n not in totest else 'release-unlinked', old_at=a0, old_end=e0, at=t,
                         end=t + (e0 - a0), used=mx[n], floor=None, why='test region, size kept'))
        t += e0 - a0
    for p in plan:
        if p['cls'] == 'test' and p['used']:
            fails.append(f"{p['name']}: linked ({p['used']} B in a release exe) but test-only in the obj4 map: MC must "
                         f"reclass it in obj1-room.md, or the recipe must not link it")
    known = {p['name'] for p in plan}
    for n, a, e in bl:
        if n not in known and n not in {f[2] for f in fixed} and n not in inner:
            notes.append(f'{n}: swreg band not in the obj4 map - left where it is')
    return plan, notes, pages, fails


SYM = re.compile(r'^([A-Z][A-Z0-9_]*)(\s*=\s*)(0x[0-9A-Fa-f]+|\d+)\b', re.M)


def swreg_patch(text, plan):
    """-> (new text, [inner constants moved], [assert messages failing with the new values], {name: value} of the
    patched module). Only NAME = <literal> lines change."""
    ns = oc.swreg_ns(text)
    new = {}
    inner = []
    for p in plan:
        n, d = p['name'], p['at'] - p['old_at']
        if p['at'] != p['old_at']:
            new[n + '_AT'] = p['at']
        if n + '_END' in ns and p['end'] != p['old_end']:
            new[n + '_END'] = p['end']
        if n + '_SIZE' in ns and p['end'] - p['at'] != p['old_end'] - p['old_at']:
            new[n + '_SIZE'] = p['end'] - p['at']
        for k, v in ns.items():
            if (k.startswith(n + '_') and k not in (n + '_AT', n + '_END', n + '_SIZE') and isinstance(v, int)
                    and p['old_at'] <= v <= p['old_end'] and d):
                new[k] = v + d
                inner.append(f'{k} {v:#x} -> {v + d:#x}')
    seen = set()

    def rep(m):
        k = m.group(1)
        if k in new:
            seen.add(k)
            return f'{k}{m.group(2)}{new[k]:#X}'.replace('0X', '0x')
        return m.group(0)
    out = SYM.sub(rep, text)
    for k in sorted(set(new) - seen):
        inner.append(f'{k}: no literal line in swreg (an expression?) - set it by hand to {new[k]:#x}')
    fails, g = [], {}
    for node in ast.parse(out).body:
        if isinstance(node, ast.Assert):
            try:
                ok = eval(compile(ast.Expression(node.test), 'swreg', 'eval'), g)
            except Exception as ex:                     # noqa: BLE001
                ok, node.msg = False, ast.Constant(f'{type(ex).__name__}: {ex}')
            if not ok:
                fails.append(f'line {node.lineno}: ' + (ast.literal_eval(node.msg) if isinstance(node.msg, ast.Constant)
                                                        else ast.unparse(node.test)[:160]) + chain_order(node.test, g))
        else:
            exec(compile(ast.Module([node], []), 'swreg', 'exec'), g)
    return out, inner, fails, {k: v for k, v in g.items() if isinstance(v, int)}


def chain_order(test, g):
    """For a failing comparison chain of NAME_AT / NAME_END names: the same names in the order the new values need
    ('\n    required: A_END <= B_AT < B_END <= ...'), names of bands that left the chain's range listed apart."""
    if not isinstance(test, ast.Compare):
        return ''
    names = [x.id for x in [test.left] + test.comparators if isinstance(x, ast.Name)]   # (literal bounds left out)
    if len(names) < 3:
        return ''
    if not all(n in g and isinstance(g[n], int) for n in names):
        return ''
    test_side = [n for n in names if g[n] >= TEST_BASE]
    rest = sorted([n for n in names if n not in test_side], key=lambda n: (g[n], not n.endswith('_END')))
    out, prev = [], None
    for n in rest:
        if prev is not None:
            out.append('<' if prev.endswith('_AT') and n.endswith('_END') and prev[:-3] == n[:-4] else '<=')
        out.append(n)
        prev = n
    tail = '' if not test_side else ('\n    in the test region now (a chain of their own, >= 0x30000): '
                                     + ', '.join(sorted(test_side, key=lambda n: g[n])))
    return '\n    required order: ' + ' '.join(out) + tail


def report(plan, notes, pages, used, inner, afails, fails=()):
    out = (['PROPOSAL FAIL:'] + ['  ' + f for f in fails] if fails else []) + [
           'obj4pack proposal (map order; sizes = max used over the 8 exes + floor, rounded to 0x100):',
           f"  {'band':<10} {'class':<16} {'old':<17} {'new':<17} {'used':>6} {'free':>6}  why"]
    for p in plan:
        u = '-' if p['used'] is None else str(p['used'])
        fr = '-' if p['used'] is None else str(p['end'] - p['at'] - p['used'])
        out.append(f"  {p['name']:<10} {p['cls']:<16} {p['old_at']:#07x}..{p['old_end']:#07x} {p['at']:#07x}..{p['end']:#07x} "
                   f"{u:>6} {fr:>6}  {p['why']}")
    rel = [p for p in plan if p['cls'] == 'release']
    if rel:
        out.append(f"OBJ4_PAGES = {pages:#x} (last release band {rel[-1]['name']} ends {rel[-1]['end']:#x}); "
                   f"before: last release byte page {max(p['old_end'] for p in rel):#x}")
    out += ['notes:'] + ['  ' + n for n in notes] if notes else []
    if inner:
        out += ['inner constants moved with their band:'] + ['  ' + s for s in inner]
    if afails:
        out += ['swreg asserts failing with the new values (rewrite by hand, e.g. the band chain):'] + ['  ' + s for s in afails]
    return '\n'.join(out)


def propose(rel, mapfile=MAP_DEFAULT, ship=(), test=(), out=None, mod=None):
    if mod is None:
        import swreg as mod
    bl = oc.bands(mod)
    mp = read_map(open(mapfile).read(), {b[0] for b in bl})
    used = measure(rel, bl)
    plan, notes, pages, fails = pack(bl, mp, used, ship, test)
    text = open(mod.__file__).read()
    new, inner, afails, _ = swreg_patch(text, plan)
    rep = report(plan, notes, pages, used, inner, afails, fails)
    diff = ''.join(difflib.unified_diff(text.splitlines(True), new.splitlines(True), 'a/tools/swreg.py', 'b/tools/swreg.py'))
    if out:
        os.makedirs(out, exist_ok=True)
        json.dump(dict(rel=os.path.abspath(rel), plan=plan, obj4_pages=pages, used=used, notes=notes, fails=fails), open(
            os.path.join(out, 'obj4pack.json'), 'w'), indent=1)
        open(os.path.join(out, 'swreg.patch'), 'w').write(diff)
        open(os.path.join(out, 'report.txt'), 'w').write(rep + '\n')
    return plan, rep, diff, fails


def compare(prop, bl, now):
    """-> [errors]: swreg vs the plan, and per exe every band's used bytes vs the proposal's (only addresses may move);
    a band whose used bytes + floor no longer fit its packed size is named as an overflow."""
    B = {n: (a, e) for n, a, e in bl}
    errs = []
    for p in prop['plan']:
        if B.get(p['name']) != (p['at'], p['end']):
            got = B.get(p['name'])
            errs.append(f"swreg {p['name']}: {'missing' if got is None else f'{got[0]:#x}..{got[1]:#x}'}, planned "
                        f"{p['at']:#x}..{p['end']:#x}")
    size = {p['name']: (p['end'] - p['at'], p['floor']) for p in prop['plan']}
    for x, d in prop['used'].items():
        for n, u in d.items():
            v = now.get(x, {}).get(n)
            if n not in B or v == u:
                continue
            errs.append(f'{x} {n}: used {v} B, before {u} B (only addresses may move)')
            if v is not None and n in size and size[n][1] is not None and v + size[n][1] > size[n][0]:
                errs.append(f'{x} {n}: overflows its packed size ({v} + floor {size[n][1]} > {size[n][0]} B)')
    return errs


def verify(rel, prop, mod=None, allow=()):
    """-> (ok, report). prop: obj4pack.json's dict. obj4check's failures per exe (info lines left out); a zero page
    below the first packed band is marked as outside the packing (there before the freeze too) - still a finding."""
    import le
    if mod is None:
        import swreg as mod
    bl = oc.bands(mod)
    out = [f"obj4pack --verify {rel} against the proposal for {prop['rel']}"]
    lo = min([p['at'] for p in prop['plan'] if p['cls'] == 'release'], default=0)
    logp = os.path.join(rel, 'build.log')
    lt = open(logp, errors='replace').read() if os.path.exists(logp) else ''
    ext, its = oc.log_extents(lt), oc.log_items(lt)
    f4 = {}
    for x in oc.EXES:
        for f in oc.check_obj4(le.LE(os.path.join(rel, x)).obj_bytes(4), bl, ext.get(x, []), allow, its.get(x, ()))[0]:
            m = re.match(r'\(a\) zero page obj4\+(0x[0-9a-f]+)', f)
            f4.setdefault(f + (' [below the packed range]' if m and int(m.group(1), 16) < lo else ''), []).append(x)
    errs = compare(prop, bl, measure(rel, bl))
    for f, xs in f4.items():
        errs.append(f"obj4check {f} ({'all 8 exes' if len(xs) == len(oc.EXES) else ', '.join(xs)})")
    out.append(f"{len(prop['plan'])} bands planned; obj4check {len(f4)} distinct finding(s); "
               f"used bytes compared on {len(prop['used'])} exes")
    return not errs, '\n'.join(out + errs + ['VERIFY ' + ('PASS' if not errs else 'FAIL')])


def main(argv):
    if '--verify' in argv:
        i = argv.index('--verify')
        al = argv[argv.index('--allow') + 1].split(',') if '--allow' in argv else ()
        ok, rep = verify(argv[i + 1], json.load(open(argv[i + 2])), allow=al)
        print(rep)
        return 0 if ok else 1
    args = [a for a in argv if not a.startswith('--')]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d   # noqa: E731
    split = lambda s: [x for x in (s or '').split(',') if x]              # noqa: E731
    rel = args[0]
    out = opt('--out')
    args = [a for a in args if a not in (out, opt('--map'), opt('--ship'), opt('--test'))]
    plan, rep, diff, fails = propose(rel, opt('--map', MAP_DEFAULT), split(opt('--ship')), split(opt('--test')), out)
    print(rep)
    print(diff if not out else f'(swreg.patch, obj4pack.json, report.txt in {out})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
