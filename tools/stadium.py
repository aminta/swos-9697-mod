"""The stadium's name before the line-ups (4.0.6, Davide's look B).

ShowStadiumInit (the line-ups screen, GameLoop's stadiumMenu) ends with FadeOutToBlack / DrawMenu /
CallToWaitRetrace / FadeIn. Its `call FadeOutToBlack` -> st_fade (chained): when the home club (gameTeam1, the TeamFile
of the left team: countryNumber = its TEAM file, teamOrdinal) has a name in DATA\\STAD<stem>.DAT, the stadium picture
(the title memory, stad.256) is shown alone with a framed banner (white frame, black fill) in the middle, the name in
the line-ups' small font doubled when twice its width fits 290 px, in the normal size otherwise; it stays ~1.5 s
(105 ticks of menuCycleTimer) or until a key / a new fire, fades out, and the game's line-ups follow as before.
No file, no record or an empty name: no banner, the game's flow unchanged. The file is read with own DOS calls
(LoadFile ends the program on a missing file).

DATA\\STAD<stem>.DAT, one per team-file namespace (stem = TEAM, or TMWn: a world of its own in a several-world build,
numbers 101.. reused; picked as careerworld's w_ns_stem does: WCUR's WNSB set, WSTEM), e.g. STADTEAM.DAT, STADTMW5.DAT.
Format (agreed with Dati coppe, little-endian): 'STAD', u16 version 1, u16 venue count V; 256 x (u32 offset,
u16 count) by TEAM file; per file its club records sorted by ordinal: u8 teamOrdinal + 33-byte NUL-padded name (at most
32 chars, the game charset A-Z 0-9 space - . '); then the venue table, V x 33 bytes (venue id 1..V).
Code in obj3 after kbd2 (CONVENTIONS 23).
"""
import re
import os
import struct

import benchx
import nasmcave
import sacups

NS_STEM = '''    movzx ecx, byte [WCUR]               ; several worlds: the current world's stem if the file is in its set
    movzx edx, al
    shl ecx, 5
    bt [WNSB + ecx], edx
    jnc .stem
    shr ecx, 3
    mov ecx, [WSTEM + ecx]
    mov [st_fn + 9], ecx
.stem:
    mov ax, [st_key]
'''
MAGIC = b'STAD'
VERSION = 2
VROW = 114                              # competition[40] + round[40] + name[33] + u8 season
REC = 34                                # u8 ordinal + 33-byte name
NAME = 33
WAIT = 105                              # ticks of menuCycleTimer (70 Hz): ~1.5 s
BIG_MAX = 290                           # doubled when 2 x the width fits this

ASM = r"""
st_fade:                                ; ShowStadiumInit's `call FadeOutToBlack` (the line-ups drawn next)
    call FADEOUT
    pushad
    mov byte [st_shown], 0
    call st_find
    jz .out
    mov esi, D0                         ; (the game's pseudo-registers D0..A6, kept around the text calls)
    mov edi, st_regs
    mov ecx, 15
    rep movsd
    call st_draw
    mov esi, [LIN]                      ; the virtual screen -> the display
    mov edi, 0A0000h
    mov ecx, 16000
    rep movsd
    call FADEIN
    mov byte [st_shown], 1
    call st_wait
    call FADEOUT
    mov esi, st_regs
    mov edi, D0
    mov ecx, 15
    rep movsd
.out:
    popad
    ret

st_find:                                ; ZF = 0: st_name = the home club's stadium (gameTeam1)
    mov byte [st_name], 0
    mov eax, [GT1]
    test eax, eax
    jz .no
    cmp eax, TOP                        ; (a highlights replay: the in-game copies)
    je .no
    mov ax, [eax]                       ; al = countryNumber (the TEAM file), ah = teamOrdinal
    mov [st_key], ax
    mov dword [st_fn + 9], 'team'       ; data\stad<stem>.dat: the team file's namespace (careerworld's w_ns_stem)
;NS_STEM
    mov edx, st_fn
    mov eax, 3D00h
    int 21h
    jc .no
    mov ebx, eax
    mov edx, st_rec                     ; the header: 'STAD', version, venue rows, their offset
    mov ecx, 12
    call .read
    jne .close
    cmp dword [st_rec], 'STAD'
    jne .close
    cmp word [st_rec + 4], 2
    jne .close
    movzx esi, word [st_rec + 6]        ; the venues first (a neutral round: the line-ups' competition + round)
    test esi, esi
    jz .club
    mov edx, [st_rec + 8]
    call .seek
    jc .close
.ven:
    mov edx, st_vrow
    mov ecx, VROW
    call .read
    jne .close
    mov al, [st_vrow + 113]             ; its season: 0 = every one, else the career's (currentSeasonShowing + 1)
    test al, al
    jz .vs
    movzx ecx, word [SSN]
    inc ecx
    cmp al, cl
    jne .vn
.vs:
    push esi
    mov esi, st_vrow
    mov edi, GNAME
    call .streq
    jne .vp
    mov esi, st_vrow + 40
    mov edi, GROUND
    call .streq
.vp:
    pop esi
    jne .vn
    mov esi, st_vrow + 80
    jmp .copy
.vn:
    dec esi
    jnz .ven
.club:
    movzx edx, byte [st_key]            ; the home club: its index entry, 12 + file x 6
    imul edx, 6
    add edx, 12
    call .seek
    jc .close
    mov edx, st_rec
    mov ecx, 6
    call .read
    jne .close
    movzx esi, word [st_rec + 4]        ; the file's records
    test esi, esi
    jz .close
    mov edx, [st_rec]
    call .seek
    jc .close
.rec:
    mov edx, st_rec
    mov ecx, 34
    call .read
    jne .close
    mov al, [st_rec]
    cmp al, [st_key + 1]
    je .hit
    ja .close                           ; (sorted by ordinal)
    dec esi
    jnz .rec
    jmp .close
.hit:
    mov esi, st_rec + 1
.copy:
    mov edi, st_name
    mov ecx, 33
    rep movsb
    mov byte [st_name + 32], 0          ; (at most 32 chars)
.close:
    mov ah, 3Eh
    int 21h
.no:
    cmp byte [st_name], 0
    ret
.read:                                  ; ecx bytes at edx; ZF = 1 when all read
    mov ah, 3Fh
    push ecx
    int 21h
    pop ecx
    jc .rf
    movzx eax, ax
    cmp eax, ecx
    ret
.rf:
    or ecx, ecx                         ; (ecx > 0: ZF = 0)
    ret
.streq:                                 ; ZF = 1: the row's string at esi = the game's at edi (to the NUL; the game's
    push ecx                            ; '*' padding ends it too), at most 40
    mov ecx, 40
.sl:
    mov al, [esi]
    mov dl, [edi]
    cmp dl, '*'
    jne .s1
    xor dl, dl
.s1:
    cmp al, dl
    jne .se
    test al, al
    jz .se
    inc esi
    inc edi
    dec ecx
    jnz .sl
.se:
    pop ecx
    ret
.seek:                                  ; to edx from the start
    mov ecx, edx
    shr ecx, 16
    mov eax, 4200h
    int 21h
    ret

st_draw:                                ; the stadium picture + the banner on the virtual screen
    mov esi, [LIN]
    lea esi, [esi + 20000h]             ; (the title memory: stad.256)
    mov edi, [LIN]
    mov ecx, 16000
    rep movsd
    mov eax, [CHT]                      ; (the line-ups' names' font: charTables[0])
    mov [A1], eax
    mov dword [A0], st_name
    call GTW
    movzx eax, word [D7]                ; the width
    mov [st_w], eax
    lea ecx, [eax + eax]
    cmp ecx, BIG_MAX
    setbe byte [st_big]
    jbe .big
    mov ebx, 160                        ; normal size: x = 160 - (w + 1) / 2, the box 12 px around it, y 90..108
    lea ecx, [eax + 1]
    shr ecx, 1
    sub ebx, ecx
    mov [st_x], ebx
    mov edi, 90
    mov edx, 108
    mov ecx, 97
    jmp .box
.big:
    mov ebx, 160                        ; doubled: x = 160 - w, y 86..112 (the text rows 94.. doubled)
    sub ebx, eax
    mov [st_x], ebx
    mov edi, 86
    mov edx, 112
    mov ecx, 94
.box:
    mov [st_y], ecx
    lea eax, [ebx - 12]                 ; eax = left, ebx = right, edi = top, edx = bottom
    add ebx, [st_w]
    cmp byte [st_big], 0
    je .r
    add ebx, [st_w]
.r:
    add ebx, 12
    mov [st_box], eax
    mov [st_box + 4], edi
    mov [st_box + 8], ebx
    mov [st_box + 12], edx
    mov cl, 2                           ; the frame (white), the fill (black) 1 px inside
    call st_rect
    inc eax
    inc edi
    dec ebx
    dec edx
    mov cl, 3
    call st_rect
    mov eax, [CHT]
    mov [A1], eax
    mov dword [A0], st_name
    mov eax, [st_x]
    mov [D1], ax
    mov eax, [st_y]
    mov [D2], ax
    mov word [D3], 2
    call DMT
    cmp byte [st_big], 0
    je .ret
    call st_double
.ret:
    ret

st_rect:                                ; colour cl, x eax..ebx, y edi..edx (inclusive) on the virtual screen
    pushad
    mov esi, edi
.y:
    imul edi, esi, 320
    add edi, [LIN]
    add edi, eax
    push eax
    mov al, cl
    mov ecx, ebx
    sub ecx, [esp]
    inc ecx
    rep stosb
    pop eax
    mov cl, [esp + 24]                  ; (pushad's ecx)
    inc esi
    cmp esi, edx
    jbe .y
    popad
    ret

st_double:                              ; the text block (st_x, st_y, w + 2 x 8) x 2 in place, from its far corner
    pushad                              ; (each target pixel lies at or after its source: nothing unread is overwritten)
    mov ebp, 7                          ; j = 7..0
.j:
    mov ecx, [st_w]
    inc ecx                             ; i = w + 1..0
.i:
    mov eax, [st_y]                     ; source (x + i, y + j)
    add eax, ebp
    imul eax, eax, 320
    add eax, [st_x]
    add eax, ecx
    add eax, [LIN]
    mov dl, [eax]
    mov eax, ebp                        ; target (x + 2i, y + 2j), 2 x 2
    add eax, eax
    add eax, [st_y]
    imul eax, eax, 320
    add eax, [st_x]
    add eax, ecx
    add eax, ecx
    add eax, [LIN]
    mov dh, dl
    mov [eax], dx
    mov [eax + 320], dx
    dec ecx
    jns .i
    dec ebp
    jns .j
    popad
    ret

st_wait:                                ; ~1.5 s; a key or a new fire ends it (the one that started the match is
    mov byte [st_rel], 0                ; still held: not a new one)
    mov byte [st_skip], 0
    mov byte [st_on], 1
    mov word [MCT], 0
.l:
    mov ax, [MCT]
.w:
    cmp ax, [MCT]                       ; (one controls read a tick)
    je .w
    pushad
    call MCC
    popad
    cmp word [LASTKEY], 0
    jne .skip
    mov al, [FIRE]
    or al, [SHORTFIRE]
    jz .rel
    cmp byte [st_rel], 0
    jne .skip
    jmp .t
.rel:
    mov byte [st_rel], 1
.t:
    cmp word [MCT], WAIT_
    jb .l
    jmp .out
.skip:
    mov byte [st_skip], 1
.out:
    mov ax, [MCT]
    mov [st_ticks], ax
    mov byte [st_on], 0
    ret

st_fn: db 'data\stadteam.dat', 0
st_mark: db 'STNM'                      ; (the harness finds these by the mark)
st_name: times 33 db 0                  ; the name shown last ('' = none)
st_shown: db 0                          ; 1 once the banner is on the display
st_big: db 0                            ; 1: doubled
st_rel: db 0
st_skip: db 0                           ; 1: ended by a key / fire
st_key: dw 0                            ; countryNumber, teamOrdinal (looked up last)
st_ticks: dw 0                          ; the ticks it stayed
st_on: db 0                             ; 1 while it waits (the harness: bench scenarios wait it out)
align 4
st_box: dd 0, 0, 0, 0                   ; left, top, right, bottom
st_x: dd 0
st_y: dd 0
st_w: dd 0
st_rec: times 34 db 0
st_vrow: times VROW db 0                ; a venue row: competition[40], round[40], name[33], season
align 4
st_regs: times 15 dd 0
"""


def sites(p):
    """The original obj1's sites and variables (benchx.sites7's for the line-ups screen and the controls)."""
    d = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d)
    D7, A0, A1 = r['D7'], r['A0'], r['A1']
    D0, D1, D2 = D7 - 28, D7 - 24, D7 - 20
    pk = lambda x: re.escape(struct.pack('<I', x))
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    s7 = benchx.INFO['S7'] if 'S7' in benchx.INFO else benchx.sites7(p, r)   # (a probe of the original: no INFO)
    end = s7['stend'] - 20          # call FadeOutToBlack / DrawMenu / CallToWaitRetrace / FadeIn, jmp SetExitMenuFlag
    assert all(d[end + k] == 0xE8 for k in (0, 5, 10, 15)), 'ShowStadiumInit end'
    assert bytes(p.get(1, end, 5)) == d[end:end + 5], 'stadium: FadeOutToBlack call already patched'
    fx = {f[1]: (f[3], f[4]) for f in p.le.fixups() if f[0] == 1 and f[1] is not None}
    tg = lambda o: fx[o]                # (the original's fixups: other modules hook some of these sites first - a
    lin = tg(s7["DRAWMENU"][1] + 2)     # release build's gameTeam1 store; DrawMenu: mov esi, [linAdr384k])
    assert d[s7['DRAWMENU'][1]:s7['DRAWMENU'][1] + 2] == b'\x8b\x35' and lin[0] == 2, ('linAdr384k', lin)
    # DrawMenuTextCentered: push D1 / D2 / A0 / A1, call GetTextWidth, 4 pops, D7 = (D7 + 1) / 2, D1 -= it,
    # jmp DrawMenuText
    m = [x.start() for x in re.finditer(rb'\xff\x35' + pk(D1) + rb'\xff\x35' + pk(D2) + rb'\xff\x35' + pk(A0)
                                         + rb'\xff\x35' + pk(A1) + rb'\xe8....(?:\x8f\x05....){4}\x66\x83\x05' + pk(D7)
                                         + rb'\x01\x66\xd1\x2d' + pk(D7) + rb'\x66\xa1' + pk(D7) + rb'\x66\x29\x05' + pk(D1)
                                         + rb'\xe9', d, re.S)]
    assert m, 'DrawMenuTextCentered'
    gtw, dmt = rel(m[0] + 24), rel(m[0] + 24 + 5 + 24 + 8 + 7 + 6 + 7)
    assert all(rel(x + 24) == gtw for x in m), ('GetTextWidth', [hex(rel(x + 24)) for x in m])
    # DrawMenuItem: mov A1, offset charTables / mov esi, A1 / movzx eax, word [D0] ...
    ct = {tg(x.start() + 6) for x in re.finditer(rb'\xc7\x05' + pk(A1) + rb'....\x8b\x35' + pk(A1)
                                                           + rb'\x0f\xb7\x05' + pk(D0) + rb'\x03\xf0\x8b\x06\xa3' + pk(A1),
                                                           d, re.S)}
    assert len(ct) == 1, ('charTables', ct)
    # InitializeInGameTeamsAndStartGame: hilStarted = 0 / plg_D0_param = D0 / gameMinSubstitutes = D1 /
    # gameMaxSubstitutes = D2 / plg_D3_param = D3 / gameTeam1 = A1 / gameTeam2 = A2
    st = lambda r: rb'\x66\xa1' + pk(r) + rb'\x66\xa3....'
    gt = {tg(x.end() - 9) for x in re.finditer(rb'\x66\xc7\x05....\x00\x00' + st(D0) + st(D1) + st(D2) + st(D7 - 16)
                                                        + rb'\xa1' + pk(A1) + rb'\xa3....\xa1' + pk(A1 + 4), d, re.S)}
    assert len(gt) == 1, ('gameTeam1', gt)
    # InitAndPlayGame: mov A1, offset gameName / call StringCopy / mov gameRound, 0
    gn = [(tg(x.start() + 6), tg(x.start() + 17)) for x in re.finditer(rb'\xc7\x05' + pk(A1) + rb'....\xe8....\xc6\x05....\x00',
                                                                    d, re.S)]
    gn = [g for g in gn if g[0][0] == 2 and g[1][0] == 2 and g[1][1] - g[0][1] == 40]
    assert len(set(gn)) == 1, ('gameName / gameRound', gn)
    # InitCareerVariables: mov currentSeasonShowing, 0 / mov seasonPlaying, 94
    ss = {tg(x.start() + 3) for x in re.finditer(rb'\x66\xc7\x05....\x00\x00\xc6\x05....\x5e', d, re.S)}
    assert len(ss) == 1, ('currentSeasonShowing', ss)
    return {'end': end, 'FADEOUT': p.call_target(1, end), 'FADEIN': p.call_target(1, end + 15), 'LIN': lin,
            'GTW': (1, gtw), 'DMT': (1, dmt), 'CHT': ct.pop(), 'GT1': gt.pop(), 'GNAME': gn[0][0], 'GROUND': gn[0][1],
            'SSN': ss.pop(), 'TOP': s7['TOP'], 'MCC': s7['MCC'],
            'MCT': s7['MCT'], 'LASTKEY': s7['LASTKEY'], 'FIRE': s7['FIRE'], 'SHORTFIRE': s7['SHORTFIRE'],
            'D0': (2, D0), 'D1': (2, D1), 'D2': (2, D2), 'D3': (2, D7 - 16), 'D7': (2, D7), 'A0': (2, A0), 'A1': (2, A1)}


def patch(p, at):
    """st_* at obj3:at (after kbd2); returns the end."""
    s = sites(p)
    sym = {k: v for k, v in s.items() if k != 'end'}
    sym.update(BIG_MAX=(0, BIG_MAX), WAIT_=(0, WAIT), VROW=(0, VROW))
    import careerworld
    ns = 'WCUR' in careerworld.LABELS                   # (a build with several worlds: TMWn.nnn files)
    if ns:
        sym.update({k: (1, careerworld.LABELS[k]) for k in ('WCUR', 'WNSB', 'WSTEM')})
    asm = ASM.replace(';NS_STEM\n', NS_STEM if ns else '')
    code, fix, rel = nasmcave.assemble_obj(asm, at, sym, 3)
    lab = nasmcave.labels(asm, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    p.branch(1, s['end'], 0xE8, 3, lab['st_fade'])
    print(f'exe: stadium: the home club\'s stadium before the line-ups, obj3+{at:#x} ({len(code)} B{", namespaces" if ns else ""}), '
          f'ShowStadiumInit obj1+{s["end"]:#x}')
    return at + len(code)


def build(records, venues=()):
    """A STAD<stem>.DAT (v2): records = {(team file, ordinal): name}; venues = [(competition, round, name, season)]:
    the exact line-ups strings (gameName / gameRound, one row per language), season 0 = every one, n = the career's
    n-th (currentSeasonShowing + 1). Header 'STAD', u16 2, u16 V, u32 the venue table's offset; 256 x (u32 offset,
    u16 count) by team file; the club records (u8 ordinal + 33-byte name); the V venue rows (VROW bytes)."""
    by = {}
    for (f, o), n in records.items():
        by.setdefault(f, []).append((o, n))
    idx, body = bytearray(), bytearray()
    off = 12 + 256 * 6
    for f in range(256):
        recs = sorted(by.get(f, []))
        idx += struct.pack('<IH', off + len(body) if recs else 0, len(recs))
        for o, n in recs:
            body += bytes([o]) + check(n).encode('ascii').ljust(NAME, b'\0')
    ven = bytearray()
    for c, r, n, sn in venues:
        assert 0 < len(c) < 40 and 0 < len(r) < 40 and '*' not in c + r and 0 <= sn < 256, ('venue', c, r, sn)
        ven += c.encode('latin-1').ljust(40, b'\0') + r.encode('latin-1').ljust(40, b'\0') \
            + check(n).encode('ascii').ljust(NAME, b'\0') + bytes([sn])
    assert len(ven) == len(venues) * VROW
    return MAGIC + struct.pack('<HHI', VERSION, len(venues), off + len(body)) + bytes(idx) + bytes(body) + bytes(ven)


def read(data):
    """A STAD<stem>.DAT back (the harness): ({(team file, ordinal): name}, [(competition, round, name, season)]);
    None if it is not a version-2 file (the game shows no banner then)."""
    if len(data) < 12 + 256 * 6 or data[:4] != MAGIC or struct.unpack_from('<H', data, 4)[0] != VERSION:
        return None
    nv, voff = struct.unpack_from('<HI', data, 6)
    z = lambda b: b.split(b'\0')[0].decode('latin-1')
    recs = {}
    for f in range(256):
        off, n = struct.unpack_from('<IH', data, 12 + f * 6)
        for k in range(n):
            r = data[off + k * REC:off + (k + 1) * REC]
            recs[(f, r[0])] = z(r[1:])
    ven = [(z(v[:40]), z(v[40:80]), z(v[80:113]), v[113])
           for v in (data[voff + k * VROW:voff + (k + 1) * VROW] for k in range(nv))]
    return recs, ven


CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -.'")


def check(name):
    assert len(name) <= 32 and set(name) <= CHARSET, ('stadium name', name)
    return name


def fit(name):
    """A source name (any case, accents) in the font: upper case, accents dropped, other characters -> space, at most
    32 (None if it does not fit: shortened by hand in the data, never cut)."""
    import unicodedata
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper().replace('`', "'")
    s = ' '.join(''.join(c if c in CHARSET else ' ' for c in s).split())
    return s if 0 < len(s) <= 32 else None


def from_world(world, csv_path):  # -> STADTMW5.DAT (World 2026-27's namespace)
    """The World 2026-27 clubs' stadiums: world = the release world dir (one pack per country), csv = Dati coppe's
    world.csv (country, key, tm_id, stadium, ...). Returns ({(team file, ordinal): name}, [problems])."""
    import csv
    import os
    import mkseason
    where = {}
    for c in sorted(os.listdir(world)):
        if os.path.isfile(os.path.join(world, c, 'pack.json')):
            pk = mkseason.Pack(os.path.join(world, c))
            for k, w in pk.where.items():
                if pk.clubs[k]['file'] != 'pool':       # (pool clubs: built from POOL05.DAT, no fixed key)
                    where[(c.upper(), k)] = w
    recs, bad = {}, []
    for row in csv.DictReader(open(csv_path, encoding='utf-8')):
        if not row['stadium'].strip():
            continue
        w = where.get((row['country'], row['key']))
        n = fit(row['stadium'])
        if w is None or n is None:
            bad.append((row['country'], row['key'], row['stadium'], 'no club' if w is None else 'over 32'))
            continue
        recs[w] = n
    return recs, bad


LANGS = (('it', 'ITALIAN.EXE'), ('en', 'ENGLISH.EXE'), ('fr', 'FRENCH.EXE'), ('de', 'GERMAN.EXE'))
HERE = os.path.dirname(os.path.abspath(__file__))
CLUBS_CSV = os.path.join(HERE, 'stadium_tmw5_clubs.csv')    # Dati coppe 2026-11-02: file, ordinal, name, stadium
VENUES_CSV = os.path.join(HERE, 'stadium_tmw5_venues.csv')  # the neutral finals: comp_xx, round_xx, venue, season


def venues(csv_path=VENUES_CSV):
    """[(competition, round, name, season)]: one row per language (identical strings once)."""
    import csv
    out = []
    for r in csv.DictReader(open(csv_path, encoding='utf-8')):
        n = fit(r['venue'])
        assert n, ('venue over 32', r['venue'])
        for lang, _ in LANGS:
            v = (r[f'comp_{lang}'], r[f'round_{lang}'], n, int(r['season']))
            if v not in out:
                out.append(v)
    return out


def gen(data):
    """DATA\\STADTMW5.DAT (4.0.6: World 2026-27 only, Davide 02/11) when the build has its team files: every club
    row must still be that club (its TMW5.nnn name), else the build stops. No STADTEAM.DAT: no banner elsewhere."""
    import csv
    if not any(n.upper().startswith('TMW5.') for n in os.listdir(data)):
        return None
    recs, bad, files = {}, [], {}
    for r in csv.DictReader(open(CLUBS_CSV, encoding='utf-8')):
        f, o = int(r['file']), int(r['ordinal'])
        if f not in files:
            fn = os.path.join(data, 'TMW5.%03d' % f)
            files[f] = open(fn, 'rb').read() if os.path.exists(fn) else b''
        d = files[f]
        nm = d[2 + 684 * o + 5:2 + 684 * o + 22].split(b'\0')[0].decode('latin-1') if 2 + 684 * (o + 1) <= len(d) else None
        if nm != r['name']:
            bad.append((f, o, r['name'], nm))
            continue
        recs[(f, o)] = check(r['stadium'])
    assert not bad, (f'{len(bad)} stadium rows on another club now (world data changed: redo the club list)', bad[:5])
    ven = venues()
    open(os.path.join(data, 'STADTMW5.DAT'), 'wb').write(build(recs, ven))
    return len(recs), len(ven)


def vcheck_exe(exe, lang, data):
    """The build's own check: this language's venue strings are strings of its exe or of a DATA file (gameName /
    gameRound copy them), exact. Returns the rows checked; stops the build on a miss."""
    if not os.path.exists(os.path.join(data, 'STADTMW5.DAT')):
        return 0
    import csv
    import glob
    blobs = [open(exe, 'rb').read()] + [open(f, 'rb').read() for f in sorted(glob.glob(os.path.join(data, '*')))
                                        if os.path.isfile(f) and os.path.getsize(f) < 4 << 20]
    miss, n = [], 0
    for r in csv.DictReader(open(VENUES_CSV, encoding='utf-8')):
        for fld in ('comp', 'round'):
            s = r[f'{fld}_{lang}'].encode('latin-1')
            n += 1
            if not any(b'\0' + s + b'\0' in b or b'\0' + s + b'*' in b for b in blobs):
                miss.append((fld, s))
    assert not miss, ('venue strings not in the game', lang, miss)
    return n


def vcheck(csv_path, build):
    """Dati coppe's venues_i18n.csv against a release build dir (SWOS/): every comp_xx / round_xx string must be a
    NUL-terminated string of that language's exe or of a DATA file (the line-ups' gameName / gameRound are copies of
    such strings). Returns [(row, lang, field, string, found in)]; '' = not found."""
    import csv
    import glob
    import os
    blobs = {lang: [(exe, open(os.path.join(build, exe), 'rb').read())] for lang, exe in LANGS
             if os.path.exists(os.path.join(build, exe))}
    data = [(os.path.basename(f), open(f, 'rb').read()) for f in sorted(glob.glob(os.path.join(build, 'DATA', '*')))
            if os.path.isfile(f) and os.path.getsize(f) < 4 << 20]
    out = []
    for i, row in enumerate(csv.DictReader(open(csv_path, encoding='utf-8')), 2):
        for lang in blobs:
            for fld in ('comp', 'round'):
                s = row[f'{fld}_{lang}'].encode('latin-1')
                hit = next((n for n, b in blobs[lang] + data if b'\0' + s + b'\0' in b
                            or b'\0' + s + b'*' in b), '')
                out.append((i, lang, fld, s.decode('latin-1'), hit))
    return out


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['vcheck']:
        for r in vcheck(sys.argv[2], sys.argv[3]):
            print(f'row {r[0]} {r[1]} {r[2]:5} {r[3]!r:40} {r[4] or "NOT FOUND"}')
