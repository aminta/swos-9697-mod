"""Stoppage time (4.0.6, Davide + Marco, 02/11): added minutes at the end of each half, internal/reports/stoppage-406.

The game's clock (UpdateTime): gameTime holds BCD minute digits (bytes +1 hundreds, +2 tens, +3 units), gameSeconds
0..59; each frame secondsSwitchAccumulator -= timeDelta (gameLenSecondsTable 30 / 18 / 12 / 9 by game length), on a
borrow +54 and gameSeconds += lastFrameTicks. It runs only with the ball in play (ST_GAME_IN_PROGRESS, not in
penalties). At 45 / 90 / 105 / 120 the half ends after 55 ticks, at the first ball out of both penalty areas
(endGameCounter), then half time / full time (aggregate, extra time, penalties) / the extra-time halves.

Here, at those four minutes (gameSeconds >= 0: the roll, not the end counter's pass) the half gets N added minutes,
decided from what happened in it - no Rand (an extra draw would shift the game's sequence):
  N = base + (3 goals + 3 substitutions made + 2 cards + dead-ball ticks / KD) / 6, both teams, in that half,
  capped by the era's cap for that half (ST_CAPS: first half, second half, each extra-time half; 0 = none); era():
  per career world (world byte) or pack (team 1's file), default 1996-97.
- st_chk (check_game_end's `cmp dword [gameTime], 1000000h`, a jmp): minute 1 resets the state; at the end minute
  ST_PH = 1, the clock stays there and the code skips to @@no_update_to_time; when the added minutes are over,
  ST_PH = 2 and the game's own end runs (its 55 ticks and the ball out of the areas: an attack in progress is played
  out) with our clock still up (Davide, MiSTer 02/11: the '+1' had gone back to a plain 45 for that wait).
- st_wh (PlayEndGameWhistleSample's `mov edx, [linAdr982k]`, only UpdateTime's four end-of-half whistles call it):
  ST_PH = 0, the game's clock again from the whistle (half time, full time, extra time, the next kick-off).
- st_min (the minute roll `add byte [gameTime+3], 1`): in added time ST_K + 1 instead (units 5 / 0: never 10), and
  the clock redrawn (its minute runs).
- st_delta (`mov ax, [timeDelta]`): in added time 9, the 10-minute game's rate (Davide: playable added time at any
  game length - 5 minutes ~26 s of play).
- st_img (the clock render's `mov ax, [D3] / mov esi, [A0]`): with ST_PH 1 / 2 the clock sprite is ours, ST_IDX,
  64 px wide: the game's clock picture (CopySprite: chunky or, half / EGA mode, planar) with its minute running (Davide:
  a TV clock, the units digit = the end minute's + K - 1 in added minute K: 90, 91 .. 94 for +5, then + N waiting for
  the whistle, 95; gameTime itself stays at the end minute), a '+' and the big digit N (the fourth official's board:
  the total, as Davide chose). The era caps keep the units <= 9 (rows() asserts it): only the units digit moves.
- st_reset (ResetTime's `mov dword [gameTime], 0`): a new match, no added time pending.
- st_goal (GoalScored's `mov eax, [gameTime]`): in added time the goal's time byte +0 (unused by the game) = ST_K;
  waiting for the whistle N; st_fmt (the scorer list's `mov esi, [A0] / mov [esi], eax`): such a time printed 45+2,
  90+3(PEN).
Off under SWOS++ (it changes UpdateTime and keeps its own clock in its highlights).
spritesIndex[ST_IDX] points at ST_HDR from the start (a blank 64 x 11 sprite): a highlight replayed from a file draws
it blank, never a stray pointer.
"""
import re
import struct

import lepatch
import nasmcave

ST_IDX = 2037                           # (benchx's index map: 2035..2036 blond ICONW, 2037 this, 2038.. free)
WQ, NL = 4, 11                          # our clock sprite: 64 px, the game's 11 lines


def era(y):
    """The parameters of a season starting in y: (cap first half, cap second half, cap each extra-time half, base,
    KD). Caps (Marco: 5 in 2026-27, 3 in 1996-97, hard maxima) and the formula (Fable's review, 02/11):
      N = base + (3 goals + 3 substitutions made + 2 cards + dead-ball ticks / KD) / 6   (units of 10 s: a goal or a
      substitution ~30 s, a card ~20 s - IFAB's list; an injury's stoppage is in the dead-ball time)
    base 0 before 1970 (many halves ended on the minute); KD 0 = no dead-ball term (1996-97 and older stay at 1-3),
    233 in today's football (~40 s of dead ball a half at 70 ticks a second -> 2 minutes: N reaches 4-5)."""
    return (3, 5, 1, 1, 233) if y >= 2000 else (2, 3, 1, 1, 0) if y >= 1990 else (1, 2, 1, 1, 0) if y >= 1971 \
        else (1, 1, 0, 0, 0)


DEFAULT_YEAR = 1996                     # the base game, friendlies of its teams, anything not in the tables


def _year(pk):
    y = re.search(r'(1[89]|20)\d\d', pk.meta.get('id', ''))
    return int(y.group(0)) if y else DEFAULT_YEAR     # (a yearless pack - test packs, lp36: the base game's rules)


def career_worlds():
    """[(career world byte, era)] of this build's career worlds (mkseason's packs: the year in the pack id)."""
    import mkseason
    return [(w, era(_year(pks[0]))) for w, pks in sorted(mkseason.worlds().items())]


def pack_files():
    """[(team file number, era)] of this build's season and tourney packs (CLASSIC SEASONS / TOURNEYS - and a friendly
    of their teams): the match's first team's file (TeamFile byte 0) picks the row."""
    import mkseason
    out = {}
    for pk in mkseason.packs():
        if pk.world is None and pk.kind in ('season', 'tourney'):
            for v in pk.meta.get('files', {}).values():
                out[v['file']] = era(_year(pk))
    return sorted(out.items())
PLUS = [(2, 2, 2), (2, 3, 2), (3, 3, 8), (0, 4, 2), (1, 4, 2), (2, 4, 2), (3, 4, 2), (4, 4, 2), (1, 5, 8), (2, 5, 2),
        (3, 5, 8), (4, 5, 8), (5, 5, 8), (2, 6, 2), (3, 6, 8), (3, 7, 8)]   # '+', the clock digits' white 2 / shadow 8

ASM = r"""
st_chk:                                 ; check_game_end: `cmp dword [GT], 1000000h` (then jnz)
    pushad
    cmp byte [SWOSPP], 0FFh
    jne .orig
    mov eax, [GT]
    cmp eax, 01000000h                  ; minute 1: a match (or its replay) starts
    jne .n1
    mov byte [ST_PH], 0
    mov dword [ST_AT], 0
    call st_score
    mov [ST_SNAP], eax
.half:
    mov eax, [ST_DEAD]                  ; (a half's first minute: its dead-ball time from here - not the break's)
    mov [ST_DSNAP], eax
    jmp .orig
.n1:
    cmp eax, 06040000h                  ; 46
    je .half
    cmp eax, 01090000h                  ; 91
    je .half
    cmp eax, 06000100h                  ; 106
    je .half
    cmp byte [ST_PH], 0
    jne .added
    cmp eax, [ST_AT]                    ; (this end minute's added time already played)
    je .orig
    cmp word [GSEC], 0                  ; (-1: the end counter's pass)
    jl .orig
    xor ebx, ebx                        ; ebx = the cap's index: 0 first half, 1 second, 2 extra time
    cmp eax, 05040000h                  ; 45
    je .end
    inc ebx
    cmp eax, 00090000h                  ; 90
    je .end
    inc ebx
    cmp eax, 05000100h                  ; 105
    je .end
    cmp eax, 00020100h                  ; 120
    jne .orig
.end:
    mov [ST_AT], eax
    call st_caps
    call st_score
    mov ecx, eax
    xchg eax, [ST_SNAP]
    sub ecx, eax                        ; the half's events (10-second units)
    movzx esi, word [ST_KD]
    test esi, esi
    jz .nd
    mov eax, [ST_DEAD]
    sub eax, [ST_DSNAP]
    xor edx, edx
    div esi
    add ecx, eax                        ; + dead-ball ticks / KD
.nd:
    mov eax, ecx
    xor edx, edx
    mov esi, 6
    div esi
    movzx ecx, byte [ST_CAPS + 3]
    add ecx, eax                        ; N = base + units / 6
    movzx eax, byte [ST_CAPS + ebx]
    cmp ecx, eax
    jbe .n
    mov ecx, eax
.n: jecxz .orig                         ; (a cap of 0: the game's end)
    mov [ST_N], cl
    mov byte [ST_K], 1
    mov byte [ST_PH], 1
    mov word [COPYT], 1                 ; (the clock redrawn: ours)
.skip:
    popad
    jmp NOUPD
.added:
    cmp byte [ST_PH], 1
    jne .orig                           ; (2: the game's own end of half, our clock up until the whistle)
    mov al, [ST_K]
    cmp al, [ST_N]
    jbe .skip
    mov byte [ST_PH], 2                 ; over: the game's own end of half
    mov word [COPYT], 1
.orig:
    popad
    cmp dword [GT], 01000000h
    jmp CHKRET

st_score:                               ; eax = 3 (goals + substitutions made) + 2 cards, both teams (10-s units)
    push ebx
    push ecx
    movzx eax, word [SG1]
    movzx ebx, word [SG2]
    add eax, ebx
    movzx ebx, word [NS1]               ; (team1NumSubs / team2NumSubs: the changes made)
    add eax, ebx
    movzx ebx, word [NS2]
    add eax, ebx
    lea ecx, [eax + eax * 2]
    movzx eax, word [TS1 + 6]           ; (bookings, sendings off)
    movzx ebx, word [TS1 + 8]
    add eax, ebx
    movzx ebx, word [TS2 + 6]
    add eax, ebx
    movzx ebx, word [TS2 + 8]
    add eax, ebx
    lea eax, [ecx + eax * 2]
    pop ecx
    pop ebx
    ret

st_dead:                                ; UpdateGameTimers' `add [stoppageTimerTotal], ax` (the ball not in play)
    add [SPT], ax
    push eax
    movzx eax, ax
    add [ST_DEAD], eax
    pop eax
    ret

st_caps:                                ; ST_CAPS (3 caps, base), ST_KD = this match's era: a career by its world
    pushad                              ; byte, else by the first team's file (season / tourney packs), else default
    mov esi, ST_DEF
    cmp word [GAMETYPE], 4
    jne .file
    mov al, [SLT + WORLD_BYTE_]
    mov edi, ST_WTAB
    jmp .find
.file:
    mov edi, [GTEAM1]
    test edi, edi
    jz .set
    mov al, [edi]                       ; (TeamFile byte 0: the team's file number)
    mov edi, ST_FTAB
.find:
    movzx ecx, byte [edi]               ; (rows: key, caps x 3, base, 0, KD)
    inc edi
    jecxz .set
.l: cmp [edi], al
    je .hit
    add edi, 8
    loop .l
    jmp .set
.hit:
    mov esi, edi
.set:
    mov eax, [esi + 1]
    mov [ST_CAPS], eax
    mov ax, [esi + 6]
    mov [ST_KD], ax
    popad
    ret

st_min:                                 ; the minute roll: `add byte [GT + 3], 1`
    cmp byte [ST_PH], 1
    je .k
    add byte [GT + 3], 1
    ret
.k: inc byte [ST_K]
    mov word [COPYT], 1                 ; (the clock's minute runs)
    ret

st_delta:                               ; `mov ax, [TDELTA]`: the added minutes at the 10-minute game's rate
    mov ax, [TDELTA]
    cmp byte [ST_PH], 1
    jne .x
    mov ax, 9
.x: ret

st_reset:                               ; ResetTime: `mov dword [GT], 0`
    mov dword [GT], 0
    mov byte [ST_PH], 0
    mov dword [ST_AT], 0
    ret

st_goal:                                ; GoalScored: `mov eax, [GT]`; in added time byte +0 = the added minute
    mov eax, [GT]                       ; (waiting for the whistle: N)
    cmp byte [ST_PH], 0
    je .x
    mov al, [ST_K]
    cmp byte [ST_PH], 1
    je .x
    mov al, [ST_N]
.x: ret

st_wh:                                  ; PlayEndGameWhistleSample: `mov edx, [LINADR]` (the end-of-half whistles)
    mov byte [ST_PH], 0                 ; (the game's clock again: UpdateTime renders it right after)
    mov word [COPYT], 1
    mov edx, [LINADR]
    ret

st_fmt:                                 ; the scorer list: `mov esi, [A0] / mov [esi], eax` (eax = the goal's time)
    mov esi, [A0]
    mov [esi], eax
    test al, al
    jz .x
    push eax
    push edi
    mov edi, ST_STR
    mov [edi], eax                      ; (byte 0 skipped by the game, then the 3 digits)
    mov byte [edi + 4], '+'
    add al, '0'
    mov [edi + 5], al
    add esi, 4
    add edi, 6
.c: mov al, [esi]                       ; the placeholder's rest: '(PEN)', '(OG)', ','
    mov [edi], al
    inc esi
    inc edi
    test al, al
    jnz .c
    mov esi, ST_STR
    mov [A0], esi
    pop edi
    pop eax
.x: ret

st_img:                                 ; the clock render: `mov ax, [D3] / mov esi, [A0]` (then imageIndex = ax)
    cmp byte [ST_PH], 0
    je .x
    pushad
    mov esi, D0                         ; (the game's D0..A6, CopySprite's)
    mov edi, ST_SAVE
    mov ecx, 60
    rep movsb
    movzx ebx, word [D3]                ; the game's picture (SPR_8 / 88 / 118_MINS, its digits in): the minute runs
    mov al, [ST_N]                      ; (Davide): its units digit = the end minute's + K - 1 in added minute K (a
    cmp byte [ST_PH], 2                 ; TV clock: 90, 91 .. 94 for +5), + N waiting for the whistle (95)
    je .u
    mov al, [ST_K]
    dec al
.u: add al, [GT + 3]
    movzx eax, al
    add eax, 331                        ; (SPR_TIME_BIG_0, the game's own clock digits)
    mov [D0], eax
    lea eax, [ebx - 328]
    imul eax, eax, 6                    ; (the units' x: the game's 6 px a digit)
    mov [D1], eax
    mov dword [D2], 0
    mov [D3], ebx
    call COPYSPR
    movzx ebx, word [ST_SAVE + 12]
    mov esi, [SPRIDX + ebx * 4]
    mov edi, ST_HDR
    mov ecx, 24
    rep movsb
    movzx ebp, word [ST_HDR + 10]       ; (the game's picture's width)
    mov dword [ST_HDR], ST_BUF
    lea eax, [ebp + 16]
    mov [ST_HDR + 10], ax
    mov word [ST_HDR + 12], NL_
    mov word [ST_HDR + 14], WQ_
    mov edi, ST_BUF
    mov ecx, NL_ * WQ_ * 8
    xor eax, eax
    rep stosb
    mov [D0], ebx                       ; the clock picture (its digits already in)
    mov dword [D3], ST_IDX_
    mov dword [D1], 0
    mov dword [D2], 0
    push ebp
    call COPYSPR                        ; (EGACopySprite uses bp)
    pop ebp
    lea ecx, [ebp + 3]
    call st_plus
    movzx eax, byte [ST_N]
    add eax, 331                        ; (SPR_TIME_BIG_0)
    mov [D0], eax
    mov dword [D3], ST_IDX_
    lea eax, [ebp + 10]                 ; (an even x: the chunky (vga) copy works in whole bytes of 2 pixels - at an
    and eax, -2                         ; odd x the digit moved left and its blank half byte ate the '+''s shadow)
    mov [D1], eax
    mov dword [D2], 0
    call COPYSPR
    mov esi, ST_SAVE
    mov edi, D0
    mov ecx, 60
    rep movsb
    popad
    mov ax, ST_IDX_
    mov esi, [A0]
    ret
.x: mov ax, [D3]
    mov esi, [A0]
    ret

st_plus:                                ; the '+' at x = ecx in ST_BUF: chunky, or 4 bit planes (half / EGA mode)
    mov esi, ST_PLUS
.l: movzx eax, byte [esi]
    cmp al, 0FFh
    je .x
    add eax, ecx                        ; x
    movzx edx, byte [esi + 1]           ; y
    mov bl, [esi + 2]                   ; colour
    cmp word [EGA], -1
    je .p
    shl edx, 5                          ; (WQ * 8 bytes a line)
    mov edi, eax
    shr edi, 1
    add edi, edx
    test al, 1
    jnz .lo
    shl bl, 4
.lo: or [ST_BUF + edi], bl
    jmp .n
.p: push ecx
    mov edi, eax
    shr edi, 3
    lea edx, [edx * 8]                  ; (WQ * 2 bytes a line, a plane)
    add edi, edx
    mov cl, al
    and cl, 7
    mov bh, 80h
    shr bh, cl
    mov ecx, 4
.pl: shr bl, 1
    jnc .pn
    or [ST_BUF + edi], bh
.pn: add edi, NL_ * WQ_ * 2
    loop .pl
    pop ecx
.n: add esi, 3
    jmp .l
.x: ret
"""


def find(p):
    """The game's sites (obj1 offsets, the original exe) and symbols."""
    import controls
    import lp36
    import sacups
    import shirtnum
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    D0, A0 = r['D7'] - 28, r['A0']
    P = lambda x: re.escape(struct.pack('<I', x))
    t = lambda o: p.target(1, o)

    def one(pat, what):
        m = [x.start() for x in re.finditer(pat, d, re.S)]
        assert len(m) == 1, (what, m)
        return m[0]
    g90 = one(rb'\x81\x3d....\x00\x00\x09\x00\x0f\x85', 'cmp gameTime, 90')
    GT = t(g90 + 2)
    gt = GT[1]
    g45 = one(rb'\x81\x3d' + P(gt) + rb'\x00\x00\x04\x05\x75', 'cmp gameTime, 45')
    s = {'roll': one(rb'\x80\x05' + P(gt + 3) + rb'\x01\x80\x3d' + P(gt + 3) + rb'\x0a', 'minute roll'),
         'chk': one(rb'\x81\x3d' + P(gt) + rb'\x00\x00\x00\x01\x75', 'cmp gameTime, 1000000h'),
         'reset': one(rb'\xc7\x05' + P(gt) + rb'\x00\x00\x00\x00\x66\xc7\x05', 'ResetTime'),
         'goal': one(rb'\xa1' + P(gt) + rb'\x8b\x35', 'GoalScored: mov eax, [gameTime]'),
         'fmt': one(rb'\x8b\x46\x08\x8b\x35' + P(A0) + rb'\x89\x06\x83\x05' + P(A0) + rb'\x01', 'goal string') + 3,
         'img': one(rb'\x66\xa1' + P(D0 + 12) + rb'\x8b\x35' + P(A0) + rb'\x66\x89\x46\x46', 'clock imageIndex')}
    # the step before the roll: mov ax, [timeDelta] / mov [D0], ax / mov ax, [D0] / sub [secondsSwitchAccumulator], ax
    m = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\xa3' + P(D0) + rb'\x66\xa1' + P(D0) + rb'\x66\x29\x05', d, re.S)
         if s['roll'] - 0x60 < x.start() < s['roll']]
    assert len(m) == 1, ('timeDelta', m)
    s['delta'] = m[0]
    # PlayEndGameWhistleSample: the 45' block's `mov stateGoal, 0 / call` (its entry: mov edx, [linAdr982k])
    m = re.search(rb'\x66\xc7\x05....\x00\x00\xe8(....)', d[g45:g45 + 0x40], re.S)
    s['wh'] = g45 + m.start() + 14 + struct.unpack('<i', m.group(1))[0]
    assert d[s['wh']:s['wh'] + 2] == b'\x8b\x15', d[s['wh']:s['wh'] + 8].hex()
    # @@no_update_to_time: the jl after cmp gameSeconds, 60
    m = [x for x in re.finditer(rb'\x66\x83\x3d(....)\x3c\x0f\x8c(....)', d[s['delta']:s['roll']], re.S)]
    assert len(m) == 1, ('cmp gameSeconds, 60', m)
    noupd = s['delta'] + m[0].end() + struct.unpack('<i', m[0].group(2))[0]
    gsec = t(s['delta'] + m[0].start(1))
    # CopySprite: the render's call after `push D3` (ff 35 D3 / e8)
    cs = [x.start() for x in re.finditer(rb'\xff\x35' + P(D0 + 12) + rb'\xe8', d[s['img'] - 0x40:s['img']])]
    assert cs, 'CopySprite call'
    o = s['img'] - 0x40 + cs[-1] + 6
    copyspr = o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    k = s['img'] + 51                                                # (mov word [copyTimeSprite], 0 after the render)
    assert d[k:k + 3] == b'\x66\xc7\x05' and d[k + 7:k + 9] == bytes(2), d[k - 4:k + 12].hex()
    copyt = t(k + 3)
    ega = one(rb'\x66\x83\x3d....\xff\x0f\x84....\x66\x81\x3d....\x33\x01', 'EGA_graphics')
    # statsTeam1Goals / statsTeam2Goals: the 90' block's copies (mov ax, [s1] / mov [copy1], ax / mov ax, [s2] ...)
    w = re.search(rb'\x66\xa1(....)\x66\xa3....\x66\xa1(....)\x66\xa3....', d[g90:g90 + 0x60], re.S)
    o = lepatch.LEPatch(bytes(p.le.data))     # the unpatched fixups for the other modules' finders (release builds: lp36
    _, (ts1, ts2, gteam1) = lp36._game_sites(o, A0)   # moves gameTeam1's store, xtra the bench sites, before this)
    # UpdateGameTimersAndCameraBreakMode, the ball not in play: add [stoppageTimerTotal], ax / cmp gameStatePl, 102
    s['dead'] = one(rb'\x66\x01\x05....\x66\x83\x3d....\x66\x75', 'add stoppageTimerTotal, ax')
    ns = [x for x in re.finditer(rb'\x66\xa1(....)\x66\xa3....\x66\xa1(....)\x66\xa3....\xa1....\xa3....\x8b\x35....'
                                 rb'\x66\x83\x7e.\x01\x74.\x66\xa1(....)', d, re.S)]
    assert len(ns) == 1, ('NumSubs', len(ns))
    import careerworld
    cw = careerworld.SITES or careerworld.sites(o)
    import benchx
    sym = {'GT': GT, 'GSEC': gsec, 'TDELTA': t(s['delta'] + 2), 'COPYT': copyt, 'NOUPD': (1, noupd),
           'CHKRET': (1, s['chk'] + 10), 'LINADR': t(s['wh'] + 2), 'COPYSPR': (1, copyspr), 'EGA': t(ega + 3),
           'SG1': t(g90 + w.start(1)), 'SG2': t(g90 + w.start(2)), 'TS1': ts1, 'TS2': ts2,
           'NS1': t(ns[0].start(1)), 'NS2': t(ns[0].start(3)), 'SPT': t(s['dead'] + 3), 'GTEAM1': gteam1,
           'D0': (2, D0), 'D1': (2, D0 + 4), 'D2': (2, D0 + 8), 'D3': (2, D0 + 12), 'A0': (2, A0),
           'SPRIDX': (2, shirtnum.spr_index(o)), 'SWOSPP': controls.locate(o)['SWOSPP'],
           'SLT': cw['slt'], 'WORLD_BYTE_': (0, careerworld.WORLD_BYTE), 'GAMETYPE': benchx_gametype(o),
           'ST_IDX_': (0, ST_IDX), 'NL_': (0, NL), 'WQ_': (0, WQ)}
    assert D0 + 60 == A0 + 28, 'D0..D7, A0..A6 contiguous'
    return s, sym


def benchx_gametype(p):
    import benchnum
    return benchnum.sites(p)[3]


def patch(p, at, lang, worlds=(), files=()):
    """Code + data at obj3:at (after the previous obj3 block's end); worlds = career_worlds(), files = pack_files():
    [(key, era(year))]. Returns the end."""
    s, sym = find(p)
    d = p.le.obj_bytes(1)
    for k, n in (('roll', 7), ('chk', 10), ('reset', 10), ('goal', 5), ('fmt', 8), ('img', 12), ('delta', 6), ('dead', 7), ('wh', 6)):
        assert p.get(1, s[k], n) == d[s[k]:s[k] + n], ('stoppage: site already patched', k)
    src = source(worlds, files)
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    spr = sym['SPRIDX']
    slot = spr[1] + ST_IDX * 4
    assert p.get(spr[0], slot, 4) == bytes(4), 'spritesIndex[ST_IDX] in use'
    p.add_ptr(spr[0], slot, 3, lab['ST_HDR'])
    for k, n, lb, op in (('chk', 10, 'st_chk', 0xE9), ('roll', 7, 'st_min', 0xE8), ('reset', 10, 'st_reset', 0xE8),
                         ('goal', 5, 'st_goal', 0xE8), ('fmt', 8, 'st_fmt', 0xE8), ('img', 12, 'st_img', 0xE8),
                         ('delta', 6, 'st_delta', 0xE8), ('dead', 7, 'st_dead', 0xE8), ('wh', 6, 'st_wh', 0xE8)):
        o = s[k]
        for f in range(o, o + n):                       # (the overwritten instructions' fixups)
            try:
                p.target(1, f)
                p.remove(1, f)
            except AssertionError:
                pass
        p.branch(1, o, op, 3, lab[lb], n)
    LABELS.update(lab)
    print(f'exe: stoppage time obj3+{at:#x} ({len(code)} B, ST_PH obj3+{lab["ST_PH"]:#x}), sites ' + ' '.join(f'{k} {v:#x}' for k, v in s.items()))
    return at + len(code)



def rows(tab):
    """Table bytes: count, then [key, cap1, cap2, capET, base, 0, KD (word)] per row."""
    out = [len(tab)]
    for k, (c1, c2, ce, base, kd) in tab:
        assert 5 + max(c1, ce) <= 9 and c2 <= 9, ('the running minute moves only its units digit', k, c1, c2, ce)
        out += [k, c1, c2, ce, base, 0, kd & 255, kd >> 8]
    return out


def source(worlds, files=()):
    """The module's source: ASM + its data (ST_DEF: the default era's row; ST_WTAB career worlds, ST_FTAB pack team
    files)."""
    db = lambda b: ', '.join(str(x) for x in b)
    return ASM + (f'ST_PH: db 0\nST_N: db 0\nST_K: db 0\nalign 4\nST_AT: dd 0\nST_SNAP: dd 0\nST_DEAD: dd 0\n'
                  f'ST_DSNAP: dd 0\nST_CAPS: db 0, 0, 0, 0\nST_KD: dw 0\n'
                  f'ST_DEF: db {db(rows([(0, era(DEFAULT_YEAR))])[1:])}\nST_WTAB: db {db(rows(worlds))}\n'
                  f'ST_FTAB: db {db(rows(files))}\n'
                  f'ST_PLUS: db {db(sum(map(list, PLUS), []) + [0xFF])}\nST_STR: times 16 db 0\n'
                  f'align 4\nST_SAVE: times 60 db 0\nST_HDR: dd ST_BUF\n dw 0, 0, 0, 1, {NL}, {WQ}, 0, 0, 0, 0\n'
                  f'ST_BUF: times {NL * WQ * 8} db 0\n')


SYMS = ('GT', 'GSEC', 'TDELTA', 'COPYT', 'NOUPD', 'CHKRET', 'LINADR', 'COPYSPR', 'EGA', 'SG1', 'SG2', 'TS1', 'TS2', 'NS1', 'NS2',
        'D0', 'D1', 'D2', 'D3', 'A0', 'SPRIDX', 'SWOSPP', 'SLT', 'GAMETYPE', 'SPT', 'GTEAM1')


def layout(at, nworlds, nfiles):
    """The labels of a build's block at obj3:at with nworlds / nfiles table rows (the harness: st_chk's address =
    at; the counts are ST_WTAB's and ST_FTAB's first bytes)."""
    sym = {k: (2, 0) for k in SYMS}
    sym.update({'WORLD_BYTE_': (0, 0), 'ST_IDX_': (0, ST_IDX), 'NL_': (0, NL), 'WQ_': (0, WQ)})
    z = (0, (0, 0, 0, 0, 0))
    return nasmcave.labels(source([z] * nworlds, [z] * nfiles), at, sym)


LABELS = {}
