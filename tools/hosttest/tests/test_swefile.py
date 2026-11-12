"""4.2: the engine's file layer (tools/swefile.h) under Unicorn, linked by cobj.link as swe.c links it: int 21h served
by a DOS of this test's own (a dict of files, handles, the DOS error codes DOS/4GW passes on), with faults injected at
every DOS call of a save:
- an error at call k (access denied): an error code back, NAME the old file (or, at the last rename, absent with a
  complete NAME.MK! that swe_recover puts back), no temporary file left but a complete MK!;
- a short write (disk full): SWEF_ESHORT, NAME the old file, no temporary file;
- a power cut before call k, and a write torn halfway: after swe_recover (a new run: no handle open), NAME is the old
  file or the new one, never a partial one; with no old file, absent or the new one; no MK$ / MK! left; the next
  save works.
Plus the names (NAME.EXT -> NAME.MK$, directories with dots, no extension, too long) and the plain calls' codes."""
import os
import struct
import sys
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import cobj  # noqa: E402

B1, DATA, STK, RET = 0x100000, 0x200000, 0x300000, 0x3F0000
NAMES, BUF, OUT = DATA, DATA + 0x1000, DATA + 0x800
ROOTS = ['swe_fopen_r', 'swe_fopen_w', 'swe_fread', 'swe_fwrite', 'swe_fclose', 'swe_fremove', 'swe_frename',
         'swe_tmpname', 'swe_save_atomic', 'swe_recover']
SRC = '#define SWEFILE_IMPL\n#include "%s/swefile.h"\n'
ESHORT, ENAME = -0x101, -0x102


class Rec:
    class le:
        page_size = 0x100000

    def __init__(self):
        self.mem, self.ptrs, self.rels = {}, [], []

    def put(self, objn, off, data):
        for i, b in enumerate(data):
            self.mem[(objn, off + i)] = b

    def add_ptr(self, objn, off, tobj, toff):
        self.ptrs.append((objn, off, tobj, toff))

    def add_rel(self, objn, off, tobj, toff):
        self.rels.append((objn, off, tobj, toff))


_CODE = None


def _code():
    global _CODE
    if _CODE is None:
        with tempfile.TemporaryDirectory() as t:
            src = os.path.join(t, 'swf.c')
            open(src, 'w').write(SRC % TOOLS)
            os.environ['COBJ_CACHE'] = t
            try:
                obj = cobj.compile_c(src, sections=True)
            finally:
                del os.environ['COBJ_CACHE']
        p = Rec()
        syms, end, bss = cobj.link(p, obj, 0, (1, 0x8000), externs={}, roots=ROOTS)
        assert not p.rels, p.rels
        img = bytearray(max(end, 0x8000) + 0x1000)
        for (o, off), b in p.mem.items():
            img[off] = b
        for o, off, tobj, toff in p.ptrs:
            struct.pack_into('<I', img, off, B1 + toff)
        _CODE = bytes(img), {k: B1 + v[1] for k, v in syms.items()}, end
    return _CODE


class Dos:
    """Files {NAME: bytes}, directories, handles; faults: fail {k: code}, short {k: n}, cut = k (stop before call k),
    tear = k (call k, a write, writes half, then the power goes)."""

    def __init__(self, files=None, fail=None, short=None, cut=None, tear=None):
        self.files = dict(files or {})
        self.dirs = {''}
        self.h, self.n, self.log = {}, 0, []
        self.fail, self.short, self.cut, self.tear = fail or {}, short or {}, cut, tear
        self.stopped = False

    def name(self, uc, a):
        s = bytes(uc.mem_read(a, 128)).split(b'\0')[0].decode('latin-1').upper()
        return s, s.rsplit('\\', 1)[0] if '\\' in s else ''

    def intr(self, uc, intno, _):
        from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, \
            UC_X86_REG_EDI, UC_X86_REG_EFLAGS
        assert intno == 0x21, intno
        rd = uc.reg_read
        ax, bx, cx, dx, di = (rd(r) for r in (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                                              UC_X86_REG_EDI))
        k = self.n
        self.n += 1
        ah = ax >> 8 & 0xFF
        self.log.append(ah)
        if k == self.cut:
            self.stopped = True
            uc.emu_stop()
            return

        def ret(v, err=False):
            uc.reg_write(UC_X86_REG_EAX, v)
            fl = rd(UC_X86_REG_EFLAGS)
            uc.reg_write(UC_X86_REG_EFLAGS, fl | 1 if err else fl & ~1)

        if k in self.fail:
            return ret(self.fail[k], True)
        if ah in (0x3C, 0x3D):
            nm, d = self.name(uc, dx)
            if d not in self.dirs:
                return ret(3, True)
            if ah == 0x3D and nm not in self.files:
                return ret(2, True)
            if ah == 0x3C:
                self.files[nm] = b''
            h = 5 + len(self.h)
            while h in self.h:
                h += 1
            self.h[h] = [nm, 0]
            return ret(0xABCD0000 | h)            # (the high word: whatever the extender leaves - the layer masks it)
        if ah in (0x3E, 0x3F, 0x40):
            f = self.h.get(bx)
            if not f:
                return ret(6, True)
            if ah == 0x3E:
                del self.h[bx]
                return ret(0)
            nm, pos = f
            if ah == 0x3F:
                d = self.files[nm][pos:pos + cx]
                uc.mem_write(dx, d)
                f[1] += len(d)
                return ret(len(d))
            n = self.short.get(k, cx)
            if k == self.tear:
                n = cx // 2
            d = bytes(uc.mem_read(dx, n))
            old = self.files[nm]
            self.files[nm] = old[:pos] + d + old[pos + n:]
            f[1] += n
            if k == self.tear:
                self.stopped = True
                uc.emu_stop()
                return
            return ret(n)
        if ah == 0x41:
            nm, _ = self.name(uc, dx)
            if nm not in self.files:
                return ret(2, True)
            if any(f[0] == nm for f in self.h.values()):
                return ret(5, True)
            del self.files[nm]
            return ret(0)
        if ah == 0x56:
            a, _ = self.name(uc, dx)
            b, _ = self.name(uc, di)
            if a not in self.files:
                return ret(2, True)
            if b in self.files:
                return ret(5, True)
            self.files[b] = self.files.pop(a)
            return ret(0)
        raise AssertionError(f'int 21h ah {ah:#x}')


def _run(dos, fn, *args):
    """fn(args) on a fresh machine: strings and bytes args are put in DATA; returns eax (signed) or None (cut)"""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_INTR
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
    img, syms, _ = _code()
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(B1, len(img) + 0xFFF & ~0xFFF)
    uc.mem_write(B1, img)
    uc.mem_map(DATA, 0x100000)
    uc.mem_map(STK, 0x100000)
    uc.hook_add(UC_HOOK_INTR, dos.intr)
    at, vals = NAMES, []
    for a in args:
        if isinstance(a, str):
            uc.mem_write(at, a.encode('latin-1') + b'\0')
            vals.append(at)
            at += 0x80
        elif isinstance(a, (bytes, bytearray)):
            uc.mem_write(BUF, bytes(a))
            vals.append(BUF)
        else:
            vals.append(a & 0xFFFFFFFF)
    sp = STK + 0xF0000
    uc.mem_write(sp, struct.pack(f'<{1 + len(vals)}I', RET, *vals))
    uc.reg_write(UC_X86_REG_ESP, sp)
    uc.emu_start(syms[fn], RET)
    if dos.stopped:
        return None
    assert uc.reg_read(UC_X86_REG_ESP) == sp + 4
    dos.uc = uc
    return struct.unpack('<i', struct.pack('<I', uc.reg_read(UC_X86_REG_EAX)))[0]


def _pat(seed, n):
    out = bytearray(n)
    for i in range(n):
        seed = (seed * 1103515245 + 12345) & 0xFFFFFFFF
        out[i] = seed >> 16 & 0xFF
    return bytes(out)


def test_swefile_names_and_calls():
    bad = []
    for name, want in (('TEST.MKT', 'TEST.MK$'), ('SAVES\\CAR.DAT', 'SAVES\\CAR.MK$'), ('A.B\\NOEXT', 'A.B\\NOEXT.MK$'),
                       ('C:\\X\\Y.Z', 'C:\\X\\Y.MK$'), ('NOEXT', 'NOEXT.MK$'), ('D:TT.1', 'D:TT.MK$')):
        d = Dos()
        r = _run(d, 'swe_tmpname', name, OUT, ord('$'))
        got = bytes(d.uc.mem_read(OUT, 96)).split(b'\0')[0].decode()
        if r or got != want:
            bad.append(f'tmpname {name}: {r} {got!r}')
    d = Dos()
    if _run(d, 'swe_tmpname', 'X' * 75 + '.MKT', OUT, ord('$')) != ENAME:
        bad.append('a long name: no SWEF_ENAME')
    if _run(Dos(), 'swe_save_atomic', 'X' * 75 + '.MKT', b'1', 1) != ENAME:
        bad.append('save: a long name not refused')
    d = Dos()
    if _run(d, 'swe_fopen_r', 'NOFILE.MKT') != -2:
        bad.append('open of a missing file != -2')
    h = _run(d, 'swe_fopen_w', 'A.MKT')
    if h != 5:
        bad.append(f'create: handle {h:#x} (the high word not masked?)')
    if _run(d, 'swe_fwrite', 5, b'abc', 0) != 0 or d.log[-1] != 0x3C:
        bad.append('a 0-byte write reached DOS (it truncates there)')
    if _run(d, 'swe_fwrite', 5, b'abc', 3) != 3 or _run(d, 'swe_fclose', 5) != 0 or d.files['A.MKT'] != b'abc':
        bad.append(f'write / close: {d.files}')
    if _run(d, 'swe_fclose', 5) != -6:
        bad.append('close of a closed handle != -6')
    if _run(d, 'swe_save_atomic', 'NODIR\\X.MKT', b'1', 1) != -3 or set(d.files) != {'A.MKT'}:
        bad.append(f'save into a missing directory: {d.files}')
    d = Dos({'B.MKT': b'old', 'A.MKT': b'x'})
    if _run(d, 'swe_frename', 'A.MKT', 'B.MKT') != 0 or d.files != {'B.MKT': b'x'}:
        bad.append(f'rename onto an existing file: {d.files}')
    if _run(d, 'swe_fremove', 'B.MKT') != 0 or _run(d, 'swe_fremove', 'B.MKT') != -2:
        bad.append('remove: codes')
    d = Dos({'R.MK!': b'new'})
    if _run(d, 'swe_recover', 'R.MKT') != 1 or d.files != {'R.MKT': b'new'}:
        bad.append(f'recover of the window: {d.files}')
    d = Dos({'R.MK$': b'ne'})
    if _run(d, 'swe_recover', 'R.MKT') != 0 or d.files:
        bad.append(f'recover: a cut MK$ taken or left: {d.files}')
    d = Dos({'R.MKT': b'old', 'R.MK!': b'new', 'R.MK$': b'ne'})
    if _run(d, 'swe_recover', 'R.MKT') != 1 or d.files != {'R.MKT': b'new'}:
        bad.append(f'recover: NAME + MK! (cut point 2) not the MK!: {d.files}')
    d = Dos({'R.MKT': b'old'})
    if _run(d, 'swe_recover', 'R.MKT') != 0 or d.files != {'R.MKT': b'old'}:
        bad.append(f'recover with nothing to do: {d.files}')
    big = _pat(7, 200000)
    d = Dos({'T.MKT': b'old'})
    if _run(d, 'swe_save_atomic', 'T.MKT', big, len(big)) != 0 or d.files != {'T.MKT': big} or d.h:
        bad.append(f'a 200000 B save: {sorted(d.files)}, handles {d.h}')
    calls = len(d.log)
    return not bad, '; '.join(bad) or (f'names, codes, rename over, recover (MK$ removed, MK! wins), a 200000 B save in {calls} '
                                       f'DOS calls, code {_code()[2]} B')


def _state(files, old, new):
    """NAME after recover: 'old' / 'new' / 'none' / 'BAD ...'"""
    v = files.get('S.MKT')
    if v is None:
        return 'none'
    return 'old' if v == old else 'new' if v == new else f'BAD {len(v)} B'


def test_swefile_faults():
    new = _pat(11, 70000)
    bad, seen = [], {}
    for old in (_pat(12, 5000), None):
        base = {'S.MKT': old} if old is not None else {}
        clean = Dos(base)
        assert _run(clean, 'swe_save_atomic', 'S.MKT', new, len(new)) == 0
        n = len(clean.log)
        tag = 'old' if old is not None else 'first'
        for k in range(n):
            d = Dos(base, fail={k: 5})
            r = _run(d, 'swe_save_atomic', 'S.MKT', new, len(new))
            st = _state(d.files, old, new)
            rest = set(d.files) - {'S.MKT'}
            closefail = d.log[k] == 0x3E         # (a failed close: its handle and the MK$ stay - never taken for a file)
            ok_left = {'S.MK!', 'S.MK$'} if closefail else {'S.MK!'}
            if (r >= 0 and st != 'new') or st.startswith('BAD') or (d.h and not closefail):
                bad.append(f'{tag} fail@{k} (ah {d.log[k]:#x}): rc {r} NAME {st} handles {d.h}')
            if st == 'none' and old is not None:     # (only the last rename's window: MK! complete, recover puts it back)
                d2 = Dos(d.files)
                if rest != {'S.MK!'} or _run(d2, 'swe_recover', 'S.MKT') != 1 or _state(d2.files, old, new) != 'new':
                    bad.append(f'{tag} fail@{k}: NAME gone, left {sorted(rest)}')
            elif rest - ok_left and r < 0:       # (a complete MK! may stay when the last rename's remove fails)
                bad.append(f'{tag} fail@{k}: rc {r}, temporary files left {sorted(rest)}')
            seen.setdefault(f'fail:{st}', 0)
            seen[f'fail:{st}'] += 1
        for k in [i for i, ah in enumerate(clean.log) if ah == 0x40]:
            d = Dos(base, short={k: 100})
            r = _run(d, 'swe_save_atomic', 'S.MKT', new, len(new))
            if r != ESHORT or _state(d.files, old, new) != ('old' if old is not None else 'none') or len(d.files) != (old is not None):
                bad.append(f'{tag} short@{k}: rc {r} files {sorted(d.files)}')
        cuts = [('cut', k) for k in range(n + 1)] + [('tear', k) for k, ah in enumerate(clean.log) if ah == 0x40]
        for how, k in cuts:
            d = Dos(base, **{how: k})
            r = _run(d, 'swe_save_atomic', 'S.MKT', new, len(new))
            d2 = Dos(d.files)                    # (power back: a new run, no handle)
            rr = _run(d2, 'swe_recover', 'S.MKT')
            st = _state(d2.files, old, new)
            ok = st in ('old', 'new') if old is not None else st in ('none', 'new')
            if r is None and k >= n:
                bad.append(f'{tag} {how}@{k}: stopped past the last call')
            if not ok or rr < 0 or set(d2.files) - {'S.MKT'}:
                bad.append(f'{tag} {how}@{k}: recover {rr}, NAME {st}, files {sorted(d.files)}')
            d3 = Dos(d2.files)
            if _run(d3, 'swe_save_atomic', 'S.MKT', new[::-1], len(new)) != 0 or d3.files.get('S.MKT') != new[::-1] \
                    or set(d3.files) != {'S.MKT'}:
                bad.append(f'{tag} {how}@{k}: the next save: {sorted(d3.files)}')
            seen.setdefault(f'cut:{st}', 0)
            seen[f'cut:{st}'] += 1
    return not bad, '; '.join(bad[:6]) or f'{n} DOS calls per save, every one failed / cut (+ torn writes, short ' \
                                         f'writes), old file and first save: outcomes {seen}'
