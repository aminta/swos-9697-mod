"""The other confederations' club cups of World 2026-27 (conti.c's data and glue). See notes/continental-cups.md.

Data: internal/conti/<conf>.format.json (package 6: rounds, draws, routes, names) + <conf>.access.json (data: the
access lists per association pack key, the ranking, the season-1 entrants), merged by cup key.

    spec, assocs, cups = conti.load(['conmebol'])          # spec bytes for CT_SPEC, association keys, cup keys
    python3 tools/conti.py --test [conf ...]               # conti.c natively (ctypes) on a synthetic world
"""
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(ROOT), '..', '..', 'internal', 'conti')
if not os.path.isdir(DATA):
    DATA = os.path.expanduser('~/swos-mod/internal/conti')

RB = 24
OUT, CHAMP = 0xFF, 0xFE
K = {'ko': 0, 'groups': 1}
DRAW = {'order': 0, 'pots2': 1, 'same_assoc_pairs': 2, 'seeded_1v2': 3, 'bracket': 4, 'groups': 5, 'fixed': 6}
ASSOC = {'allow': 0, 'any': 0, 'no': 1, 'no_unless_via': 2, 'allow_if_via': 2}
LEVEL = {'pens': 0, 'et_pens': 1, 'away_pens': 2}
CODE = {'cup': 1, 'next': 0x40, 'ap': 0x41, 'cl': 0x42}
ALIAS = {'r1': 'first', 'playoffs': 'po'}   # (access files' round names -> the format's)


def _read(conf, kind):
    p = os.path.join(DATA, f'{conf}.{kind}.json')
    return json.load(open(p)) if os.path.exists(p) else None


def _draw(rd):
    """(draw byte, association rule byte) of a round's 'draw' value."""
    d = rd.get('draw')
    if rd['kind'] == 'groups':
        return DRAW['groups'], ASSOC.get((d or {}).get('same_assoc', 'no'), 1)
    if isinstance(d, str):
        return DRAW.get(d, DRAW['order']) if d != 'fixed' else DRAW['order'], 0
    if not d:
        return DRAW['order'], 0
    kind = d.get('kind')
    rule = ASSOC.get(d.get('same_assoc', 'allow'), 0)
    if kind == 'same_assoc_pairs':
        return DRAW['same_assoc_pairs'], 0
    if kind == 'seeded_1v2':
        return DRAW['seeded_1v2'], rule
    if kind == 'fixed' and d.get('ties'):
        return DRAW['fixed'], 0
    if kind in ('bracket',):
        return DRAW['bracket'], 0
    if d.get('pots') == 2 or kind in ('pots2',):
        return DRAW['pots2'], rule
    return DRAW['order'], rule


def load(confs, files=None, words=None):
    """-> (spec bytes, [association pack keys], [(conf, cup key)]). files: {association key: its league team file}
    (the game's build; the tests: 100 + index), words: {club key: team word} (the ranking's clubs)."""
    cups, assocs = [], []
    for conf in confs:
        fm, ac = _read(conf, 'format'), _read(conf, 'access')
        assert fm, f'{conf}: no format file'
        acc = {c['key']: c for c in (ac or {}).get('cups', [])}
        for c in fm['cups']:
            cups.append((conf, c, acc.get(c['key'], {})))
            for a in acc.get(c['key'], {}).get('access', {}):
                if a not in ('holders', 'from') and a not in assocs:
                    assocs.append(a)
    index = {(conf, c['key']): i for i, (conf, c, _) in enumerate(cups)}
    rkey = {i: {r['key']: j for j, r in enumerate(c['rounds'])} for i, (_, c, _) in enumerate(cups)}

    def target(conf, ci, s):
        """'r16' / 'sud:po' / 'sud:groups' -> cup << 4 | round."""
        if ':' in s:
            ck, rk = s.split(':')
            cj = index[(conf, ck)]
            return cj << 4 | rkey[cj][rk]
        return ci << 4 | rkey[ci][s]

    body = b''
    access, holders = [], []
    for ci, (conf, c, a) in enumerate(cups):
        rounds = c['rounds']
        out = b''
        for j, rd in enumerate(rounds):
            dr, rule = _draw(rd)
            b = bytearray(RB)
            b[0] = K[rd['kind']]
            b[1] = rd.get('legs', 2 if rd['kind'] == 'ko' else 0)
            b[2] = LEVEL.get(rd.get('level', 'pens'), 0)
            b[3] = 1 if rd.get('host') in ('neutral', 'centralised') else 0
            b[4], b[5] = dr, rule
            if rd['kind'] == 'groups':
                b[6], b[7], b[8] = rd['groups'], rd['size'], rd.get('rounds', 2)
                b[16] = 1 if (rd.get('draw') or {}).get('holder') else 0
            b[9] = rd.get('month') or (rd.get('months') or [8])[0]
            b[10] = CHAMP if j == len(rounds) - 1 else (ci << 4 | (j + 1))
            b[11] = OUT
            for q in range(4):
                b[12 + q] = OUT
            if rd['kind'] == 'groups':
                b[10] = OUT
                for q, t in (rd.get('out') or {}).items():
                    b[12 + int(q) - 1] = target(conf, ci, t)
            if (c.get('losers') or {}).get(rd['key']):
                b[11] = target(conf, ci, c['losers'][rd['key']])
            out += bytes(b)
        body += bytes((len(rounds), 0, 0, 0)) + out
        for ak, entries in (a.get('access') or {}).items():
            if ak == 'holders':
                for src, rk in entries.items():
                    holders.append((index[(conf, src)], ci, rkey[ci][rk]))
                continue
            if ak == 'from':
                continue
            for rk, code in entries:
                rk = ALIAS.get(rk, rk) if rk not in rkey[ci] else rk
                k = CODE[code] if isinstance(code, str) else (0 if code <= 1 else code)
                access.append((assocs.index(ak), ci, rkey[ci][rk], k))
    spec = bytes((len(cups), len(assocs), 0, 0)) + body
    spec += struct.pack('<H', len(access)) + b''.join(bytes(x) for x in access)
    spec += bytes((len(holders),)) + b''.join(bytes(x) for x in holders)
    spec += bytes((files or {}).get(a, 100 + i) & 0xFF for i, a in enumerate(assocs))
    rank = {}
    for conf in confs:
        for k, v in ((_read(conf, 'access') or {}).get('ranking') or {}).items():
            if words and k in words:
                rank[words[k]] = min(int(round(v)), 0xFFFF)
    spec += struct.pack('<H', len(rank)) + b''.join(struct.pack('<HH', w, v) for w, v in sorted(rank.items()))
    return spec, assocs, [(conf, c['key']) for conf, c, _ in cups]


# --- native test ------------------------------------------------------------------------------------------------------
def _native():
    import ctypes
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    lib = os.path.join(d, 'conti.dylib')
    subprocess.run(['clang', '-O1', '-shared', '-fPIC', '-o', lib, os.path.join(ROOT, 'tools', 'conti.c')], check=True)
    return ctypes.CDLL(lib)


def test(confs=('conmebol',), seasons=3, seed=7):
    import ctypes
    import random
    spec, assocs, cups = load(list(confs))
    L = _native()
    lay = (ctypes.c_uint32 * 20).in_dll(L, 'CT_LAYOUT')
    s_in, s_st, s_out = lay[0], lay[1], lay[2]
    o_league, o_cup, o_ap, o_cl, o_club = lay[3], lay[4], lay[5], lay[6], lay[7]
    o_win, o_sec, o_last, o_nent, o_ent, o_res = lay[8], lay[9], lay[10], lay[11], lay[12], lay[13]
    NA, NL, NC, NCUP, NRD, NE = lay[14:20]
    buf = ctypes.create_string_buffer(spec, len(spec))
    ctypes.c_void_p.in_dll(L, 'CT_SPEC').value = ctypes.addressof(buf)
    IN = (ctypes.c_ubyte * s_in).in_dll(L, 'CT_IN')
    OUTB = (ctypes.c_ubyte * s_out).in_dll(L, 'CT_OUT')
    rnd = random.Random(seed)
    names = {}
    for season in range(seasons):
        b = bytearray(s_in)
        clubs = []
        for a, ak in enumerate(assocs):         # 12 clubs per association, strength by size
            base = 3000 if ak in ('bra', 'arg') else 1500
            for k in range(18):
                cid = (100 + a) | k << 8
                names[cid] = f'{ak}{k + 1}'
                clubs.append((cid, a, base + rnd.randint(0, 1500) - 60 * k, rnd.randint(100, 9000)))
        struct.pack_into('<IHH', b, 0, seed * 100 + season, len(clubs), 0)
        for i, (cid, a, st, pt) in enumerate(clubs):
            struct.pack_into("<HBBII", b, o_club + 12 * i, cid, a, 0, st, pt)
        for a in range(len(assocs)):
            mine = sorted([i for i, c in enumerate(clubs) if c[1] == a], key=lambda i: -clubs[i][2] + rnd.randint(0, 900))
            for l in range(NL):
                struct.pack_into('<H', b, o_league + 2 * (a * NL + l), mine[l] + 1)
            struct.pack_into('<H', b, o_cup + 2 * a, mine[rnd.randint(0, 6)] + 1)
        ctypes.memmove(IN, bytes(b), s_in)
        L.ct_season()
        o = bytes(OUTB)
        print(f'--- season {season + 1}')
        for ci, (conf, ck) in enumerate(cups):
            w, s2 = struct.unpack_from('<H', o, o_win + 2 * ci)[0], struct.unpack_from('<H', o, o_sec + 2 * ci)[0]
            nm = lambda x: names[clubs[x - 1][0]] if x else '-'
            counts = [o[o_nent + ci * NRD + r] for r in range(NRD)]
            print(f'{conf}:{ck} rounds {[c for c in counts if c]} winner {nm(w)} runner-up {nm(s2)}')


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['--test']:
        test(sys.argv[2:] or ['conmebol'])


# --- the game ---------------------------------------------------------------------------------------------------------
PAGES = 4                               # obj1 pages: the C code + the glue (patch.py: after split's / statecup's)
BSS = 0x14000                           # obj2 .bss: CT_IN, CT_ST, CT_OUT, the edition (patch.py: in the career BSS)
CONFS = ['conmebol', 'concacaf', 'afc', 'caf', 'ofc']
LABELS = {}
ST_SIZE = 4 + 16 * 12                   # sizeof(struct ct_state)


def ready():
    """The confederations with both files (format + access): the others wait for their data."""
    return [c for c in CONFS if _read(c, 'format') and _read(c, 'access')]


def enabled():
    return bool(ready())


GLUE = r'''
ct_tab:                                 ; replaces `call cseg_927A2` (the season end's top 9 of a division): its whole
    pushad                              ; final order first (conti.c ct_table: up to 16 clubs, DIY = that division)
    push es
    push ds
    pop es
    cld
    push dword DIY
    call CT_TABLE
    add esp, 4
    pop es
    popad
    jmp C927A2

ct_ctry:                                ; replaces `call cseg_93974` (a country's qualifiers, Europe only): the
    pushad                              ; other confederations' input first (its table, the top 9 records, the cup
    push es                             ; winner's record), the first country of a season end clears it
    push ds
    pop es
    cld
    mov dword [CT_SPEC], SPEC
    cmp byte [ct_on], 0
    jne .on
    mov byte [ct_on], 1
    call CT_BEGIN
.on:
    push dword CUPREC + 2ACh
    push dword STAND
    call CT_COUNTRY
    add esp, 8
    pop es
    popad
    jmp C93974

ct_fill:                                ; careerworld w_ct_fill (the season end's record count, after uefaq's fill):
    cmp byte [ct_on], 0                 ; every country seen -> the editions
    je .r
    pushad
    mov byte [ct_on], 0
    push es
    push ds
    pop es
    cld
    movzx eax, word [SEL]
    push dword [STAND]                  ; (a seed: changes every season)
    push eax
    call CT_GO
    add esp, 8
    pop es
    popad
.r:
    ret

ct_on: db 0
'''


def _world_maps(confs):
    """{association pack key: league team file}, {club key: team word} from the enabled World 2026-27 packs."""
    import mkseason
    files, words = {}, {}
    for pk in mkseason.packs():
        pid = pk.meta.get('id', '')
        if not pid.startswith('world-2026-27-'):
            continue
        key = pid[len('world-2026-27-'):]
        try:
            files[key] = pk.files[pk.league['clubs']][0]
        except (KeyError, TypeError, AttributeError):
            continue
        for k, (fl, n) in getattr(pk, 'where', {}).items():
            words[k] = fl | n << 8
    return files, words


def patch(p, at, limit, bss_at, area):
    """conti.c + its glue at obj1:at (..limit), .bss at obj2:bss_at; returns the code end. World 2026-27 only."""
    import re
    import cobj
    import nasmcave
    import sacups
    import careerworld as cw
    import engine
    import lib97
    confs = ready()
    files, words = _world_maps(confs)
    spec, assocs, cups = load(confs, files, words)
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    t927 = [m.start() for m in re.finditer(rb'\xc7\x05' + A(a0 + 4) + rb'.{4}\xc7\x05' + A(a0 + 12) + rb'.{4}\xc7\x05' +
                                           A(a0 + 8) + rb'.{4}\xa1' + A(a0 + 8) + rb'\x83\xc0\x6d', d1, re.S)]
    t939 = [m.start() for m in re.finditer(rb'\xa0.{4}\xa2' + A(a0 - 32) + rb'\x66\x81\x25' + A(a0 - 32) +
                                           rb'\xff\x00\x66\xc1\x25' + A(a0 - 32) + rb'\x02\xc7\x05' + A(a0), d1, re.S)]
    assert len(t927) == 1 and len(t939) == 1, (t927, t939)
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]
    c927, c939 = calls(t927[0]), calls(t939[0])
    assert len(c927) == 2 and len(c939) == 2, (c927, c939)
    obj = cobj.compile_c(os.path.join(ROOT, 'tools', 'conti.c'))
    syms, end, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= BSS, hex(bss)
    q = cw._qual_sites(d1, p)
    symbols = {'DIY': (2, lib97._sites(p)[3] + 0x41F), 'STAND': q['STAND'], 'CUPREC': q['CUPREC'],
               'SEL': (2, sacups.SEL_ADDR[0]), 'SPEC': (2, area.add(spec)), 'C927A2': (1, t927[0]),
               'C93974': (1, t939[0]), 'CT_SPEC': syms['CT_SPEC'], 'CT_TABLE': syms['ct_table'],
               'CT_BEGIN': syms['ct_begin'], 'CT_COUNTRY': syms['ct_country'], 'CT_GO': syms['ct_go']}
    glue = (end + 15) & ~15
    code, fix = nasmcave.assemble(GLUE, glue, symbols)
    lab = nasmcave.labels(GLUE, glue, symbols)
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    rel = lambda a, to: struct.pack('<i', to - (a + 5))
    for c in c927:
        p.put(1, c + 1, rel(c, lab['ct_tab']))
    for c in c939:
        p.put(1, c + 1, rel(c, lab['ct_ctry']))
    a = cw.LABELS['w_ct_fill']
    p.put(1, a, b'\xe9' + rel(a, lab['ct_fill']))
    assert struct.unpack('<I', p.get(1, syms['CT_LAYOUT'][1] + 4, 4))[0] == ST_SIZE      # (engine item 'CT')
    engine.ITEM_AT['CT'] = syms['CT_ST']
    LABELS.update(lab, syms=syms, assocs=assocs, cups=cups)
    print(f'exe: other confederations\' cups (conti.c): {len(cups)} cups of {", ".join(confs)}, '
          f'{len(assocs)} associations, spec {len(spec)} B; C obj1+{at:#x}..{end:#x}, glue ..{glue + len(code):#x}, '
          f'bss obj2+{bss_at:#x} ({bss} B)')
    return glue + len(code)
