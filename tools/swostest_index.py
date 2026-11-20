#!/usr/bin/env python3
"""Scenario index of tools/swostest.py (PROBE, plan 5.1, MC 19/11): read THIS instead of grepping the 46 k-line file.

    python3 tools/swostest_index.py                 # every scenario: name, line, canary, twin, needs, first doc line
    python3 tools/swostest_index.py WORD [WORD...]  # only rows whose name / needs / doc contain every WORD (case-insensitive)
    python3 tools/swostest_index.py -show NAME      # the scenario's source (its own lines only)
    python3 tools/swostest_index.py -tsv            # tab-separated, for scripts

Rows = every scenario the runner knows (swostest.SCENARIOS: @scenario, the @sc of the modules swostest registers -
fpgate, zonetest, tacgate, ... - and the generated ones such as practice_*), each located in its own file.
Generated from the AST on each call (about 1 s, cached by the file's md5 under internal/swostest/index/), so it is never
stale and never committed. Columns:
  line    where `def NAME` is (tools/swostest.py, else module:line; open the file there, read the function, stop)
  canary  C1..C12 when the scenario is one of the release's 12 canaries (tools/probe.py CANARIES)
  twin    'twin' when it declares a red twin (@probe.red_twin), '-' otherwise
  needs   the environment variables it reads, directly or through the helpers it calls (two levels, harness plumbing such
          as Session / Dosbox / build excluded), plus 'self-build' when it builds its own exe (gate rule 2: LOCAL only)
"""
import ast
import hashlib
import inspect
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'swostest.py')
CACHE = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'swostest', 'index')
# harness plumbing every scenario goes through: its env reads are the runner's, not the scenario's needs
PLUMBING = {'Session', 'Dosbox', 'run_case', 'check', 'require', 'car_info', 'rel_data_default', 'build_key', 'unique_out',
            'build_inputs', 'build_cleanup', 'main', 'run_serial', 'run_parallel', 'scenario', 'spp_restore'}
BUILDERS = {'build', 'builds', 'world_build'}       # a call to one of these (or a *_build helper) = self-building
DEPTH = 2
NAMED = re.compile(r'^[A-Z][A-Z0-9_]*_(BUILD|DATA|CAR|EXE|DIR|SYMS)$')


def _env_reads(fn):
    """Names read through os.environ.get('X') / os.environ['X'] / os.getenv('X') / env.get('X') / 'X' in os.environ."""
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('get', 'getenv', 'pop', 'setdefault') \
                and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            base = ast.unparse(n.func.value)
            if base in ('os.environ', 'os', 'environ', 'env', 'E'):
                out.add(n.args[0].value)
        elif isinstance(n, ast.Subscript) and ast.unparse(n.value) == 'os.environ' and isinstance(n.slice, ast.Constant) \
                and isinstance(n.ctx, ast.Load):
            out.add(n.slice.value)
        elif isinstance(n, ast.Compare) and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str) \
                and any(ast.unparse(c) == 'os.environ' for c in n.comparators):
            out.add(n.left.value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and NAMED.match(n.value):
            out.add(n.value)                   # (names in a tuple looped over: foreign_exe's FOREIGNBUY_BUILD, SWOSTEST_BUILD...)
    return {v for v in out if isinstance(v, str) and v.isupper()}


def _calls(fn):
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                out.add(n.func.id)
            elif isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in ('T', 'mod', 'swostest'):
                out.add(n.func.attr)          # (a registered module's call into swostest: T.world8485(), mod.build())
    return out


REG = re.compile(r"^__import__\('([a-z0-9_]+)'\)\.register\(", re.M)


def modules(src=SRC):
    """swostest.py and the modules it registers scenarios from (__import__('X').register(...): fpgate, zonetest...)."""
    text = open(src, encoding='utf-8', errors='replace').read()
    return [src] + [os.path.join(HERE, m + '.py') for m in REG.findall(text) if os.path.isfile(os.path.join(HERE, m + '.py'))]


def build_index(src=SRC):
    """One row per scenario the runner knows (swostest.SCENARIOS after import: @scenario, the registered modules'
    @sc, the generated ones such as practice_*), located in its file by the AST: line, needs, self-build."""
    sys.path.insert(0, HERE)
    import probe
    import swostest
    trees = {f: ast.parse(open(f, encoding='utf-8', errors='replace').read()) for f in modules(src)}
    top = {}                                   # every top-level function of every file (helpers called by name)
    for f, t in trees.items():
        for n in t.body:
            if isinstance(n, ast.FunctionDef):
                top.setdefault(n.name, n)
    at = {}                                    # (file, first line incl. decorators) -> def node, nested ones too
    for f, t in trees.items():
        for n in ast.walk(t):
            if isinstance(n, ast.FunctionDef):
                first = min([d.lineno for d in n.decorator_list] + [n.lineno])
                at[(f, first)] = n
                at.setdefault((f, n.lineno), n)
    direct = {}

    def reads(node):
        k = id(node)
        if k not in direct:
            direct[k] = _env_reads(node)
        return direct[k]
    canary = {s: c['id'] for c in probe.CANARIES for s in c['scenarios']}
    rows = []
    for name, fn in swostest.SCENARIOS.items():
        raw = inspect.unwrap(fn)
        f, line = os.path.realpath(inspect.getsourcefile(raw) or ''), raw.__code__.co_firstlineno
        f = next((k for k in trees if os.path.realpath(k) == f), f)
        node = at.get((f, line))
        needs, selfb, end = set(), False, line
        if node is not None:
            end, line = node.end_lineno, node.lineno
            needs, seen, frontier = set(reads(node)), {node.name}, [node]
            for _ in range(DEPTH + (0 if node in top.values() else 1)):     # (a nested / generated def: one more level)
                nxt = []
                for g in frontier:
                    for h in _calls(g) - seen - PLUMBING:
                        if h in BUILDERS or h.endswith('_build'):
                            selfb = True
                        hn = top.get(h)
                        if hn is None or h in swostest.SCENARIOS:
                            continue
                        needs |= reads(hn)
                        nxt.append(hn)
                        seen.add(h)
                frontier = nxt
        doc = (inspect.getdoc(fn) or '').strip().splitlines()
        rows.append({'name': name, 'file': os.path.relpath(f, os.path.dirname(HERE)), 'line': line, 'end': end,
                     'canary': canary.get(name, ''), 'twin': name in probe.TWINS,
                     'needs': sorted(needs - {'SWOSTEST_SCENARIO'}) + (['self-build'] if selfb else []),
                     'doc': doc[0] if doc else ''})
    return rows


def index(src=SRC):
    h = hashlib.md5(open(src, 'rb').read()).hexdigest()
    for pc in modules(src)[1:] + [os.path.join(HERE, 'probe.py'), os.path.abspath(__file__)]:     # (the canary list, this generator)
        if os.path.exists(pc):
            h += hashlib.md5(open(pc, 'rb').read()).hexdigest()[:8]
    cf = os.path.join(CACHE, h + '.json')
    try:
        return json.load(open(cf))
    except (OSError, ValueError):
        pass
    rows = build_index(src)
    try:
        os.makedirs(CACHE, exist_ok=True)
        tmp = cf + f'.{os.getpid()}'
        json.dump(rows, open(tmp, 'w'))
        os.replace(tmp, cf)
    except OSError:
        pass
    return rows


def _short(needs, n=6):
    return (','.join(needs[:n]) + (f',+{len(needs) - n}' if len(needs) > n else '')) or '-'


def main(argv):
    rows = index()
    if argv[:1] == ['-show']:
        r = next((r for r in rows if r['name'] == argv[1]), None)
        if not r:
            print(f'no scenario {argv[1]!r}')
            return 1
        lines = open(os.path.join(os.path.dirname(HERE), r['file']), encoding='utf-8', errors='replace').read().splitlines()
        print(f'# {r["file"]}:{r["line"]}-{r["end"]}')
        print('\n'.join(lines[r['line'] - 2:r['end']]))
        return 0
    tsv = '-tsv' in argv
    words = [w.lower() for w in argv if w != '-tsv']
    n = 0
    for r in rows:
        hay = ' '.join([r['name'], r['file'], r['doc'], ' '.join(r['needs']), r['canary']]).lower()
        if not all(w in hay for w in words):
            continue
        n += 1
        if tsv:
            print('\t'.join([r['name'], f"{r['file']}:{r['line']}", r['canary'] or '-', 'twin' if r['twin'] else '-', ','.join(r['needs']), r['doc']]))
        else:
            where = str(r['line']) if r['file'] == 'tools/swostest.py' else f"{os.path.basename(r['file'])[:-3]}:{r['line']}"
            print(f"{r['name']:28} {where:>12} {r['canary'] or '-':4} {'twin' if r['twin'] else '-':4} "
                  f"{_short(r['needs'])}  | {r['doc'][:100]}")
    if not tsv:
        print(f'({n} of {len(rows)} scenarios)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
