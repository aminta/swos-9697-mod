"""Build the release patcher: one self-contained HTML page that turns the user's original files into the mod.

Only differences are shipped. Each patched file is encoded as a list of operations on the user's original:
  COPY  (offset, length) from the original file   -> original game bytes are never included
  INSERT bytes                                      -> only what the mod wrote (code, names, tables, squads)
Copies need a 16-byte match, so inserted runs hold at most short fragments of original bytes.

Encoding (little endian varints): header 'SWD1'; then ops until the end:
  varint (length << 1 | kind)   kind 0 = COPY, 1 = INSERT
  COPY:   zigzag varint (source offset - end of the previous copy)
  INSERT: length raw bytes
The page checks the md5 of every input and of every result, so a wrong or modified original is refused.

Usage: python3 tools/mkpatcher.py   (after `patch.py it|en|fr|de`), writes release/swos-9697-mod-patcher.html
"""
import base64
import hashlib
import json
import os
import struct

ROOT = os.path.join(os.path.dirname(__file__), '..')
VERSION = '1.2'
BLOCK = 16
FILES = [  # (id, original path, patched path, file name in the game folder)
    ('ITALIAN.EXE', 'orig/ITALIAN.EXE', 'c/SWOS/ITALIAN.EXE', 'ITALIAN.EXE'),
    ('ENGLISH.EXE', 'orig/ENGLISH.EXE', 'c/SWOS/ENGLISH.EXE', 'ENGLISH.EXE'),
    ('FRENCH.EXE', 'orig/FRENCH.EXE', 'c/SWOS/FRENCH.EXE', 'FRENCH.EXE'),
    ('GERMAN.EXE', 'orig/GERMAN.EXE', 'c/SWOS/GERMAN.EXE', 'GERMAN.EXE'),
    ('TEAM.020', 'orig/DATA/TEAM.020', 'c/SWOS/DATA/TEAM.020', 'DATA/TEAM.020'),
    # Roadmap 2 (1.1): new African countries (africa.py), shipped whole (orig None): produced together with TEAM.020
    ('TEAM.052', None, 'c/SWOS/DATA/TEAM.052', 'DATA/TEAM.052'),
    ('TEAM.053', None, 'c/SWOS/DATA/TEAM.053', 'DATA/TEAM.053'),
    ('TEAM.054', None, 'c/SWOS/DATA/TEAM.054', 'DATA/TEAM.054'),
    ('TEAM.056', None, 'c/SWOS/DATA/TEAM.056', 'DATA/TEAM.056'),
    ('TEAM.058', None, 'c/SWOS/DATA/TEAM.058', 'DATA/TEAM.058'),
    ('TEAM.061', None, 'c/SWOS/DATA/TEAM.061', 'DATA/TEAM.061'),
    ('TEAM.063', None, 'c/SWOS/DATA/TEAM.063', 'DATA/TEAM.063'),
    ('TEAM.086', None, 'c/SWOS/DATA/TEAM.086', 'DATA/TEAM.086'),
    ('TEAM.087', None, 'c/SWOS/DATA/TEAM.087', 'DATA/TEAM.087'),
    ('TEAM.088', None, 'c/SWOS/DATA/TEAM.088', 'DATA/TEAM.088'),
    # GOG release (2013): same files, 2 bytes changed in each exe (a national cup's months); TEAM.020 identical.
    # Originals in orig/gog/, built with patch.patch_exe(orig/gog/X, c/gog/X, ...)
    ('ITALIAN.EXE (GOG)', 'orig/gog/ITALIAN.EXE', 'c/gog/ITALIAN.EXE', 'ITALIAN.EXE'),
    ('ENGLISH.EXE (GOG)', 'orig/gog/ENGLISH.EXE', 'c/gog/ENGLISH.EXE', 'ENGLISH.EXE'),
    ('FRENCH.EXE (GOG)', 'orig/gog/FRENCH.EXE', 'c/gog/FRENCH.EXE', 'FRENCH.EXE'),
    ('GERMAN.EXE (GOG)', 'orig/gog/GERMAN.EXE', 'c/gog/GERMAN.EXE', 'GERMAN.EXE'),
]


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def zigzag(n):
    return (n << 1) ^ (n >> 63)


def encode(src, dst):
    index = {}
    for i in range(len(src) - BLOCK + 1):
        index.setdefault(src[i:i + BLOCK], []).append(i)
    ops = bytearray(b'SWD1')
    lit = bytearray()
    last = 0
    i = 0
    inserted = 0

    def flush():
        nonlocal inserted
        if lit:
            ops.extend(varint(len(lit) << 1 | 1))
            ops.extend(lit)
            inserted += len(lit)
            lit.clear()

    while i < len(dst):
        best_len, best_at = 0, 0
        for at in index.get(dst[i:i + BLOCK], [])[:64]:
            n = BLOCK
            while i + n < len(dst) and at + n < len(src) and dst[i + n] == src[at + n]:
                n += 1
            if n > best_len:
                best_len, best_at = n, at
                if at == last:
                    break
        if best_len >= BLOCK:
            flush()
            ops.extend(varint(best_len << 1))
            ops.extend(varint(zigzag(best_at - last)))
            last = best_at + best_len
            i += best_len
        else:
            lit.append(dst[i])
            i += 1
    flush()
    return bytes(ops), inserted


def decode(src, ops):
    assert ops[:4] == b'SWD1'
    out = bytearray()
    p, last = 4, 0

    def rd():
        nonlocal p
        n = shift = 0
        while True:
            b = ops[p]
            p += 1
            n |= (b & 0x7f) << shift
            shift += 7
            if not b & 0x80:
                return n
    while p < len(ops):
        v = rd()
        n, kind = v >> 1, v & 1
        if kind:
            out += ops[p:p + n]
            p += n
        else:
            z = rd()
            at = last + ((z >> 1) ^ -(z & 1))
            out += src[at:at + n]
            last = at + n
    return bytes(out)


def build():
    entries = []
    for fid, orig, patched, target in FILES:
        src = open(os.path.join(ROOT, orig), 'rb').read() if orig else b''
        dst = open(os.path.join(ROOT, patched), 'rb').read()
        ops, inserted = encode(src, dst)
        assert decode(src, ops) == dst, fid
        e = {'id': fid, 'target': target, 'size': len(src), 'md5': hashlib.md5(src).hexdigest() if orig else None,
             'out_md5': hashlib.md5(dst).hexdigest(), 'out_size': len(dst), 'delta': base64.b64encode(ops).decode()}
        if not orig:
            e['with'] = 'TEAM.020'                  # new file: produced when the user's TEAM.020 is recognised
        entries.append(e)
        print(f'{fid}: {len(dst)} bytes, delta {len(ops)} bytes ({inserted} inserted)')
    page = open(os.path.join(ROOT, 'tools', 'patcher_template.html'), encoding='utf-8').read()
    page = page.replace('/*PATCHES*/null', json.dumps(entries)).replace('{{VERSION}}', VERSION)
    out = os.path.join(ROOT, 'release', 'swos-9697-mod-patcher.html')
    open(out, 'w', encoding='utf-8').write(page)
    print(f'{out}: {len(page)} bytes')


if __name__ == '__main__':
    build()
