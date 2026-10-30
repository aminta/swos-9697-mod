"""C code in the exe: clang compiles a C file for a 486 (ELF i386 relocatable object), link() lays it into an obj1
cave (code, read-only data, data) and a zero-filled obj2 area (.bss), applying the relocations: R_386_32 -> an LE
32-bit offset fixup (two records when it straddles a page, as the Watcom linker does), R_386_PC32 -> a relative
displacement (calls inside the code, or to the game's routines given as externs).

The C file must be freestanding: no library calls (link() fails on any undefined symbol that is not an extern),
cdecl functions (ebx, esi, edi, ebp preserved). Called from asm with pushad / popad around."""
import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile

CFLAGS = ['-target', 'i686-unknown-none-elf', '-march=i486', '-ffreestanding', '-fno-pic', '-fno-pie', '-Os',
          '-fno-stack-protector', '-mno-sse', '-mno-mmx', '-fno-builtin', '-fno-asynchronous-unwind-tables',
          '-fno-unwind-tables', '-Wall', '-Werror']


CACHE = os.environ.get('COBJ_CACHE') or os.path.expanduser('~/swos-mod/internal/swostest/cobj')


def _src_key(src, flags):
    """The object's identity without the compiler: the flags, the C file and its #include "..." files (recursive)."""
    h, todo, seen = hashlib.sha256(repr((CFLAGS, list(flags))).encode()), [os.path.abspath(src)], set()
    while todo:
        f = todo.pop()
        if f in seen or not os.path.isfile(f):
            continue
        seen.add(f)
        b = open(f, 'rb').read()
        h.update(os.path.basename(f).encode() + b'\0' + b)
        todo += [os.path.join(os.path.dirname(f), i.decode()) for i in re.findall(rb'^\s*#\s*include\s*"([^"]+)"', b, re.M)]
    return h.hexdigest()[:24]


def compile_c(src, flags=()):
    """The object file's bytes. Every object compiled is kept in CACHE/<key>.o (key: _src_key). The Apple clang of
    one macOS gives other code than another's (4.0.5: MacMiniM1Server's clang 15 vs clang 21 here - gplay.c 901 bytes
    longer, an exe one page longer, world_gplay_poule FAILing there only): with COBJ_REF=1 (remote_run.sh on the
    server) a cached object - this Mac's, synced - is used instead of compiling; a missing one is compiled with the
    local clang, a warning on stderr and its key in COBJ_MISS_LOG (the build is not reused then)."""
    key = _src_key(src, flags)
    cached = os.path.join(CACHE, key + '.o')
    if os.environ.get('COBJ_REF'):
        if os.path.exists(cached):
            return open(cached, 'rb').read()
        print(f'COBJ WARNING: no reference object for {os.path.basename(src)} {list(flags)} ({key}): compiled with '
              'this Mac\'s clang, the build may differ from the reference Mac\'s', file=sys.stderr, flush=True)
        if os.environ.get('COBJ_MISS_LOG'):
            open(os.environ['COBJ_MISS_LOG'], 'a').write(f'{key} {os.path.basename(src)} {" ".join(flags)}\n')
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, 'c.o')
        r = subprocess.run(['clang', *CFLAGS, *flags, '-c', src, '-o', out], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        obj = open(out, 'rb').read()
    if not os.environ.get('COBJ_REF'):              # (the reference Mac: its objects, for the server's builds)
        try:
            os.makedirs(CACHE, exist_ok=True)
            if not os.path.exists(cached) or open(cached, 'rb').read() != obj:
                open(cached + f'.tmp{os.getpid()}', 'wb').write(obj)
                os.replace(cached + f'.tmp{os.getpid()}', cached)
        except OSError:
            pass
    return obj


def _elf(o):
    assert o[:4] == b'\x7fELF' and o[4] == 1 and o[5] == 1, 'not ELF32 LSB'
    e_type, e_machine = struct.unpack_from('<HH', o, 16)
    assert e_type == 1 and e_machine == 3, (e_type, e_machine)
    shoff, = struct.unpack_from('<I', o, 32)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', o, 46)
    secs = [dict(zip(('name', 'type', 'flags', 'addr', 'offset', 'size', 'link', 'info', 'align', 'entsize'),
                     struct.unpack_from('<10I', o, shoff + i * shentsize))) for i in range(shnum)]
    strs = secs[shstrndx]
    for s in secs:
        a = strs['offset'] + s['name']
        s['name'] = o[a:o.index(b'\0', a)].decode()
    return secs


def link(p, obj, text_at, bss_at, externs=None, limit=None):
    """obj = compile_c() bytes; text_at = obj1 offset of the cave; bss_at = (obj, offset) of the zero-filled area;
    externs = {name: (obj, offset)}. Returns ({global symbol: (obj, offset)}, end of the obj1 part, bss size)."""
    externs = externs or {}
    secs = _elf(obj)
    base = {}                                       # section index -> (obj, offset)
    at, bss = text_at, 0
    for i, s in enumerate(secs):
        if not s['flags'] & 2 or not s['size']:     # SHF_ALLOC
            continue
        al = max(s['align'], 1)
        if s['type'] == 8:                          # SHT_NOBITS
            bss = (bss + al - 1) // al * al
            base[i] = (bss_at[0], bss_at[1] + bss)
            bss += s['size']
        else:
            assert s['type'] == 1, (s['name'], s['type'])
            at = (at + al - 1) // al * al
            base[i] = (1, at)
            at += s['size']
    if limit is not None:
        assert at <= limit, (hex(at), hex(limit))
    symtab = next(s for s in secs if s['type'] == 2)
    strtab = secs[symtab['link']]
    syms = []
    for k in range(symtab['size'] // 16):
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', obj, symtab['offset'] + 16 * k)
        a = strtab['offset'] + name
        nm = obj[a:obj.index(b'\0', a)].decode()
        if shndx == 0:
            if k == 0:
                syms.append(None)
                continue
            assert nm in externs, f'undefined symbol {nm!r} (no library in the exe)'
            syms.append(externs[nm])
        elif shndx == 0xFFF1:                       # SHN_ABS
            syms.append((0, value))
        elif shndx in base:
            syms.append((base[shndx][0], base[shndx][1] + value))
        else:
            syms.append(None)                       # (a non-allocated section: debug info)
        syms[-1] = syms[-1] if syms[-1] is None else syms[-1] + (nm, info >> 4)
    image = {i: bytearray(obj[s['offset']:s['offset'] + s['size']]) for i, s in enumerate(secs)
             if i in base and s['type'] == 1}
    fixups = []
    for s in secs:
        if s['type'] != 9 or s['info'] not in image:    # SHT_REL for an allocated progbits section
            continue
        tgt, img = s['info'], image[s['info']]
        for k in range(s['size'] // 8):
            off, info = struct.unpack_from('<II', obj, s['offset'] + 8 * k)
            sym, typ = info >> 8, info & 0xFF
            tobj, toff = syms[sym][:2]
            a, = struct.unpack_from('<i', img, off)
            if typ == 1:                            # R_386_32: S + A, an LE fixup
                assert tobj in (1, 2), (syms[sym], off)
                struct.pack_into('<I', img, off, toff + a)
                fixups.append((base[tgt][1] + off, tobj, toff + a))
            elif typ == 2:                          # R_386_PC32: S + A - P
                assert tobj == 1, syms[sym]
                struct.pack_into('<i', img, off, toff + a - (base[tgt][1] + off))
            else:
                raise ValueError(f'relocation type {typ}')
    for i, img in image.items():
        p.put(1, base[i][1], bytes(img))
    for off, tobj, toff in fixups:
        add_ptr(p, off, tobj, toff)
    out = {}
    for s in syms:
        if s is not None and s[3] == 1 and s[2]:   # STB_GLOBAL
            out[s[2]] = s[:2]
    return out, at, bss


def add_ptr(p, off, tobj, toff):
    """lepatch.add_ptr for obj1, also when the dword straddles two pages (a record in each, the second one with a
    negative source offset)."""
    ps = p.le.page_size
    if off % ps <= ps - 4:
        p.add_ptr(1, off, tobj, toff)
        return
    gp, po = p._page(1, off)
    p.recs[gp].append(p._record(0x07, po, tobj, toff))
    p.recs[gp + 1].append(p._record(0x07, po - ps, tobj, toff))
    p.put(1, off, struct.pack('<I', toff))
