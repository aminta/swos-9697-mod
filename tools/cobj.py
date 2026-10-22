"""C code in the exe: clang compiles a C file for a 486 (ELF i386 relocatable object), link() lays it into an obj1
cave (code, read-only data, data) and a zero-filled obj2 area (.bss), applying the relocations: R_386_32 -> an LE
32-bit offset fixup (two records when it straddles a page, as the Watcom linker does), R_386_PC32 -> a relative
displacement (calls inside the code, or to the game's routines given as externs).

The C file must be freestanding: no library calls (link() fails on any undefined symbol that is not an extern),
cdecl functions (ebx, esi, edi, ebp preserved). Called from asm with pushad / popad around."""
import os
import struct
import subprocess
import tempfile

CFLAGS = ['-target', 'i686-unknown-none-elf', '-march=i486', '-ffreestanding', '-fno-pic', '-fno-pie', '-Os',
          '-fno-stack-protector', '-mno-sse', '-mno-mmx', '-fno-builtin', '-fno-asynchronous-unwind-tables',
          '-fno-unwind-tables', '-Wall', '-Werror']


def compile_c(src, flags=()):
    """The object file's bytes."""
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, 'c.o')
        r = subprocess.run(['clang', *CFLAGS, *flags, '-c', src, '-o', out], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return open(out, 'rb').read()


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
