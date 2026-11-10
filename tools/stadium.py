"""The stadium's name on the versus screen (4.0.6, Davide 02/11: it replaces look B's stadium-picture screen).

VersusInit (the versus screen before the line-ups: the competition title over the two team bars) ends with
FadeOutToBlack / DrawMenu / CallToWaitRetrace / FadeIn. Its `call DrawMenu` -> st_vs (chained): when the home club
(gameTeam1, the TeamFile of the left team: countryNumber = its TEAM file, teamOrdinal) has a name in
DATA\\STAD<stem>.DAT, the name is drawn centred under the bars (on the title's centre), GAP rows below their last row,
in the small menu / list font (charTables[0], normal size; Davide: smaller than the title) and the title's colour,
and the frame copied to the display before the game's fade-in. No file, no record or an empty name: the screen as the game draws it. Nothing waits and
no controls are read (02/11: with look B's 1.5 s banner shown - its wait read the controls - bench_world's in-match
bench cursor never moved; with the file read and no banner it did).
The file is read with own DOS calls (LoadFile ends the program on a missing file).

DATA\\STAD<stem>.DAT, one per team-file namespace (stem = TEAM, or TMWn: a world of its own in a several-world build,
numbers 101.. reused; picked as careerworld's w_ns_stem does: WCUR's WNSB set, WSTEM), e.g. STADTEAM.DAT, STADTMW5.DAT.
Format v3 (4.0.6 full official names, Davide 05/11; v2 = 02/11 with Dati coppe, still read), little-endian: 'STAD',
u16 version 3, u16 venue rows V, u32 the venue table's offset; 256 x (u32 offset, u16 count) by TEAM file; per file
its club records sorted by ordinal: u8 teamOrdinal + 49-byte NUL-padded name (at most 48 chars, the game charset A-Z
0-9 space - . '; v2: 33 bytes, 32 chars); then V venue rows of VROW bytes: competition[40] + round[40] + name[49] +
u8 season (v2: name[33]). 48 small-font characters are at most 288 px: always inside the 320-px screen.
A neutral final: the line-ups' gameName / gameRound equal a row's
competition / round (exact, to the NUL; the game's '*' padding ends a string) and its season is 0 or the career's
(currentSeasonShowing + 1): the row's name, before the home club's. One row per language (the exes' own strings).
4.0.6 ships only DATA\\STADTMW5.DAT (World 2026-27, Davide 02/11; gen() from stadium_tmw5_*.csv), no STADTEAM.DAT.
Known limits: a final whose home side is a pool club (file 253, outside the world's namespace) shows no venue; the
season of a row is compared with currentSeasonShowing outside careers too.
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
VERSION = 3
NAME = 49                               # 48 chars + NUL (v2: 33)
VROW = 80 + NAME + 1                    # competition[40] + round[40] + name + u8 season
REC = 1 + NAME                          # u8 ordinal + name
OLD = {2: 33, 3: NAME}                  # the name field by file version (the game reads both)
GAP = 25                                # rows clear between the team bars and the name (Davide's round-3 mock: 20 / 25)

ASM = r"""
st_vs:                                  ; VersusInit's `call DrawMenu` (the versus screen drawn and flipped, faded in next)
    call DRAWMENU
    pushad
    mov byte [st_shown], 0
    call st_find
    jz .out
    mov esi, D0                         ; (the game's pseudo-registers D0..A6, kept around the text call)
    mov edi, st_regs
    mov ecx, 15
    rep movsd
    mov eax, [CHT]                      ; the small menu / list font (charTables[0], Davide 02/11)
    mov [A1], eax
    mov esi, CURMENU + 16h              ; entry 0, the title: its colour (as DrawMenuItem picks it), its centre
    movzx eax, word [esi + 24h]         ; stringFlags
    and eax, 0Fh
    jnz .c
    mov al, 2
.c:
    mov [D3], ax
    movzx eax, word [esi + 14h]         ; x + width / 2
    movzx ecx, word [esi + 18h]
    shr ecx, 1
    add eax, ecx
    mov [D1], ax
    mov esi, CURMENU + 16h + 2 * 38h    ; entry 2, the left team's bar: below its last row, the gap
    movzx eax, word [esi + 16h]
    add ax, [esi + 1Ah]
    add eax, GAP_
    mov [st_y], eax
    mov [D2], ax
    mov dword [A0], st_name
    call DMTC
    mov esi, [LIN]                      ; the virtual screen -> the display (DrawMenu flipped it before the name)
    mov edi, 0A0000h
    mov ecx, 16000
    rep movsd
    mov byte [st_shown], 1
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
    mov eax, 34                         ; the record and venue-row sizes by version: v2 names 33 B, v3 49 B
    cmp word [st_rec + 4], 2
    je .v
    cmp word [st_rec + 4], 3
    jne .close
    mov al, 50
.v:
    mov [st_rsz], eax
    add eax, 80
    mov [st_vsz], eax
    movzx esi, word [st_rec + 6]        ; the venues first (a neutral round: the line-ups' competition + round)
    test esi, esi
    jz .club
    mov edx, [st_rec + 8]
    call .seek
    jc .close
.ven:
    mov edx, st_vrow
    mov ecx, [st_vsz]
    call .read
    jne .close
    mov al, [st_vrow + ecx - 1]         ; its season: 0 = every one, else the career's (currentSeasonShowing + 1)
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
    mov ecx, [st_rsz]
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
    mov ecx, [st_rsz]
    dec ecx
    rep movsb
    mov byte [st_name + 48], 0          ; (at most 48 chars)
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

st_fn: db 'data\stadteam.dat', 0
st_mark: db 'STNM'                      ; (the harness finds these by the mark)
st_name: times 49 db 0                  ; the name shown last ('' = none)
st_shown: db 0                          ; 1 once the name is on the versus screen
st_key: dw 0                            ; countryNumber, teamOrdinal (looked up last)
st_y: dd 0                              ; the name's top row
st_rec: times 50 db 0
st_vrow: times VROW db 0                ; a venue row: competition[40], round[40], name[49], season
align 4
st_rsz: dd 0                            ; this file's record / venue-row size (v2 34 / 114, v3 50 / 130)
st_vsz: dd 0
st_regs: times 15 dd 0
"""


def sites(p):
    """The original obj1's sites and variables (vs: VersusInit's `call DrawMenu`; its `mov ecx, 100` after the fade-in
    at vs + 15)."""
    d = bytes(p.le.obj_bytes(1))
    r = sacups.regs(d)
    D7, A0, A1 = r['D7'], r['A0'], r['A1']
    D0, D1, D2 = D7 - 28, D7 - 24, D7 - 20
    pk = lambda x: re.escape(struct.pack('<I', x))
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    s7 = benchx.INFO['S7'] if 'S7' in benchx.INFO else benchx.sites7(p, r)   # (a probe of the original: no INFO)
    # VersusInit's end: call FadeOutToBlack / DrawMenu / CallToWaitRetrace / FadeIn, mov ecx, 100 / push ecx / call
    vs = [x.start() for x in re.finditer(rb'\xe8....\xe8....\xe8....\xe8....\xb9\x64\x00\x00\x00\x51\xe8', d, re.S)]
    assert len(vs) == 1, ('VersusInit end', vs)
    vs = vs[0] + 5                      # its `call DrawMenu`
    assert rel(vs) == s7['DRAWMENU'][1], ('VersusInit: not DrawMenu', hex(rel(vs)))
    assert bytes(p.get(1, vs, 5)) == d[vs:vs + 5], 'stadium: VersusInit\'s DrawMenu call already patched'
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
    assert len(m) == 1, ('DrawMenuTextCentered', m)
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
    # DrawMenu: ... mov drawSpritesWriteOnly, 80 / mov menuStatus, 0 / mov A6, offset g_currentMenu
    dm = s7['DRAWMENU'][1]
    cm = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(A0 + 24) + rb'....', d[dm:dm + 0x60], re.S)]
    assert cm, 'g_currentMenu'
    cur = tg(dm + cm[0] + 6)
    assert cur[0] == 2, ('g_currentMenu', cur)
    return {'vs': vs, 'DRAWMENU': (1, dm), 'CURMENU': cur, 'LIN': lin, 'DMTC': (1, m[0]), 'CHT': ct.pop(),
            'GT1': gt.pop(), 'GNAME': gn[0][0], 'GROUND': gn[0][1], 'SSN': ss.pop(), 'TOP': s7['TOP'],
            'D0': (2, D0), 'D1': (2, D1), 'D2': (2, D2), 'D3': (2, D7 - 16), 'D7': (2, D7), 'A0': (2, A0), 'A1': (2, A1)}


def patch(p, at):
    """st_* at obj3:at (after kbd2); returns the end."""
    s = sites(p)
    sym = {k: v for k, v in s.items() if k != 'vs'}
    sym.update(GAP_=(0, GAP), VROW=(0, VROW))
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
    p.branch(1, s['vs'], 0xE8, 3, lab['st_vs'])
    print(f'exe: stadium: the home club\'s stadium on the versus screen, obj3+{at:#x} ({len(code)} B'
          f'{", namespaces" if ns else ""}), VersusInit obj1+{s["vs"]:#x}')
    return at + len(code)


def build(records, venues=(), version=VERSION):
    """A STAD<stem>.DAT (v3): records = {(team file, ordinal): name}; venues = [(competition, round, name, season)]:
    the exact line-ups strings (gameName / gameRound, one row per language), season 0 = every one, n = the career's
    n-th (currentSeasonShowing + 1). Header 'STAD', u16 3, u16 V, u32 the venue table's offset; 256 x (u32 offset,
    u16 count) by team file; the club records (u8 ordinal + 49-byte name); the V venue rows (VROW bytes).
    version=2: the 4.0.6-I10 layout (33-byte names, names <= 32), for the harness's old-file case."""
    nm = OLD[version]
    lim = nm - 1
    by = {}
    for (f, o), n in records.items():
        by.setdefault(f, []).append((o, n))
    idx, body = bytearray(), bytearray()
    off = 12 + 256 * 6
    for f in range(256):
        recs = sorted(by.get(f, []))
        idx += struct.pack('<IH', off + len(body) if recs else 0, len(recs))
        for o, n in recs:
            body += bytes([o]) + check(n, lim).encode('ascii').ljust(nm, b'\0')
    ven = bytearray()
    for c, r, n, sn in venues:
        assert 0 < len(c) < 40 and 0 < len(r) < 40 and '*' not in c + r and 0 <= sn < 256, ('venue', c, r, sn)
        ven += c.encode('latin-1').ljust(40, b'\0') + r.encode('latin-1').ljust(40, b'\0') \
            + check(n, lim).encode('ascii').ljust(nm, b'\0') + bytes([sn])
    assert len(ven) == len(venues) * (81 + nm)
    return MAGIC + struct.pack('<HHI', version, len(venues), off + len(body)) + bytes(idx) + bytes(body) + bytes(ven)


def read(data):
    """A STAD<stem>.DAT back (the harness): ({(team file, ordinal): name}, [(competition, round, name, season)]);
    None if it is not a version-2 / 3 file (the game shows no name then)."""
    if len(data) < 12 + 256 * 6 or data[:4] != MAGIC or struct.unpack_from('<H', data, 4)[0] not in OLD:
        return None
    nm = OLD[struct.unpack_from('<H', data, 4)[0]]
    rec, vrow = 1 + nm, 81 + nm
    nv, voff = struct.unpack_from('<HI', data, 6)
    z = lambda b: b.split(b'\0')[0].decode('latin-1')
    recs = {}
    for f in range(256):
        off, n = struct.unpack_from('<IH', data, 12 + f * 6)
        for k in range(n):
            r = data[off + k * rec:off + (k + 1) * rec]
            recs[(f, r[0])] = z(r[1:])
    ven = [(z(v[:40]), z(v[40:80]), z(v[80:80 + nm]), v[80 + nm])
           for v in (data[voff + k * vrow:voff + (k + 1) * vrow] for k in range(nv))]
    return recs, ven


CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -.'")


def check(name, lim=NAME - 1):
    assert len(name) <= lim and set(name) <= CHARSET, ('stadium name', name)
    return name


def fit(name):
    """A source name (any case, accents) in the font: upper case, accents dropped, other characters -> space, at most
    48 (None if it does not fit: the short official form or today's name in the data, never a cut)."""
    import unicodedata
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper().replace('`', "'")
    s = ' '.join(''.join(c if c in CHARSET else ' ' for c in s).split())
    return s if 0 < len(s) <= NAME - 1 else None


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
            bad.append((row['country'], row['key'], row['stadium'], 'no club' if w is None else 'over 48'))
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
        assert n, ('venue over 48', r['venue'])
        for lang, _ in LANGS:
            v = (r[f'comp_{lang}'], r[f'round_{lang}'], n, int(r['season']))
            if v not in out:
                out.append(v)
    return out


def unmatched(data):
    """The club rows whose (file, ordinal) is not that club in the build's TMW5.nnn (another name, or no such club /
    file): [(file, ordinal, csv name, name there or None)]. 0 on the release data (the harness: stadium_clublist)."""
    import csv
    bad, files = [], {}
    for r in csv.DictReader(open(CLUBS_CSV, encoding='utf-8')):
        f, o = int(r['file']), int(r['ordinal'])
        if f not in files:
            fn = os.path.join(data, 'TMW5.%03d' % f)
            files[f] = open(fn, 'rb').read() if os.path.exists(fn) else b''
        d = files[f]
        nm = d[2 + 684 * o + 5:2 + 684 * o + 22].split(b'\0')[0].decode('latin-1') if 2 + 684 * (o + 1) <= len(d) else None
        if nm != r['name']:
            bad.append((f, o, r['name'], nm))
    return bad


def gen(data):
    """DATA\\STADTMW5.DAT (4.0.6: World 2026-27 only, Davide 02/11) when the build has its team files. A club row
    that is not that club in this build's data (an older world snapshot - the old-save scenarios build on the released
    4.0's -, a partial world: world_ns's first 20 files) gets no stadium: its line stays hidden, never another club's
    name; the count is printed. On the release data every row matches (stadium_clublist)."""
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
    if bad:
        print(f'STADTMW5.DAT: {len(bad)} club rows not in this world data, no stadium for them: {bad[:3]}')
    ven = venues()
    open(os.path.join(data, 'STADTMW5.DAT'), 'wb').write(build(recs, ven))
    return len(recs), len(ven)


def vcheck_exe(exe, lang, data):
    """The build's own check: this language's venue strings are strings of its exe or of a DATA file (gameName /
    gameRound copy them), exact. Returns the strings checked; prints the misses (a partial world - world_ns's first 20
    files - has not every competition: those venue rows just never match); stadium_clublist wants none on a release
    build (venue_misses)."""
    if not os.path.exists(os.path.join(data, 'STADTMW5.DAT')):
        return 0
    miss, n = venue_misses(exe, lang, data)
    if miss:
        print(f'exe: stadium venues: {len(miss)} {lang} strings not in this build (rows never matched): {miss[:3]}')
    return n


def venue_misses(exe, lang, data):
    """([(field, string)] of this language's venue rows not in its exe / DATA, strings checked)."""
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
    return miss, n


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
