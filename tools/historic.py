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
import lib97
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

# Mitropa Cup 1934 (16 clubs, all rounds two legs incl. the final, play-off on aggregate tie, no away goals). TEAM.090.
# Ties in the real round-of-16 order, first-leg home club first: winners keep the tie order, so the natural pairing gives
# the real quarter-finals (W1-W2 Ferencvaros-Kladno, W3-W4 Bologna-Rapid, W5-W6 Ujpest-Juventus, W7-W8 Admira-Sparta) and
# semi-finals (Ferencvaros-Bologna, Juventus-Admira: DRAWS swaps to Admira at home first, and Admira first in the final).
# (1996 club giving the kit when mitropa34.py has none, index, 1934 name); squads: tools/mitropa34.py, build_m34.
M34_ID = 0xC2
M34_FILE = 90
M34_NAMES = {'it': b'COPPA MITROPA 1934', 'en': b'MITROPA CUP 1934', 'fr': b'COUPE MITROPA 1934', 'de': b'MITROPACUP 1934'}
M34 = [(16, 5, 'FERENCVAROS'), (1, 1, 'FLORIDSDORFER AC'),
       (6, 9, 'SK KLADNO'), (20, 21, 'AMBROSIANA'),
       (20, 7, 'BOLOGNA'), (16, 3, 'BOCSKAI'),
       (6, 8, 'SLAVIA PRAHA'), (1, 5, 'RAPID WIEN'),
       (1, 0, 'AUSTRIA WIEN'), (16, 16, 'UJPEST'),
       (20, 22, 'JUVENTUS'), (6, 4, 'TEPLITZER FK'),
       (1, 4, 'ADMIRA WIEN'), (20, 28, 'NAPOLI'),
       (16, 9, 'HUNGARIA'), (6, 10, 'SPARTA PRAHA')]
M34_LEGS = 0xA8              # two legs; on an aggregate tie a play-off (replay) with extra time, then the coin toss

# FA Cup 1871-72 (first edition): 15 clubs (tools/facup72.py), TEAM.091. Real first-round draw (7 ties) with Hampstead
# Heathens' bye (last club: lib97.lib_bye plays round 1 with 14, lib97.lib_pre puts the 15th into the 8-club round 2),
# then an open draw every round as in 1872 (DRAWS entry [0xFF] = bye only, then the game's random draw); single matches,
# a draw is replayed; a drawn replay gets extra time and then the coin toss (Davide: no endless replays, no penalties). Walkovers and the committee's "both teams go through"
# decisions cannot be reproduced (see STATUS session 26h).
FA_ID = 0xC3
FA_FILE = 91
FA_NAME = b'FA CUP 1871-72'
FA_LEGS = 0x28               # 1 match; a draw is replayed; in the replay extra time, then the coin toss (penalties if replay)

# Fixed next-round placement (replaces the random draw cseg_27F08 for our contests). Qualifiers arrive in A2+59h ordered
# 1st of each group A..F, then 2nd A..F (cseg_8A2CE: rank bonus 1000, group bonus 100, + points); slots are group-major.
# (contest id, teams in the round, permutation: new[k] = old[perm[k]])
DRAWS = [(WC82_ID, [0, 2, 11, 1, 3, 10, 6, 8, 5, 7, 9, 4]),   # 2nd round: 1A 1C 2F | 1B 1D 2E | 2A 2C 1F | 2B 2D 1E
         (WC82_ID, [0, 2, 1, 3]),                           # semi-finals: winner A - winner C, B - D
         (M34_ID, list(range(16))), (M34_ID, list(range(8))),  # keep the tie order (no random draw)
         (M34_ID, [0, 1, 3, 2]),                            # SF: Ferencvaros-Bologna, Admira-Juventus
         (M34_ID, [1, 0]),                                  # final: Admira at home first
         (FA_ID, list(range(14))), (FA_ID, [0xFF] + [0] * 7)]  # FA Cup: real 1st round; round 2: bye club + open draw
DRAWS += lib97.DRAWS                                        # Copa Libertadores 1997 (session 27): fixed real bracket

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
    call DRAW_PRE                       ; lib97.lib_pre (Libertadores holder into the round of 16), else ret
    cmp byte [edx + 2], 0FFh            ; 'pre only': the bye club joins, then the game's own random draw
    je .orig
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

draw_pre_none:
    ret
DRAW_TABLE: DRAW_BYTES
DRAW_TMP: times 64 db 0

; Coin toss (Mitropa 1934, FA Cup 1871-72): where the game would start a penalty shoot-out (only in the replay / play-off:
; legs byte 'penalties if replay'), the winner is drawn by lot. The 'penalty score' becomes 127-126 (impossible in a
; shoot-out) and the results screen shows COIN_TEXT instead of 'WIN n-m ON PENS'.
coin_ours:                              ; ZF = 1 if the running contest is one of ours
    cmp byte [DIYCOPY + 2Dh], M34_ID_
    je .r
    cmp byte [DIYCOPY + 2Dh], FA_ID_
.r:
    ret

coin_flip:                              ; eax = 0 or 1 (the game's random generator)
    pushad
    call RAND2
    movzx eax, byte [D0]
    shr eax, 7
    mov [COIN_TMP], eax
    popad
    mov eax, [COIN_TMP]
    ret

coin_sim:                               ; replaces `call cseg_2B84D` (simulated shoot-out) in cseg_2AE97
    call coin_ours
    jne PENS_SIM
    call coin_flip
    mov dword [D5], 7Fh                 ; side 0 wins: D6 <= D5
    mov dword [D6], 7Eh
    test eax, eax
    jz .r
    mov dword [D5], 7Eh                 ; side 1 wins: D6 > D5
    mov dword [D6], 7Fh
.r:
    ret

coin_play:                              ; replaces `call StartPenalties` in UpdateTime (penaltiesState already -1)
    call coin_ours
    jne START_PENALTIES
    call coin_flip
    test eax, eax
    jnz .t2
    mov word [PEN1], 7Fh
    mov word [PEN2], 7Eh
    mov dword [WINNER], TOP_TEAM
    jmp END_OF_GAME
.t2:
    mov word [PEN1], 7Eh
    mov word [PEN2], 7Fh
    mov dword [WINNER], BOTTOM_TEAM
    jmp END_OF_GAME

coin_text:                              ; replaces `mov ax, [skip flag]` before the results PrintFormatted (cseg_289AC)
    call coin_ours
    jne .x
    test byte [D7], 8                   ; penalties
    jz .x
    cmp word [D0], 7Eh
    jb .x
    cmp word [D1], 7Eh
    jb .x
    mov dword [A0], COIN_TEXT
.x:
    mov ax, [SKIP]
    ret
COIN_TMP: dd 0

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
    files[M34_FILE] = build_m34(src_dir)
    files[FA_FILE] = build_fa()
    return files


FILLER = {   # invented names for the '?' slots (no source), per nationality
    1: ('Franz Josef Karl Johann Leopold Rudolf Anton Ernst'.split(), 'Huber Gruber Pichler Moser Steiner Hofer Lechner Berger'.split()),
    15: ('J\u00f3zsef J\u00e1nos Istv\u00e1n L\u00e1szl\u00f3 Ferenc Gyula S\u00e1ndor Imre'.split(), 'Nagy T\u00f3th Horv\u00e1th Varga Moln\u00e1r N\u00e9meth Farkas Balogh'.split()),
    6: ('Josef Jan V\u00e1clav Karel Jaroslav Ladislav Anton\u00edn Miroslav'.split(), 'Nov\u00e1k Dvo\u0159\u00e1k Vesel\u00fd Hor\u00e1k N\u011bmec Pokorn\u00fd Mare\u0161 Posp\u00ed\u0161il'.split()),
    18: ('Mario Giuseppe Giovanni Luigi Carlo Pietro Bruno Aldo'.split(), 'Rossi Bianchi Colombo Ricci Marino Greco Bruno Galli'.split()),
}


def build_m34(src_dir):
    """TEAM.090: the 16 Mitropa 1934 clubs (tools/mitropa34.py) on the 1934 national teams of the SWOS 2020 DLC."""
    import random
    import c1c2
    import mitropa34
    d = open(os.path.join(SWOS2020, 'x_wc34', 'CUSTOMS.EDT'), 'rb').read()
    nations, known = {}, {}
    for k in range(struct.unpack('>H', d[:2])[0]):
        r = d[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE]
        nations.setdefault(r[76], r) if r[5:22].split(b'\0')[0] in (b'ITALY', b'AUSTRIA', b'HUNGARY', b'CZECHOSLOVAKIA') else None
        for j in range(16):
            p = r[76 + j * 38:76 + (j + 1) * 38]
            known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
    rng = random.Random(1934)
    recs, fillers = [], []
    for i, (club, coach, nat, target, kit, roles) in enumerate(mitropa34.CLUBS):
        t = nations[nat]
        n, k, _ = M34[i]                                   # the 1996 placeholder club: kit when none is given
        old = open(os.path.join(src_dir, 'TEAM.%03d' % n), 'rb').read()[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE]
        r = bytearray(t)
        r[0], r[1] = M34_FILE, i
        struct.pack_into('>H', r, 2, BASE + i)
        r[5:22] = club.encode('latin1').ljust(17, b'\0')[:17]
        r[26:36] = bytes(kit) + bytes((0, 1, 1, 1, 1)) if kit else old[26:36]
        r[36:59] = c1c2.swos_name(coach).encode('latin1').ljust(23, b'\0')[:23] if coach else bytes(23)
        avg = sum(t[76 + j * 38 + 32] for j in range(16)) / 16
        step = max(-3, min(2, round((target - avg) / 2)))
        pools = {c: list(v) for c, v in roles.items()}
        borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
        for j in range(16):
            p = 76 + j * 38
            cls = c1c2.CLASS[t[p + 26] >> 5]
            src = next(x for x in borrow[cls] if pools[x])
            who = pools[src].pop(0)
            pnat = nat
            if isinstance(who, tuple):
                who, pnat = who
            if who == '?':
                first, last = FILLER[nat]
                while True:
                    who = f'{rng.choice(first)} {rng.choice(last)}'
                    if c1c2.swos_name(who) not in known:
                        break
                fillers.append((club, who))
            name = c1c2.swos_name(who)
            if name in known and known[name][0] == pnat:   # a 1934 international: Insane's record (skills, face)
                q = bytearray(known[name])
                q[2] = t[p + 2]                            # the slot's shirt number
                r[p:p + 38] = q
            else:
                r[p] = pnat
                r[p + 3:p + 26] = name.encode('latin1').ljust(23, b'\0')[:23]
                c1c2.level_player(r, p, step)
            if name in mitropa34.STARS:
                c1c2.level_player(r, p, 1)
                r[p + 32] = 49
        assert not any(pools.values()), (club, pools)
        recs.append(bytes(r))
    print(f'TEAM.090: Mitropa 1934, {len(fillers)} invented names: {fillers}')
    return struct.pack('>H', len(recs)) + b''.join(recs)


def build_fa():
    """TEAM.091: the 15 FA Cup 1871-72 clubs (tools/facup72.py) on the SWOS 2020 'British Football Pioneers' DLC by
    Francescomanetti82 and Gorzo (template club: slots, numbers, faces, kit; players of the same name keep its record)."""
    import random
    import c1c2
    import facup72
    d = open(os.path.join(SWOS2020, 'x_pioneers', 'CUSTOMS.EDT'), 'rb').read()
    teams, known = {}, {}
    for k in range(struct.unpack('>H', d[:2])[0]):
        r = d[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE]
        teams[r[5:22].split(b'\0')[0].decode('latin1')] = r
        for j in range(16):
            p = r[76 + j * 38:76 + (j + 1) * 38]
            known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
    first = 'George Henry Charles Frederick William Arthur Edward Walter Herbert Alfred'.split()
    last = 'Smith Taylor Brown Wilson Johnson Wright Walker Hall Green Wood Hughes Edwards Turner Cooper Parker'.split()
    rng = random.Random(1872)
    recs, fillers = [], []
    for i, (club, capt, tname, target, kit, roles) in enumerate(facup72.CLUBS):
        t = teams[tname]
        r = bytearray(t)
        r[0], r[1] = FA_FILE, i
        struct.pack_into('>H', r, 2, BASE + i)
        r[5:22] = club.encode('latin1').ljust(17, b'\0')[:17]
        if kit:
            r[26:36] = bytes(kit) + bytes((0, 1, 1, 1, 1))
        r[36:59] = c1c2.swos_name(capt).encode('latin1').ljust(23, b'\0')[:23] if capt != '?' else bytes(23)
        avg = sum(t[76 + j * 38 + 32] for j in range(16)) / 16
        step = max(-3, min(3, round((target - avg) / 2)))
        pools = {c: list(v) for c, v in roles.items()}
        borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
        for j in range(16):
            p = 76 + j * 38
            cls = c1c2.CLASS[t[p + 26] >> 5]
            who = pools[next(x for x in borrow[cls] if pools[x])].pop(0)
            if who == '?':
                while True:
                    who = f'{rng.choice(first)} {rng.choice(last)}'
                    if c1c2.swos_name(who) not in known:
                        break
                fillers.append((club, who))
            name = c1c2.swos_name(who)
            src = facup72.ALIAS.get(name, name)
            if src in known and known[src][0] == t[p]:     # the Pioneers' record of the same player
                q = bytearray(known[src])
                q[2] = t[p + 2]
                q[3:26] = name.encode('latin1').ljust(23, b'\0')[:23]
                r[p:p + 38] = q
            else:
                r[p + 3:p + 26] = name.encode('latin1').ljust(23, b'\0')[:23]
                c1c2.level_player(r, p, step)
        assert not any(pools.values()), (club, pools)
        recs.append(bytes(r))
    print(f'TEAM.091: FA Cup 1871-72, {len(fillers)} invented names: {fillers}')
    return struct.pack('>H', len(recs)) + b''.join(recs)


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


def _coin(long, short):
    """long (36 columns) and short (26 columns) variants, as the game's own result strings."""
    def pad(t, w):
        n = len(t) - 2 + 12
        left = max(0, (w - n) // 2)
        return (' ' * left + t + ' ' * max(0, w - n - left)).encode('latin1')
    return pad(long, 36) + b'\0' + pad(short, 26) + b'\0'


COIN_TEXT = {'it': _coin('%a VINCE AL SORTEGGIO', '%a VINCE A SORTE'),
             'en': _coin('%a WIN ON THE TOSS OF A COIN', '%a WIN THE COIN TOSS'),
             'fr': _coin('%a GAGNE AU TIRAGE AU SORT', '%a GAGNE AU SORT'),
             'de': _coin('%a GEWINNT DURCH LOSENTSCHEID', '%a GEWINNT PER LOS')}


def _coin_sites(p, draw_orig):
    """Hook sites of the coin toss (see ASM) in any language."""
    import re
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    d7 = r['D7']
    a0 = d7 + 4
    out = {}
    # cseg_2AE97: or byte [D7], 8; (pushes); call cseg_2B84D - the second 'or byte [D7], 8' in the exe
    ors = [m.start() for m in re.finditer(re.escape(b'\x80\x0d' + struct.pack('<I', d7) + b'\x08'), d1)]
    assert len(ors) == 2, ors
    k = d1.index(b'\xe8', ors[1] + 7)
    assert k - ors[1] < 0x40
    out['sim_call'], out['pens_sim'] = k, k + 5 + struct.unpack_from('<i', d1, k + 1)[0]
    # UpdateTime: mov [winningTeamPtr], 0; call EndOfGame; jmp; mov word [extraTimeState], -1; call StartFirstExtraTime;
    # jmp; mov word [penaltiesState], -1; call StartPenalties
    pat = (rb'\xc7\x05(.{4})\x00\x00\x00\x00\xe8(.{4})\xe9.{4}\x66\xc7\x05.{4}\xff\xff\xe8.{4}\xe9.{4}'
           rb'\x66\xc7\x05(.{4})\xff\xff\xe8(.{4})')
    m = list(re.finditer(pat, d1, re.S))
    assert len(m) == 1, len(m)
    m = m[0]
    out['winner'] = struct.unpack('<I', m.group(1))[0]
    eog = m.start() + 10
    out['end_of_game'] = eog + 5 + struct.unpack('<i', m.group(2))[0]
    ps = struct.unpack('<I', m.group(3))[0]
    out['pen_call'] = m.end() - 5
    out['start_pen'] = m.end() + struct.unpack('<i', m.group(4))[0]
    # @@team2_wins: mov [winningTeamPtr], offset bottomTeamInGame; jmp; @@team1_wins: mov [..], offset topTeamInGame; jmp
    w = re.escape(m.group(1))
    t = list(re.finditer(rb'\xc7\x05' + w + rb'.{4}\xeb.\xc7\x05' + w + rb'.{4}\xeb.', d1, re.S))
    assert len(t) == 1 and 0 < m.start() - t[0].start() < 0x40, len(t)
    tobj, out['bottom'] = p.target(1, t[0].start() + 6)
    tobj2, out['top'] = p.target(1, t[0].start() + 18)
    assert tobj == tobj2 == 2
    # after the match: mov ax, [penaltiesState]; or ax, ax; jns; mov ax, [team1PenaltyGoals]; ...; mov ax, [team2PenaltyGoals]
    q = re.search(rb'\x66\xa1' + re.escape(struct.pack('<I', ps)) + rb'\x66\x0b\xc0\x79.\x66\xa1(.{4})\x66\xa3.{4}\x66\xa1(.{4})',
                  d1, re.S)
    out['pen1'], out['pen2'] = (struct.unpack('<I', q.group(k))[0] for k in (1, 2))
    # cseg_289AC: mov [A0], offset aAWin01OnPensRe; jmp short $+2; mov ax, [skip]; or ax, ax; jz; mov esi, [A0]
    t = list(re.finditer(rb'\xc7\x05' + re.escape(struct.pack('<I', a0)) + rb'.{4}\xeb\x00\x66\xa1(.{4})\x66\x0b\xc0\x74.\x8b\x35'
                         + re.escape(struct.pack('<I', a0)), d1, re.S))
    assert len(t) == 1, len(t)
    out['text_site'] = t[0].start() + 12
    out['skip'] = struct.unpack('<I', t[0].group(1))[0]
    # the game's random generator: first call of cseg_27F08 (the draw shuffle)
    k = d1.index(b'\xe8', draw_orig)
    out['rand2'] = k + 5 + struct.unpack_from('<i', d1, k + 1)[0]
    # diyFileBufferCopy: as lib97
    # diyFileBufferCopy (as lib97._sites): end of cseg_24DFA -> cseg_2573C -> mov [A0], offset diyFileBufferCopy
    m = re.search(rb'\x66\x89\x86\x61\x01\x00\x00\xe8(.{4})\xe8.{4}\xc3\xcc\xeb\xfe', d1, re.S)
    c = m.start() + 12 + struct.unpack('<i', m.group(1))[0]
    k = d1.find(b'\xc7\x05' + struct.pack('<I', a0), c)
    assert 0 < k - c < 0x60
    out['diycopy'] = struct.unpack_from('<I', d1, k + 6)[0]
    return out


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


def patch(p, lang, area, cave, draw_pre=None):
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

    # Mitropa Cup 1934: same layout, knockout stages only; [0Ah] = 0 away goals off (as worldCup)
    assert cd[wc + 0x0a] == 0
    assert ct + 4 * M34_FILE not in fx2
    p.add_ptr(2, ct + 4 * M34_FILE, 2, rec)                # a club's country = CLASSICS (never null)
    p.put(2, tcn + 2 * M34_FILE, struct.pack('<H', BASE))
    rel = area.add(M34_NAMES[lang] + b'\0') - sacups.STR_BASE
    hdr = bytearray(cd[wc:wc + 0x28])
    hdr[0] = M34_ID
    hdr[12] = 2
    stages = bytes([4, 16, 0, 16, 8, 0, 8, 4, 0, 4, 2, 0, 2, 1, 0, 0, 0, 0, 0, 0] + [M34_LEGS] * 4 + [0, 0])
    assert len(stages) == 0x28 - 0x0e
    hdr[0x0e:0x28] = stages
    m34 = at
    blob = bytes(hdr) + struct.pack('<II', rel, rel) + b''.join(bytes((M34_FILE, i)) for i in range(len(M34)))
    p.put(1, at, blob)
    at = (at + len(blob) + 3) & ~3

    # FA Cup 1871-72: 15 clubs, knockout only, single matches, replays (legs byte 0: 1 leg, no e.t., no penalties)
    import facup72
    assert ct + 4 * FA_FILE not in fx2
    p.add_ptr(2, ct + 4 * FA_FILE, 2, rec)
    p.put(2, tcn + 2 * FA_FILE, struct.pack('<H', BASE))
    rel = area.add(FA_NAME + b'\0') - sacups.STR_BASE
    nfa = len(facup72.CLUBS)
    hdr = bytearray(cd[wc:wc + 0x28])
    hdr[0] = FA_ID
    hdr[12] = 2
    stages = bytes([4, nfa, 0, nfa, 8, 0, 8, 4, 0, 4, 2, 0, 2, 1, 0, 0, 0, 0, 0, 0] + [FA_LEGS] * 4 + [0, 0])
    assert len(stages) == 0x28 - 0x0e and nfa == 15
    hdr[0x0e:0x28] = stages
    fa = at
    blob = bytes(hdr) + struct.pack('<II', rel, rel) + b''.join(bytes((FA_FILE, i)) for i in range(nfa))
    p.put(1, at, blob)
    at = (at + len(blob) + 3) & ~3

    table = at                                             # CLASSICS: [-2, WC82, M34, FA, -1] (cups only)
    p.put(1, at, struct.pack('<i', -2))
    p.add_ptr(1, at + 4, 1, wc82)
    p.add_ptr(1, at + 8, 1, m34)
    p.add_ptr(1, at + 12, 1, fa)
    p.put(1, at + 16, struct.pack('<i', -1))
    at += 20
    p.add_ptr(2, comp + 4 * CLASSICS, 1, table)

    wpre = at                                              # preset world table: + CLASSICS
    p.add_ptr(1, at, cobj, wc)
    p.put(1, at + 4, b'\xff' * 4 + conts + bytes((CLASSICS, 0xff)))
    at = (at + 8 + len(conts) + 2 + 3) & ~3

    odd_groups(p)
    pre_call, season_call, select = _calls(p)
    draw_calls, draw_orig = _draw_call(p)
    coin = _coin_sites(p, draw_orig)
    coin_text = area.add(COIN_TEXT[lang])
    names_call, set_names, calc_entry = _names_call(p)
    regs = sacups.regs(p.le.obj_bytes(1))
    a0 = regs['D7'] + 4
    tbl = b''.join(bytes((cid, len(pm))) + bytes(pm) for cid, pm in DRAWS) + b'\0'
    symbols = {'COMP254': (2, comp + 4 * 254), 'WORLD_PRESET': (1, wpre), 'SELECT': (1, select),
               'A2': (2, a0 + 8), 'A3': (2, a0 + 12), 'DRAW_ORIG': (1, draw_orig),
               'DRAW_BYTES': (0, 'db ' + ', '.join(str(b) for b in tbl)),
               'DRAW_PRE': (1, draw_pre) if draw_pre is not None else (0, 'draw_pre_none'),
               'D0': (2, a0 - 32), 'A0': (2, a0), 'SET_COUNTRY_NAMES': (1, set_names), 'CALC_ENTRY': (1, calc_entry),
               'CLASSICS_NAME': (2, rec + 1), 'MENU_COLOR': (0, MENU_COLOR), 'MENU_GAP': (0, MENU_GAP),
               'M34_ID_': (0, M34_ID), 'FA_ID_': (0, FA_ID), 'COIN_TEXT': (2, coin_text),
               'DIYCOPY': (2, coin['diycopy']), 'RAND2': (1, coin['rand2']), 'D5': (2, a0 - 12), 'D6': (2, a0 - 8),
               'D7': (2, a0 - 4), 'D1': (2, a0 - 28), 'PENS_SIM': (1, coin['pens_sim']),
               'START_PENALTIES': (1, coin['start_pen']), 'END_OF_GAME': (1, coin['end_of_game']),
               'PEN1': (2, coin['pen1']), 'PEN2': (2, coin['pen2']), 'WINNER': (2, coin['winner']),
               'TOP_TEAM': (2, coin['top']), 'BOTTOM_TEAM': (2, coin['bottom']), 'SKIP': (2, coin['skip'])}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, pre_call + 1, struct.pack('<i', labels['hist_preset'] - (pre_call + 5)))
    p.put(1, names_call + 1, struct.pack('<i', labels['hist_names'] - (names_call + 5)))
    for site, label in ((coin['sim_call'], 'coin_sim'), (coin['pen_call'], 'coin_play')):
        p.put(1, site + 1, struct.pack('<i', labels[label] - (site + 5)))
    p.put(1, coin['text_site'], b'\xe8' + struct.pack('<i', labels['coin_text'] - (coin['text_site'] + 5)) + b'\x90')
    print(f'exe: historic: coin toss: sim call obj1+{coin["sim_call"]:#x}, StartPenalties call obj1+{coin["pen_call"]:#x}, '
          f'results text obj1+{coin["text_site"]:#x}')
    for c in draw_calls:
        p.put(1, c + 1, struct.pack('<i', labels['hist_draw'] - (c + 5)))
    print(f'exe: historic: fixed draws {[(hex(cid), len(pm)) for cid, pm in DRAWS]}, calls {[hex(c) for c in draw_calls]}')
    # season: no historic league yet -> its call stays on the original world table
    print(f'exe: historic: {name.decode()} = country {CLASSICS}, {full.decode()} id {WC82_ID:#x} @ obj1+{wc82:#x}, '
          f'preset call obj1+{pre_call:#x} -> obj1+{labels["hist_preset"]:#x} (season call obj1+{season_call:#x} untouched)')
    return (at + len(code) + 3) & ~3
