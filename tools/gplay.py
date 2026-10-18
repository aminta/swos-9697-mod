"""Knockout promotion / relegation play-offs of a career world (pack.json league 'ko_playoffs', kind 'promotion'):
the glue around tools/gplay.c, decided at the season end from the final tables of every division of the country.

Season end (cseg_91D4D, per league struct A4): chained after dplay on the same two calls -
- gp_cap (the `call cseg_9221F`: dplay's dp_cap, or the game's, first): a country of GP_TAB (found by its league
  struct's address: a world's leagues share one contest id) -> division D7's final table (DIY+6Dh rows in order:
  team, global number from the team record +2, wins, goals, points) into GP_IN.t[D7];
- gp_end (the `call cseg_9228D`, dp_end first): after the country's last division, gp_season() (C) and its moves
  into leaguesTableCopy (signed division deltas) + the promotion / relegation animation of the career club.
Data: the divisions' promoted / relegated counts are the direct moves only; the play-off adds its winner's move and
the move of a winner_div entrant that does not win (to loser_div). Not playable yet (the career club's play-off in
slot 4: dplay's mechanism, to come); the European play-offs are uefaq's.

pack.json league "ko_playoffs": [{ "key", "names": {lang: [long, short]},
  "kind": "promotion" | "europe" | "placement" | "playout" (the last round's losers go down to loser_div),
  "entrants": [[div, place] | {"div": d, "best_without_europe": true} | {"league_cup_winner": true, "if_places": [a, b]}],
  "rounds": [{"ties": [[a, b], ...] | (with "pairing": "best_worst", "clubs": [...]), "legs": 1 | 2,
              "host": "listed" | "better" | "drawn" | "neutral", "level": "better" | "et_pens" | "et_better" | "pens",
              "gap": g (a tie of clubs g+ points apart is not played: the better placed goes through)}],
  "winner_div": d, "loser_div": d2 | "reserve" (out of the league), "skip_qualified": bool }]   (0-based divisions, 1-based places; tie members:
  an entrant index, "W<k>" / "L<k>" the winner / loser of tie k, ties numbered in order across rounds)
"""
import os
import re
import struct

KINDS = {'promotion': 1, 'europe': 2, 'placement': 3, 'playout': 4}
RESERVE = 0xFE                  # loser_div 'reserve': out of every division (gplay.c)
HOSTS = {'listed': 0, 'better': 1, 'drawn': 2, 'neutral': 3}
LEVELS = {'better': 0, 'et_pens': 1, 'et_better': 2, 'pens': 3}


def compile_spec(pos, ndiv):
    """pack.json 'ko_playoffs' -> the bytes gplay.c walks (ended by a 0); raises ValueError on a bad entry."""
    out = bytearray()
    for po in pos:
        key = po.get('key', '?')
        kind = KINDS.get(po.get('kind'))
        if not kind:
            raise ValueError(f'{key}: kind {" / ".join(KINDS)}')
        ents = []
        for e in po['entrants']:
            if isinstance(e, list) and len(e) == 2:
                d, p = e
                if not (0 <= d < ndiv and p >= 1):
                    raise ValueError(f'{key}: entrant {e}')
                ents.append((0, d, p, 0))
            elif isinstance(e, dict) and e.get('best_without_europe'):
                ents.append((1, e['div'], 0, 0))
            elif isinstance(e, dict) and e.get('league_cup_winner'):
                a, b = e.get('if_places', [0, 0])
                ents.append((2, 0, a, b))
            else:
                raise ValueError(f'{key}: entrant {e}')
        if not 2 <= len(ents) <= 63:
            raise ValueError(f'{key}: 2..63 entrants')
        rounds, nt = bytearray(), 0
        for rd in po['rounds']:
            # a best_worst block: the round itself, or its first tie entry {pairing, clubs}; other ties as listed
            tl = list(rd.get('ties') or [])
            blk = rd if rd.get('pairing') else (tl.pop(0) if tl and isinstance(tl[0], dict) else None)
            if blk is not None and (blk.get('pairing') != 'best_worst' or len(blk['clubs']) % 2):
                raise ValueError(f'{key}: pairing best_worst with an even number of clubs')
            if any(isinstance(t, dict) for t in tl):
                raise ValueError(f'{key}: a best_worst block only as the first tie of a round')
            bm = list(blk['clubs']) if blk is not None else []
            mem = bm + [m for t in tl for m in t]
            ties, pairing = len(mem) // 2, len(bm)
            codes = []
            for m in mem:
                if isinstance(m, int):
                    if not 0 <= m < len(ents):
                        raise ValueError(f'{key}: member {m}')
                    codes.append(m)
                else:
                    mm = re.fullmatch(r'([WL])(\d+)', str(m))
                    if not mm or int(mm.group(2)) >= nt:
                        raise ValueError(f'{key}: member {m} (W<k> / L<k> of an earlier tie)')
                    codes.append((0x80 if mm.group(1) == 'W' else 0xC0) | int(mm.group(2)))
            legs = rd.get('legs', 1)
            if legs not in (1, 2) or rd.get('host', 'listed') not in HOSTS or rd.get('level', 'et_pens') not in LEVELS:
                raise ValueError(f'{key}: legs 1 / 2, host {sorted(HOSTS)}, level {sorted(LEVELS)}')
            gap = rd.get('gap', 0)
            if not (isinstance(gap, int) and 0 <= gap < 256):
                raise ValueError(f'{key}: gap 0..255 points')
            rounds += bytes((ties, legs, HOSTS[rd.get('host', 'listed')], LEVELS[rd.get('level', 'et_pens')], pairing,
                             gap))
            rounds += bytes(codes)
            nt += ties
        if nt > 63:
            raise ValueError(f'{key}: at most 63 ties')
        wd, ld = po.get('winner_div', 0), po.get('loser_div', 0)
        ld = RESERVE if ld == 'reserve' else ld
        if kind in (1, 4) and not (0 <= wd < ndiv and (0 <= ld < ndiv or ld == RESERVE)):
            raise ValueError(f'{key}: winner_div / loser_div (a division, or "reserve")')
        flags = 1 if po.get('skip_qualified') else 0
        out += bytes((kind, len(ents), len(po['rounds']), wd, ld, flags))
        out += b''.join(bytes(e) for e in ents) + rounds
    return bytes(out + b'\0')


ASM = '''
gp_find:                                ; edx = a league struct -> esi = its GP_TAB entry in the running world, or ZF = 1
    xor eax, eax                        ; (a season or any other mode: world 0, the original one)
    cmp word [GAMETYPE], 4
    jne .w
    mov al, [SLT + WORLD_BYTE]          ; (a career: its world)
.w:
    mov esi, GP_TAB
.l:
    cmp dword [esi], 0                  ; (the table ends with a null struct: world 0 is a world)
    je .no
    cmp [esi], edx
    jne .n
    cmp [esi + 4], al
    je .yes
.n:
    add esi, 9
    jmp .l
.yes:
    or esi, esi
    ret
.no:
    xor esi, esi
    ret

gp_cap:                                 ; replaces `call cseg_9221F` (after dplay's dp_cap) in cseg_91D4D
    call GP_CAP_NEXT
    pushad
    mov edx, [A4R]
    call gp_find
    jz .x
    movzx eax, word [D7R]
    cmp eax, GD_N
    jae .x
    movzx ecx, word [DIY + 31h]
    cmp ecx, GT_N
    jbe .n
    mov ecx, GT_N
.n:
    mov [GP_IN + O_N + eax], cl
    imul edi, eax, GT_N * RSZ
    add edi, GP_IN + O_T
    xor ebx, ebx
.r:
    cmp ebx, ecx
    jae .x
    movzx esi, word [DIY + 6Dh + ebx * 2]   ; the place's row offset (row * 12h)
    mov eax, esi
    xor edx, edx
    push ecx
    mov ecx, 12h
    div ecx
    pop ecx
    mov ax, [DIY + 12Dh + eax * 2]
    mov [edi], ax
    mov edx, [DIY + esi + 2B3h]         ; its team record: the global number
    add edx, [SELTEAMS]
    mov ax, [edx + 2]
    mov [edi + 2], ax
    mov ax, [DIY + esi + 2B9h]
    mov [edi + 4], ax
    mov ax, [DIY + esi + 2BFh]
    mov [edi + 6], ax
    mov ax, [DIY + esi + 2C1h]
    mov [edi + 8], ax
    mov ax, [DIY + esi + 2C3h]
    mov [edi + 10], ax
    add edi, RSZ
    inc ebx
    jmp .r
.x:
    popad
    ret

gp_end:                                 ; replaces `call cseg_9228D` (after dplay's dp_end) in cseg_91D4D
    call GP_END_NEXT
    pushad
    mov edx, [A4R]
    call gp_find
    jz .x
    mov edx, [A4R]
    movzx eax, word [D7R]
    inc eax
    cmp al, [edx + 9]                   ; (the league's last division)
    jne .x
    mov [GP_IN], al                     ; nd
    mov eax, [esi + 5]
    mov [GP_IN + O_SPEC], eax
    movzx ecx, byte [GP_IN]
    dec ecx
.c:
    cmp byte [GP_IN + O_N + ecx], 0     ; every division captured
    je .clr
    dec ecx
    jns .c
    push es
    push ds
    pop es
    cld
    call gp_season
    pop es
    movzx ecx, byte [GP_OUT]
    xor ebx, ebx
.m:
    cmp ebx, ecx
    jae .bal
    imul esi, ebx, MSZ
    add esi, GP_OUT + O_MV
    movzx eax, word [esi]
    mov dl, [esi + 4]
    add [SLTCOPY + eax], dl
    mov ax, [esi + 2]
    cmp ax, [CAREERTEAM]
    jne .nm
    test dl, dl
    js .up
    mov word [ANIM_REL], 1
    jmp .nm
.up:
    mov word [ANIM_PRO], 1
.nm:
    inc ebx
    jmp .m
.bal:                                   ; (cseg_9487A checks the table's 8-bit sum at every country's season end:
    xor eax, eax                        ; a move of several divisions breaks the game's +1 / -1 pairs, so the
    mov esi, SLTCOPY                    ; balance byte BAL takes the difference, as pgroups' pg_fix does)
    mov ecx, NSUM
.s:
    add al, [esi]
    inc esi
    loop .s
    sub [SLTCOPY + BAL], al
.clr:
    xor eax, eax
    mov ecx, GD_N
.z:
    mov [GP_IN + O_N + ecx - 1], al
    loop .z
.x:
    popad
    ret
'''


def table_lines(tables):
    """GP_TAB: per country dd its league struct, db world, dd its spec; a 0 world ends it. Specs after it."""
    import mkseason
    lines, syms = ['GP_TAB:'], {}
    import engine
    for i, (world, lfile, spec) in enumerate(tables):
        lines.append(f'    dd GPL{i}\n    db {world}\n    dd GPS{i}')
        syms[f'GPL{i}'] = (1, engine.LEAGUE_AT[lfile[1]] if isinstance(lfile, tuple) else mkseason.LEAGUE_AT[(world, lfile)])
    lines.append('    dd 0\n    db 0\n    dd 0')
    lines.append('GP_EPT:')                    # (uefaq UQ_EPP: per country file its specs, for the European ones)
    for i, (world, lfile, spec) in enumerate(tables):
        if not isinstance(lfile, tuple):        # (world 0's: no league-phase world, no UEFA qualifiers)
            lines.append(f'    db {lfile}\n    dd GPS{i}')
    lines.append('    db 0FFh')
    for i, (_, _, spec) in enumerate(tables):
        lines.append(f'GPS{i}: db ' + ', '.join(str(b) for b in spec))
    return '\n'.join(lines), syms


LABELS = {}


def patch(p, at, limit, tables, bss_at):
    """tables: mkseason.gplay_tables(). C + glue + specs in obj1 at..limit, the C .bss at obj2 bss_at. Returns the end."""
    import bigtables
    import careerworld
    import cobj
    import dplay
    import pgroups
    import nasmcave
    import split
    cap, c9221f, end_site, c9228d, diy, ct, rel, pro, r = dplay._sites(p)
    tgt = lambda a: a + 5 + struct.unpack('<i', p.get(1, a + 1, 4))[0]   # (the current targets: dplay's, or the game's)
    assert p.get(1, cap, 1) == b'\xe8' and p.get(1, end_site, 1) == b'\xe8'
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gplay.c'))
    syms, cend, bss = cobj.link(p, obj, at, (2, bss_at), limit=limit)
    assert bss <= 0x2000, hex(bss)                  # (patch.py: two BSS pages: + the reserves' state)
    keys = ('RSZ', 'GT_N', 'O_N', 'O_T', 'O_SPEC', 'O_MV', 'MSZ', 'GD_N')
    lay = dict(zip(keys, struct.unpack(f'<{len(keys)}I', p.get(1, syms['GP_LAYOUT'][1], 4 * len(keys)))))
    import mkseason
    sel = mkseason._hook_sites(p)[3]
    s = careerworld.SITES
    tab_src, tab_syms = table_lines(tables)
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update(tab_syms)
    symbols.update({'GP_IN': syms['GP_IN'], 'GP_OUT': syms['GP_OUT'], 'gp_season': syms['gp_season'],
                    'A4R': (2, r['A0'] + 16), 'D7R': (2, r['D7']), 'SLT': s['slt'], 'SLTCOPY': s['sltcopy'],
                    'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'DIY': (2, diy), 'SELTEAMS': (2, sel),
                    'CAREERTEAM': (2, ct), 'ANIM_REL': (2, rel), 'ANIM_PRO': (2, pro),
                    'GP_CAP_NEXT': (1, tgt(cap)), 'GP_END_NEXT': (1, tgt(end_site)),
                    'BAL': (0, pgroups.BALANCE), 'GAMETYPE': split.sites(p)['GAMETYPE'], 'NSUM': (0, bigtables.LIMIT if bigtables.ON[0] else 2000)})
    asm = ASM + tab_src + '\n'
    glue = (cend + 15) & ~15
    code, fix = nasmcave.assemble(asm, glue, symbols)
    lab = nasmcave.labels(asm, glue, symbols)
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    for site, target in ((cap, 'gp_cap'), (end_site, 'gp_end')) if tables else ():   # (relative calls: no fixups;
        p.put(1, site + 1, struct.pack('<i', lab[target] - (site + 5)))                # none: only pg_season)
    import uefaq
    if uefaq.LABELS.get('UQ_EPP') and tables:              # a league-phase world: its European play-offs (uefaq.c ep_run)
        p.add_ptr(1, uefaq.LABELS['UQ_EPP'], 1, lab['GP_EPT'])
    LABELS.update(lab, GP_IN=syms['GP_IN'], GP_OUT=syms['GP_OUT'], layout=lay, pg_season=syms['pg_season'], rs_season=syms['rs_season'],
                  RS_STATE=syms['RS_STATE'])
    print(f"exe: knockout play-offs (gplay): {len(tables)} countries, C obj1+{at:#x}..{cend:#x}, glue ..{glue + len(code):#x}, "
          f"GP_IN obj2+{syms['GP_IN'][1]:#x}")
    return glue + len(code)
