"""A bench of up to 15 substitutes (4.1, Panchina block 1: the in-match teams).

The game passes every match "substitutions X from a bench of Y" (InitializeInGameTeamsAndStartGame: D1 ->
gameMinSubstitutes, D2 -> gameMaxSubstitutes, Y <= 5 everywhere) and builds each in-match team (topTeamInGame /
bottomTeamInGame, 1704 bytes: TeamGame 42 + PlayerInfo 61 per player) with 16 players (InitInGameTeamStructure).
InitInGamePlayer already takes the players from 11 + gameMaxSubstitutes on out of the match (position -1,
substituted). The buffers' tail (bytes 1018..1703) is free (harness bench_mem, 2026-10-29), so 26 players fit
(42 + 26 x 61 = 1628), also in the highlights (SetHilFileHeader copies 1704 bytes per team).

- bx_max replaces `mov [gameMaxSubstitutes], ax`: a non-zero BENCH word (bx_bench; the per-competition rule comes in
  phase 2, a test poke until then) is the match's bench instead, at most 15.
- bx_next replaces InitInGameTeamStructure's `add word [D2], 1 / cmp word [D2], 16` (the jnz after it stays): the
  loop goes to 11 + max(5, bench) players; a team with fewer players (only the managed career club has more than 16:
  careerTeam, careerNumPlayers, its order in currentMatchPlayers, 32 places) gets empty places: zeroed, position -1,
  substituted, which every bench routine skips.
  (A, 4.1) a career's CPU club with a bench over 5: 16 + the players of its XTRA block (bx_xnamed: xtra's cached block,
  the ones the managed club bought blanked), places 16.. = the block's players in order; GetPlayerAtIndex serves
  those places through xbrowse's xs_ga (index 16 + r = the r-th player still there) and GetPlayer through xtra's
  gp_wide (the cached slot; the after-match cards / injuries / goals of those players land in that cache only:
  not kept once it is re-read). Builds without xtra (no XTRA blocks): 16 as before. Friendlies / seasons: 16 (phase 2).
  (2, 4.0.6) with a bench over 5 an injured / suspended bench player is left out of the match (Davide 31/10, the real
  rule): InitInGamePlayer already marks him substituted with position -1 (IsPlayerInjured), bx_next turns his place
  into an empty one (no name, no figure in the dugout; the order is not changed, the bench is one shorter; the
  after-match write-backs skip substituted places, so his injury / cards stay as they were). The pre-match ready
  check (ShowOrHidePlayMatchButton's GetNumberOfAvailablePlayers(11 + max), pm_nr) then asks only for 11 available
  starters; the game's bench of 5 keeps its own check of 16 places.
- inGameTeamPlayerOffsets (16 x index * 61) moves to a 26-entry table here: every fixup to it is retargeted.
- The game's own `cmp word [gameMaxSubstitutes], 5` branches (a bench over 5 = the first bench place is the
  goalkeeper's only, in FirePressedInSubsMenu, UpdateSubstitutePlayerIndices and DrawBenchPlayersAndCoach twice)
  compare with 127: never taken.

Block 2 (the bench graphic, 4.1): the dugout keeps its art and 5 places; with a bigger bench they are a window of 5
that scrolls with the cursor (Davide's choice B).
- BenchMenuHandleControls' `cmp [g_benchPlayerIndex], 5` / `, 6` (the cursor's last place / one past it) ->
  bx_cmp_last / bx_cmp_last1: the last place is max(5, gameMaxSubstitutes) <= 15 (5 in a training game); empty
  places are skipped by IsThisPlayerOkToSelect as the game's own substituted players.
- DrawBenchAndSubsMenu's `mov ax, [g_benchPlayerIndex]` (the arrow's row) -> bx_arrow: the window start bx_win
  follows the cursor (the coach or a training game: 0), the arrow's row = index - bx_win; (4.0.6, two humans) the
  bench's entry (BenchCheckControls' `mov word [g_benchPlayerIndex], 0`) -> bx_bentry: the window back at the top.
- DrawBenchPlayersAndCoach's `mov word [D7], 1` / `cmp word [D7], 6` -> bx_win_init / bx_win_end: places
  bx_win + 1 .. bx_win + 5 (A0 moved on by bx_win players); the opponent's bench (g_subsState -1) its first 5.
- Block 3, the names (on namespr's 112 px sprites, 4.0.5): plOrdinalsTable / plNamesLengthTable /
  plNamesLengthTableCopy (obj2, 16 bytes a team) move here at 26 a team (bx_ord / bx_len / bx_lenc, every reference
  retargeted; the team-2 offsets +16 -> +26 in SwapPlayerNameData, SetCurrentPlayerName, CopyPlayerNameLengths and
  its loop 16 -> 26): SwapPlayerNameData indexes them by the entering player's place, which ran past the tables
  (team 2) or into the other team's half (team 1) for a player from place 17 on. ns_make's tail jump into
  MakeSpritesFromPlayerNames -> bx_make: the names of places 0..(11 + bench - 1) of both teams, 0..15 on the game's
  255.. / 271.., 16..25 on sprites NB.. (1912.., see the index map below) with namespr's spare headers N..CAP-1;
  SetCurrentPlayerName's `add word [D1], 255` / `, 271` -> bx_name1 / bx_name2 (places 16+ -> NB + 10 x team).
- The after-match write-backs (cseg_2F194 cards, UpdatePlayerInjuries, cseg_2F3AB goals: `mov word [D2], 15`, 16
  in-match players) -> bx_wcount: 11 + max(5, gameMaxSubstitutes) places (16 with the game's bench: no stale
  record read), so a player from place 17 on who came on keeps his card / injury / goals (GetPlayer: careerTeam's 32).

The three 17-row player lists (pre-match screen, SQUADRA, tactics editor; task 1 = rows 12..17 a window on the places
from 12 on, scrolled by the box left of row 17), 4.0.6 (Davide 31/10):
- a marked player stays marked when the window scrolls: the game keeps the mark as his place (selectedPlayerPosition /
  dseg_16F48C / dseg_17994A = GetPlayerInfoBreakPosition's D1, not a row), draws it wherever he shows and swaps by
  place, so pm_rot / et_rot no longer cancel it (sq_rot never did);
- the cursor scrolls the window as in the dugout: MenuProc's `mov [D6], ax` (the move, 2 up / 3 down, before it looks
  for the next entry) -> bx_mdir: on row 17 down / row 12 up, while the window can move (0 .. players - 17, as the
  box), the window moves one place and the cursor stays (the menu redrawn, no entry search). The screen is told by the
  selected entry's onSelect (OnSwapPlayer, SquadCommon, EditTacticsPlayerNamesCommon) and its ordinal.
- VIEW OPPONENT (the pre-match screen with viewingOpponentTeam; Davide's PANpt4 photo: a CPU BOLOGNA showed 11 + 5,
  its places 17.. out of sight): with a bench over 5 the opponent's places are 16 + its XTRA block's players (po_n, as
  bx_next: a career's CPU club), at most 11 + the bench; rows 12..17 a window bx_po on them (pm_row; row 17 = entry
  29 made visible, the game shows it by the own team's count), read-only: on a CPU club's view up / down anywhere move
  the window one place (bx_mdir, wrapping as the box), nothing else changes.
- (4.0.6) ViewSquad (the game's squad view: AGG. GIOCATORE AL CALCIOMERC., offers, ...; the box and row 17 only for the
  managed club) and SelectNationalTeam (the national call-ups, careerTeam, at most 20 players: the game's per-player
  tables there, dseg_D6F48 / dseg_D6F98, hold 20): rows 12..17 a window bx_vw on the places from 12 on, as SQUADRA.
  vw_cmp (their AfterDrawCommon's `cmp word [D1], 10h`: row -> place in D1 / D6, no number from 11 + bench on),
  vw_gpi (their Common's GetPlayerInfoBreakPosition: the picked row -> its place), vw_rot (the box: the window one down
  with a bench over 5, else the game's rotation), bx_mdir (the cursor on rows 12 / 17), vw_vinit (ViewSquad's entry:
  the window kept only when it comes back to a bench row of the managed club) and vw_ninit (the call-ups: at the top).

Phase 2 (4.0.6): each competition's real rule (internal/panchina/fase2.md: official 2026-27 texts or the largest bench
seen in real 2026-27 team sheets). bench_table() builds, per exe language, a table of the World 2026-27 competitions
with a known bench: title (the country's button name + ' ' + the competition's / division's first name: what the game
shows, FORMAT's key; 40 characters at most), named substitutes, substitutions allowed, extra-time substitute (stored,
used at extra time: bx_et), from tools/bench2627.json x the world's career packs in SEASON_PACKS (none: no table, the
game's rule everywhere). bx_look (careers only) finds the current competition's title (DIY_competitionStart + 4, as at
the kick-off of InitializeInGameTeamsAndStartGame: e.g. ITALIA SERIE D GIRONE A) in it, cached by title; bx_max takes
its bench (else the game's: a career league passes its record's +65h, 5), bx_min (`mov [gameMinSubstitutes], ax`) its
substitutions (else the game's +63h, 3), sq_n its bench for the pre-match screens. The test switch bx_bench wins over
both. Competitions not in the table keep the game's 3 from 5. (4.0.5, Davide 30/10) bench_table fills bench2627.json's
unknowns (null / no key) at build time, no exe code: a lower division from the nearest higher division with data, a
cup or state championship from the country's top league ('=league.N': division N's), a play-off / poule from its
clubs' division; every country a prefix entry ('<COUNTRY> ', et bit 7: bx_strpre) = its top league or its
confederation's default, so any other title of it (supercups...) has a real bench; the table's entries are the
title + NUL + 3 bytes (no padding: 184 entries, < 4 KB, in benchx's 2 pages). internal/reports/bench-unknowns-2627.md.

spritesIndex past the game's 1335 entries (shirtnum.py's extension into the 3072 free bytes after it: indices
1335..2102; it cannot move, SWOS++ holds its address):
  1335..1417 shirtnum (match shirt numbers 17..99)      1620..1707 menunum (menu numbers 12..99)
  1418..1619 blond set slots 1-2 (single-team, 4.0.5)  1708..1909 blond set slots 3-4
  1910..1911 blond ICONBL (receding face icons, 4.0.5)  1912..1931 benchx NB (names of places 17..26, 10 a team)
  1932..2032 blond set slot 5 (4.0.5)                   2033..2034 blond ICON3 (shaved face icons)
  2035..2102 free
"""
import os
import re
import struct

import blond
import menunum
import nasmcave
import shirtnum

MAXP = 26                               # 11 + 15
NB = blond.ICONBL + 2                   # the name sprites of places 17..26: team 1 1912.., team 2 1922.. (after the bald icons)
SPR_END = shirtnum.NEWBASE + 3072 // 4  # 2103: spritesIndex's room ends here
assert (shirtnum.NEWBASE + 83 == blond.NEW1 and blond.NEW2 + 101 == menunum.NEWBASE and menunum.NEWBASE + 88 == blond.NEW3
        and blond.NEW3 + 202 == blond.ICONBL and NB + 2 * (MAXP - 16) <= SPR_END), 'spritesIndex map overlaps'
PI = 61                                 # sizeof PlayerInfo
TABLE = struct.pack('<16H', *(i * PI for i in range(16)))     # 0, 61 .. 915

ASM = r"""
bx_max:                                 ; replaces `mov [GMAX], ax` (InitializeInGameTeamsAndStartGame)
    cmp word [bx_bench], 0
    je .comp
    mov ax, [bx_bench]
    jmp .cap
.comp:                                  ; (phase 2) the competition's real bench (bx_look), else the game's
    call bx_look
    cmp byte [bx_lkres], 0
    je .game
    movzx ax, byte [bx_lkres]
.cap:
    cmp ax, 15
    jbe .game
    mov ax, 15
.game:
    mov [GMAX], ax
    ret

bx_min:                                 ; (phase 2) replaces `mov [GMIN], ax`: the competition's substitutions
    cmp word [bx_bench], 0              ; allowed (bx_look), else the game's; the test switch keeps the game's
    jne .game
    call bx_look
    cmp byte [bx_lkres + 1], 0
    je .game
    movzx ax, byte [bx_lkres + 1]
.game:
    mov [GMIN], ax
    ret

bx_look:                                ; (phase 2) [bx_lkres] = the current competition's (named subs, subs used), 0 0 =
    pushad                              ; not in the table (the game's rule). Careers only: the current competition =
    mov word [bx_lkres], 0              ; DIY_competitionStart, its title at +4 (the slot's name, as FORMAT's key);
    mov byte [bx_lket], 0               ; [bx_lket] = its extra-time substitute (4.0.6)
    cmp word [GAMETYPE], 4
    jne .out
    cmp byte [SLT + WORLD_BYTE_], BXWORLD_   ; the career's world (careerworld's save byte): the 2026-27 one only (the
    jne .out                            ; 1996-97 base game and the historic worlds keep the game's rule, same titles)
    mov esi, DIYNAME
    mov edi, bx_lkname
    call bx_streq                       ; the same title as last time: its result
    jne .new
    mov ax, [bx_lkkeep]
    mov [bx_lkres], ax
    mov al, [bx_lketk]
    mov [bx_lket], al
    jmp .out
.new:
    mov esi, DIYNAME                    ; remember the title (up to its NUL, at most 40 characters)
    mov edi, bx_lkname
    mov ecx, 40
.cp:
    lodsb
    stosb
    test al, al
    jz .cpd
    loop .cp
    mov byte [edi], 0
.cpd:
    mov word [bx_lkkeep], 0
    mov byte [bx_lketk], 0
    mov ecx, [bx_tabn]
    mov edx, bx_tab
.f:
    jecxz .found
    mov esi, edx
.nx:                                    ; (4.0.5) an entry = its title, NUL, named subs, subs used, extra-time sub
    inc edx                             ; (bit 7: a prefix entry, '<COUNTRY> ': any title of that country); edx past
    cmp byte [edx - 1], 0               ; the NUL
    jne .nx
    mov edi, bx_lkname
    test byte [edx + 2], 80h
    jnz .pf
    call bx_streq
    je .hit
    jmp .nt
.pf:
    call bx_strpre
    je .hit
.nt:
    add edx, 3
    dec ecx
    jmp .f
.hit:
    mov ax, [edx]
    mov [bx_lkkeep], ax
    mov al, [edx + 2]
    and al, 1
    mov [bx_lketk], al
.found:
    mov ax, [bx_lkkeep]
    mov [bx_lkres], ax
    mov al, [bx_lketk]
    mov [bx_lket], al
.out:
    popad
    ret

bx_et:                                  ; (4.0.6) UpdateTime's `call StartFirstExtraTime`: the competition's extra-time
    push eax                            ; substitute (UEFA: a 6th in extra time, bench2627.json 'et') added to the
    call bx_look                        ; substitutions allowed (gameMinSubstitutes, set again at every kick-off)
    movzx ax, byte [bx_lket]
    add [GMIN], ax
    pop eax
    jmp SFET

bx_streq:                               ; ZF = 1: the strings at esi and edi are equal up to the NUL, or in their first
    push ecx                            ; 40 characters (a longer title: the table keeps 40, as FORMAT's keys)
    push eax
    mov ecx, 40
.c:
    mov al, [esi]
    cmp al, [edi]
    jne .r
    test al, al
    jz .r                               ; (ZF = 1)
    inc esi
    inc edi
    loop .c
    cmp eax, eax
.r:
    pop eax
    pop ecx
    ret

bx_strpre:                              ; (4.0.5) ZF = 1: the string at edi starts with the one at esi (to its NUL)
    push eax
.c:
    mov al, [esi]
    test al, al
    jz .r                               ; (ZF = 1)
    cmp al, [edi]
    jne .r
    inc esi
    inc edi
    jmp .c
.r:
    pop eax
    ret

bx_next:                                ; replaces `add word [D2], 1 / cmp word [D2], 16`: ZF = 1 when the loop ends
    push eax
    push ecx
    push edi
    cmp word [GMAX], 5                  ; a bench over 5: a bench player InitInGamePlayer left out (IsPlayerInjured:
    jbe .in                             ; injured / suspended -> substituted, position -1) becomes an empty place
    cmp word [D2], 11                   ; (Davide 31/10: left out of the match, the bench one shorter, the order kept)
    jb .in
    mov edi, [A6]
    sub edi, PI                         ; the place just made
    cmp byte [edi + 42], 0
    je .in
    push edi
    add edi, 42
    mov ecx, PI
    xor al, al
    rep stosb
    pop edi
    mov byte [edi + 42], 1              ; substituted
    mov byte [edi + 46], -1             ; position
.in:
    inc word [D2]
    movzx ecx, word [GMAX]              ; the loop's end: 11 + max(5, bench), at most 26
    cmp ecx, 5
    jae .m
    mov ecx, 5
.m:
    add ecx, 11
    cmp ecx, MAXP
    jbe .l
    mov ecx, MAXP
.l:
    mov eax, 16                         ; the team's players: 16, the managed career club careerNumPlayers,
    cmp dword [A2], CT                  ; a career's CPU club 16 + the players of its XTRA block (when the bench
    jne .cpu                            ; needs them)
    movzx eax, word [CNP]
    jmp .a
.cpu:
    cmp ecx, 16
    jbe .a
    push esi
    mov esi, [A2]
    mov ax, [esi]
    pop esi
    call bx_xnamed
    add eax, 16
.a:
    cmp ax, cx
    jbe .n
    mov eax, ecx
.n:
    cmp [D2], ax
    jb .more
    mov edi, [A6]                       ; the rest are empty places: A6 -> this place (already advanced)
.empty:
    cmp [D2], cx
    jae .done
    push ecx
    push edi
    add edi, 42
    mov ecx, PI
    xor al, al
    rep stosb
    pop edi
    pop ecx
    mov byte [edi + 42], 1              ; substituted
    mov byte [edi + 46], -1             ; position
    add edi, PI
    inc word [D2]
    jmp .empty
.done:
    mov [A6], edi
    xor eax, eax                        ; ZF = 1: done
    jmp .out
.more:
    or eax, 1                           ; ZF = 0: next player
.out:
    pop edi
    pop ecx
    pop eax
    ret

bx_xnamed:                              ; ax = team word -> eax = the players of its XTRA block (a career's CPU club;
%if HASX_                               ; the ones the managed club bought are blanked there), else 0
    cmp word [GAMETYPE], 4
    jne .no
    cmp word [TRAIN], 0
    jne .no
    push ecx
    push edx
    call XTB                            ; eax -> the cache entry (dw team, db players, db valid, block) or 0
    test eax, eax
    jz .out
    movzx ecx, byte [eax + 2]
    lea edx, [eax + 4 + 3]              ; the first player's name
    xor eax, eax
.c:
    test ecx, ecx
    jz .out
    cmp byte [edx], 0
    je .s
    inc eax
.s:
    add edx, 38
    dec ecx
    jmp .c
.out:
    pop edx
    pop ecx
    ret
.no:
%endif
    xor eax, eax
    ret

bx_stad:                                ; ShowStadiumInit's last `jmp SetExitMenuFlag` (the line-ups drawn and faded in):
    pushad                              ; a bench over 5 with players past place 16 -> its rows 12..16 turn pages
    mov al, [MENU + 16h + 31 * 38h + 4]
    mov ah, [MENU + 16h + 58 * 38h + 4]
    mov [bx_st16], ax
    call bx_stpages                     ; (places 17-21, 22-26), ~1.5 s each; a key or a new fire starts the match
    mov [bx_stn], eax
    mov dword [bx_stk], 0
    test eax, eax
    jz .out
    mov byte [bx_strel], 0
.page:
    call bx_stwait
    jc .out
    inc dword [bx_stk]
    call bx_stset
    pushad
    call DRAWMENU
    popad
    mov eax, [bx_stk]
    cmp eax, [bx_stn]
    jb .page
    call bx_stwait                      ; (the last page's time)
.out:
    popad
    jmp SETEXIT

bx_stpages:                             ; eax = the pages after the first: (the last named place of either team - 11) / 5
    xor eax, eax
    cmp word [TRAIN], 0
    jne .r
    movzx ecx, word [GMAX]
    cmp ecx, 5
    jbe .r
    add ecx, 10                         ; the last in-match place: 11 + max - 1, at most 25
    cmp ecx, MAXP - 1
    jbe .c
    mov ecx, MAXP - 1
.c:
    xor edx, edx                        ; the last named place
    mov esi, TOP
    call .team
    mov esi, BOT
    call .team
    cmp edx, 16
    jb .r
    lea eax, [edx - 11]
    xor edx, edx
    mov ebx, 5
    div ebx
.r:
    ret
.team:
    mov ebx, 16
.t:
    cmp ebx, ecx
    ja .tr
    imul edi, ebx, PI
    cmp byte [esi + edi + 80], 0        ; PlayerInfoHeader.fullName
    je .n
    cmp ebx, edx
    jbe .n
    mov edx, ebx
.n:
    inc ebx
    jmp .t
.tr:
    ret

bx_stset:                               ; rows 12..16 of both teams (entries 27..31, 54..58) = places 11 + 5 x page ..
    movzx ecx, word [GMAX]
    add ecx, 10
    cmp ecx, MAXP - 1
    jbe .c
    mov ecx, MAXP - 1
.c:
    mov esi, TOP
    mov edi, MENU + 16h + 27 * 38h
    mov ebp, bx_stlog
    call .team
    mov esi, BOT
    mov edi, MENU + 16h + 54 * 38h
.team:
    mov eax, [bx_stk]
    imul ebx, eax, 5
    add ebx, 11                         ; the first place of the page
    mov edx, 5
.r:
    mov word [edi + 4], 1               ; isInvisible
    mov dword [ebp], 0
    cmp ebx, ecx
    ja .nx
    imul eax, ebx, PI
    lea eax, [esi + eax + 80]
    cmp byte [eax], 0
    je .nx
    mov [edi + 26h], eax                ; fg.string
    mov word [edi + 4], 0
    mov [ebp], eax
.nx:
    add ebp, 4
    add edi, 38h
    inc ebx
    dec edx
    jnz .r
    ret

bx_stwait:                              ; ~1.5 s (105 ticks of menuCycleTimer, 70 Hz); CF = 1: a key or a new fire
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
    cmp byte [bx_strel], 0              ; (the fire that started the match, still held: not a new one)
    jne .skip
    jmp .t
.rel:
    mov byte [bx_strel], 1
.t:
    cmp word [MCT], 105
    jb .l
    clc
    ret
.skip:
    stc
    ret

bx_gmax5:                               ; ShowStadiumInit's `mov ax, [GMAX]` (D1 = 5 - it rows hidden): at most 5
    mov ax, [GMAX]                      ; (a bench of 15 gave -10: one row hidden, the line-ups showed 4 substitutes)
    cmp ax, 5
    jbe .a
    mov ax, 5
.a:
    ret

bx_lastw:                               ; ax = the cursor's last bench place: max(5, GMAX) <= 15; 5 in a training game
    mov ax, [GMAX]
    cmp ax, 5
    jae .a
    mov ax, 5
.a:
    cmp ax, 15
    jbe .b
    mov ax, 15
.b:
    cmp word [TRAIN], 0
    je .c
    mov ax, 5
.c:
    ret

bx_cmp_last:                            ; replaces `cmp word [IDX], 5` (its flags)
    push eax
    call bx_lastw
    cmp [IDX], ax
    pop eax
    ret

bx_cmp_last1:                           ; replaces `cmp word [IDX], 6`
    push eax
    call bx_lastw
    inc ax
    cmp [IDX], ax
    pop eax
    ret

bx_arrow:                               ; replaces `mov ax, [IDX]` (the arrow's row): ax = IDX - bx_win
    push ebx
    movzx eax, word [IDX]
    xor ebx, ebx
    cmp word [TRAIN], 0
    jne .set
    or eax, eax
    jz .set                             ; (the coach: the first 5)
    movzx ebx, word [bx_win]
    dec eax                             ; the cursor's place - 1
    cmp eax, ebx
    jae .down
    mov ebx, eax                        ; above the window: it starts there
    jmp .set
.down:
    sub eax, 4
    cmp eax, ebx
    jle .set
    mov ebx, eax                        ; below it: it ends there
.set:
    mov [bx_win], bx
    movzx eax, word [IDX]
    sub eax, ebx
    pop ebx
    ret

bx_bentry:                              ; (4.0.6, two humans) replaces BenchCheckControls' `mov word [IDX], 0` (a bench
    mov word [IDX], 0                   ; entered, @@init_bench_vars): the window back at the top too, before the dugout
    mov word [bx_win], 0                ; is drawn (the other team's bench showed the window where the first one left it)
    ret

bx_win_init:                            ; replaces `mov word [D7], 1` (DrawBenchPlayersAndCoach, A0 -> place 11)
    push eax
    xor eax, eax
    cmp word [SUBST], 0
    jl .w                               ; (the opponent's bench: its first 5)
    cmp word [TRAIN], 0
    jne .w
    mov ax, [bx_win]
.w:
    mov [bx_cur], ax
    inc eax
    mov [D7], ax
    dec eax
    imul eax, eax, PI
    add [A0], eax
    pop eax
    ret

bx_win_end:                             ; replaces `cmp word [D7], 6`
    push eax
    mov ax, [bx_cur]
    add ax, 6
    cmp [D7], ax
    pop eax
    ret

bx_name1:                               ; replaces `add word [D1], 255` (SetCurrentPlayerName, D1 = the place)
    cmp word [D1], 16
    jae .x
    add word [D1], 255
    ret
.x:
    add word [D1], NB_ - 16             ; places 16..25: our sprites NB..
    ret
bx_name2:                               ; replaces `add word [D1], 271`
    cmp word [D1], 16
    jae .x
    add word [D1], 271
    ret
.x:
    add word [D1], NB_ + 10 - 16
    ret

bx_places:                              ; eax = the in-match places: 11 + max(5, GMAX) <= 26
    movzx eax, word [GMAX]
    cmp eax, 5
    jae .a
    mov eax, 5
.a:
    cmp eax, 15
    jbe .b
    mov eax, 15
.b:
    add eax, 11
    ret

bx_wcount:                              ; replaces `mov word [D2], 15`: the in-match places - 1
    push eax
    call bx_places
    dec eax
    mov [D2], ax
    pop eax
    ret

bx_make:                                ; replaces ns_make's `jmp MakeSpritesFromPlayerNames` (A5 / A6: the teams)
    xor ecx, ecx                        ; our 20 headers: copies of 255's (namespr's), pixels of their own
.h:
    mov esi, [SPRIDX + 255 * 4]
    imul edi, ecx, 24
    add edi, XHDR
    push ecx
    push edi
    mov ecx, 24
    rep movsb
    pop edi
    pop ecx
    imul edx, ecx, DATA_
    add edx, XDATA
    mov [edi], edx                      ; sprData
    mov [SPRIDX + NB_ * 4 + ecx * 4], edi
    inc ecx
    cmp ecx, 20
    jb .h
    call bx_places
    mov [bx_np], eax
    mov dword [bx_t], 0
.team:
    mov eax, [A5]
    cmp dword [bx_t], 0
    je .t1
    mov eax, [A6]
.t1:
    mov [bx_pl], eax
    mov dword [bx_i], 0
.pl:
    mov ecx, [bx_i]
    cmp ecx, [bx_np]
    jae .next
    mov eax, [bx_t]
    cmp ecx, 16
    jae .x
    shl eax, 4
    lea eax, [eax + ecx + 255]          ; the game's 255.. / 271..
    jmp .s
.x:
    imul eax, eax, 10
    lea eax, [eax + ecx + NB_ - 16]
.s:
    mov [D6], ax                        ; the sprite
    imul eax, [bx_t], 26
    lea eax, [eax + ecx + bx_len]
    mov [A4], eax                       ; its length's byte
    mov eax, [bx_pl]
    lea edx, [eax + SHORT_]
    mov [A0], edx                       ; the short name
    mov dl, [eax + SHIRT_]
    mov [D0], dl                        ; the shirt number
    call MKNAME
    add dword [bx_pl], PI
    inc dword [bx_i]
    jmp .pl
.next:
    inc dword [bx_t]
    cmp dword [bx_t], 2
    jb .team
    ret


sq_n:                                   ; ax = 11 + the bench (5..15): the first out-of-squad place (pre-match screens)
    mov ax, [bx_bench]                  ; (the test switch, else the competition's real bench: bx_look)
    test ax, ax
    jnz .t
    call bx_look
    movzx ax, byte [bx_lkres]
.t:
    cmp ax, 5
    jae .a
    mov ax, 5
.a:
    cmp ax, 15
    jbe .b
    mov ax, 15
.b:
    add ax, 11
    ret

sq_row:                                 ; replaces SquadAfterDrawCommon's `sub word [D7], 1Ch` (entry -> row): rows
    sub word [D7], 1Ch                  ; 11.. -> places 11 + bx_sq ..
    cmp word [D7], 11
    jb .r
    push eax
    mov ax, [bx_sq]
    add [D7], ax
    pop eax
.r:
    ret

sq_cmp:                                 ; replaces `cmp word [D7], 10h` (jnz follows): ZF = 1 (the game's row 17,
    push eax                            ; orange) for a place >= 11 + bench
    call sq_n
    cmp [D7], ax
    jb .no
    cmp eax, eax
    pop eax
    ret
.no:
    test esp, esp
    pop eax
    ret

sq_gpi:                                 ; replaces SquadCommon's `call GetPlayerInfoBreakPosition` (D1 = the row)
    cmp word [D1], 11
    jb .g
    push eax
    mov ax, [bx_sq]
    add [D1], ax
    pop eax
.g:
    jmp GPI

sq_rot:                                 ; replaces SquadOnSelect45's `call RotatePlayersLeft` (the box left of row 17)
    push eax
    call sq_n
    cmp ax, 16
    pop eax
    jbe ROTATE                          ; the game's bench of 5: its rotation
    push eax                            ; a bench over 5: rows 12..17 = a window on places 11 + bx_sq .., one down
    push ebx                            ; (back to the top after the last)
    mov ax, [bx_sq]
    inc ax
    mov bx, [SQCNT]
    sub bx, 17
    cmp ax, bx
    jle .ok
    xor eax, eax
.ok:
    mov [bx_sq], ax
    pop ebx
    pop eax
    add esp, 4                          ; (not back into SquadOnSelect45: it redraws rows 17 only) the whole menu
    jmp DRAWMENU

sq_init:                                ; replaces SquadFinish's `mov dword [dseg_16F490], 0`: the window at the top
    mov dword [S490], 0
    mov word [bx_sq], 0
    ret

sq_c3:                                  ; cseg_125F4 and its 2 copies (swaps: numbers swapped unless both starters or
    push eax                            ; both bench): `cmp word [D3], 10h` -> 11 + bench
    call sq_n
    cmp [D3], ax
    pop eax
    ret

sq_c4:
    push eax
    call sq_n
    cmp [D4], ax
    pop eax
    ret

sq_bn:                                  ; SetBenchPlayersNumbers' `cmp word [D1], 16`: places 11 .. 11 + bench - 1 numbered
    push eax                            ; 12.., at most the team's players (careerNumPlayers for careerTeam, else 16)
    push ebx
    call sq_n
    mov bx, 16
    cmp dword [A0], CT
    jne .c
    mov bx, [CNP]
.c:
    cmp ax, bx
    jbe .d
    mov ax, bx
.d:
    cmp [D1], ax
    pop ebx
    pop eax
    ret

; the pre-match screen (playMatchMenu): with a bench over 5 the game's maxSubstitutesEntries stays 5 (its 17 rows, the
; 17th grey + the rotate box) and rows 12..17 are a window on places 11 + bx_pw .. 16 + bx_pw (own team; the opponent's
; at the top): bench places (< 11 + bench) drawn as the game's substitutes, the others as its 17th row (no number)
pm_max:                                 ; ShowPlayMatchMenu: replaces `mov [maxSubstitutesEntries], ax`
    push eax
    call sq_n
    cmp ax, 16
    pop eax
    jbe .s
    mov ax, 5
.s:
    mov [MAXSUB], ax
    mov word [bx_pw], 0
    mov word [bx_po], 0
    ret

pm_row:                                 ; DrawPlayerEntries: replaces `sub word [D7], 13` (cmp word [D7], 16 follows)
    sub word [D7], 13
    mov word [bx_pp], -1
    push eax
    call sq_n
    cmp ax, 16
    jbe .r
    push ebx
    mov bx, [D7]
    cmp bx, 11
    jb .rb
    cmp bx, 16
    ja .rb
    cmp word [VOPP], 0
    jne .op
    add bx, [bx_pw]
    jmp .nw
.op:                                    ; (4.0.6) the opponent (VIEW OPPONENT, read-only): rows 12..17 a window bx_po
    push eax                            ; over its places 12.. when it has more than 16 (po_n)
    call po_n
    cmp ax, 16
    jbe .op0
    add bx, [bx_po]
    cmp word [D7], 15                   ; row 16 drawn: row 17 (entry 29) shown too (the game shows it by the own
    jne .op0                            ; team's count; SetVariableButtons resets it on the way back)
    mov word [MENU + 16h + 29 * 38h + 4], 0
.op0:
    pop eax
.nw:
    mov [bx_pp], bx                     ; the place pm_gpi reads
    cmp bx, ax
    jb .bench
    mov word [D7], 16                   ; out of the squad: the game's 17th row
    jmp .rb
.bench:
    cmp word [D7], 16
    jne .rb
    mov word [D7], 15                   ; a bench place on row 17: a substitute's row
.rb:
    pop ebx
.r:
    pop eax
    ret

po_n:                                   ; ax = the viewed opponent's places: 16 (the game's), or with a bench over 5
    call sq_n                           ; 16 + its XTRA block's players (a career's CPU club, as bx_next), at most
    cmp ax, 16                          ; 11 + the bench
    jbe .g
    push ecx
    push esi
    mov cx, ax
    mov esi, [PMT2]
    mov ax, [esi]
    call bx_xnamed
    add eax, 16
    cmp ax, cx
    jbe .c
    mov ax, cx
.c:
    pop esi
    pop ecx
    ret
.g:
    mov ax, 16
    ret

pm_gpi:                                 ; DrawPlayerEntries' `call GetPlayerInfoBreakPosition` (D1 = its row): the place
    cmp word [bx_pp], 0
    jl .g
    push eax
    mov ax, [bx_pp]
    mov [D1], ax
    mov word [bx_pp], -1
    pop eax
.g:
    jmp GPI

pm_gpi2:                                ; OnSwapPlayer's 2 calls + shirtedit's se_ctl (D1 = the row, 16 -> 16): the place
    push eax
    call sq_n
    cmp ax, 16
    jbe .g
    cmp word [D1], 11
    jb .g
    cmp word [VOPP], 0
    jne .g
    mov ax, [bx_pw]
    add [D1], ax
.g:
    pop eax
    jmp GPI

pm_n:                                   ; PlayMatchMenuSwapPlayers' `mov ax, [maxSubstitutesEntries]` (11 + it = the
    call sq_n                           ; bench boundary): the bench
    sub ax, 11
    cmp ax, 5
    ja .r
    mov ax, [MAXSUB]
.r:
    ret

pm_nr:                                  ; ShowOrHidePlayMatchButton's GetNumberOfAvailablePlayers(11 + it): the game's
    call pm_n                           ; bench of 5 its own check (16 places); a bench over 5 only the 11 starters
    cmp ax, 5                           ; (an unavailable bench player is left out at kick-off: bx_next)
    jbe .r
    xor eax, eax
.r:
    ret

pm_rot:                                 ; PlayMatchOnSelect30's `call RotatePlayersLeft` (the box left of row 17)
    push eax
    call sq_n
    cmp ax, 16
    pop eax
    jbe ROTATE                          ; the game's bench of 5: its rotation
    cmp word [VOPP], 0
    jne .r
    push eax                            ; a bench over 5: the window one place down (back to the top after the last);
    push ebx                            ; nobody moves; a marked player stays marked (selectedPlayerPosition is his
    mov ax, [bx_pw]                     ; place, not a row: drawn brown wherever he shows, the swap by place)
    inc ax
    mov bx, [NPS]
    sub bx, 17
    cmp ax, bx
    jle .ok
    xor eax, eax
.ok:
    mov [bx_pw], ax
    pop ebx
    pop eax
.r:
    ret

; the tactics editor's player list (editTacticsMenu, names = entries 11..27, the box = 28): the same window, bx_tw
et_row:                                 ; EditTacticsAfterDrawPlayerNames: replaces `sub word [D7], 11` (a call of
    sub word [D7], 11                   ; cseg_4F37E and `cmp word [D7], 16` follow)
    mov word [bx_tp], -1
    push eax
    call sq_n
    cmp ax, 16
    jbe .r
    push ebx
    mov bx, [ETNP]                      ; (the window back in range for this team)
    sub bx, 17
    cmp [bx_tw], bx
    jle .w
    mov word [bx_tw], 0
.w:
    mov bx, [D7]
    cmp bx, 11
    jb .rb
    cmp bx, 16
    ja .rb
    add bx, [bx_tw]
    mov [bx_tp], bx                     ; the place et_gpi reads
    cmp bx, ax
    jb .bench
    mov word [D7], 16
    jmp .rb
.bench:
    cmp word [D7], 16
    jne .rb
    mov word [D7], 15
.rb:
    pop ebx
.r:
    pop eax
    ret

et_gpi:                                 ; its 2 GetPlayerInfoBreakPosition calls (D1 = the drawn row; the faces' rows are
    cmp word [bx_tp], 0                 ; < 11): the place
    jl .g
    cmp word [D1], 11
    jb .g
    push eax
    mov ax, [bx_tp]
    mov [D1], ax
    pop eax
.g:
    jmp GPI

et_gpi2:                                ; EditTacticsPlayerNamesCommon's call (fire on a name, D1 = the row)
    push eax
    call sq_n
    cmp ax, 16
    jbe .g
    cmp word [D1], 11
    jb .g
    mov ax, [bx_tw]
    add [D1], ax
.g:
    pop eax
    jmp GPI

et_rot:                                 ; EditTacticsOnSelect28's `call RotatePlayersLeft`
    push eax
    call sq_n
    cmp ax, 16
    pop eax
    jbe ROTATE
    push eax
    push ebx
    mov ax, [bx_tw]
    inc ax
    mov bx, [ETNP]
    sub bx, 17
    cmp ax, bx
    jle .ok
    xor eax, eax
.ok:
    mov [bx_tw], ax                     ; (the mark kept, as pm_rot)
    pop ebx
    pop eax
    ret

bx_mdir:                                ; MenuProc's `mov [D6], ax` (the move in menu notion: 2 up, 3 down; [A0] = the
    mov [D6], ax                        ; selected entry): a bench over 5, the cursor on the window's first / last row
    push eax                            ; (12 / 17) moving up / down scrolls the window instead, the cursor stays (as
    push ebx                            ; the dugout); on the pre-match screen, SQUADRA and the tactics editor
    push esi
    call sq_n
    cmp ax, 16
    jbe .no
    cmp word [VOPP], 0                  ; (VIEW OPPONENT, a CPU club: read-only) up / down move its window, any entry
    je .own
    mov esi, [PMT2]
    cmp byte [esi + 4], 1               ; teamControls: TEAM_COMPUTER
    jne .own
    call po_n
    cmp ax, 16
    jbe .no
    sub ax, 17                          ; its last start
    mov bx, [bx_po]
    cmp word [D6], 3
    jne .oup
    inc bx                              ; down: one place on (back to the top after the last)
    cmp bx, ax
    jle .oset
    xor ebx, ebx
    jmp .oset
.oup:
    cmp word [D6], 2
    jne .no
    dec bx                              ; up: one place back (to the last from the top)
    jns .oset
    mov bx, ax
.oset:
    mov [bx_po], bx
    jmp .scroll
.own:
    mov esi, [A0]
    mov eax, [esi + 42]                 ; its onSelect: the screen
    movzx ebx, word [esi + 2]           ; its ordinal
    cmp eax, ONSWAP
    jne .sq
    cmp word [VOPP], 0
    jne .no
    sub ebx, 13                         ; rows = entries 13..29
    mov esi, bx_pw
    movzx eax, word [NPS]
    jmp .w
.sq:
    cmp eax, SQCOMMON
    jne .et
    sub ebx, 28                         ; entries 28..44
    mov esi, bx_sq
    movzx eax, word [SQCNT]
    jmp .w
.et:
    cmp eax, ETCOMMON
    jne .vs
    sub ebx, 11                         ; entries 11..27
    mov esi, bx_tw
    movzx eax, word [ETNP]
.w:                                     ; ebx = the row (0..16), esi -> the window, eax = the squad's players
    sub eax, 17                         ; the window's last start (as the box: *_rot)
    cmp word [D6], 3
    jne .up
    cmp ebx, 16
    jne .no
    cmp [esi], ax
    jge .no
    inc word [esi]
    jmp .scroll
.up:
    cmp word [D6], 2
    jne .no
    cmp ebx, 11
    jne .no
    cmp word [esi], 0
    jle .no
    dec word [esi]
.scroll:
    pop esi
    pop ebx
    pop eax
    add esp, 4                          ; (not back into MenuProc's next-entry search) the whole menu redrawn
    jmp DRAWMENU
.no:
    pop esi
    pop ebx
    pop eax
    ret
.vs:                                    ; (4.0.6) ViewSquad: entries 4..20, the managed club's players (else 16)
    cmp eax, VSCOMMON
    jne .nt
    sub ebx, 4
    mov esi, bx_vw
    mov eax, 16
    cmp dword [VSTEAM], CT
    jne .w
    movzx eax, word [CNP]
    jmp .w
.nt:                                    ; SelectNationalTeam: entries 8..24, careerTeam (at most 20)
    cmp eax, NTCOMMON
    jne .no
    sub ebx, 8
    mov esi, bx_vw
    movzx eax, word [CNP]
    jmp .w

rot_d0:                                 ; ViewSquadOnSelect21 / SelectNationalTeamOnSelect25: replaces `mov word [D0], 5`
    push eax                            ; (RotatePlayersLeft's first place - 11): with a bench over 5 the rotation starts
    call sq_n                           ; after the bench (no silent bench change; a window there = later)
    sub ax, 11
    mov [D0], ax
    pop eax
    ret

; (4.0.6) ViewSquad and SelectNationalTeam (the national call-ups): rows 12..17 a window bx_vw on the places from 12
; on, as SQUADRA (the box left of row 17 and the cursor move it); the rows' place = row + bx_vw from row 12 on
vw_cmp:                                 ; their AfterDrawCommon: replaces `cmp word [D1], 10h` (D1 = the row, D6 = row + 1;
    cmp word [D1], 11                   ; jnz follows, ZF = 1: no number, the game's 17th row): D1 / D6 -> the place,
    jb .p                               ; ZF = 1 for a place >= 11 + bench
    push eax
    mov ax, [bx_vw]
    add [D1], ax
    add [D6], ax
    pop eax
.p:
    push eax
    call sq_n
    cmp [D1], ax
    jb .no
    cmp eax, eax
    pop eax
    ret
.no:
    test esp, esp
    pop eax
    ret

vw_gpi:                                 ; their Common's `call GetPlayerInfoBreakPosition` (D1 = the row): the place
    cmp word [D1], 11
    jb .g
    push eax
    mov ax, [bx_vw]
    add [D1], ax
    pop eax
.g:
    jmp GPI

vw_rot:                                 ; ViewSquadOnSelect21 / SelectNationalTeamOnSelect25's `call RotatePlayersLeft`
    push eax                            ; (the box: only for the managed club / careerTeam): a bench over 5 = the
    call sq_n                           ; window one down (back to the top after the last), the whole menu redrawn
    cmp ax, 16
    pop eax
    jbe ROTATE
    push eax
    push ebx
    mov ax, [bx_vw]
    inc ax
    mov bx, [CNP]
    sub bx, 17
    cmp ax, bx
    jle .ok
    xor eax, eax
.ok:
    mov [bx_vw], ax
    pop ebx
    pop eax
    add esp, 4
    jmp DRAWMENU

vw_vinit:                               ; ViewSquad's entry (cseg_53F43): replaces `mov [dseg_17A470], ax` (the row to
    mov [VSROW], ax                     ; select, D3): the window kept only when it returns to a bench row of the
    cmp ax, 11                          ; managed club (as far as its players go), else at the top
    jl .z
    cmp dword [VSTEAM], CT
    jne .z
    push eax
    mov ax, [CNP]
    sub ax, 17
    cmp [bx_vw], ax
    jle .k
    mov [bx_vw], ax
.k:
    cmp word [bx_vw], 0
    jge .k2
    mov word [bx_vw], 0
.k2:
    pop eax
    ret
.z:
    mov word [bx_vw], 0
    ret

vw_ninit:                               ; SelectNationalTeamInit: replaces `mov dword [dseg_17BA3A], 0`: the window at
    mov dword [NTSEL], 0                ; the top
    mov word [bx_vw], 0
    ret

bx_t: dd 0
bx_i: dd 0
bx_pl: dd 0
bx_np: dd 0
bx_ord: times 2 * MAXP db 0             ; plOrdinalsTable, 26 a team
bx_len: times 2 * MAXP db 0             ; plNamesLengthTable
bx_lenc: times 2 * MAXP db 0            ; plNamesLengthTableCopy

bx_win: dw 0
bx_cur: dw 0
bx_bench: dw 0                          ; the match's bench (0 = the game's), test switch BENCH_FORCE
bx_sq: dw 0                             ; the squad screen's window: rows 12..17 = places 11 + bx_sq .. (bench > 5)
bx_pw: dw 0                             ; the pre-match screen's window (the same, places 11 + bx_pw ..)
bx_pp: dw -1                            ; DrawPlayerEntries: the place of the row being drawn (-1 = the game's)
bx_tw: dw 0                             ; the tactics editor's window
bx_tp: dw -1                            ; its drawn row's place
bx_po: dw 0                             ; (4.0.6) the pre-match screen's opponent window (VIEW OPPONENT), bx_bench + 12
bx_lkres: dw 0                          ; (phase 2) bx_look: named subs, subs used of the current competition (0 = game's)
bx_lkkeep: dw 0
bx_lkname: times 41 db 0                ; the title looked up last
bx_stmark: db 'BXST'                    ; the line-ups screen (bx_stad; the harness finds these by the mark):
bx_stk: dd 0                            ; the page shown last (0 = the first)
bx_stn: dd 0                            ; the pages after the first
bx_st16: dw 0                           ; entries 31 / 58 (row 16) invisible on the first page (bytes)
bx_stlog: times 10 dd 0                 ; the last page's rows 12..16 (team 1, team 2): name pointers, 0 = hidden
bx_strel: db 0                          ; fire seen released during the pages
bx_vw: dw 0                             ; (4.0.6) ViewSquad / the national call-ups' window
bx_lket: db 0                           ; (4.0.6) bx_look: the competition's extra-time substitute (bx_vw + 2)
bx_lketk: db 0                          ; its cached value
align 2
bx_table:
%assign i 0
%rep MAXP
    dw i * PI
%assign i i + 1
%endrep
"""

LABELS = {}


def sites(p, regs):
    """(GMAX store, its variable, the InitInGameTeamStructure loop step, the 4 `cmp [GMAX], 5`, the table)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d1, d2, d3 = regs['D7'] - 24, regs['D7'] - 20, regs['D7'] - 16
    d0 = regs['D7'] - 28                    # mov word [hilStarted], 0 / D0 -> plg_D0_param / D1 -> GMIN / D2 -> GMAX / D3
    ms = list(re.finditer(rb'\x66\xc7\x05....\x00\x00\x66\xa1' + pk(d0) + rb'\x66\xa3....\x66\xa1' + pk(d1)
                          + rb'\x66\xa3....\x66\xa1' + pk(d2) + rb'\x66\xa3(....)\x66\xa1' + pk(d3), d, re.S))
    assert len(ms) == 1, ('gameMaxSubstitutes store', len(ms))
    store = ms[0].start() + 9 + 12 + 12 + 6
    gmax = p.target(1, store + 2)[1]
    a6 = regs['A0'] + 24
    lp = [m.start() + 39 for m in re.finditer(rb'(?:\xc6\x46.\x00){8}\x83\x05' + pk(a6) + rb'\x3d\x66\x83\x05' + pk(d2)
                                             + rb'\x01\x66\x83\x3d' + pk(d2) + rb'\x10\x0f\x85', d, re.S)]
    assert len(lp) == 1, ('InitInGameTeamStructure loop', lp)
    g = struct.pack('<I', gmax)
    c5 = [m.start() for m in re.finditer(rb'\x66\x83\x3d....\x05', d, re.S) if d[m.start() + 3:m.start() + 7] == g
          and p.target(1, m.start() + 3) == (2, gmax)]
    assert len(c5) == 4, ('cmp [gameMaxSubstitutes], 5', len(c5))
    d2b = p.le.obj_bytes(2)
    tb = [m.start() for m in re.finditer(re.escape(TABLE), d2b)]
    assert len(tb) == 1, ('inGameTeamPlayerOffsets', tb)
    return store, gmax, lp[0], c5, tb[0], d2


def sites7(p, regs):
    """(A): g_gameType (InitInGameTeamStructure's `mov word [esi], 100 / cmp [g_gameType], GAME_TYPE_CAREER`);
    ShowStadiumInit's `mov ax, [gameMaxSubstitutes]` (in `D1 = 5 - it`: the rows hidden for a bench under 5)."""
    d = p.le.obj_bytes(1)
    gt = {p.target(1, x.start() + 8) for x in re.finditer(rb'\x66\xc7\x06\x64\x00\x66\x83\x3d....\x04\x0f\x84', d, re.S)}
    assert len(gt) == 1, ('g_gameType', gt)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d1, gmax = regs['D7'] - 24, sites(p, regs)[1]
    st = [m.start() + 9 for m in re.finditer(rb'\x66\xc7\x05' + pk(d1) + rb'\x05\x00\x66\xa1' + pk(gmax) + rb'\x66\x29\x05'
                                              + pk(d1), d)]
    assert len(st) == 1, ('ShowStadiumInit 5 - gameMaxSubstitutes', st)
    assert bytes(p.get(1, st[0], 6)) == d[st[0]:st[0] + 6], 'ShowStadiumInit already patched'
    a6 = regs['A0'] + 24                    # the end: call FadeOutToBlack / DrawMenu / CallToWaitRetrace / FadeIn, jmp SetExitMenuFlag
    t = [m.start() for m in re.finditer(rb'(?:\xe8....){4}\xe9', d[st[0]:st[0] + 0x100], re.S)]
    assert len(t) == 1, ('ShowStadiumInit end', t)
    end = st[0] + t[0]
    rel = lambda o: o + 5 + struct.unpack('<i', d[o + 1:o + 5])[0]
    drawmenu, setexit = rel(end + 5), rel(end + 20)
    assert bytes(p.get(1, end + 20, 5)) == d[end + 20:end + 25], 'ShowStadiumInit end already patched'
    cm = [p.target(1, drawmenu + k + 6) for k in range(0, 80) if d[drawmenu + k:drawmenu + k + 6] == b'\xc7\x05' + struct.pack('<I', a6)]
    assert d[drawmenu:drawmenu + 2] == b'\x8b\x35' and len(cm) == 1 and cm[0][0] == 2, ('g_currentMenu', cm)
    mc = list(re.finditer(rb'\xe8....\x66\xa1(....)\x66\xa3' + pk(regs['D7'] - 28) + rb'\x66\xa1....\x66\xa3' + pk(regs['D7'] - 20)
                          + rb'\x66\xa1....\x66\x0b\xc0\x7e', d, re.S))
    assert len(mc) == 1, ('MenuCheckControls', len(mc))
    mcc = mc[0].start()
    fr = list(re.finditer(rb'\xc6\x05....\x00\xc6\x05(....)\x00\xc6\x05(....)\x00\x66\xc7\x05', d[mcc:mcc + 0x80], re.S))
    assert len(fr) == 1, ('MenuCheckControls fire / shortFire', fr)
    o = mcc + fr[0].start()
    mct = {p.target(1, m.start() + 3) for m in re.finditer(rb'\x66\xc7\x05(....)\x00\x00\x66\x83\x3d\1\x01\x7c', d, re.S)}
    assert len(mct) == 1, ('menuCycleTimer', mct)
    tb = re.search(rb'(?:\xc7\x05.{8}){4}\x66\xc7\x05.{4}\xa7\x06', d, re.S)      # (as the harness: top / bottomTeamInGame)
    return {'gametype': gt.pop(), 'stadium': st[0], 'stend': end + 20, 'DRAWMENU': (1, drawmenu), 'SETEXIT': (1, setexit),
            'MENU': cm[0], 'MCC': (1, mcc), 'LASTKEY': p.target(1, mcc + 7), 'SHORTFIRE': p.target(1, o + 9),
            'FIRE': p.target(1, o + 16), 'MCT': mct.pop(), 'TOP': p.target(1, tb.start() + 6), 'BOT': p.target(1, tb.start() + 26)}


def sites2(p, regs):
    """Block 2's sites in the original obj1: {name: offset} + the variables IDX, TRAIN, SUBST (obj2) and HIDE (obj1)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    J = rb'(?:\xe9....|\xeb.)'
    m = list(re.finditer(rb'\x66\x83\x3d(....)\x05\x75.' + J + rb'\x66\xc7\x05\1\x00\x00' + J + rb'\x66\x83\x05\1\x01'
                         rb'\x66\x83\x3d\1\x06\x74', d, re.S))
    assert len(m) == 1, ('BenchMenuHandleControls cursor', len(m))
    idx = p.target(1, m[0].start() + 3)[1]
    c6 = m[0].end() - 9                         # (cmp word [IDX], 6: the 8 bytes before the jz)
    ar = [x.start() for x in re.finditer(rb'\x66\xa1' + re.escape(m[0].group(1)) + rb'\x66\xa3....\x66\x83\x2d....\x0c', d, re.S)]
    assert len(ar) == 1, ('the bench arrow', ar)
    wi = list(re.finditer(rb'\x05\x9f\x02\x00\x00\xa3' + pk(regs['A0']) + rb'\x66\xa1(....)\x66\x0b\xc0\x74', d, re.S))
    assert len(wi) == 1, ('DrawBenchPlayersAndCoach A0 + 671', len(wi))
    w0 = wi[0].start()
    train = p.target(1, w0 + 12)[1]
    d7 = regs['D7']
    d7i = [x.start() for x in re.finditer(rb'\x66\xc7\x05' + pk(d7) + rb'\x01\x00', d) if 0 < x.start() - w0 < 80]
    d7e = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + pk(d7) + rb'\x06\x0f\x85', d) if 0 < x.start() - w0 < 0x300]
    assert len(d7i) == 1 and len(d7e) == 1, ('the bench drawing loop', d7i, d7e)
    sb = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x0f\x88', d, re.S) if 0 < x.start() - d7i[0] < 0x60]
    assert len(sb) == 1, ('g_subsState in the bench loop', sb)
    subst = p.target(1, sb[0] + 2)[1]
    d1 = regs['D7'] - 24
    n1 = [x.start() for x in re.finditer(rb'\x66\x81\x05' + pk(d1) + rb'\xff\x00', d)]
    n2 = [x.start() for x in re.finditer(rb'\x66\x81\x05' + pk(d1) + rb'\x0f\x01', d)]
    assert len(n1) == 1 and len(n2) == 1 and 0 < n2[0] - n1[0] < 0x80, ('the name sprites', n1, n2)
    hd = [x.start() for x in re.finditer(rb'\x8b\x35' + pk(regs['A0']) + rb'\x66\xc7\x46.\xff\xff\x66\xc7\x46.\xa8\x61', d, re.S)
          if 0 < n1[0] - x.start() < 0x400]
    assert len(hd) == 1, ('@@hide_current_player_name', hd)
    lp = sites(p, regs)[2]                      # the three after-match loops just before InitInGameTeamStructure
    d2 = regs['D7'] - 20
    wb = [x.start() for x in re.finditer(rb'\x66\xc7\x05' + pk(d2) + rb'\x0f\x00\x8b\x35' + pk(regs['A0'] + 4) + rb'\x8a\x46[\x2a\x2c]', d)
          if lp - 0x600 < x.start() < lp]
    assert len(wb) == 3, ('the after-match write-back loops', [hex(x) for x in wb])
    be = [x.start() + 18 for x in re.finditer(rb'\x66\xc7\x05....\xff\xff\x66\xc7\x05' + pk(subst) + rb'\x00\x00\x66\xc7\x05'
                                              + pk(idx) + rb'\x00\x00', d, re.S)]
    assert len(be) == 1, ('@@init_bench_vars', be)  # (plToBeSubstitutedPos -1, g_subsState 0, g_benchPlayerIndex 0)
    at = {'bentry': be[0], 'wb0': wb[0], 'wb1': wb[1], 'wb2': wb[2], 'c5': m[0].start(), 'c6': c6, 'arrow': ar[0], 'd7i': d7i[0], 'd7e': d7e[0], 'n1': n1[0], 'n2': n2[0]}
    for k, a in at.items():                     # (no other hook there)
        assert bytes(p.get(1, a, 9)) == d[a:a + 9], ('block 2 site already patched', k, hex(a))
    return at, {'IDX': (2, idx), 'TRAIN': (2, train), 'SUBST': (2, subst), 'HIDE': (1, hd[0])}


def sites3(p, regs, n1, n2):
    """Block 3: the three name tables (obj2) and their references, the +16 team offsets, MakeSpritesFromPlayerNames'
    record fields (shortName, shirtNumber) and MakePlayerNameSprite, ns_make's tail jump (namespr's code)."""
    import namespr
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    A0 = regs['A0']
    cp = [m for m in re.finditer(rb'\xc7\x05' + pk(A0) + rb'(....)\xc7\x05' + pk(A0 + 4) + rb'(....)\xc7\x05' + pk(A0 + 8)
                                  + rb'(....)', d, re.S)
          if all(p.target(1, m.start(k))[0] == 2 for k in (1, 2, 3))]
    tabs = [[p.target(1, m.start(k))[1] for k in (1, 2, 3)] for m in cp]
    cp = [m for m, t in zip(cp, tabs) if t[1] - t[0] == 32 and t[2] - t[1] == 32]
    assert len(cp) == 1, ('CopyPlayerNameLengths', len(cp))
    c = cp[0].start()
    ordt, lent, lenc = (p.target(1, cp[0].start(k))[1] for k in (1, 2, 3))
    rs = {k: refs(p, 2, t, t + 32) for k, t in (('ord', ordt), ('len', lent), ('lenc', lenc))}
    assert [len(rs[k]) for k in ('ord', 'len', 'lenc')] == [3, 2, 3], {k: len(v) for k, v in rs.items()}
    assert all(toff == t for k, t in (('ord', ordt), ('len', lent), ('lenc', lenc)) for _, _, toff in rs[k])
    imm = []                                    # (offset of a 0x10 byte: a team-2 offset or the loop's 16)
    x = [m.start() + 2 for m in re.finditer(rb'\x88\x46\x10', d[c:c + 0xa0])]
    y = [m.start() + 7 for m in re.finditer(rb'\x66\x83\x3d' + pk(regs['D7'] - 28) + rb'\x10\x75', d[c:c + 0xa0])]
    assert len(x) == 1 and len(y) == 1, ('CopyPlayerNameLengths +16 / 16', x, y)
    imm += [c + x[0], c + y[0]]
    sw = [o for _, o, _ in rs['ord'] if any(o2 == o + 10 for _, o2, _ in rs['lenc'])]
    assert len(sw) == 1, ('SwapPlayerNameData', sw)
    z = [m.start() + 2 for m in re.finditer(rb'\x83\xc0\x10', d[sw[0]:sw[0] + 0x40])]
    assert len(z) == 2, ('SwapPlayerNameData add eax, 16', z)
    imm += [sw[0] + k for k in z]
    w = [m.start() + 3 for m in re.finditer(rb'\x8a\x44\x1e\x10', d[n1:n2])]
    assert len(w) == 2, ('SetCurrentPlayerName [esi + ebx + 16]', w)
    imm += [n1 + k for k in w]
    ms, ns_call = namespr.make_sites(p)
    f = re.match(rb'.{28}\xa1' + pk(A0 + 20) + rb'\x83\xc0(.)\xa3' + pk(A0) + rb'\x8b\x35' + pk(A0 + 20) + rb'\x8a\x46(.)'
                 rb'\xa2....\xe8', d[ms:ms + 0x60], re.S)
    assert f, ('MakeSpritesFromPlayerNames team 1 loop', d[ms:ms + 0x60].hex())
    short, shirt = f.group(1)[0], f.group(2)[0]
    mk = ms + f.end() - 1
    mkname = mk + 5 + struct.unpack('<i', d[mk + 1:mk + 5])[0]
    cur = bytes(p.get(1, ns_call, 5))        # namespr's call -> ns_make: its `jmp MakeSpritesFromPlayerNames`
    nsm = ns_call + 5 + struct.unpack('<i', cur[1:])[0]
    code = bytes(p.get(1, nsm, 0xE0))
    jm = [k for k in range(len(code) - 4) if code[k] == 0xE9 and nsm + k + 5 + struct.unpack('<i', code[k + 1:k + 5])[0] == ms]
    assert len(jm) == 1, ('ns_make tail jump', jm)
    return {'imm': imm, 'refs': rs, 'jmp': nsm + jm[0], 'short': short, 'shirt': shirt, 'mkname': mkname}


def sites4(p, regs):
    """The pre-match squad screen (task 1, Davide 30/10: rows 12..17 a window of 6 when the bench is over 5)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d7, a0 = regs['D7'], regs['A0']
    d0, d1, d3, d4, d6 = d7 - 28, d7 - 24, d7 - 16, d7 - 12, d7 - 4
    # SquadAfterDrawCommon: sub word [D7], 1Ch / mov eax, [team] / mov [A6], eax / cmp word [D7], 10h / jnz
    m = list(re.finditer(rb'\x66\x83\x2d' + pk(d7) + rb'\x1c\xa1(....)\xa3' + pk(a0 + 24) + rb'\x66\x83\x3d' + pk(d7)
                         + rb'\x10\x0f\x85', d, re.S))
    assert len(m) == 1, ('SquadAfterDrawCommon', len(m))
    row, tp = m[0].start(), struct.unpack('<I', m[0].group(1))[0]
    # SquadCommon: mov ax, [D6] / mov [D1], ax / mov eax, [team] / mov [A0], eax / call GetPlayerInfoBreakPosition
    g = [x.start() + 22 for x in re.finditer(rb'\x66\xa1' + pk(d6) + rb'\x66\xa3' + pk(d1) + rb'\xa1' + pk(tp) + rb'\xa3'
                                              + pk(a0) + rb'\xe8', d)]
    assert len(g) == 1, ('SquadCommon GPI', g)
    # SquadOnSelect45: mov eax, [team] / mov [A0], eax / or eax, eax / mov word [D0], 5 / call RotatePlayersLeft
    r = [x.start() + 21 for x in re.finditer(rb'\xa1' + pk(tp) + rb'\xa3' + pk(a0) + rb'\x0b\xc0\x66\xc7\x05' + pk(d0)
                                              + rb'\x05\x00\xe8', d)]
    assert len(r) == 1, ('SquadOnSelect45', r)
    # SquadFinish: mov dword [team + 10], 0 / mov word [team + 6], -1
    i = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(tp + 10) + rb'\x00\x00\x00\x00\x66\xc7\x05' + pk(tp + 6)
                                         + rb'\xff\xff', d)]
    assert len(i) == 1, ('SquadFinish', i)
    # SquadCommon's swap end: mov word [team + 6], -1 / jmp DrawMenu
    dm = {x.start() + 14 + struct.unpack_from('<i', d, x.start() + 10)[0]
          for x in re.finditer(rb'\x66\xc7\x05' + pk(tp + 6) + rb'\xff\xff\xe9', d)}
    assert len(dm) == 1, ('DrawMenu', dm)
    # cseg_125F4: cmp word [D3], 10h / jnb / cmp word [D4], 10h / jnb / cmp word [D3], 0Bh
    c = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + pk(d3) + rb'\x10\x73.\x66\x83\x3d' + pk(d4) + rb'\x10\x73.\x66\x83\x3d'
                                         + pk(d3) + rb'\x0b', d, re.S)]
    assert len(c) == 3, ('cseg_125F4 + the play match / tactics copies', c)
    # SetBenchPlayersNumbers' loop end: add byte [esi+4Eh], 1 / add word [D1], 1 / cmp word [D1], 16 / jnz
    bn = [x.start() + 12 for x in re.finditer(rb'\x80\x46\x4e\x01\x66\x83\x05' + pk(d1) + rb'\x01\x66\x83\x3d' + pk(d1)
                                               + rb'\x10\x75', d)]
    assert len(bn) == 1, ('SetBenchPlayersNumbers', bn)
    bn = bn[0]
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    return dict(row=row, cmp=row + 18, gpi=g[0], gpi_t=rel(g[0]), rot=r[0], rot_t=rel(r[0]), init=i[0], drawmenu=dm.pop(),
                c3=c, bn=bn, tp=tp, D3=d3, D4=d4)


def sites5(p, regs, s4):
    """The pre-match screen (playMatchMenu, task 1): rows 12..17 a window of 6 when the bench is over 5."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    t = lambda o: p.target(1, o)
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    d7, a0 = regs['D7'], regs['A0']
    d0, d1 = d7 - 28, d7 - 24
    # ShowPlayMatchMenu: mov ax, [D1] / mov [maxSubstitutesEntries], ax / mov ax, [D0] / mov [playMatchControlFlags], ax /
    # mov ax, [D2] / mov [playMatchExcludeFlags], ax / mov [inEditTactics], ax
    m = [x.start() + 6 for x in re.finditer(rb'\x66\xa1' + pk(d1) + rb'\x66\xa3....\x66\xa1' + pk(d0) + rb'\x66\xa3....\x66\xa1'
                                            + pk(d7 - 20) + rb'\x66\xa3....\x66\xa3', d, re.S)]
    assert len(m) == 1, ('ShowPlayMatchMenu', m)
    out = dict(store=m[0], MAXSUB=t(m[0] + 2))
    mx = pk(out['MAXSUB'][1])
    # PlayMatchMenuReinit: mov ax, [D0] / mov [numPlayersToShowInMenu], ax / mov dword [pmSelectedPlayerEntry], 0 /
    # mov word [viewingOpponentTeam], 0 / mov word [selectedPlayerPosition], -1
    m = [x.start() for x in re.finditer(rb'\x66\xa1' + pk(d0) + rb'\x66\xa3....\xc7\x05....\x00\x00\x00\x00\x66\xc7\x05'
                                        rb'....\x00\x00\x66\xc7\x05....\xff\xff', d, re.S)]
    assert len(m) == 1, ('PlayMatchMenuReinit', m)
    r = m[0]
    out.update(NPS=t(r + 8), PMSEL=t(r + 14), VOPP=t(r + 25), SELPOS=t(r + 34))
    # DrawPlayerEntries: mov esi, [A5] / mov ax, [esi+2] / mov [D7], ax / sub word [D7], 13 / cmp word [D7], 16
    m = [x.start() + 16 for x in re.finditer(rb'\x8b\x35' + pk(a0 + 20) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d7) +
                                             rb'\x66\x83\x2d' + pk(d7) + rb'\x0d\x66\x83\x3d' + pk(d7) + rb'\x10', d)]
    assert len(m) == 1, ('DrawPlayerEntries', m)
    out['row'] = m[0]
    gpi = s4['gpi_t']
    calls = lambda lo, hi: [o for o in range(lo, hi) if d[o] == 0xE8 and rel(o) == gpi]
    # its @@set_positions: mov ax, [D7] / mov [D1], ax / call GetPlayerInfoBreakPosition
    g = [x.end() - 1 for x in re.finditer(rb'\x66\xa1' + pk(d7) + rb'\x66\xa3' + pk(d1) + rb'\xe8', d[m[0]:m[0] + 0x800])]
    g = [m[0] + o for o in g if rel(m[0] + o) == gpi]
    assert len(g) == 1, ('DrawPlayerEntries GPI', g)
    out['dgpi'] = g[0]
    # OnSwapPlayer: mov eax, [playMatchTeam1Ptr] / mov [A1], eax / mov ax, [viewingOpponentTeam] / ... (its 2 GPI calls)
    m = [x.start() for x in re.finditer(rb'\xa1....\xa3' + pk(a0 + 4) + rb'\x66\xa1' + pk(out['VOPP'][1]) +
                                        rb'\x66\x0b\xc0\x75.\x66\xa1....\x66\x0b\xc0\x75.\xe9', d, re.S)]
    assert len(m) == 1, ('OnSwapPlayer', m)
    out['onswap'] = m[0]
    e = re.match(rb'\xa1....\xa3....\x66\xa1....\x66\x0b\xc0\x75(.)', d[m[0]:], re.S)   # its @@viewing_opponent_team:
    o = m[0] + e.end() + e.group(1)[0]                                                    # mov eax, [playMatchTeam2Ptr]
    assert d[o] == 0xA1 and d[o + 5] == 0xA3 and d[o + 6:o + 10] == struct.pack('<I', a0 + 4), ('playMatchTeam2Ptr', hex(o))
    out['PMT2'] = t(o + 1)
    g = calls(m[0], m[0] + 0x240)
    assert len(g) == 2, ('OnSwapPlayer GPI', g)
    out['sgpi'] = g
    # PlayMatchMenuSwapPlayers (D0) / ShowOrHidePlayMatchButton (D1): mov word [Dx], 11 / mov ax, [max] / add [Dx], ax
    for k, dx in (('swap', d0), ('ready', d1)):
        m = [x.start() + 9 for x in re.finditer(rb'\x66\xc7\x05' + pk(dx) + rb'\x0b\x00\x66\xa1' + mx + rb'\x66\x01\x05'
                                                + pk(dx), d)]
        assert len(m) == 1, (k, m)
        out[k] = m[0]
    # PlayMatchOnSelect30: mov ax, [max] / mov [D0], ax / call RotatePlayersLeft
    m = [x.end() - 1 for x in re.finditer(rb'\x66\xa1' + mx + rb'\x66\xa3' + pk(d0) + rb'\xe8', d)]
    m = [o for o in m if rel(o) == s4['rot_t']]
    assert len(m) == 1, ('PlayMatchOnSelect30', m)
    out['rot'] = m[0]
    # shirtedit's se_ctl (MenuProc's MenuCheckControls call, if hooked): its row -> place call
    m = [x.start() for x in re.finditer(rb'\xe8....\xe8....\x66\xb8\x04\x00\x66\x83\x3d....\x32\x7f', d, re.S)]
    assert len(m) == 1, ('MenuProc', m)
    c = [x for x in re.finditer(rb'\xe8(....)\x66\xc7\x05(....)\x00\x00\xe8(....)', d[m[0]:m[0] + 0x100], re.S)]
    assert len(c) == 1, ('MenuCheckControls call', len(c))
    mc = m[0] + c[0].start(3) - 1
    se = mc + 5 + struct.unpack('<i', bytes(p.get(1, mc + 1, 4)))[0]
    out['se'] = None
    if se != rel(mc):
        code = bytes(p.get(1, se, 0x600))
        g = [se + o for o in range(len(code) - 5) if code[o] == 0xE8 and se + o + 5 + struct.unpack_from('<i', code, o + 1)[0] == gpi]
        assert len(g) == 1, ('se_ctl GPI', g)
        out['se'] = g[0]
    return out


def sites8(p, regs, s4, s5, s6):
    """(1, 4.0.6) the cursor scroll: MenuProc's direction store, the starts of the three screens' row handlers (their
    entries' onSelect: OnSwapPlayer, SquadCommon, EditTacticsPlayerNamesCommon)."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d6, d0, a0 = regs['D7'] - 4, regs['D7'] - 28, regs['A0']
    # MenuProc: mov ax, [esi] / mov [D6], ax / mov esi, [A0] / add esi, [D6] (@@check_next_entry_loop)
    m = [x.start() + 3 for x in re.finditer(rb'\x66\x8b\x06\x66\xa3' + pk(d6) + rb'\x8b\x35' + pk(a0) + rb'\x03\x35' + pk(d6), d)]
    assert len(m) == 1, ('MenuProc direction', m)
    # SquadCommon: push dword [D0] / mov dword [D0], 28 / call CalcMenuEntryAddress (its GPI call follows)
    sq = [x.start() for x in re.finditer(rb'\xff\x35' + pk(d0) + rb'\xc7\x05' + pk(d0) + rb'\x1c\x00\x00\x00\xe8', d)]
    sq = [o for o in sq if 0 < s4['gpi'] - o < 0x80]
    assert len(sq) == 1, ('SquadCommon', sq)
    # EditTacticsPlayerNamesCommon: mov ax, [dseg_179952] / or ax, ax / jns @@out / push dword [D0]
    et = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x0f\x89....\xff\x35' + pk(d0), d, re.S)]
    et = [o for o in et if 0 < s6['fgpi'] - o < 0x100]
    assert len(et) == 1, ('EditTacticsPlayerNamesCommon', et)
    return dict(mdir=m[0], SQCOMMON=(1, sq[0]), ETCOMMON=(1, et[0]), ONSWAP=(1, s5['onswap']), PMT2=s5['PMT2'])


def sites9(p, regs, s4, s6, ct, cnp):
    """(4.0.6) ViewSquad and SelectNationalTeam (the national call-ups): the same window as SQUADRA."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    d7, a0 = regs['D7'], regs['A0']
    d0, d1, d2, d3, d6 = d7 - 28, d7 - 24, d7 - 20, d7 - 16, d7 - 4
    gpi = s4['gpi_t']
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    # both AfterDrawCommon: mov [D1], ax / add word [D6], 1 / cmp word [D1], 10h / jnz
    c = [x.start() + 14 for x in re.finditer(rb'\x66\xa3' + pk(d1) + rb'\x66\x83\x05' + pk(d6) + rb'\x01\x66\x83\x3d'
                                              + pk(d1) + rb'\x10\x75', d)]
    assert len(c) == 2, ('ViewSquad / SelectNationalTeam AfterDrawCommon', c)
    # ViewSquadCommon: mov eax, [squadTeamPtr] / mov [A0], eax / call GPI / mov ax, [D1] / mov [dseg_17A474], ax / jmp
    v = [x for x in re.finditer(rb'\xa1(....)\xa3' + pk(a0) + rb'\xe8....\x66\xa1' + pk(d1) + rb'\x66\xa3....\xe9', d, re.S)
         if rel(x.start() + 10) == gpi]
    assert len(v) == 1, ('ViewSquadCommon', v)
    vg, vsteam = v[0].start() + 10, struct.unpack('<I', v[0].group(1))[0]
    # SelectNationalTeamCommon: mov dword [A0], careerTeam / call GPI / mov ax, [dseg_17BA48] / or ax, ax / jz
    n = [x.start() + 10 for x in re.finditer(rb'\xc7\x05' + pk(a0) + pk(ct) + rb'\xe8....\x66\xa1....\x66\x0b\xc0\x74', d, re.S)
         if rel(x.start() + 10) == gpi]
    assert len(n) == 1, ('SelectNationalTeamCommon', n)
    # the Commons' starts (their entries' onSelect): push dword [D0] / mov dword [D0], 4 (8) / call CalcMenuEntryAddress
    def start(o, e):
        m = [x.start() for x in re.finditer(rb'\xff\x35' + pk(d0) + rb'\xc7\x05' + pk(d0) + bytes([e]) + rb'\x00\x00\x00\xe8', d)
             if 0 < o - x.start() < 0x80]
        assert len(m) == 1, ('Common start', e, m)
        return m[0]
    # cseg_53F43 (ViewSquad's entry): mov ax, [D2] / mov [dseg_17A46E], ax / mov ax, [D3] / mov [dseg_17A470], ax
    i = [x.start() + 18 for x in re.finditer(rb'\x66\xa1' + pk(d2) + rb'\x66\xa3....\x66\xa1' + pk(d3) + rb'\x66\xa3', d, re.S)]
    i = [o for o in i if re.search(rb'\x66\xa1' + pk(d3) + rb'\x66\xa3' + re.escape(d[o + 2:o + 6]), d[o + 6:o + 0x200])]
    assert len(i) == 1, ('cseg_53F43', i)                    # (its D3 read back after ShowMenu: the same address)
    # SelectNationalTeamInit: mov dword [dseg_17BA3A], 0 / mov word [dseg_17BA48], 0 / cmp word [careerNumPlayers], 20
    ni = [x.start() for x in re.finditer(rb'\xc7\x05....\x00\x00\x00\x00\x66\xc7\x05....\x00\x00\x66\x83\x3d' + pk(cnp)
                                          + rb'\x14\x74', d, re.S)]
    assert len(ni) == 1, ('SelectNationalTeamInit', ni)
    rots = [o + 9 for o in s6['rot5']]
    assert all(d[o] == 0xe8 and rel(o) == s4['rot_t'] for o in rots), 'ViewSquad / national RotatePlayersLeft calls'
    return dict(cmp=c, gpi=[vg, n[0]], rot=rots, vinit=i[0], ninit=ni[0], VSCOMMON=(1, start(vg, 4)),
                NTCOMMON=(1, start(n[0], 8)), VSTEAM=(2, vsteam), VSROW=p.target(1, i[0] + 2), NTSEL=p.target(1, ni[0] + 2))


def sites10(p):
    """(4.0.6) UpdateTime: mov word [extraTimeState], -1 / call StartFirstExtraTime (mov word [halfNumber], 1 / ...)
    / jmp; the call's offset, StartFirstExtraTime."""
    d = p.le.obj_bytes(1)
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    m = [x.start() + 9 for x in re.finditer(rb'\x66\xc7\x05....\xff\xff\xe8....\xe9', d, re.S)]
    m = [o for o in m if d[rel(o):rel(o) + 3] == b'\x66\xc7\x05' and d[rel(o) + 7:rel(o) + 10] == b'\x01\x00\xe8']
    assert len(m) == 1, ('StartFirstExtraTime call', m)
    return m[0], rel(m[0])


def sites6(p, regs, s4):
    """The tactics editor's player list (task 1): the same window."""
    d = p.le.obj_bytes(1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    t = lambda o: p.target(1, o)
    rel = lambda o: o + 5 + struct.unpack_from('<i', d, o + 1)[0]
    d7, a0 = regs['D7'], regs['A0']
    d0, d1, d6 = d7 - 28, d7 - 24, d7 - 4
    gpi = s4['gpi_t']
    ld = rb'\x66\xa1' + pk(d7) + rb'\x66\xa3' + pk(d1) + rb'\xe8'      # mov ax, [D7] / mov [D1], ax / call
    out = {}
    # EditTacticsAfterDrawPlayerNames: mov esi, [A5] / mov ax, [esi+2] / mov [D7], ax / sub word [D7], 11 /
    # push dword [D7] / call cseg_4F37E / pop dword [D7] / cmp word [D7], 16
    m = [x.start() + 16 for x in re.finditer(rb'\x8b\x35' + pk(a0 + 20) + rb'\x66\x8b\x46\x02\x66\xa3' + pk(d7) +
                                             rb'\x66\x83\x2d' + pk(d7) + rb'\x0b\xff\x35' + pk(d7) + rb'\xe8....\x8f\x05' + pk(d7) +
                                             rb'\x66\x83\x3d' + pk(d7) + rb'\x10', d, re.S)]
    assert len(m) == 1, ('EditTacticsAfterDrawPlayerNames', m)
    out['row'] = m[0]
    f = rel(m[0] + 14)                                                  # cseg_4F37E
    g = []
    for lo in (m[0], f):                                                # the names' and cseg_4F37E's GPI call
        c = [lo + x.end() - 1 for x in re.finditer(ld, d[lo:lo + 0x400]) if rel(lo + x.end() - 1) == gpi]
        assert len(c) == 1, ('tactics GPI', hex(lo), c)
        g += c
    out['dgpi'] = g
    # EditTacticsPlayerNamesCommon: mov [esi+18h], al / mov ax, [D6] / mov [D1], ax / push dword [A0] / call GPI
    m = [x.end() - 1 for x in re.finditer(rb'\x88\x46\x18\x66\xa1' + pk(d6) + rb'\x66\xa3' + pk(d1) + rb'\xff\x35' + pk(a0)
                                          + rb'\xe8', d)]
    m = [o for o in m if rel(o) == gpi and re.search(rb'\x66\xc7\x05' + pk(d0) + rb'\x0b\x00|\xc7\x05' + pk(d0)
                                                       + rb'\x0b\x00\x00\x00', d[o - 0xC0:o])]   # (D0 = 11: the names,
    assert len(m) == 1, ('EditTacticsPlayerNamesCommon', m)                                  #  not EditTacticsCommon's faces)
    out['fgpi'] = m[0]
    # ... its selection: mov word [sel], -1 / jmp DrawMenu; mov eax, [selEntry] / mov [A0], eax / mov eax, [A5] /
    # mov [selEntry], eax
    m = [x.start() for x in re.finditer(rb'\x66\xc7\x05(....)\xff\xff\xe9', d[out['fgpi']:out['fgpi'] + 0x200], re.S)]
    assert m, 'tactics selection'
    out['ETSEL'] = t(out['fgpi'] + m[0] + 3)
    m = [x.start() for x in re.finditer(rb'\xa1(....)\xa3' + pk(a0) + rb'\xa1' + pk(a0 + 20) + rb'\xa3\1',
                                        d[out['fgpi']:out['fgpi'] + 0x200], re.S)]
    assert len(m) == 1, ('tactics selected entry', m)
    out['ETSELE'] = t(out['fgpi'] + m[0] + 1)
    # EditTacticsOnSelect28: mov eax, [chooseTacticsTeamPtr] / mov [A0], eax / mov word [D0], 5 / call RotatePlayersLeft /
    # mov dword [A0], offset cseg_4EC02 (10, 27, -1: entries to redraw)
    m = [x.end() - 1 for x in re.finditer(rb'\xa1....\xa3' + pk(a0) + rb'\x66\xc7\x05' + pk(d0) + rb'\x05\x00\xe8', d, re.S)]
    r = []
    for o in m:
        if rel(o) == s4['rot_t'] and d[o + 5:o + 7] == b'\xc7\x05':
            tg = t(o + 11)
            if tg[0] == 1 and d[tg[1]:tg[1] + 6] == b'\x0a\x00\x1b\x00\xff\xff':
                r.append(o)
    assert len(r) == 1, ('EditTacticsOnSelect28', r)
    out['rot'] = r[0]
    other = [x.end() - 1 for x in re.finditer(rb'\x66\xc7\x05' + pk(d0) + rb'\x05\x00\xe8', d)]
    other = [o for o in other if rel(o) == s4['rot_t'] and o not in r + [s4['rot']]]   # ViewSquadOnSelect21,
                                                                                         # SelectNationalTeamOnSelect25
    assert len(other) == 2, ('the other RotatePlayersLeft(5) callers', other)
    out['rot5'] = [o - 9 for o in other]                             # their mov word [D0], 5
    # cseg_4ECAD: mov ax, [editTacticsNumPlayers] / mov [D1], ax / sub word [D1], 16 / jz
    m = [x.start() for x in re.finditer(rb'\x66\xa1(....)\x66\xa3' + pk(d1) + rb'\x66\x83\x2d' + pk(d1) + rb'\x10\x74', d, re.S)]
    m = [o for o in m if re.search(rb'\xc7\x05' + pk(d0) + rb'\x1c\x00', d[o - 0x60:o])]   # (after D0 = 28:
    assert len(m) == 1, ('editTacticsNumPlayers', m)                                             #  the box hidden)
    out['ETNP'] = t(m[0] + 2)
    return out


def refs(p, tobj, lo, hi):
    """Every 32-bit fixup source (objn, off) whose target is tobj:lo..hi-1 -> [(objn, off, toff)]."""
    out = []
    for gp, recs in enumerate(p.recs):
        objn, base = p.page_obj[gp]
        for r in recs:
            if r[0] & 0x20 or r[0] & 0xf == 2:
                continue
            po = struct.unpack_from('<h', r, 2)[0]
            if po < 0:                          # (the second half of a straddling pointer: counted on its page)
                continue
            q = 4
            t = struct.unpack_from('<H', r, q)[0] if r[1] & 0x40 else r[q]
            q += 2 if r[1] & 0x40 else 1
            toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, q)[0]
            if t == tobj and lo <= toff < hi:
                out.append((objn, base + po, toff))
    return out


LOG = []
BENCH_WORLD = [0]                       # the World 2026-27's career world number (the packs' 'world'), 0 = none
BENCH_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bench2627.json')   # (4.0.6: in the repo)


def fallback_divs(v, n):
    """(4.0.5, Davide 30/10) A league's per-division benches with the unknown ones (null) filled from the nearest
    higher division that has data (a division with none above it keeps null: the game's 5). A cup's fallback (the
    top league's, or '=league.N') reads these filled values: reports/bench-unknowns-2627.md."""
    vals = list(v) if isinstance(v, list) else [v] * n
    vals += [None] * (n - len(vals))
    for i, x in enumerate(vals):
        if x is None and i:
            vals[i] = vals[i - 1]
    return vals


def bench_table(lang):
    """(phase 2) [(title, named, used, et)] of the World 2026-27 competitions with a known real bench: the career packs
    of world 5 in SEASON_PACKS x tools/bench2627.json (absent: none, the game's rule everywhere). The title =
    the country's button name in the exe language + ' ' + the competition's (a league: the division's) first name, as
    the game shows it (fmtgame's FORMAT keys). (4.0.5, Davide 30/10) Unknowns filled: a division from the nearest
    higher one (fallback_divs), a cup / state championship from the top league ('=league.N': that division's); each
    country a prefix entry '<button> ' (et | 80h: bx_look matches any title of the country, its play-offs and
    supercups too) = its top league, or its confederation's default ('confederations', by the pack's continent) for a
    country with no data; exact entries only where they differ from it. Order: exact, continental, prefixes longest
    first (IRLANDA DEL NORD before IRLANDA)."""
    import json
    if not os.path.isfile(BENCH_DATA):
        return []
    data = json.load(open(BENCH_DATA))
    used = int(data.get('used', 5))
    norm = lambda x: ((min(int(x.get('named')), 15), int(x.get('et') or 0)) if isinstance(x, dict) else
                      (min(int(x), 15), 0)) if x and (not isinstance(x, dict) or x.get('named')) else None
    out, pre, seen = [], [], set()
    for d in filter(None, os.environ.get('SEASON_PACKS', '').split(',')):
        f = os.path.join(d, 'pack.json')
        if not os.path.isfile(f):
            continue
        pk = json.load(open(f))
        cc = os.path.basename(d.rstrip('/'))
        if pk.get('kind') != 'career' or pk.get('world') != 5:
            continue
        ent = data['countries'].get(cc) or {}
        import complist                         # (4.0.5: the names as the game's titles hold them, as mkseason's)
        complist.fit_titles(pk)
        BENCH_WORLD[0] = pk['world']
        btn = pk.get('button_names', {}).get(lang) or pk['button']
        first = lambda names: (names.get(lang) or names['*'])[0]
        lg = next((c for c in pk['competitions'] if c.get('type') == 'league'), None)
        lvals = fallback_divs(ent.get(lg['key']), len(lg.get('divisions') or [0])) if lg else []
        top = norm(lvals[0] if lvals and lvals[0] is not None else
                   (data.get('confederations') or {}).get(pk.get('continent')))
        for c in pk['competitions']:
            v, raw = ent.get(c['key']), []
            if c.get('type') == 'league':
                divs = c.get('divisions') or [{'names': c['names']}]   # (one division: the league's own names)
                vals = lvals if c is lg else v if isinstance(v, list) else [v] * len(divs)
                items = [(first(dv['names']), x) for dv, x in zip(divs, vals)]
            else:                               # (4.0.5) a cup / state championship without data: '=league.N' = that
                if isinstance(v, str) and v.startswith('=league.'):   # division's (its clubs' own league), none =
                    v = lvals[int(v[8:])] if int(v[8:]) < len(lvals) else None   # the top league's (Davide 30/10)
                items = [(first(c['names']), v)]
            if c is lg:                         # (4.0.5) the league's own contests (fmtgame's titles): each gplay
                nm = lambda names: (names.get(lang) or names.get('*') or next(iter(names.values())))
                nm1 = lambda names: (lambda x: x[0] if isinstance(x, list) else x)(nm(names))
                for po in c.get('ko_playoffs') or []:   # play-off / play-out / poule = its clubs' division (the
                    dv = [e[0] for e in po.get('entrants') or [] if isinstance(e, list)]   # lowest if mixed)
                    if po.get('names') and dv and max(dv) < len(lvals):
                        items.append((nm1(po['names']), ent.get(po.get('key')) or lvals[max(dv)]))
                if c.get('cup_d'):                  # cupd: the Coppa Italia Serie D (its own json key 'cup_d'; its
                    items.append((nm1(c['cup_d'].get('names') or {'*': ['COPPA ITALIA SERIE D']}), ent.get('cup_d')))
                    raw.append(items[-1])           # tie's title has no country too: bench_cup at CELLE VARAZZE)
                if c.get('playoffs') == 'ita':      # dplay: Serie B play-off / play-out (Serie B's), Serie C play-off
                    import dplay
                    items += [(n.decode(), lvals[k]) for n, k in zip(dplay.NAMES, (1, 1, 2)) if k < len(lvals)]
            for name, x in items + [(None, x) for _, x in raw]:   # (a number = named subs; {'named', 'et'}: with an
                t = f'{btn} {name}' if name is not None else raw.pop(0)[0]   # extra-time sub)
                t = t.encode('latin-1')[:40]
                x = norm(x) or top
                if x and (x != top or name is None) and t not in seen:
                    seen.add(t)
                    out.append((t, x[0], used, x[1]))
        if top:
            pre.append(((btn + ' ').encode('latin-1')[:40], top[0], used, top[1] | 0x80))
    if pre:                                         # (the world is in this build) its continental cups: no country
        import uefaq                                # ('qual': the career club's qualifying tie too, uefaq's title)
        for name, v in (data.get('continental') or {}).items():
            q = [uefaq.NAMES[lang] + name[5:]] if v.get('qual') and name.startswith('UEFA ') else []
            q += [v['names'][lang]] if lang in (v.get('names') or {}) else []   # (its name in this exe's language)
            for t in [x for n in [name] + q for x in (' ' + n, n)]:
                t = t.encode('latin-1')[:40]
                if v.get('named') and t not in seen:
                    seen.add(t)
                    out.append((t, min(int(v['named']), 15), used, int(v.get('et') or 0)))
    return out + sorted(pre, key=lambda e: -len(e[0]))


def table_asm(tab):
    """bx_tabn / bx_tab: the entries of bench_table."""
    lines = ['align 4', f'bx_tabn: dd {len(tab)}', 'bx_tab:']
    for t, n, u, e in tab:                          # (4.0.5: titles NUL-terminated, no padding: the 2 pages)
        b = t + b'\0' + bytes((n, u, e))
        lines.append('    db ' + ','.join(str(x) for x in b))
    return '\n' + '\n'.join(lines) + '\n'


def patch(p, at, ns_at, lang='it'):
    """Code + data at obj1:at (a page of its own), namespr's pages at ns_at; returns the end."""
    import sacups
    import xtra
    regs = sacups.regs(p.le.obj_bytes(1))
    store, gmax, lp, c5, table, d2 = sites(p, regs)
    if 'CT' in xtra.LABELS:                         # xtra already hooked cseg_5DB56 (its site is a call now)
        ct = xtra.LABELS['CT']
        cnp = ct + 1292                             # careerNumPlayers follows careerTeam
    else:
        _, cnp, ct, _, _ = xtra.sites(p)
    s2, v2 = sites2(p, regs)
    s3 = sites3(p, regs, s2['n1'], s2['n2'])
    import namespr
    import shirtnum
    hdr, data, _ = namespr.layout(ns_at)
    assert namespr.CAP - namespr.N >= 20
    v3 = {'XHDR': (1, hdr + namespr.N * 24), 'XDATA': (1, data + namespr.N * namespr.DATA), 'DATA_': (0, namespr.DATA),
          'SPRIDX': (2, shirtnum.spr_index(p)), 'MKNAME': (1, s3['mkname']), 'SHORT_': (0, s3['short']),
          'SHIRT_': (0, s3['shirt']), 'NB_': (0, NB), 'D6': (2, regs['D7'] - 4), 'D0': (2, regs['D7'] - 28),
          'A4': (2, regs['A0'] + 16), 'A5': (2, regs['A0'] + 20)}
    at = (at + 15) & ~15
    sym = {**v2, **v3, 'D7': (2, regs['D7']), 'D1': (2, regs['D7'] - 24), 'A0': (2, regs['A0']), 'GMAX': (2, gmax), 'D2': (2, d2), 'A2': (2, regs['A0'] + 8), 'A6': (2, regs['A0'] + 24),
           'CT': (2, ct), 'CNP': (2, cnp), 'MAXP': (0, MAXP), 'PI': (0, PI)}
    s4 = sites4(p, regs)
    sym.update({'GPI': (1, s4['gpi_t']), 'ROTATE': (1, s4['rot_t']), 'DRAWMENU': (1, s4['drawmenu']),
                'SQCNT': (2, s4['tp'] - 2), 'S490': (2, s4['tp'] + 10), 'D3': (2, s4['D3']), 'D4': (2, s4['D4'])})
    s5 = sites5(p, regs, s4)
    sym.update({k: s5[k] for k in ('MAXSUB', 'NPS', 'PMSEL', 'VOPP', 'SELPOS')})
    s6 = sites6(p, regs, s4)
    sym.update({k: s6[k] for k in ('ETSEL', 'ETSELE', 'ETNP')})
    s8 = sites8(p, regs, s4, s5, s6)
    sym.update({k: s8[k] for k in ('SQCOMMON', 'ETCOMMON', 'ONSWAP', 'PMT2')})
    s9 = sites9(p, regs, s4, s6, ct, cnp)
    sym.update({k: s9[k] for k in ('VSCOMMON', 'NTCOMMON', 'VSTEAM', 'VSROW', 'NTSEL')})
    etc, sfet = sites10(p)
    sym['SFET'] = (1, sfet)
    s7 = sites7(p, regs)
    hasx = 'xt_block' in xtra.LABELS                # (A): a career's CPU clubs, places 16.. from their XTRA blocks
    sym.update({k: s7[k] for k in ('DRAWMENU', 'SETEXIT', 'MENU', 'MCC', 'LASTKEY', 'SHORTFIRE', 'FIRE', 'MCT', 'TOP', 'BOT')})
    sym.update({'GAMETYPE': s7['gametype'], 'HASX_': (0, int(hasx)), 'XTB': (1, xtra.LABELS['xt_block']) if hasx else (0, 0)})
    import lp36                                     # (phase 2) the current competition's title, the table
    gmin = p.target(1, store - 12 + 2)
    assert bytes(p.get(1, store - 12, 2)) == b'\x66\xa3' and gmin[0] == 2, 'gameMinSubstitutes store'
    import careerworld
    tab = bench_table(lang)
    sym.update({'GMIN': gmin, 'DIYNAME': (2, lp36._sites(p)['DIY'] + 4),
                'SLT': (careerworld.SITES or careerworld.sites(p))['slt'], 'WORLD_BYTE_': (0, careerworld.WORLD_BYTE),
                'BXWORLD_': (0, BENCH_WORLD[0] if tab else 255)})
    asm = ASM + table_asm(tab)
    code, fix = nasmcave.assemble(asm, at, sym)
    lab = nasmcave.labels(asm, at, sym)
    LOG.append(f'benchx phase 2: {len(tab)} competitions with a real bench ({lang})')
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    # gameMaxSubstitutes store (6 bytes: 66 A3 addr) -> call bx_max + nop
    p.remove(1, store + 2)
    p.put(1, store, b'\xe8' + struct.pack('<i', lab['bx_max'] - (store + 5)) + b'\x90')
    p.remove(1, store - 12 + 2)                     # (phase 2) gameMinSubstitutes store -> call bx_min + nop
    p.put(1, store - 12, b'\xe8' + struct.pack('<i', lab['bx_min'] - (store - 12 + 5)) + b'\x90')
    # the loop step (16 bytes: add word [D2], 1 / cmp word [D2], 16) -> call bx_next + 11 nops (the jnz stays)
    p.remove(1, lp + 3)
    p.remove(1, lp + 11)
    p.put(1, lp, b'\xe8' + struct.pack('<i', lab['bx_next'] - (lp + 5)) + b'\x90' * 11)
    p.remove(1, s7['stadium'] + 2)                  # the line-ups screen: mov ax, [GMAX] (66 A1 addr) -> call bx_gmax5
    p.put(1, s7['stadium'], b'\xe8' + struct.pack('<i', lab['bx_gmax5'] - (s7['stadium'] + 5)) + b'\x90')
                                                    # its end: jmp SetExitMenuFlag (rel32, no fixup) -> jmp bx_stad
    p.put(1, s7['stend'], b'\xe9' + struct.pack('<i', lab['bx_stad'] - (s7['stend'] + 5)))
    for c in c5:                                    # the game's 'bench over 5' branches: never
        p.put(1, c + 7, b'\x7f')
    def call9(o, n, lbl, fixat):                     # an n-byte instruction with an address at o + fixat -> call + nops
        p.remove(1, o + fixat)
        p.put(1, o, b'\xe8' + struct.pack('<i', lab[lbl] - (o + 5)) + b'\x90' * (n - 5))
    call9(s2['c5'], 8, 'bx_cmp_last', 3)            # cmp word [IDX], 5 (66 83 3D addr 05)
    call9(s2['c6'], 8, 'bx_cmp_last1', 3)
    call9(s2['arrow'], 6, 'bx_arrow', 2)            # mov ax, [IDX] (66 A1 addr)
    call9(s2['bentry'], 9, 'bx_bentry', 3)          # (4.0.6) mov word [IDX], 0 (66 C7 05 addr 00 00): a bench entered
    call9(s2['d7i'], 9, 'bx_win_init', 3)           # mov word [D7], 1 (66 C7 05 addr 01 00)
    call9(s2['d7e'], 8, 'bx_win_end', 3)            # cmp word [D7], 6 (66 83 3D addr 06)
    call9(s2['n1'], 9, 'bx_name1', 3)               # add word [D1], 255 (66 81 05 addr FF 00)
    call9(s2['n2'], 9, 'bx_name2', 3)
    for k in ('wb0', 'wb1', 'wb2'):                 # mov word [D2], 15 (66 C7 05 addr 0F 00)
        call9(s2[k], 9, 'bx_wcount', 3)
    for k, lbl in (('ord', 'bx_ord'), ('len', 'bx_len'), ('lenc', 'bx_lenc')):   # block 3: the name tables, 26 a team
        for objn, off, toff in s3['refs'][k]:
            p.retarget(objn, off, 1, lab[lbl])
            p.put(objn, off, struct.pack('<I', lab[lbl]))
    for o in s3['imm']:                             # the team-2 offsets / the copy loop: 16 -> 26
        assert bytes(p.get(1, o, 1)) == b'\x10', hex(o)
        p.put(1, o, bytes([MAXP]))
    p.put(1, s3['jmp'], b'\xe9' + struct.pack('<i', lab['bx_make'] - (s3['jmp'] + 5)))
    rs = refs(p, 2, table, table + 32)
    assert 10 <= len(rs) <= 24, ('inGameTeamPlayerOffsets refs', len(rs))
    for objn, off, toff in rs:
        p.retarget(objn, off, 1, lab['bx_table'] + toff - table)
        p.put(objn, off, struct.pack('<I', lab['bx_table'] + toff - table))
    call9(s4['row'], 8, 'sq_row', 3)                # task 1, the squad screen: sub word [D7], 1Ch
    call9(s4['cmp'], 8, 'sq_cmp', 3)                # cmp word [D7], 10h
    call9(s4['init'], 10, 'sq_init', 2)             # mov dword [dseg_16F490], 0
    for c in s4['c3']:                              # the 3 swap blocks (squad, play match, tactics names):
        call9(c, 8, 'sq_c3', 3)                     # cmp word [D3], 10h
        call9(c + 10, 8, 'sq_c4', 3)                # cmp word [D4], 10h
    call9(s4['bn'], 8, 'sq_bn', 3)                  # cmp word [D1], 16
    for k, lbl in (('gpi', 'sq_gpi'), ('rot', 'sq_rot')):   # call rel32 (no fixup)
        p.put(1, s4[k], b'\xe8' + struct.pack('<i', lab[lbl] - (s4[k] + 5)))
    d1o = p.le.obj_bytes(1)
    for k, n in (('store', 6), ('row', 8), ('swap', 6), ('ready', 6)):   # nobody else patched them
        assert bytes(p.get(1, s5[k], n)) == d1o[s5[k]:s5[k] + n], k
    call9(s5['store'], 6, 'pm_max', 2)              # the pre-match screen: mov [maxSubstitutesEntries], ax
    call9(s5['row'], 8, 'pm_row', 3)                # DrawPlayerEntries: sub word [D7], 13
    assert bytes(p.get(1, s6['row'], 8)) == d1o[s6['row']:s6['row'] + 8]
    call9(s6['row'], 8, 'et_row', 3)                # the tactics editor: sub word [D7], 11
    for o in s6['rot5']:
        assert bytes(p.get(1, o, 9)) == d1o[o:o + 9] and d1o[o:o + 3] == b'\x66\xc7\x05', hex(o)
        call9(o, 9, 'rot_d0', 3)                    # mov word [D0], 5
    call9(s5['swap'], 6, 'pm_n', 2)                 # PlayMatchMenuSwapPlayers: mov ax, [maxSubstitutesEntries]
    assert bytes(p.get(1, s8['mdir'], 6)) == d1o[s8['mdir']:s8['mdir'] + 6]
    call9(s8['mdir'], 6, 'bx_mdir', 2)              # (1, 4.0.6) MenuProc: mov [D6], ax (the cursor scroll)
    call9(s5['ready'], 6, 'pm_nr', 2)               # ShowOrHidePlayMatchButton: the same
    for o in s9['cmp']:                             # (4.0.6) ViewSquad / national call-ups: cmp word [D1], 10h
        call9(o, 8, 'vw_cmp', 3)
    call9(s9['vinit'], 6, 'vw_vinit', 2)            # cseg_53F43: mov [dseg_17A470], ax
    call9(s9['ninit'], 10, 'vw_ninit', 2)           # SelectNationalTeamInit: mov dword [dseg_17BA3A], 0
    rcalls = [(s5['dgpi'], 'pm_gpi'), (s5['rot'], 'pm_rot')] + [(o, 'pm_gpi2') for o in s5['sgpi']]
    rcalls += [(o, 'et_gpi') for o in s6['dgpi']] + [(s6['fgpi'], 'et_gpi2'), (s6['rot'], 'et_rot')]
    rcalls += [(o, 'vw_gpi') for o in s9['gpi']] + [(o, 'vw_rot') for o in s9['rot']] + [(etc, 'bx_et')]
    if s5['se']:
        rcalls.append((s5['se'], 'pm_gpi2'))        # shirtedit's se_ctl (row -> place)
    for o, lbl in rcalls:                           # call rel32 (no fixup)
        assert bytes(p.get(1, o, 1)) == b'\xe8', hex(o)
        p.put(1, o, b'\xe8' + struct.pack('<i', lab[lbl] - (o + 5)))
    bf = int(os.environ.get('BENCH_FORCE', '0'))   # BENCH_FORCE=n (test / playtest builds only): every match's bench
    if bf:                                          # n (<= 15) until the per-competition rule (phase 2)
        p.put(1, lab['bx_bench'], struct.pack('<H', min(bf, 15)))
        print(f'exe: BENCH_FORCE={min(bf, 15)} (test build)')
    assert lab['bx_bench'] - lab['bx_ord'] == 4 + 6 * MAXP   # (the harness finds the tables from bx_bench)
    assert lab['bx_vw'] - lab['bx_bench'] == 114               # (bench_view reads the window there)
    LABELS.update(lab)
    print(f'exe: bench up to 15 (block 1: in-match teams of {MAXP}; GMAX obj2+{gmax:#x}, loop obj1+{lp:#x}, '
          f'{len(rs)} offset-table refs moved; block 2: bench window of 5, cursor to 15, names of places 17+ on sprites {NB}.. (name tables 26 a team), 3 after-match loops to 11 + bench; code obj1+{at:#x}, {len(code)} B, bx_bench obj1+{lab["bx_bench"]:#x})')
    return at + len(code)
