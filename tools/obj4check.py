"""obj4 release-shape checker (MC 15/11, for the 4.2 rc freeze: obj1-room.md "Release order rule"). Read-only.

    python3 tools/obj4check.py c/RELxx [--allow NAME,...]     check the 8 exes of a release dir (SWOS/ + gog/)
    python3 tools/obj4check.py --grep [REF ...]               literal obj4 addresses in tools/ (worktree or git refs)
    python3 tools/obj4check.py --static [REF ...]             patch.py OBJ4_PAGES lines that floor: END page-aligned

On every exe (obj4 = the engine object; its file pages = OBJ4_PAGES of that build, read from the LE object table):
 (a) no all-zero obj4 file page: each one is listed with the bands it lies in ('no band' = a hole);
 (b) every release band that is linked (bytes in the exe or an extent in build.log) lies wholly below
     OBJ4_PAGES * 0x1000 and, if it is an obj4-map band (MAP_BANDS: obj1-room.md, the list MC named), keeps its floor
     free: END - the band's used end >= FLOOR (256 B; 128 B for the bands the obj4
     map gives 128: SETPIECE, DIFF2, SPX). The used end = max(the last non-zero byte in the band, the end of every extent
     the build's log gives inside it for that exe - 'obj4+0xA..0xB', 'obj4+0xA (N B') - so zero-filled tables that the
     log reports count as used; a band holding other bands (SLOW: NAMEFIT, TRIAL, BOX) owns up to the first of them.
     Older bands (REG, CONTI4, NAMEFIT, BOX...) get their free bytes listed as info;
 (c) a test-only band (TEST_ONLY) and a 4.3 reservation (MKT*) have no byte in a release exe.
Bands come from tools/swreg.py: every NAME_AT with a NAME_END (or NAME_SIZE), whatever the branch defines; bands named
in the obj4 map but absent from this swreg are listed as 'not in swreg' (info). --allow NAME: a zero page inside that
band is reported but not counted (an intentional zero block MC has ruled on).

--grep: hex literals 0xC000..0x3FFFF on a line with an obj4 context (obj4, OBJ4, put(4 / get(4 / target(4, add_ptr(..., 4,
'4, 0x'), in tools/**/*.py / *.c / *.asm, swreg.py itself excluded; each with the swreg symbol of the same value when there
is one. Comment-only lines are listed apart (--grep-code: code lines only)."""
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

PAGE = 0x1000
FLOOR = 256
FLOOR_128 = {'SETPIECE', 'DIFF2', 'SPX'}            # obj1-room.md obj4 map: '>= 128 B left'
TEST_ONLY = {'FPORT', 'CDKN', 'FPORT2', 'SP_METER', 'DIFF_TC'}
UNLINKED_PREFIX = ('MKT',)                          # 4.3 reservations: no bytes in 4.2
MAP_BANDS = ['DRIB1V1', 'DIFF', 'KITS', 'SWEFILE', 'S7SWAP', 'OBJ1MV', 'SETPIECE', 'FPORT', 'S7GEO', 'DIFF2', 'SPX',
             'CDKN', 'PRACTICE', 'FPORT2', 'S3C', 'MKTHOOK', 'MKTLOAD', 'MKTAGE', 'SP_METER', 'DIFF_TC']
EXES = [f'{d}/{e}.EXE' for d in ('SWOS', 'gog') for e in ('ITALIAN', 'ENGLISH', 'FRENCH', 'GERMAN')]


def bands(mod=None):
    """[(name, at, end)] sorted by address, from swreg's NAME_AT + NAME_END / NAME_SIZE pairs."""
    if mod is None:
        import swreg as mod
    g = vars(mod)
    out = []
    for k, v in g.items():
        if k.endswith('_AT') and isinstance(v, int):
            n = k[:-3]
            e = g.get(n + '_END')
            if not isinstance(e, int) and isinstance(g.get(n + '_SIZE'), int):
                e = v + g[n + '_SIZE']
            if isinstance(e, int) and e > v:
                out.append((n, v, e))
    if isinstance(g.get('REG_AT'), int) and isinstance(g.get('OBJ4_END'), int):
        out = [b for b in out if b[0] != 'REG'] + [('REG', g['REG_AT'], g['OBJ4_END'])]
    return sorted(out, key=lambda b: (b[1], b[2]))


def kind(name):
    if name in TEST_ONLY:
        return 'test-only'
    if name.startswith(UNLINKED_PREFIX):
        return 'unlinked (4.3)'
    return 'release'


def log_extents(log_text):
    """{exe relative path: [(start, end)]} of the obj4 extents in a release build.log (a section ends at 'OK <path>')."""
    out, cur = {}, []
    rng = re.compile(r'obj4\+0x([0-9a-fA-F]+)\s*\.\.\s*(?:obj4\+)?0x([0-9a-fA-F]+)\b(?! zero)')   # ('... zero': a
    # parked band the build zero-fills, e.g. 'match speed PARKED: obj4+0xc000..0xc400 zero')
    siz = re.compile(r'obj4\+0x([0-9a-fA-F]+) \((\d+) B')
    for ln in log_text.splitlines():
        m = re.match(r'OK (.*/(SWOS|gog)/[A-Z]+\.EXE)$', ln.strip())
        if m:
            out[m.group(1).split('/')[-2] + '/' + m.group(1).split('/')[-1]] = cur
            cur = []
            continue
        for a, b in rng.findall(ln):
            cur.append((int(a, 16), int(b, 16)))
        for a, n in siz.findall(ln):
            cur.append((int(a, 16), int(a, 16) + int(n)))
    return out


def check_obj4(o4, bl, extents=(), allow=()):
    """o4: obj4's file bytes; bl: bands(); extents: [(start, end)] of the log. -> (fails, infos, rows):
    rows = [(name, kind, at, end, used_end or None, free or None)]."""
    fails, infos, rows = [], [], []
    size = len(o4)
    for p in range(size // PAGE):
        if any(o4[p * PAGE:(p + 1) * PAGE]):
            continue
        inb = [n for n, a, e in bl if a < (p + 1) * PAGE and e > p * PAGE]
        msg = f'zero page obj4+{p * PAGE:#x} ({", ".join(inb) if inb else "no band"})'
        if inb and all(n in allow for n in inb):
            infos.append(msg + ' [allowed]')
        else:
            fails.append('(a) ' + msg)
    for n, a, e0 in bl:
        k = kind(n)
        inner = [a2 for n2, a2, e2 in bl if n2 != n and a < a2 and e2 <= e0]
        e = min(inner) if inner else e0         # (a band holding others - SLOW's page 13 - owns up to the first one:
        nz = [i for i in range(a, min(e, size)) if o4[i]] if a < size else []
        ext = [y for x, y in extents if a <= x < e]
        used = None
        if nz or ext:
            used = max(([nz[-1] + 1] if nz else []) + [min(y, e) for y in ext])
        free = (e - used) if used is not None else None
        rows.append((n, k, a, e, used, free))
        if k != 'release':
            if nz:
                fails.append(f'(c) {k} band {n} {a:#x}..{e:#x} has bytes in a release exe '
                             f'({len(nz)} non-zero, {nz[0]:#x}..{nz[-1]:#x})')
            continue
        if used is None:
            continue                                # (not linked in this build)
        if e > size:
            fails.append(f'(b) band {n} {a:#x}..{e:#x} crosses OBJ4_PAGES ({size // PAGE:#x} pages, end {size:#x})')
        fl = 128 if n in FLOOR_128 else FLOOR
        if free < fl and n not in MAP_BANDS:
            infos.append(f'(b) band {n} {a:#x}..{e:#x}: {free} B free (not an obj4-map band: no floor, info)')
        elif free < fl:
            fails.append(f'(b) band {n} {a:#x}..{e:#x}: {free} B free, floor {fl} B (used to {used:#x})')
    return fails, infos, rows


def check_release(rel, mod=None, allow=()):
    """-> (ok, report text) for the 8 exes of release dir rel."""
    import le
    bl = bands(mod)
    logp = os.path.join(rel, 'build.log')
    ext = log_extents(open(logp, errors='replace').read()) if os.path.exists(logp) else {}
    out, bad = [], 0
    names = {b[0] for b in bl}
    miss = [n for n in MAP_BANDS if n not in names]
    out.append(f'obj4check {rel}: {len(bl)} bands from swreg; obj4 map bands not in this swreg: {", ".join(miss) or "none"}')
    first_rows = None
    for x in EXES:
        p = os.path.join(rel, x)
        if not os.path.exists(p):
            out.append(f'{x}: missing')
            bad += 1
            continue
        L = le.LE(p)
        o4 = L.obj_bytes(4)
        f, i, rows = check_obj4(o4, bl, ext.get(x, []), allow)
        bad += bool(f)
        out.append(f'{x}: OBJ4_PAGES {L.obj(4).npages:#x} (file {len(o4):#x}), {"FAIL" if f else "OK"}'
                   + (f' - {len(f)} finding(s)' if f else '') + ('' if x in ext else ' (no build.log section)'))
        out += ['  ' + s for s in f + i]
        if first_rows is None:
            first_rows = (x, rows)
    if first_rows:
        out.append(f'bands ({first_rows[0]}; used end = last byte / log extent):')
        for n, k, a, e, u, fr in first_rows[1]:
            out.append(f'  {n:<10} {k:<15} {a:#07x}..{e:#07x} '
                       + ('not linked' if u is None else f'used to {u:#07x}, {fr} B free'))
    return bad == 0, '\n'.join(out)


GREP_CTX = re.compile(r"obj4|OBJ4|(?:put|get|target|obj_bytes)\(\s*4\b|add_ptr\([^)]*,\s*4\s*,|\b4,\s*0x")
HEX = re.compile(r'\b0x([0-9A-Fa-f]{4,5})\b')


def split_code(f, text):
    """[(lineno, code part, comment part)] of a source file: Python '#' comments and docstrings, C / asm '//' '/* */' ';'
    comments go to the comment part."""
    out, doc, cblk = [], None, False
    py = f.endswith('.py')
    for i, ln in enumerate(text.splitlines(), 1):
        code, com = ln, ''
        if py:
            if doc:
                k = ln.find(doc)
                if k < 0:
                    out.append((i, '', ln))
                    continue
                code, com, doc = ln[k + 3:], ln[:k + 3], None
            m = re.search(r'("""|\'\'\')', code)
            if m and code[:m.start()].strip() in ('', 'r', 'f') or (m and code[:m.start()].rstrip().endswith(('=', '(', ','))):
                q = m.group(1)
                rest = code[m.end():]
                if q in rest:
                    com += code[m.start():m.end() + rest.index(q) + 3]
                    code = code[:m.start()] + rest[rest.index(q) + 3:]
                else:
                    com += code[m.start():]
                    code, doc = code[:m.start()], q
            k = code.find('#')
            if k >= 0:
                code, com = code[:k], com + code[k:]
        else:
            if cblk:
                k = ln.find('*/')
                if k < 0:
                    out.append((i, '', ln))
                    continue
                code, com, cblk = ln[k + 2:], ln[:k + 2], False
            k = code.find('/*')
            if k >= 0 and '*/' not in code[k:]:
                code, com, cblk = code[:k], com + code[k:], True
            com += ' '.join(re.findall(r'/\*.*?\*/', code))
            code = re.sub(r'/\*.*?\*/', '', code)
            for c in ('//', ';') if f.endswith('.asm') else ('//',):
                k = code.find(c)
                if k >= 0:
                    code, com = code[:k], com + code[k:]
        out.append((i, code, com))
    return out


def grep_files(files, mod=None):
    """files: {name: text} -> [(file, lineno, literal, swreg symbol or '', is_comment)]: hex 0xC000..0x3FFFF on a line
    with an obj4 context (the context may sit in the line's comment: 'obj4+0x...' notes)."""
    vals = {}
    if mod is None:
        import swreg as mod
    for k, v in vars(mod).items():
        if k.isupper() and isinstance(v, int):
            vals.setdefault(v, []).append(k)
    out = []
    for f, t in files.items():
        if os.path.basename(f.split(':')[-1]) in ('swreg.py', 'obj4check.py'):
            continue
        for n, code, com in split_code(f, t):
            if not GREP_CTX.search(code + com):
                continue
            for part, is_com in ((code, False), (com, True)):
                for h in HEX.findall(part):
                    v = int(h, 16)
                    if 0xC000 <= v < 0x40000:
                        out.append((f, n, '0x' + h, '/'.join(vals.get(v, [])), is_com))
    return out


ASSIGN = re.compile(r'\s*(?:[A-Z][A-Z0-9_, ]*=|#define\s)')


def grep_assign(files):
    """files: {name: text}. Page-region constants (0x100-aligned, 0xC000..0x3FFFF) assigned at top level
    (NAME = 0x... / #define) in a module that names obj4 - a band address kept outside swreg is one of these; obj2 / obj3
    constants of such modules show up too (check by hand). -> [(file, lineno, literal, swreg symbol or '')]."""
    import swreg
    vals = {}
    for k, v in vars(swreg).items():
        if k.isupper() and isinstance(v, int):
            vals.setdefault(v, []).append(k)
    out = []
    for f, t in files.items():
        if os.path.basename(f.split(':')[-1]) in ('swreg.py', 'obj4check.py') or not re.search(r'obj4|OBJ4|text_obj=4', t):
            continue
        for i, ln in enumerate(t.splitlines(), 1):
            if ASSIGN.match(ln):
                for h in HEX.findall(re.split(r'#(?!define)|//', ln)[0]):
                    v = int(h, 16)
                    if 0xC000 <= v < 0x40000 and v % 0x100 == 0:
                        out.append((f, i, '0x' + h, '/'.join(vals.get(v, []))))
    return out


def source_files(refs=(), root=None):
    """{name: text} of tools/*.py / *.c / *.asm in the worktree (refs empty) or at each git ref ('ref:path')."""
    root = root or os.path.dirname(TOOLS)
    out = {}
    for ref in refs or [None]:
        if ref is None:
            import glob
            for p in sorted(sum((glob.glob(os.path.join(root, 'tools', '**', e), recursive=True)
                                 for e in ('*.py', '*.c', '*.asm')), [])):
                out[os.path.relpath(p, root)] = open(p, errors='replace').read()
            continue
        ls = subprocess.run(['git', '-C', root, 'ls-tree', '-r', '--name-only', ref, 'tools/'], capture_output=True,
                            text=True).stdout.split()
        for p in ls:
            if p.endswith(('.py', '.c', '.asm')):
                out[f'{ref}:{p}'] = subprocess.run(['git', '-C', root, 'show', f'{ref}:{p}'], capture_output=True,
                                                   text=True, errors='replace').stdout
    return out


def grep_source(refs=(), root=None):
    return grep_files(source_files(refs, root))


def ref_text(path, ref=None, root=None):
    """tools/<path> of the worktree, or at git ref."""
    root = root or os.path.dirname(TOOLS)
    if ref is None:
        p = os.path.join(root, 'tools', path)
        return open(p, errors='replace').read() if os.path.exists(p) else None
    r = subprocess.run(['git', '-C', root, 'show', f'{ref}:tools/{path}'], capture_output=True, text=True, errors='replace')
    return r.stdout if r.returncode == 0 else None


def swreg_ns(text):
    """swreg's constants from its source (exec'd alone: it imports nothing at module level but struct)."""
    ns = {}
    exec(compile(text, 'swreg.py', 'exec'), ns)
    return ns


def static_pages(ref=None, root=None):
    """MC 15/11: every OBJ4_PAGES line of tools/patch.py that floors (X // 0x1000 with no + 0xFFF / -(-X // ...) /
    + 1) needs X page-aligned, or the band's last page is past OBJ4_PAGES. X = swreg.NAME or module.page_end() (its
    return expression evaluated with swreg). -> [(lineno, expr, value or None, status)], status 'ok' / 'NOT ALIGNED' /
    'rounds up' / 'unresolved'."""
    src = ref_text('patch.py', ref, root)
    sw = swreg_ns(ref_text('swreg.py', ref, root))
    out = []
    for n, ln in enumerate(src.splitlines(), 1):
        code = ln.split('#')[0]
        if 'OBJ4_PAGES' not in code or '0x1000' not in code or '=' not in code:
            continue
        m = re.search(r'max\(\s*swe\.OBJ4_(?:PAGES|BASE)\s*,\s*(.*)\)\s*$', code.strip())
        if not m:
            continue
        e = m.group(1).strip()
        if re.search(r'\+\s*0xFFF|-\(-|//\s*0x1000\s*\+\s*1', e, re.I):
            out.append((n, e, None, 'rounds up'))
            continue
        mm = re.fullmatch(r'(.+?)\s*//\s*0x1000', e)
        x = mm.group(1).strip() if mm else None
        if x and x.startswith('(') and x.endswith(')'):
            x = x[1:-1].strip()
        val = None
        try:
            if x and re.fullmatch(r'swreg\.\w+', x):
                val = sw[x.split('.')[1]]
            elif x and re.fullmatch(r'\w+\.page_end\(\)', x):
                mod = x.split('.')[0]
                ms = ref_text(mod + '.py', ref, root) or ''
                fm = re.search(r'def page_end\(\):.*?return (.+?)(?:\s*#.*)?\n', ms, re.S)
                val = eval(fm.group(1), {'swreg': type('S', (), sw)}) if fm else None
            elif x and re.fullmatch(r'\w+\.[A-Z_][A-Z0-9_]*', x):          # (a module constant: spmeter.SPM_END)
                mod, k = x.split('.')
                ms = ref_text(mod + '.py', ref, root) or ''
                fm = re.search(r'^' + k + r'\s*=\s*([^#\n]+)', ms, re.M)
                val = eval(fm.group(1), {'swreg': type('S', (), sw)}) if fm else None
        except Exception:
            val = None
        st = 'unresolved' if val is None else ('ok' if val % 0x1000 == 0 else 'NOT ALIGNED')
        out.append((n, e, val, st))
    return out


def main(argv):
    if argv and argv[0] in ('--grep', '--grep-code'):
        hits = grep_source(argv[1:])
        code = [h for h in hits if not h[4]]
        com = [h for h in hits if h[4]]
        print(f'obj4check --grep: {len(code)} code line hits, {len(com)} comment hits (read-only)')
        for f, n, lit, sym, _ in code:
            print(f'{f}:{n}: {lit}' + (f'  = swreg.{sym}' if sym else ''))
        asg = grep_assign(source_files(argv[1:]))
        print(f'-- page-region constants assigned in modules that name obj4 ({len(asg)}; obj2 / obj3 ones too: by hand):')
        for f, n, lit, sym in asg:
            print(f'{f}:{n}: {lit}' + (f'  = swreg.{sym}' if sym else ''))
        if argv[0] == '--grep':
            print('-- comments:')
            for f, n, lit, sym, _ in com:
                print(f'{f}:{n}: {lit}' + (f'  = swreg.{sym}' if sym else ''))
        return 0
    if argv and argv[0] == '--static':
        bad = 0
        for ref in argv[1:] or [None]:
            rows = static_pages(ref)
            print(f'obj4check --static {ref or "(worktree)"}: tools/patch.py OBJ4_PAGES lines that floor')
            for n, e, v, st in rows:
                bad += st in ('NOT ALIGNED', 'unresolved')
                print(f'  patch.py:{n}: {e}' + (f' = {v:#x}' if v is not None else '') + f'  {st}')
        print('obj4check --static:', 'PASS' if not bad else f'FAIL ({bad})')
        return 1 if bad else 0
    if not argv:
        print(__doc__)
        return 2
    allow = []
    if '--allow' in argv:
        allow = argv[argv.index('--allow') + 1].split(',')
    ok, rep = check_release(argv[0], allow=allow)
    print(rep)
    print('obj4check:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
