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
VERSION = '3.3.6'
BLOCK = 16
FILES = [  # (id, original path, patched path, file name in the game folder)
    ('ITALIAN.EXE', 'orig/ITALIAN.EXE', 'c/SWOS/ITALIAN.EXE', 'ITALIAN.EXE'),
    ('ENGLISH.EXE', 'orig/ENGLISH.EXE', 'c/SWOS/ENGLISH.EXE', 'ENGLISH.EXE'),
    ('FRENCH.EXE', 'orig/FRENCH.EXE', 'c/SWOS/FRENCH.EXE', 'FRENCH.EXE'),
    ('GERMAN.EXE', 'orig/GERMAN.EXE', 'c/SWOS/GERMAN.EXE', 'GERMAN.EXE'),
    ('TEAM.020', 'orig/DATA/TEAM.020', 'c/SWOS/DATA/TEAM.020', 'DATA/TEAM.020'),
    # 2.5: Australia (NSL 1996-97), New Zealand (NSSL 1996-97), USA (MLS 1997): changed original files
    ('TEAM.044', 'orig/DATA/TEAM.044', 'c/SWOS/DATA/TEAM.044', 'DATA/TEAM.044'),
    ('TEAM.062', 'orig/DATA/TEAM.062', 'c/SWOS/DATA/TEAM.062', 'DATA/TEAM.062'),
    ('TEAM.073', 'orig/DATA/TEAM.073', 'c/SWOS/DATA/TEAM.073', 'DATA/TEAM.073'),
    # 3.3.0: purple clubs (kit colour 10) in original team files the mod did not change before
    ('TEAM.001', 'orig/DATA/TEAM.001', 'c/SWOS/DATA/TEAM.001', 'DATA/TEAM.001'),
    ('TEAM.002', 'orig/DATA/TEAM.002', 'c/SWOS/DATA/TEAM.002', 'DATA/TEAM.002'),
    ('TEAM.013', 'orig/DATA/TEAM.013', 'c/SWOS/DATA/TEAM.013', 'DATA/TEAM.013'),
    ('TEAM.035', 'orig/DATA/TEAM.035', 'c/SWOS/DATA/TEAM.035', 'DATA/TEAM.035'),
    ('TEAM.047', 'orig/DATA/TEAM.047', 'c/SWOS/DATA/TEAM.047', 'DATA/TEAM.047'),
    ('TEAM.055', 'orig/DATA/TEAM.055', 'c/SWOS/DATA/TEAM.055', 'DATA/TEAM.055'),
    ('TEAM.071', 'orig/DATA/TEAM.071', 'c/SWOS/DATA/TEAM.071', 'DATA/TEAM.071'),
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
    # 2.0: classic tourneys (historic.py): World Cup 1982, Mitropa Cup 1934, FA Cup 1871-72
    ('TEAM.089', None, 'c/SWOS/DATA/TEAM.089', 'DATA/TEAM.089'),
    ('TEAM.090', None, 'c/SWOS/DATA/TEAM.090', 'DATA/TEAM.090'),
    ('TEAM.091', None, 'c/SWOS/DATA/TEAM.091', 'DATA/TEAM.091'),
    ('TEAM.146', None, 'c/SWOS/DATA/TEAM.146', 'DATA/TEAM.146'),   # 3.2: World Cup 1934 (tourney pack)
    # 2.6: DDR 1988-89 (packs/ddr-1988-89, mkseason.py): Oberliga clubs, FDGB-Pokal-only clubs
    ('TEAM.092', None, 'c/SWOS/DATA/TEAM.092', 'DATA/TEAM.092'),
    ('TEAM.093', None, 'c/SWOS/DATA/TEAM.093', 'DATA/TEAM.093'),
    # 2.6: European cups 1988-89 (same pack): foreign clubs of CC, CWC, UEFA
    ('TEAM.094', None, 'c/SWOS/DATA/TEAM.094', 'DATA/TEAM.094'),
    ('TEAM.095', None, 'c/SWOS/DATA/TEAM.095', 'DATA/TEAM.095'),
    ('TEAM.096', None, 'c/SWOS/DATA/TEAM.096', 'DATA/TEAM.096'),
    # 3.0: career world Europe 1984-85 (packs/europe-1984-85, DaniSwos's database): league and cup-only clubs, world table
    ('TEAM.101', None, 'c/SWOS/DATA/TEAM.101', 'DATA/TEAM.101'),
    ('TEAM.102', None, 'c/SWOS/DATA/TEAM.102', 'DATA/TEAM.102'),
    ('TEAM.103', None, 'c/SWOS/DATA/TEAM.103', 'DATA/TEAM.103'),
    ('TEAM.104', None, 'c/SWOS/DATA/TEAM.104', 'DATA/TEAM.104'),
    ('TEAM.105', None, 'c/SWOS/DATA/TEAM.105', 'DATA/TEAM.105'),
    ('TEAM.106', None, 'c/SWOS/DATA/TEAM.106', 'DATA/TEAM.106'),
    ('TEAM.107', None, 'c/SWOS/DATA/TEAM.107', 'DATA/TEAM.107'),
    ('TEAM.108', None, 'c/SWOS/DATA/TEAM.108', 'DATA/TEAM.108'),
    ('TEAM.109', None, 'c/SWOS/DATA/TEAM.109', 'DATA/TEAM.109'),
    ('TEAM.110', None, 'c/SWOS/DATA/TEAM.110', 'DATA/TEAM.110'),
    ('TEAM.111', None, 'c/SWOS/DATA/TEAM.111', 'DATA/TEAM.111'),
    ('TEAM.112', None, 'c/SWOS/DATA/TEAM.112', 'DATA/TEAM.112'),
    ('TEAM.113', None, 'c/SWOS/DATA/TEAM.113', 'DATA/TEAM.113'),
    ('TEAM.114', None, 'c/SWOS/DATA/TEAM.114', 'DATA/TEAM.114'),
    ('TEAM.115', None, 'c/SWOS/DATA/TEAM.115', 'DATA/TEAM.115'),
    ('TEAM.116', None, 'c/SWOS/DATA/TEAM.116', 'DATA/TEAM.116'),
    ('TEAM.117', None, 'c/SWOS/DATA/TEAM.117', 'DATA/TEAM.117'),
    ('TEAM.118', None, 'c/SWOS/DATA/TEAM.118', 'DATA/TEAM.118'),
    ('TEAM.119', None, 'c/SWOS/DATA/TEAM.119', 'DATA/TEAM.119'),
    ('TEAM.120', None, 'c/SWOS/DATA/TEAM.120', 'DATA/TEAM.120'),
    ('TEAM.121', None, 'c/SWOS/DATA/TEAM.121', 'DATA/TEAM.121'),
    ('TEAM.122', None, 'c/SWOS/DATA/TEAM.122', 'DATA/TEAM.122'),
    ('TEAM.123', None, 'c/SWOS/DATA/TEAM.123', 'DATA/TEAM.123'),
    ('TEAM.124', None, 'c/SWOS/DATA/TEAM.124', 'DATA/TEAM.124'),
    ('TEAM.125', None, 'c/SWOS/DATA/TEAM.125', 'DATA/TEAM.125'),
    ('TEAM.126', None, 'c/SWOS/DATA/TEAM.126', 'DATA/TEAM.126'),
    ('TEAM.127', None, 'c/SWOS/DATA/TEAM.127', 'DATA/TEAM.127'),
    ('TEAM.128', None, 'c/SWOS/DATA/TEAM.128', 'DATA/TEAM.128'),
    ('TEAM.129', None, 'c/SWOS/DATA/TEAM.129', 'DATA/TEAM.129'),
    ('TEAM.130', None, 'c/SWOS/DATA/TEAM.130', 'DATA/TEAM.130'),
    ('TEAM.131', None, 'c/SWOS/DATA/TEAM.131', 'DATA/TEAM.131'),
    ('TEAM.132', None, 'c/SWOS/DATA/TEAM.132', 'DATA/TEAM.132'),
    ('TEAM.133', None, 'c/SWOS/DATA/TEAM.133', 'DATA/TEAM.133'),
    ('TEAM.134', None, 'c/SWOS/DATA/TEAM.134', 'DATA/TEAM.134'),
    ('TEAM.135', None, 'c/SWOS/DATA/TEAM.135', 'DATA/TEAM.135'),
    ('TEAM.136', None, 'c/SWOS/DATA/TEAM.136', 'DATA/TEAM.136'),
    ('TEAM.137', None, 'c/SWOS/DATA/TEAM.137', 'DATA/TEAM.137'),
    ('TEAM.138', None, 'c/SWOS/DATA/TEAM.138', 'DATA/TEAM.138'),
    ('TEAM.139', None, 'c/SWOS/DATA/TEAM.139', 'DATA/TEAM.139'),
    ('TEAM.140', None, 'c/SWOS/DATA/TEAM.140', 'DATA/TEAM.140'),
    ('TEAM.141', None, 'c/SWOS/DATA/TEAM.141', 'DATA/TEAM.141'),
    ('TEAM.142', None, 'c/SWOS/DATA/TEAM.142', 'DATA/TEAM.142'),
    ('TEAM.143', None, 'c/SWOS/DATA/TEAM.143', 'DATA/TEAM.143'),
    ('TEAM.144', None, 'c/SWOS/DATA/TEAM.144', 'DATA/TEAM.144'),
    ('TEAM.145', None, 'c/SWOS/DATA/TEAM.145', 'DATA/TEAM.145'),      # Italy 1947-48 (CLASSIC SEASONS)
    ('WORLD04.TMD', None, 'c/SWOS/DATA/WORLD04.TMD', 'DATA/WORLD04.TMD'),
    # 3.1: the national teams of the Europe 1984-85 world (packs/europe-1984-85/national), in place of TEAM.080-085
    ('TEAM.180', None, 'c/SWOS/DATA/TEAM.180', 'DATA/TEAM.180'),
    ('TEAM.181', None, 'c/SWOS/DATA/TEAM.181', 'DATA/TEAM.181'),
    ('TEAM.182', None, 'c/SWOS/DATA/TEAM.182', 'DATA/TEAM.182'),
    ('TEAM.183', None, 'c/SWOS/DATA/TEAM.183', 'DATA/TEAM.183'),
    ('TEAM.184', None, 'c/SWOS/DATA/TEAM.184', 'DATA/TEAM.184'),
    ('TEAM.185', None, 'c/SWOS/DATA/TEAM.185', 'DATA/TEAM.185'),
    # GOG release (2013): same files, 2 bytes changed in each exe (a national cup's months); TEAM.020 identical.
    # Originals in orig/gog/, built with patch.patch_exe(orig/gog/X, c/gog/X, ...)
    ('ITALIAN.EXE (GOG)', 'orig/gog/ITALIAN.EXE', 'c/gog/ITALIAN.EXE', 'ITALIAN.EXE'),
    ('ENGLISH.EXE (GOG)', 'orig/gog/ENGLISH.EXE', 'c/gog/ENGLISH.EXE', 'ENGLISH.EXE'),
    ('FRENCH.EXE (GOG)', 'orig/gog/FRENCH.EXE', 'c/gog/FRENCH.EXE', 'FRENCH.EXE'),
    ('GERMAN.EXE (GOG)', 'orig/gog/GERMAN.EXE', 'c/gog/GERMAN.EXE', 'GERMAN.EXE'),
    # 2.7: SWOS++ (Zlatko Karakas) on the modded English exe, built by tools/swospp.py from the two ENGLISH.EXE above
    ('ENGLISH.EXE + SWOS++', 'orig/ENGLISH.EXE', 'c/swospp/ENGLISH.EXE', 'ENGLISH.EXE'),
    ('ENGLISH.EXE + SWOS++ (GOG)', 'orig/gog/ENGLISH.EXE', 'c/swospp/gog/ENGLISH.EXE', 'ENGLISH.EXE'),
]
BUILD = os.environ.get('PATCHER_BUILD')   # e.g. c/REL30: built files read from there instead of c/ (c/SWOS -> c/REL30/SWOS)
if BUILD:
    FILES = [(i, o, BUILD + '/' + p[2:] if p.startswith('c/') else p, t) for i, o, p, t in FILES]
SWOSPP_BASE = {'ENGLISH.EXE + SWOS++': 'ENGLISH.EXE', 'ENGLISH.EXE + SWOS++ (GOG)': 'ENGLISH.EXE (GOG)'}


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


OLD = os.path.join(ROOT, 'orig', 'old-patchers')       # the patchers published with every release (gh release download)


def old_outputs():
    """{(file id, md5): (bytes, version)} of every modded file the earlier releases produced (their patcher applied to the
    originals), so that a user who keeps the modded game can be upgraded without going back to the originals."""
    import glob
    import re
    found = {}
    for f in sorted(glob.glob(os.path.join(OLD, 'patcher-v*.html'))):
        ver = re.search(r'patcher-v(.*)\.html', f).group(1)
        page = open(f, encoding='utf-8').read()
        table = json.loads(re.search(r'PATCHES\s*=\s*(\[.*?\]);\s*\n', page, re.S).group(1))
        for e in table:
            if 'from' in e or 'via' in e:       # upgrade / extra-source entries: their output is also produced from the original
                continue
            orig = next((o for fid, o, _, _ in FILES if fid == e['id']), None)
            src = open(os.path.join(ROOT, orig), 'rb').read() if orig else b''
            if e['md5']:
                assert hashlib.md5(src).hexdigest() == e['md5'], (ver, e['id'])
            out = decode(src, base64.b64decode(e['delta']))
            assert hashlib.md5(out).hexdigest() == e['out_md5'], (ver, e['id'])
            found.setdefault((e['id'], e['out_md5']), (out, ver))
    return found


def upgrades(entries):
    """Extra entries: old modded file (recognised by its md5) -> this release's file. Old files identical to the new one
    need nothing (the page says 'already up to date')."""
    cur = {e['id']: e for e in entries}
    extra = []
    olds = sorted(old_outputs().items(), key=lambda kv: (kv[0][0], kv[1][1]))
    # an old modded English exe can also become mod + SWOS++
    olds += [((v, md5), ov) for (fid, md5), ov in olds for v, b in SWOSPP_BASE.items() if b == fid]
    for (fid, md5), (old, ver) in olds:
        e = cur.get(fid)
        if e is None or md5 == e['out_md5'] or any(x['id'] == fid and x['md5'] == md5 for x in entries + extra):
            continue
        dst = open(os.path.join(ROOT, next(p for i, _, p, _ in FILES if i == fid)), 'rb').read()
        ops, inserted = encode(old, dst)
        assert decode(old, ops) == dst
        extra.append({'id': fid, 'target': e['target'], 'size': len(old), 'md5': md5, 'out_md5': e['out_md5'],
                      'out_size': e['out_size'], 'delta': base64.b64encode(ops).decode(), 'from': ver})
        print(f'  upgrade {fid} from {ver}: delta {len(ops)} bytes')
    return extra


def build_swospp():
    """c/swospp/[gog/]ENGLISH.EXE = this release's English exes + SWOS++ (tools/swospp.py)."""
    import swospp
    c = (BUILD or 'c') + '/'
    for src, dst in ((c + 'SWOS/ENGLISH.EXE', c + 'swospp/ENGLISH.EXE'), (c + 'gog/ENGLISH.EXE', c + 'swospp/gog/ENGLISH.EXE')):
        os.makedirs(os.path.dirname(os.path.join(ROOT, dst)), exist_ok=True)
        swospp.install(os.path.join(ROOT, src), os.path.join(ROOT, dst))


def swospp_sources(entries):
    """Extra entries for the SWOS++ variants: from an original game that already has SWOS++ (patchit.com install),
    and from this release's plain English exe (add SWOS++ to an up-to-date game)."""
    import swospp
    cur = {e['id']: e for e in entries}
    extra = []
    for vid, base in SWOSPP_BASE.items():
        e = cur[vid]
        dst = open(os.path.join(ROOT, next(p for i, _, p, _ in FILES if i == vid)), 'rb').read()
        orig = open(os.path.join(ROOT, next(o for i, o, _, _ in FILES if i == base)), 'rb').read()
        plain = open(os.path.join(ROOT, next(p for i, _, p, _ in FILES if i == base)), 'rb').read()
        for src, via in ((swospp.patchit(orig), 'swospp'), (plain, 'mod')):
            if any(x['id'] == vid and x['md5'] == hashlib.md5(src).hexdigest() for x in entries + extra):
                continue
            ops, inserted = encode(src, dst)
            assert decode(src, ops) == dst
            extra.append({'id': vid, 'target': e['target'], 'size': len(src), 'md5': hashlib.md5(src).hexdigest(),
                          'out_md5': e['out_md5'], 'out_size': e['out_size'], 'delta': base64.b64encode(ops).decode(),
                          'via': via})
            print(f'  {vid} via {via}: delta {len(ops)} bytes')
    return extra


def build():
    build_swospp()
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
    entries += upgrades(entries)
    entries += swospp_sources(entries)
    page = open(os.path.join(ROOT, 'tools', 'patcher_template.html'), encoding='utf-8').read()
    page = page.replace('/*PATCHES*/null', json.dumps(entries)).replace('{{VERSION}}', VERSION)
    out = os.path.join(ROOT, 'release', 'swos-9697-mod-patcher.html')
    open(out, 'w', encoding='utf-8').write(page)
    print(f'{out}: {len(page)} bytes')


if __name__ == '__main__':
    build()
