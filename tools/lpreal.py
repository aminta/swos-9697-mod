"""4.0.5 World 2026-27: the real UEFA league-phase fixtures in the world's first season (lp36's draw replaced).

Data (Dati coppe): internal/world2526/formats/{ucl,uel,uecl}2627_leaguephase.csv - matchday, date, home, away,
home_pack, away_pack (the first-season clubs' keys: pack.json first_europe). The build checks every list against the
world's first-season clubs of that cup (mkseason.world_defs: 36 clubs, each match day 18 matches, every club once a
day) and writes DATA\\LPREAL.DAT:

    dd n; n x (db contest id (0 Champions League, 1 Europa League, 2 Conference League), world, days, matches,
               36 x dw team word (the first season's clubs), matches x (db home, away: indices into those 36))

lr_draw replaces lp_start's `call lp_mkdraw` (lp36: the season's draw into DIY + CAL_OFF, rows in matchday order):
in a career of a world's first season (careerworld w_rec +42 = the season playing), the file read into fmtpage's
shared buffer; its entry for this contest and world, every one of its 36 clubs found among the contest's rows (DIY +
12Dh: the row's team word) -> CAL_OFF = the real pairs (rows); else (a later season, another club qualified - an old
save, a changed world -, no file) lp_mkdraw's draw as before. 18 matches a day: lp_pair's day = match / 18 holds.
"""
import csv
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'LPREAL.DAT'
CUPS = (('cc', 0, 'ucl'), ('cwc', 1, 'uel'), ('uefa', 2, 'uecl'))   # world_defs key, contest id, data file stem


def _src():
    return os.environ.get('LPREAL_DATA') or os.path.join(ROOT, 'internal', 'world2526', 'formats')


def entries():
    """[(contest id, world, days, [36 team words], [(home index, away index)] in matchday order)] of the worlds whose
    league-phase cups have a real list (none without the private data)."""
    import mkseason
    out = []
    for w in mkseason.world_defs():
        for key, cid, stem in CUPS:
            clubs = w['clubs'].get(key) or []
            path = os.path.join(_src(), f'{stem}2627_leaguephase.csv')
            if w.get('year') != 2026 or len(clubs) != 36 or not os.path.exists(path):   # (2026-27 lists only:
                continue                            # not the World 2025-26 test world's league phases)
            idx = {(os.path.basename(pk.path.rstrip('/')), c): i for i, (pk, c) in enumerate(clubs)}
            rows = list(csv.DictReader(open(path, encoding='utf-8')))
            days = sorted({int(r['matchday']) for r in rows})
            pairs = []
            for d in days:
                day = [(idx.get((r['home_pack'], r['home'])), idx.get((r['away_pack'], r['away'])))
                       for r in rows if int(r['matchday']) == d]
                bad = [r for r in rows if int(r['matchday']) == d and
                       ((r['home_pack'], r['home']) not in idx or (r['away_pack'], r['away']) not in idx)]
                assert not bad, f'{stem}: matchday {d}: clubs not among the first-season {key} clubs: {bad[:2]}'
                assert len(day) == 18 and len({x for pq in day for x in pq}) == 36, \
                    f'{stem}: matchday {d}: {len(day)} matches, every club once'
                pairs += day
            n = len(days)
            assert n in (6, 8) and len(set(pairs)) == len(pairs), f'{stem}: {n} matchdays, no match twice'
            for i in range(36):                     # (each club: n matches, half at home)
                h, a = sum(1 for p in pairs if p[0] == i), sum(1 for p in pairs if p[1] == i)
                assert h + a == n and h == n // 2, f'{stem}: club {clubs[i][1]}: {h} home, {a} away'
            words = [pk.where[c][0] | pk.where[c][1] << 8 for pk, c in clubs]
            out.append((cid, w['n'], n, words, pairs))
    return out


def blob(ents):
    b = bytearray(struct.pack('<I', len(ents)))
    for cid, world, days, words, pairs in ents:
        b += bytes([cid, world, days, len(pairs)]) + struct.pack('<36H', *words) + bytes(x for pq in pairs for x in pq)
    return bytes(b)


def write(out_dir):
    """DATA\\LPREAL.DAT (the patcher ships it: file_names); [(name, entries)]."""
    ents = entries()
    if not ents:
        return []
    open(os.path.join(out_dir, NAME), 'wb').write(blob(ents))
    return [(NAME, len(ents))]


def file_names():
    return [NAME] if entries() else []


ASM = r"""
lr_draw:                                ; replaces lp_start's `call lp_mkdraw`
    pushad
    cmp word [GAMETYPE], 4
    jne .draw
    call W_REC
    jz .draw
    mov al, [ebx + 42]                  ; (the world's first season)
    cmp al, [SEASONPLAYING]
    jne .draw
    mov al, [DIYCOPY + 2Dh]             ; (lp_mkdraw's format setup first: the 6- / 8-matchday variables)
    call LP_FMT
    mov edx, LRFILE
    mov eax, 3D00h
    int 21h
    jc .draw
    mov ebx, eax
    mov edx, BUF
    mov ecx, BUFLEN_
    mov ah, 3Fh
    int 21h
    pushfd
    mov ah, 3Eh
    int 21h
    popfd
    jc .draw
    mov esi, BUF + 4
    mov ebp, [BUF]
.e: test ebp, ebp
    jz .draw
    mov al, [SLT + WORLD_BYTE]
    cmp al, [esi + 1]
    jne .n
    mov al, [DIYCOPY + 2Dh]
    cmp al, [esi]
    je .hit
.n: movzx eax, byte [esi + 3]
    lea esi, [esi + 4 + 72 + eax * 2]
    dec ebp
    jmp .e
.hit:
    xor ecx, ecx                        ; each of the 36 clubs: its row (its team word among the rows)
.k: mov ax, [esi + 4 + ecx * 2]
    xor edx, edx
.r: cmp ax, [DIY + 12Dh + edx * 2]
    je .f
    inc edx
    cmp edx, 36
    jb .r
    jmp .draw                           ; (a club not in this contest: the draw)
.f: mov [LRMAP + ecx], dl
    inc ecx
    cmp ecx, 36
    jb .k
    movzx ecx, byte [esi + 3]
    add ecx, ecx
    add esi, 4 + 72
    xor edx, edx
.c: movzx eax, byte [esi + edx]
    mov al, [LRMAP + eax]
    mov [DIY + CAL_OFF_ + edx], al
    inc edx
    cmp edx, ecx
    jb .c
    popad
    ret
.draw:
    popad
    jmp LP_MKDRAW
"""


def patch(p, at, limit, area, buf, buf_len):
    """lr_draw at obj1:at (< limit; small data in obj2 area), the file read into obj2:buf (buf_len bytes: fmtpage's
    shared buffer). Returns the end, or at when the build has no real list."""
    if not entries():
        print(f'exe: WARNING lpreal: no real league-phase list ({_src()}): season 1 drawn by the game')
        return at
    import careerworld
    import lp36
    import nasmcave
    s, cw = lp36._sites(p), careerworld.SITES
    a, z, mk = lp36.LABELS['lp_start'], lp36.LABELS['lp_pair'], lp36.LABELS['lp_mkdraw']
    d1 = bytes(p.get(1, a, z - a))                      # lp_start's `call lp_mkdraw` (its only one)
    calls = [a + i for i in range(len(d1) - 4) if d1[i] == 0xE8 and a + i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == mk]
    assert len(calls) == 1, calls
    site = calls[0]
    syms = {'GAMETYPE': __import__('split').sites(p)['GAMETYPE'], 'W_REC': (1, careerworld.LABELS['w_rec']),
            'SEASONPLAYING': (2, cw['season']), 'SLT': cw['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE),
            'DIY': (2, s['DIY']), 'DIYCOPY': (2, s['DIYCOPY']), 'LP_FMT': (1, lp36.LABELS['lp_fmt']),
            'LP_MKDRAW': (1, lp36.LABELS['lp_mkdraw']), 'CAL_OFF_': (0, lp36.CAL_OFF),
            'LRFILE': (2, area.add(b'data\\lpreal.dat\0')), 'LRMAP': (2, area.add(bytes(36))),
            'BUF': (2, buf), 'BUFLEN_': (0, buf_len)}
    code, fix = nasmcave.assemble(ASM, at, syms)
    lab = nasmcave.labels(ASM, at, syms)
    assert at + len(code) <= limit, f'lpreal: {at + len(code):#x} > {limit:#x}'
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', lab['lr_draw'] - (site + 5)))
    print(f'exe: real league-phase fixtures (season 1, {NAME}): {len(entries())} contests, code obj1+{at:#x} '
          f'({len(code)} B)')
    return at + len(code)
