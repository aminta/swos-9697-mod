"""Historic tournaments (session 26): playable only in PRESET COMPETITION and SEASON, never in a career.

Every team/competition selection screen is SelectTeamsFinalMenu started from competitionsTable[254] (worldTable:
[worldCup, -1] + continents 80..85 + FF). Only two of its five callers are rerouted to a cave stub: the preset
competition one (SelectTeamsForPresetCompetition) and the season one. The stub points competitionsTable[254] at an
extended world table for the duration of the call and then restores it, so the historic countries exist only there;
career start, career world view, transfers, team editing, friendlies and DIY keep the original table.

Country numbers (club range 86+, team file = country number):
  89 CLASSICS: countriesTable record + competitionsTable [-2, cups..., -1] (cups only: a season would add them to the
     league); TEAM.089 = the World Cup 1982 nations (SWOS 2020 DLC by Insane). Not in any continent table, seasonEndList, QTABLE or trailer.
Global numbers: every historic file uses the same base (they never meet each other or real teams in one contest;
SetLeagueNumbers / someLeaguesTable run only in a career), so all historic tournaments together cost MAX_TEAMS numbers.
"""
import os
import struct

import countries
import nasmcave
import sacups

BASE = 1786                 # shared by all historic team files (1786..1817)
MAX_TEAMS = 32
CLASSICS = 89
TEAM_SIZE = 684

MENU_COLOR = 11              # bg.backAndFrameColor of the CLASSICS button: BLUE_TO_PURPLE_11 (continents are brown)
MENU_GAP = 5                 # pixels between OCEANIA and CLASSICS
NAMES = {'it': b'TORNEI STORICI', 'en': b'CLASSIC TOURNEYS', 'fr': b'TOURNOIS ANCIENS', 'de': b'TURNIERKLASSIKER'}   # <= 16 chars

# World Cup 1982: squads from the SWOS 2020 DLC "1982 FIFA WORLD CUP (Spain)" by Insane (v1.1, sensiblesoccer.de,
# used with permission: credit the author). Its CUSTOMS.EDT holds the 24 nations (+ 24 legend teams of other years);
# taken by name, in the real group order A..F.
SWOS2020 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orig', 'swos2020')
WC82_ID = 0xC1
WC82_FILE = 'WC1982_CUSTOMS.EDT'
WC82 = ['ITALY', 'POLAND', 'PERU', 'CAMEROON',                         # A
        'WEST GERMANY', 'AUSTRIA', 'CHILE', 'ALGERIA',                  # B
        'ARGENTINA', 'BELGIUM', 'HUNGARY', 'EL SALVADOR',               # C
        'ENGLAND', 'FRANCE', 'CZECHOSLOVAKIA', 'KUWAIT',                # D
        'SPAIN', 'YUGOSLAVIA', 'NORTHERN IRELAND', 'HONDURAS',          # E
        'BRAZIL', 'SOVIET UNION', 'SCOTLAND', 'NEW ZEALAND']            # F

# Fixed next-round placement (replaces the random draw cseg_27F08 for our contests). Qualifiers arrive in A2+59h ordered
# 1st of each group A..F, then 2nd A..F (cseg_8A2CE: rank bonus 1000, group bonus 100, + points); slots are group-major.
# (contest id, teams in the round, permutation: new[k] = old[perm[k]])
DRAWS = [(WC82_ID, [0, 2, 11, 1, 3, 10, 6, 8, 5, 7, 9, 4]),   # 2nd round: 1A 1C 2F | 1B 1D 2E | 2A 2C 1F | 2B 2D 1E
         (WC82_ID, [0, 2, 1, 3])]                           # semi-finals: winner A - winner C, B - D

ASM = '''
hist_draw:                              ; replaces `call cseg_27F08` in cseg_26DFC (A2 = DIY buffer, A3 = round)
    pushad
    mov esi, [A2]
    mov al, [esi + 2Dh]
    mov edi, [A3]
    movzx ecx, word [edi + 161h]
    mov edx, DRAW_TABLE
.find:
    cmp byte [edx], 0
    je .orig
    cmp [edx], al
    jne .next
    cmp [edx + 1], cl
    je .perm
.next:
    movzx ebx, byte [edx + 1]
    lea edx, [edx + ebx + 2]
    jmp .find
.perm:
    add esi, 59h
    xor ebx, ebx
.copy:
    mov al, [esi + ebx]
    mov [DRAW_TMP + ebx], al
    inc ebx
    cmp ebx, ecx
    jb .copy
    xor ebx, ebx
.put:
    movzx eax, byte [edx + 2 + ebx]
    mov al, [DRAW_TMP + eax]
    mov [esi + ebx], al
    inc ebx
    cmp ebx, ecx
    jb .put
    popad
    ret
.orig:
    popad
    jmp DRAW_ORIG

DRAW_TABLE: DRAW_BYTES
DRAW_TMP: times 64 db 0

hist_names:                             ; replaces `call SetCountryNames` in SelectTeamsReinit
    call SET_COUNTRY_NAMES
    pushad
    push dword [D0]
    push dword [A0]
    mov dword [D0], 21                  ; first team/country entry
    call CALC_ENTRY
    mov esi, [A0]
.e:
    cmp word [esi + 2], 87              ; ordinal 87 = view selected teams (end of the entries)
    je .done
    cmp word [esi + 4], 0               ; isInvisible
    jne .n
    cmp dword [esi + 26h], CLASSICS_NAME
    jne .n
    mov word [esi + 1Eh], MENU_COLOR    ; bg.backAndFrameColor
    add word [esi + 16h], MENU_GAP      ; y (recomputed by SetTeamsCoordinates before every layout)
.n:
    add esi, 56
    jmp .e
.done:
    pop dword [A0]
    pop dword [D0]
    popad
    ret

hist_preset:
    push dword [COMP254]
    mov dword [COMP254], WORLD_PRESET
    call SELECT
    pop dword [COMP254]
    ret
'''


def build_teams(src_dir):
    """{file number: bytes} of the historic team files."""
    files = {}
    recs = []
    d = open(os.path.join(SWOS2020, WC82_FILE), 'rb').read()
    by = {}
    for k in range(struct.unpack('>H', d[:2])[0]):
        r = d[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE]
        by.setdefault(r[5:22].split(b'\0')[0].decode('latin1'), r)
    for i, name in enumerate(WC82):
        r = bytearray(by[name])
        r[0], r[1] = CLASSICS, i
        struct.pack_into('>H', r, 2, BASE + i)
        recs.append(bytes(r))
    assert len(recs) <= MAX_TEAMS
    files[CLASSICS] = struct.pack('>H', len(recs)) + b''.join(recs)
    return files


def _calls(p):
    """obj1 offsets of `call SelectTeamsFinalMenu` in the preset and season selectors, and the callee."""
    import re
    d1 = p.le.obj_bytes(1)
    d0 = sacups.regs(d1)['D7'] - 28
    ms = list(re.finditer(rb'\xc6\x05' + re.escape(struct.pack('<I', d0)) + rb'\xff\xe8(.{4})', d1, re.S))
    by = {}
    for m in ms:
        by.setdefault(m.end() + struct.unpack('<i', m.group(1))[0], []).append(m)
    select = max(by, key=lambda k: len(by[k]))
    sites = by[select]
    assert len(sites) == 5, len(sites)
    def pre(m):                                            # mov word [var], imm16 just before the mov D0, 255
        return d1[m.start() - 9:m.start() - 6], d1[m.start() - 6:m.start() - 2], d1[m.start() - 2:m.start()]
    preset = [m for m in sites if pre(m)[0] == b'\x66\xc7\x05' and pre(m)[2] == b'\x01\x00'
              and d1[m.end():m.end() + 3] == b'\x66\xc7\x05' and d1[m.end() + 3:m.end() + 7] == pre(m)[1]
              and d1[m.end() + 7:m.end() + 10] == b'\x00\x00\xc3']
    season = [m for m in sites if d1[m.end()] == 0xc3 and pre(m)[0] == b'\x66\xc7\x05' and pre(m)[2] == b'\x00\x00']
    assert len(preset) == 1 and len(season) == 1, (len(preset), len(season))
    return preset[0].end() - 5, season[0].end() - 5, select


def odd_groups(p):
    """Allow odd group sizes (World Cup 1982: 4 groups of 3). The preset/DIY cup setup (cseg_24DFA) traps with
    `test D0, 1; jz ok; int 3; jmp $` when a group stage has an odd number of teams per group, but the groups are DIY
    leagues and the league engine handles odd sizes (DIY leagues take 2..24 teams; days = n(n-1)/2 / (n div 2) = n,
    one team resting each day). The jz becomes jmp."""
    import re
    d1 = p.le.obj_bytes(1)
    d0 = sacups.regs(d1)['D7'] - 28
    ms = list(re.finditer(rb'\x66\x0b\xc0\x74\x0f\xf7\x05' + re.escape(struct.pack('<I', d0)) +
                          rb'\x01\x00\x00\x00\x74\x03\xcc\xeb\xfe', d1))
    assert len(ms) == 1, len(ms)
    p.put(1, ms[0].end() - 5, b'\xeb')
    print(f'exe: odd group sizes allowed (trap obj1+{ms[0].end() - 3:#x})')


def _names_call(p):
    """SelectTeamsReinit: call SetTeamsCoordinates; call SetLeagueNames; call SetCountryNames; mov ax, [...].
    SetCountryNames is the one that colours names starting with '.' (cmp byte [esi],'.'; ...; mov word [esi+1Eh],7).
    Returns (offset of `call SetCountryNames`, SetCountryNames, CalcMenuEntryAddress)."""
    import re
    d1 = p.le.obj_bytes(1)
    d0 = sacups.regs(d1)['D7'] - 28
    out = []
    for m in re.finditer(rb'\xe8(.{4})\xe8(.{4})\xe8(.{4})\x66\xa1', d1, re.S):
        t = m.start() + 15 + struct.unpack('<i', m.group(3))[0]
        body = d1[t:t + 0x200]
        i = body.find(b'\x80\x3e\x2e')
        if i < 0 or not re.search(rb'\x66\xc7\x46\x1e\x07\x00', body[i:i + 20]):
            continue
        c = re.search(rb'\xc7\x05' + re.escape(struct.pack('<I', d0)) + rb'\x15\x00\x00\x00\xe8(.{4})', body, re.S)
        out.append((m.start() + 10, t, t + c.end() + struct.unpack('<i', c.group(1))[0]))
    assert len(out) == 1, out
    return out[0]


def _draw_call(p):
    """obj1 offsets of the two `call cseg_27F08` (next-round random draw) and of cseg_27F08."""
    import re
    d1 = p.le.obj_bytes(1)
    a0 = sacups.regs(d1)['D7'] + 4
    a2, a3 = a0 + 8, a0 + 12
    head = (b'\xa1' + struct.pack('<I', a2) + b'\x83\xc0\x59\xa3' + struct.pack('<I', a0) + b'\x8b\x35' +
            struct.pack('<I', a3) + b'\x66\x8b\x86\x61\x01\x00\x00')
    starts = {m.start() for m in re.finditer(re.escape(head), d1)}
    calls = [(m.start(), m.end() + struct.unpack('<i', m.group(1))[0]) for m in re.finditer(rb'\xe8(.{4})', d1, re.S)]
    # cseg_26A78 (knockout rounds) and cseg_26DFC (group rounds): mov ax,[esi+15Fh]; or ax,ax; jnz +10;
    # call cseg_27F08; jmp near ...
    sites = [(c, t) for c, t in calls if t in starts and d1[c + 5] == 0xe9
             and d1[c - 12:c] == b'\x66\x8b\x86\x5f\x01\x00\x00\x66\x0b\xc0\x75\x0a']
    assert len(sites) == 2 and sites[0][1] == sites[1][1], sites
    return [c for c, _ in sites], sites[0][1]


def patch(p, lang, area, cave):
    """Register CLASSICS and the World Cup 1982; returns the new cave end."""
    d2 = p.le.obj_bytes(2)
    ct, tcn, _, _ = countries.tables(p)
    comp = countries.COMP[0]
    fx2 = {f[1] for f in p.le.fixups() if f[0] == 2}
    assert ct + 4 * CLASSICS not in fx2 and comp + 4 * CLASSICS not in fx2
    wobj, world = p.target(2, comp + 4 * 254)
    wd = p.le.obj_bytes(wobj)
    assert wd[world + 4:world + 8] == b'\xff' * 4
    cobj, wc = p.target(wobj, world)                       # worldCup: 0x28 header, 2 names, 24 (file, ordinal) pairs
    cd = p.le.obj_bytes(cobj)
    assert cd[wc + 1] == 2 and cd[wc + 2] == 0xff and cd[wc + 5] + 5 == 0x28 and cd[wc + 15] == 24
    conts = wd[world + 8:wd.index(b'\xff', world + 8)]
    assert sorted(conts) == list(range(80, 86))

    name = NAMES[lang]
    rec = area.add(bytes((countries.CONTINENT['europe'],)) + name + b'\0' + name + b'\0')
    p.add_ptr(2, ct + 4 * CLASSICS, 2, rec)
    p.put(2, tcn + 2 * CLASSICS, struct.pack('<H', BASE))

    wc_name = sacups.STR_BASE + struct.unpack_from('<I', cd, wc + 0x28)[0]
    full = cd[wc_name:cd.index(b'\0', wc_name)] + b' 1982'
    rel = area.add(full + b'\0') - sacups.STR_BASE
    hdr = bytearray(cd[wc:wc + 0x28])
    hdr[0] = WC82_ID
    assert hdr[12] == 3
    hdr[12] = 2                                            # 2 points for a win (1982)
    # real 1982 formula: 6 groups of 4 (top 2) -> 4 groups of 3 (winners) -> semi-finals, 3rd place play-off, final.
    # Stages from +0Eh: count, (teams, groups, teams per group) per stage (knockout: groups 0, 3rd place: FF), the
    # final 1, padding; from +22h one byte per stage (0 groups, 0x14 single match).
    stages = bytes([5, 24, 6, 4, 12, 4, 3, 4, 0, 4, 2, 0xff, 2, 2, 0, 2, 1, 0, 0, 0, 0, 0, 0x14, 0x14, 0x14, 0])
    assert len(stages) == 0x28 - 0x0e
    hdr[0x0e:0x28] = stages
    pairs = b''.join(bytes((CLASSICS, i)) for i in range(len(WC82)))
    at = cave
    wc82 = at
    blob = bytes(hdr) + struct.pack('<II', rel, rel) + pairs
    p.put(1, at, blob)
    at = (at + len(blob) + 3) & ~3

    table = at                                             # CLASSICS: [-2, WC82, -1] (cups only)
    p.put(1, at, struct.pack('<i', -2))
    p.add_ptr(1, at + 4, 1, wc82)
    p.put(1, at + 8, struct.pack('<i', -1))
    at += 12
    p.add_ptr(2, comp + 4 * CLASSICS, 1, table)

    wpre = at                                              # preset world table: + CLASSICS
    p.add_ptr(1, at, cobj, wc)
    p.put(1, at + 4, b'\xff' * 4 + conts + bytes((CLASSICS, 0xff)))
    at = (at + 8 + len(conts) + 2 + 3) & ~3

    odd_groups(p)
    pre_call, season_call, select = _calls(p)
    draw_calls, draw_orig = _draw_call(p)
    names_call, set_names, calc_entry = _names_call(p)
    regs = sacups.regs(p.le.obj_bytes(1))
    a0 = regs['D7'] + 4
    tbl = b''.join(bytes((cid, len(pm))) + bytes(pm) for cid, pm in DRAWS) + b'\0'
    symbols = {'COMP254': (2, comp + 4 * 254), 'WORLD_PRESET': (1, wpre), 'SELECT': (1, select),
               'A2': (2, a0 + 8), 'A3': (2, a0 + 12), 'DRAW_ORIG': (1, draw_orig),
               'DRAW_BYTES': (0, 'db ' + ', '.join(str(b) for b in tbl)),
               'D0': (2, a0 - 32), 'A0': (2, a0), 'SET_COUNTRY_NAMES': (1, set_names), 'CALC_ENTRY': (1, calc_entry),
               'CLASSICS_NAME': (2, rec + 1), 'MENU_COLOR': (0, MENU_COLOR), 'MENU_GAP': (0, MENU_GAP)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, pre_call + 1, struct.pack('<i', labels['hist_preset'] - (pre_call + 5)))
    p.put(1, names_call + 1, struct.pack('<i', labels['hist_names'] - (names_call + 5)))
    for c in draw_calls:
        p.put(1, c + 1, struct.pack('<i', labels['hist_draw'] - (c + 5)))
    print(f'exe: historic: fixed draws {[(hex(cid), len(pm)) for cid, pm in DRAWS]}, calls {[hex(c) for c in draw_calls]}')
    # season: no historic league yet -> its call stays on the original world table
    print(f'exe: historic: {name.decode()} = country {CLASSICS}, {full.decode()} id {WC82_ID:#x} @ obj1+{wc82:#x}, '
          f'preset call obj1+{pre_call:#x} -> obj1+{labels["hist_preset"]:#x} (season call obj1+{season_call:#x} untouched)')
    return (at + len(code) + 3) & ~3
