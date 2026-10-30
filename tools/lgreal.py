"""4.0.5 World 2026-27: the real league calendars of the world's first season (the COMPLETE lists only).

Data (Dati coppe): internal/world2526/formats/<cc>2627_fixtures.csv - matchday, date, home, away, home_tm, away_tm
(the pack's club keys). The build checks every list against its pack's top division (its clubs, n / 2 matches a day,
every club once a day, the division's days: games x (n - 1), or a split league's days before the split - its list
covers the regular season only, the split stays the generated one) and writes DATA\\LGREAL.DAT:

    dd n; n x (db world, clubs, days, matches a day, clubs x dw team word, days x matches x (db home, away: indices))

A list that does not fit is left out (a warning: that league keeps the generated calendar).
Run time (split.py's hooks of cseg_8F1F2 / cseg_89758, chained):
- lg_init (split's `call sp_init`, a league's init into the DIY): our mark cleared; in a career's first season of
  its world, the file's entry whose clubs are all among the DIY's rows (DIY + 12Dh: the rows' team words) -> its pairs
  (rows) into our buffer LGB (bss), the DIY marked (row 47 + 8: 'LG' + the entry's number - not the row's team dword);
- lg_pair (split's `call sp_pair`, every pairing: the career calendar's builder, the match days, the season-end
  simulation): a marked DIY on a day of the list -> the day's match from LGB (the same day / match rule as sp_pair),
  else sp_pair (a split league's post-split days) / the game; after a load the buffer is filled again from the file.
"""
import csv
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'LGREAL.DAT'
COMPLETE = ('ita', 'eng', 'esp', 'ger', 'fra', 'por', 'ned', 'bel', 'tur', 'pol', 'cze', 'rou', 'ukr', 'rus', 'lux',
            'wal', 'gre', 'srb', 'bul', 'isr', 'den', 'aut', 'svk', 'sco', 'hun', 'nir', 'and', 'mda', 'cro', 'svn',
            'bih')                      # (Regia 30/10: the COMPLETE lists; the partial / missing keep the generated)
BSS_SIZE = 0x400                        # LGB: key, days, matches a day, -, pairs (<= 0x3B0), the clubs' rows map at 3C0h
MAP_AT = 0x3C0
MK = 0x2B3 + 18 * 47 + 8                # the DIY's mark: row 47's bytes 8.. (never its team dword)


def _src():
    return os.environ.get('LGREAL_DATA') or os.path.join(ROOT, 'internal', 'world2526', 'formats')


def entries(log=None):
    """[(world, [team words], days, [(home index, away index)] in day order)] of the COMPLETE lists that fit."""
    import mkseason
    out = []
    by = {os.path.basename(pk.path.rstrip('/')): pk for pk in mkseason.packs() if pk.world}
    for cc in COMPLETE:
        pk, path = by.get(cc), os.path.join(_src(), f'{cc}2627_fixtures.csv')
        if not pk or not os.path.exists(path):
            continue
        m = json.load(open(os.path.join(pk.path, 'pack.json')))
        comp = next(c for c in m['competitions'] if c.get('type') == 'league')
        dv = (comp.get('divisions') or [{}])[0]
        cl = os.path.join(pk.path, 'clubs.csv')         # (the top division's clubs: file 'league' / the competition's)
        clubs = [r['key'] for r in csv.DictReader(open(cl, encoding='utf-8'))
                 if (r.get('file') or 'league') == comp.get('clubs', 'league') and (r.get('division') or '0') == '0'] \
            if os.path.exists(cl) else None
        why = None
        rows = list(csv.DictReader(open(path, encoding='utf-8')))
        if not clubs:
            why = 'no club list in the pack'
        else:
            n, idx = len(clubs), {c: i for i, c in enumerate(clubs)}
            days = sorted({int(r['matchday']) for r in rows})
            sp = (dv.get('split') or {})
            want = (sp.get('after') if sp.get('after') is not None and not sp.get('stages')
                    else (sp.get('stages') or [{}])[0].get('after') if sp.get('stages') else None)
            games = dv.get('games') or comp.get('games') or 2
            want = want if want is not None else games * (n - 1)
            pairs = []
            if any(st.get('home') in ('balance', 'reverse3') for st in (sp.get('stages') or [sp] if sp else [])):
                why = 'its post-split home rule reads the pre-split fixtures (split.py matrix): the generated ' \
                      'calendar keeps the 2 + 2 balance (4.0.6: the matrix from the real list)'
            elif n % 2 or n > 20:
                why = f'{n} clubs (odd / more than 20)'
            elif days != list(range(1, len(days) + 1)) or len(days) != want:
                why = f'{len(days)} matchdays, the division has {want}'
            else:
                for d in days:
                    day = [(idx.get(r['home']), idx.get(r['away'])) for r in rows if int(r['matchday']) == d]
                    if None in [x for pq in day for x in pq]:
                        why = f'matchday {d}: a club not in the top division ' \
                              f'{[r["home"] for r in rows if int(r["matchday"]) == d and r["home"] not in idx][:1]}'
                        break
                    if len(day) != n // 2 or len({x for pq in day for x in pq}) != n:
                        why = f'matchday {d}: {len(day)} matches, not every club once'
                        break
                    pairs += day
            if not why:
                out.append((pk.world, [pk.where[c][0] | pk.where[c][1] << 8 for c in clubs], len(days), pairs))
        if why and log is not None:
            log.append(f'{cc}: {why}')
    return out


def blob(ents):
    b = bytearray(struct.pack('<I', len(ents)))
    for world, words, days, pairs in ents:
        n = len(words)
        assert days * (n // 2) * 2 <= MAP_AT - 4, (world, n, days)
        b += bytes([world, n, days, n // 2]) + struct.pack(f'<{n}H', *words) + bytes(x for pq in pairs for x in pq)
    return bytes(b)


def write(out_dir):
    log = []
    ents = entries(log)
    for x in log:
        print(f'{NAME}: WARNING {x}: the generated calendar')
    if not ents:
        return []
    open(os.path.join(out_dir, NAME), 'wb').write(blob(ents))
    return [(NAME, len(ents))]


def file_names():
    return [NAME] if entries() else []


ASM = r"""
lg_init:                                ; replaces split's `call sp_init` (the end of cseg_8F1F2: a league -> DIY)
    call SP_INIT
    pushad
    mov dword [DIY + MK_], 0
    cmp word [DIY], 0                   ; (a league)
    jne .x
    cmp word [GAMETYPE], 4
    jne .x
    call W_REC
    jz .x
    mov al, [ebx + 42]                  ; (the world's first season)
    cmp al, [SEASONPLAYING]
    jne .x
    call lg_load
    test eax, eax
    jz .x
    mov word [DIY + MK_], 474Ch         ; 'LG' + the entry's number
    mov [DIY + MK_ + 2], al
.x: popad
    ret

lg_load:                                ; the file's entry of the DIY's clubs -> LGB (rows); eax = its number, 0 none
    pushad
    mov byte [LGB], 0
    mov edx, LGFILE
    mov eax, 3D00h
    int 21h
    jc .no
    mov ebx, eax
    mov edx, BUF
    mov ecx, BUFLEN_
    mov ah, 3Fh
    int 21h
    pushfd
    mov ah, 3Eh
    int 21h
    popfd
    jc .no
    mov esi, BUF + 4
    mov ebp, [BUF]
    mov edi, 1
.e: test ebp, ebp
    jz .no
    mov al, [SLT + WORLD_BYTE]
    cmp al, [esi]
    jne .n
    mov al, [DIY + 31h]                 ; (the league's clubs)
    cmp al, [esi + 1]
    jne .n
    xor ecx, ecx
.k: mov ax, [esi + 4 + ecx * 2]         ; each club: its row
    xor edx, edx
.r: cmp ax, [DIY + 12Dh + edx * 2]
    je .f
    inc edx
    cmp dl, [esi + 1]
    jb .r
    jmp .n
.f: mov [LGB + MAP_ + ecx], dl
    inc ecx
    cmp cl, [esi + 1]
    jb .k
    mov al, [esi + 2]
    mov [LGB + 1], al
    mov al, [esi + 3]
    mov [LGB + 2], al
    movzx eax, byte [esi + 2]
    movzx ecx, byte [esi + 3]
    imul ecx, eax
    add ecx, ecx
    movzx edx, byte [esi + 1]
    lea ebx, [esi + 4 + edx * 2]
    xor edx, edx
.c: movzx eax, byte [ebx + edx]
    mov al, [LGB + MAP_ + eax]
    mov [LGB + 4 + edx], al
    inc edx
    cmp edx, ecx
    jb .c
    mov eax, edi
    mov [LGB], al
    mov [esp + 28], eax
    popad
    ret
.n: movzx eax, byte [esi + 1]
    movzx ecx, byte [esi + 2]
    movzx edx, byte [esi + 3]
    imul ecx, edx
    lea esi, [esi + 4 + eax * 2]
    lea esi, [esi + ecx * 2]
    inc edi
    dec ebp
    jmp .e
.no:
    mov dword [esp + 28], 0
    popad
    ret

lg_pair:                                ; replaces split's `call sp_pair` (cseg_89758, before its home / away test)
    pushad
    cmp word [DIY + MK_], 474Ch
    jne .no
    cmp word [DIY], 0
    jne .no
    mov al, [DIY + MK_ + 2]
    cmp al, [LGB]
    je .have
    call lg_load                        ; (after a load: our buffer filled again)
    cmp al, [DIY + MK_ + 2]
    jne .no
.have:
    movzx ecx, word [DIY + 1C1h]        ; the day (sp_pair's rule: the day done -> the next one's first match)
    movzx edx, byte [LGB + 1]
    cmp ecx, edx
    jae .no
    xor ebx, ebx
    cmp word [DIY + 1BFh], 0
    jne .m
    movzx ebx, word [DIY + 1C9h]
.m: movzx edx, byte [LGB + 2]
    cmp ebx, edx
    jae .no
    imul ecx, edx
    add ecx, ebx
    movzx eax, byte [LGB + 4 + ecx * 2]
    movzx ebx, byte [LGB + 5 + ecx * 2]
    imul eax, eax, 18
    add eax, DIY
    mov [A1], eax
    imul ebx, ebx, 18
    add ebx, DIY
    mov [A2], ebx
    popad
    add esp, 4                          ; return from cseg_89758 itself (as sp_pair)
    ret
.no:
    popad
    jmp SP_PAIR

LGFILE: db 'data\lgreal.dat', 0
"""


def patch(p, at, limit, buf, buf_len, lgb):
    """lg_init / lg_pair at obj1:at (< limit), the file read into obj2:buf (fmtpage's shared buffer), LGB at obj2:lgb
    (BSS_SIZE, ours). split.patch must have run (its sp_init / sp_pair calls are retargeted). Returns the end."""
    if not entries():
        print(f'exe: WARNING lgreal: no real league calendar ({_src()}): season 1 generated by the game')
        return at
    import careerworld
    import lp36
    import nasmcave
    import split
    ss, cw, s36 = split.sites(p), careerworld.SITES, lp36._sites(p)
    calls = {}
    for k in ('init', 'swap'):
        site = ss[k]
        b = bytes(p.get(1, site, 5))
        assert b[0] == 0xE8, f'lgreal: split {k} site {site:#x} not hooked'
        calls[k] = (site, site + 5 + struct.unpack_from('<i', b, 1)[0])
    a0 = __import__('sacups').regs(p.le.obj_bytes(1))['A0']
    syms = {'GAMETYPE': ss['GAMETYPE'], 'W_REC': (1, careerworld.LABELS['w_rec']), 'SEASONPLAYING': (2, cw['season']),
            'SLT': cw['slt'], 'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'DIY': (2, s36['DIY']),
            'A1': (2, a0 + 4), 'A2': (2, a0 + 8), 'SP_INIT': (1, calls['init'][1]), 'SP_PAIR': (1, calls['swap'][1]),
            'MK_': (0, MK), 'MAP_': (0, MAP_AT), 'LGB': (2, lgb), 'BUF': (2, buf), 'BUFLEN_': (0, buf_len)}
    code, fix = nasmcave.assemble(ASM, at, syms)
    lab = nasmcave.labels(ASM, at, syms)
    assert at + len(code) <= limit, f'lgreal: {at + len(code):#x} > {limit:#x}'
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    for k, lb in (('init', 'lg_init'), ('swap', 'lg_pair')):
        site = calls[k][0]
        p.put(1, site + 1, struct.pack('<i', lab[lb] - (site + 5)))
    print(f'exe: real league calendars (season 1, {NAME}): {len(entries())} leagues, code obj1+{at:#x} ({len(code)} B)')
    return at + len(code)
