"""The harness has no two top-level definitions of one name (MC 17/11): Python silently keeps only the later one, so
a merge that brings a second `def fr_syms` / `def fr_sites` shadows the first for every caller (42-frtest + 42-frnd,
17/11: two fr_syms, and a skeleton fr_sites over 4.0.6's benchx one). An ast walk of tools/swostest.py: every top-level
def / class name once (a redefinition inside if / try is not top-level and stays allowed). Host only."""
import ast
import collections
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..'))


def dups(path):
    tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    seen = collections.defaultdict(list)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            seen[n.name].append(n.lineno)
    return {k: v for k, v in seen.items() if len(v) > 1}


def test_swostest_no_duplicate_defs():
    d = dups(os.path.join(TOOLS, 'swostest.py'))
    assert not d, f'swostest.py: top-level names defined more than once (the later one silently wins): {d}'


def test_dups_finds_one():
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as t:
        t.write('def a():\n    pass\n\n\ndef b():\n    pass\n\n\ndef a():\n    pass\n')
    try:
        assert dups(t.name) == {'a': [1, 9]}
    finally:
        os.unlink(t.name)
