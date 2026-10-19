"""Knockout promotion / relegation play-offs of a career world (pack.json league 'ko_playoffs', kind 'promotion'):
the glue around tools/gplay.c, decided at the season end from the final tables of every division of the country.

Season end (cseg_91D4D, per league struct A4): chained after dplay on the same two calls -
- gp_cap (the `call cseg_9221F`: dplay's dp_cap, or the game's, first): a country of GP_TAB (found by its league
  struct's address: a world's leagues share one contest id) -> division D7's final table (DIY+6Dh rows in order:
  team, global number from the team record +2, wins, goals, points) into GP_IN.t[D7];
- gp_end (the `call cseg_9228D`, dp_end first): after the country's last division, gp_season() (C) and its moves
  into leaguesTableCopy (signed division deltas) + the promotion / relegation animation of the career club.
Data: the divisions' promoted / relegated counts are the direct moves only; the play-off adds its winner's move and
the move of a winner_div entrant that does not win (to loser_div). The European play-offs are uefaq's.

Played (promotion / playout play-offs whose entrants are all [div, place]; rules in gplay.c 'The playable play-offs'):
- gp_lend replaces the two `call cseg_8ECAE` (the career league's last match day; dplay's dp_lend, or the game's, after
  it): a country of GP_TAB -> the career club's final table, gp_need() (C) picks the play-off it is in (Season mode,
  g_gameType 3: the division's own play-off and play-out, up to 2); the other divisions of its entrants are simulated
  now (cseg_3ABB2, as dplay) and kept in the state; gp_lend_c() builds the contest (type 1, no draw, id FE; Season's
  second: FC) and it goes into slot 4 as dplay's (cseg_8B2D3 D0 = 4, cseg_8ECAE's tail with the clubs in dseg_114EE4;
  slot 3: cseg_8B2D3 D0 = 3, its clubs from the contest's list);
- lib97: bye_find asks gp_bye first (the clubs that wait in round 1; nc_bye takes the contest's game rounds from the
  entry), nc_adv's NC_DPP slot is gp_perm (then dplay's dp_perm): every later round from the spec's member codes;
- gp_draw (cseg_2AE97's draw mark, after dplay's dp_draw) and gp_rec (its end, before dp_rec): the results;
- gp_ssim (`call cseg_915ED`, after dp_ssim): an early-simulated division gets those results back at the season end;
- gp_end: gp_played_c() gives gp_season the played winners. The state GP_ST (saved with the career by the engine's
  save block; gp_sync restores D8CBA / D8CB6 after a load), the season end's log GP_LOG (harness: 'GPLOGPTR').
Test builds: GPLAY_FORCE=k puts the career club on place k of its division at the league end and the season end.

pack.json league "ko_playoffs": [{ "key", "names": {lang: [long, short]},
  "kind": "promotion" | "europe" | "placement" | "playout" (the last round's losers go down to loser_div) |
          "stage_title" (4.0 ARG, + "stage": 0 / 1 a tournament's knockout, 2 the Trofeo: its champion and runner-up
          in GP_OUT.sres[stage], not the league's champion; built mid-season by gp_build, never by gp_need) |
          "title" (the champion = the last tie's winner, or the final group's 1st) | "continental" (its winner and
          runner-up take the continental places; the champion stays the table's 1st),
  "entrants": [[div, place] | {"div": d, "best_without_europe": true} | {"league_cup_winner": true, "if_places": [a, b]}
               | {"stage_place": s, "place": a, "div": d} (place a of split stage s's kept table, e.g. an Apertura)],
  "rounds": [{"ties": [[a, b], ...] | (with "pairing": "best_worst", "clubs": [...]), "legs": 1 | 2,
              "series": 3 (best of three single matches, games 1 and 3 at the better placed's; not the last round),
              "pairing": "draw" + "clubs" (the clubs drawn into ties; a club {"best_of": [P..]}: the best of those
              placings by their own groups' points, goal difference, goals - a ranking round before),
              "host": "listed" | "better" | "drawn" | "neutral", "level": "better" | "et_pens" | "et_better" | "pens",
              "gap": g (a tie of clubs g+ points apart is not played: the better placed goes through),
              "skip_if_same": bool (a tie of one club with itself is not played: it goes through)}
             | {"group": {"rounds": 1..4, "bonus": [points per member], "host": "listed" | "neutral"},
                "members": [...]} (a round robin; its placings P<k>, numbered across the group rounds)],
  "winner_div": d, "loser_div": d2 | "reserve" (out of the league), "skip_qualified": bool,
  "winners": w (a promotion play-off ending with a group: its top w go to winner_div) }]   (0-based divisions,
  1-based places; members: an entrant index, "W<k>" / "L<k>" the winner / loser of tie k, ties numbered in order
  across rounds, "P<k>" the k-th placing of the group rounds, "BL" the best placed loser of the previous knockout
  round); levels also "away_pens" / "away_better" (away goals, then penalties / the better placed: simulated as
  et_pens / better)
"""
import os
import re
import struct

RS_SIZE = 8 * 132                   # gplay.c RS_STATE: struct rs_state {u8 init, n, pad[2]; u16 q[64];} x RC 8
KINDS = {'promotion': 1, 'europe': 2, 'placement': 3, 'playout': 4, 'title': 5, 'continental': 6, 'promedio': 7,
         'stage_title': 8}
RESERVE = 0xFE                  # loser_div 'reserve': out of every division (gplay.c)
HOSTS = {'listed': 0, 'better': 1, 'drawn': 2, 'neutral': 3}
LEVELS = {'better': 0, 'et_pens': 1, 'et_better': 2, 'pens': 3, 'away_pens': 4, 'away_better': 5}
SKIP_SAME = 0x80                # host byte bit 7: a tie of one club with itself is not played (4.0 package 6)
BEST_LOSER = 0x3F               # member 'BL': the best placed loser of the previous round (entrants are 0..62)


def compile_spec(pos, ndiv):
    """pack.json 'ko_playoffs' -> the bytes gplay.c walks (ended by a 0); raises ValueError on a bad entry."""
    out = bytearray()
    for po in pos:
        key = po.get('key', '?')
        kind = KINDS.get(po.get('kind'))
        if not kind:
            raise ValueError(f'{key}: kind {" / ".join(KINDS)}')
        if kind == 7:                           # Argentina: {kind promedio, matches: this season's, loser_div}
            m, ld = po.get('matches'), po.get('loser_div')
            if not (isinstance(m, int) and 1 <= m < 256 and isinstance(ld, int) and 0 < ld < ndiv):
                raise ValueError(f'{key}: promedio needs matches 1..255 and loser_div 1..{ndiv - 1}')
            out += bytes((7, 0, 0, m, ld, 0))
            continue
        ents = []
        for e in po['entrants']:
            if isinstance(e, list) and len(e) == 2:
                d, p = e
                if not (0 <= d < ndiv and p >= 1):
                    raise ValueError(f'{key}: entrant {e}')
                ents.append((0, d, p, 0))
            elif isinstance(e, dict) and e.get('best_without_europe'):
                ents.append((1, e['div'], 0, 0))
            elif isinstance(e, dict) and 'stage_place' in e:   # place of a split stage's kept table (title)
                d, s, a = e.get('div', 0), e['stage_place'], e.get('place', 1)
                if not (0 <= d < ndiv and (0 <= s < 2 or 4 <= s < 7) and a >= 1):   # (4..6: GP_SS)
                    raise ValueError(f'{key}: entrant {e}')
                ents.append((3, d, a, s))
            elif isinstance(e, dict) and e.get('loser_of_previous'):   # the play-off before's final loser
                ents.append((4, 0, 0, 0))
            elif isinstance(e, dict) and 'stage_title' in e:   # 4.0 ARG: the Trofeo's finalists from the stage titles
                c, d = e['stage_title'], e.get('div', 0)       # 1 the 1st stage's champion; 2 / 3 the other finalist:
                if not (c in (1, 2, 3) and 0 <= d < ndiv):     # the 2nd stage's champion, or (the same club won both)
                    raise ValueError(f'{key}: entrant {e}')    # the two stages' runners-up (2: the 1st's, 3: the 2nd's)
                ents.append((5, d, c, 0))
            elif isinstance(e, dict) and e.get('league_cup_winner'):
                a, b = e.get('if_places', [0, 0])
                ents.append((2, 0, a, b))
            else:
                raise ValueError(f'{key}: entrant {e}')
        if not 2 <= len(ents) <= 63:
            raise ValueError(f'{key}: 2..63 entrants')
        rounds, nt, npl = bytearray(), 0, 0
        def code(m):
            if m == 'BL':
                if not nt:
                    raise ValueError(f'{key}: BL (the best loser) needs an earlier knockout round')
                return BEST_LOSER
            if isinstance(m, int):
                if not 0 <= m < len(ents):
                    raise ValueError(f'{key}: member {m}')
                return m
            mm = re.fullmatch(r'([WLP])(\d+)', str(m))
            if not mm or int(mm.group(2)) >= (npl if mm.group(1) == 'P' else nt):
                raise ValueError(f'{key}: member {m} (W<k> / L<k> of an earlier tie, P<k> an earlier placing)')
            return {'W': 0x80, 'L': 0xC0, 'P': 0x40}[mm.group(1)] | int(mm.group(2))
        nrd = 0
        for rd in po['rounds']:
            for c in list(rd.get('clubs') or []):  # {'best_of': [P..]}: a ranking round first (a group of 0 meetings:
                if isinstance(c, dict) and 'best_of' in c:   # the placings by their own groups' figures), its 1st
                    bo = c['best_of']
                    if not (2 <= len(bo) <= 24 and all(re.fullmatch(r'P\d+', str(m)) for m in bo)):
                        raise ValueError(f'{key}: best_of: 2..24 earlier placings P<k>')
                    rounds += bytes((len(bo), 0x80, HOSTS['neutral'], 0, 0, 0)) + bytes(code(m) for m in bo)
                    rounds += bytes(len(bo))
                    rd = dict(rd, clubs=[f'P{npl}' if x is c else x for x in rd['clubs']])
                    npl += len(bo)
                    nrd += 1
            nrd += 1
            if 'group' in rd:           # a round robin: (members, 0x80 | meetings, host, 0, 0, 0) codes, bonuses
                g, mem = rd['group'], rd['members']
                meet, bonus = g.get('rounds', 2), g.get('bonus', [0] * len(mem))
                if not (2 <= len(mem) <= 24 and meet in (1, 2, 3, 4) and len(bonus) == len(mem)
                        and all(0 <= b < 256 for b in bonus) and g.get('host', 'listed') in ('listed', 'neutral')):
                    raise ValueError(f'{key}: group of 2..24 members, rounds 1..4, a bonus per member, host '
                                     f'listed / neutral')
                rounds += bytes((len(mem), 0x80 | meet, HOSTS[g.get('host', 'listed')], 0, 0, 0))
                rounds += bytes(code(m) for m in mem) + bytes(bonus)
                npl += len(mem)
                continue
            # a best_worst block: the round itself, or its first tie entry {pairing, clubs}; other ties as listed
            tl = list(rd.get('ties') or [])
            blk = rd if rd.get('pairing') else (tl.pop(0) if tl and isinstance(tl[0], dict) else None)
            if blk is not None and (blk.get('pairing') not in ('best_worst', 'draw') or len(blk['clubs']) % 2):
                raise ValueError(f'{key}: pairing best_worst / draw with an even number of clubs')
            if any(isinstance(t, dict) for t in tl):
                raise ValueError(f'{key}: a best_worst block only as the first tie of a round')
            bm = list(blk['clubs']) if blk is not None else []
            mem = bm + [m for t in tl for m in t]
            ties, pairing = len(mem) // 2, len(bm) | (0x80 if blk is not None and blk.get('pairing') == 'draw' else 0)
            codes = [code(m) for m in mem]
            legs = rd.get('legs', 1)
            if rd.get('series'):                # best of three: legs byte 3 (single matches, the first to 2 wins)
                if rd['series'] != 3 or legs != 1:
                    raise ValueError(f'{key}: "series": 3 (single matches)')
                legs = 3
            if legs not in (1, 2, 3) or rd.get('host', 'listed') not in HOSTS or rd.get('level', 'et_pens') not in LEVELS:
                raise ValueError(f'{key}: legs 1 / 2, host {sorted(HOSTS)}, level {sorted(LEVELS)}')
            gap = rd.get('gap', 0)
            if not (isinstance(gap, int) and 0 <= gap < 256):
                raise ValueError(f'{key}: gap 0..255 points')
            host = HOSTS[rd.get('host', 'listed')] | (SKIP_SAME if rd.get('skip_if_same') else 0)
            rounds += bytes((ties, legs, host, LEVELS[rd.get('level', 'et_pens')], pairing,
                             gap))
            rounds += bytes(codes)
            nt += ties
        if nt > 63 or npl > 64:
            raise ValueError(f'{key}: at most 63 ties, 64 group placings')
        win = po.get('winners', 1)
        if not 1 <= win <= 15:
            raise ValueError(f'{key}: winners 1..15')
        wd, ld = po.get('winner_div', 0), po.get('loser_div', 0)
        ld = RESERVE if ld == 'reserve' else ld
        if kind == 8:                           # stage_title: winner_div byte = the stage (0, 1; 2 the Trofeo)
            wd, ld = po.get('stage'), 0
            if wd not in (0, 1, 2):
                raise ValueError(f'{key}: stage_title needs "stage" 0 / 1 (the tournaments) or 2 (their champions)')
        if kind in (1, 4) and not (0 <= wd < ndiv and (0 <= ld < ndiv or ld == RESERVE)):
            raise ValueError(f'{key}: winner_div / loser_div (a division, or "reserve")')
        if rounds and po['rounds'][-1].get('series'):
            raise ValueError(f'{key}: a best-of-three ("series": 3) not as the last round')
        flags = (1 if po.get('skip_qualified') else 0) | ((win if win > 1 else 0) << 4)
        out += bytes((kind, len(ents), nrd, wd, ld, flags))
        out += b''.join(bytes(e) for e in ents) + rounds
    stages = set()                              # 4.0 ARG: the Trofeo's entrants (type 5) read GP_OUT.sres of the stage
    for po in pos:                              # titles 0 and 1, filled earlier in the same gp_season pass
        if KINDS.get(po.get('kind')) == 8:
            stages.add(po.get('stage'))
        if any(isinstance(e, dict) and 'stage_title' in e for e in po.get('entrants', [])) and not {0, 1} <= stages:
            raise ValueError(f"{po.get('key', '?')}: a 'stage_title' entrant needs the stage_title play-offs of stages 0 and "
                             f"1 before it")
    out = bytes(out + b'\0')
    SPEC_NAMES[out] = [(po.get('names') or {}, po.get('key', '?'), po.get('record')) for po in pos]
    keys = [po.get('key') for po in pos]
    for po in pos:                      # 'then_build': the key of the play-off built when this one ends
        if po.get('then_build') is not None and po['then_build'] not in keys:
            raise ValueError(f"{po.get('key', '?')}: then_build {po['then_build']!r}: no such play-off key")
    THEN[out] = bytes(keys.index(po['then_build']) + 1 if po.get('then_build') is not None else 0 for po in pos)
    if any(po.get('kind') == 'title' and po['rounds'] and 'group' in po['rounds'][0] for po in pos):
        T2_SPECS.add(out)               # (a group contest played in a career: the engine block's item 'GS')
    BUILD_AFTER[out] = [(i, po['build_after']) for i, po in enumerate(pos) if po.get('build_after')]
    for i, name in BUILD_AFTER[out]:
        if KINDS.get(pos[i].get('kind')) != 8 or not isinstance(name, str):
            raise ValueError(f"{pos[i].get('key', '?')}: build_after (a split stage's 'then' name) needs kind stage_title")
    return out


PLAY_ASM = '''
gp_c:                                   ; eax = a C function: called with es = ds, cld (C may use string ops)
    push es
    push ds
    pop es
    cld
    call eax
    pop es
    ret

gp_clrn:                                ; GP_IN's captured counts cleared
    push eax
    push ecx
    xor eax, eax
    mov ecx, GD_N
.z:
    mov [GP_IN + O_N + ecx - 1], al
    loop .z
    pop ecx
    pop eax
    ret

gp_regs:                                ; the game's pseudo registers D0 .. A6 <-> GP_REGS (eax = 0: save, 1: back)
    pushad
    mov esi, D0R
    mov edi, GP_REGS
    test eax, eax
    jz .c
    xchg esi, edi
.c:
    mov ecx, 15
.l:
    mov eax, [esi]
    mov [edi], eax
    add esi, 4
    add edi, 4
    loop .l
    popad
    ret

gp_setup:                               ; ZF = 0 if the career league (D8CAA) is a country of GP_TAB: its spec, names,
    mov edx, [D8CAA]                    ; nd, the career club's division's current table (competitionFileBuffer),
    test edx, edx                       ; the club, the week just played, the game type, the season into GP_IN
    jz .no
    call gp_find
    jz .no
    mov eax, [esi + 5]
    mov [GP_IN + O_SPEC], eax
    sub esi, GP_TAB                     ; its names (GP_NMT, by the entry's index)
    mov eax, esi
    xor edx, edx
    mov ecx, 9
    div ecx
    push eax
    mov eax, [GP_NMT + eax * 4]
    mov [GP_NM], eax
    pop eax
    mov eax, [GP_THT + eax * 4]
    mov [GP_TH], eax
    mov edx, [D8CAA]
    mov al, [edx + 9]
    mov [GP_IN], al                     ; (nd)
    call gp_clrn
    movzx eax, word [D6CDC]             ; the career club's division: its table
    cmp eax, GD_N
    jae .no
    mov [GP_IN + O_MDIV], al
    push eax                            ; (split's kept stage table too: GP_IN.st, stage_place entrants)
    push es                             ; (es first: the C code's arguments right above the return address)
    push ds
    pop es
    cld
    push dword SP_MAGIC
    push eax
    push dword [SELTEAMS]
    push dword SP_KEEP
    push dword SP_ST
    push dword CFB
    call gp_keep
    add esp, 24
    pop es
    pop eax
    mov ebp, CFB
    call gp_rows
    mov ax, [CAREERTEAM]
    mov [GP_IN + O_MGR], ax
    movzx eax, word [CAL_CUR]           ; the week of the match day just played (its calendar entry +1)
    movzx eax, byte [CAL + eax + 1]
    mov [GP_IN + O_WEEK], ax
    mov al, [GAMETYPE]
    mov [GP_IN + O_GT], al
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    or esp, esp
    ret
.no:
    xor eax, eax
    ret

gp_install:                             ; GP_BUILT (gp_lend_c): each ko built into its slot (4, or 3: Season's second,
    xor ebx, ebx                        ; a career's group contest)
.k:
    cmp ebx, 2
    jae .x
    bt dword [GP_BUILT], ebx
    jnc .n
    imul esi, ebx, KO_SIZE
    add esi, GP_ST + ST_KO
    cmp byte [esi + KO_SLOT], 4
    jne .s3
    pushad
    push es                             ; slot 4 cleared, as never used this season
    push ds
    pop es
    mov edi, SLOT4
    mov ecx, 443h
    xor eax, eax
    cld
    rep stosb
    pop es
    lea eax, [esi + KO_CON]             ; slot 4: buffer + calendar (cseg_8B2D3, as cseg_8DAC3 at a season start)
    mov [A0R], eax
    mov word [D0R], 4
    mov word [D1R], 0
    mov word [D2R], 0
    pushad
    call C8B2D3
    popad
    movzx ecx, byte [esi + KO_N]
    xor ebx, ebx
.t:
    mov ax, [esi + KO_TEAM + ebx * 2]   ; its clubs, as cseg_8ECAE's loop lists them
    mov [LIST4 + ebx * 2], ax
    inc ebx
    cmp ebx, ecx
    jb .t
    mov dword [A4R], SLOT4              ; cseg_8ECAE's tail: teams into slot 4, pointers, saved
    mov word [D7R], 0
    pushad
    call C8EE5D
    popad
    popad
    jmp .n
.s3:
    pushad                              ; slot 3: its clubs from the contest's list (cseg_8B2D3 D0 = 3, D2 = 0)
    lea eax, [esi + KO_CON]
    mov [A0R], eax
    mov word [D0R], 3
    mov word [D1R], 0
    mov word [D2R], 0
    call C8B2D3
    popad
.n:
    inc ebx
    jmp .k
.x:
    ret

gp_lend:                                ; replaces `call cseg_8ECAE` (the career league's last match day) before
    pushad                              ; dplay's dp_lend (or the game's): in a country of GP_TAB the career club's
    call gp_setup                       ; play-off (Season: the division's play-off and play-out) into slot 4 (3)
    jz .next
%if FORCE_ON
    mov dword [GP_CFB], CFB             ; (GPLAY_FORCE test builds: the league's own table too)
    mov eax, gp_forcecfb
    call gp_c
%endif
    mov eax, gp_need
    call gp_c
    test eax, eax
    jz .none
    xor ebx, ebx                        ; the other divisions of its entrants simulated now (as cseg_8ECAE does for
.sim:                                   ; a native play-off's clubs), their tables kept for the season end
    cmp ebx, SDX_N
    jae .built
    movzx ecx, byte [GP_IN + O_SIM + ebx]
    cmp ecx, 0FFh
    je .sn
    pushad
    xor eax, eax
    call gp_regs
    mov word [F846], 1
    call SAVESEL
    mov edx, [D8CAA]
    mov [A0R], edx
    mov [D0R], cx
    call C3ABB2                         ; the whole division simulated (cseg_3ABB2) into DIY
    call RESTSEL
    mov word [F846], 0
    mov eax, 1
    call gp_regs
    popad
    pushad
    mov eax, ecx
    mov ebp, DIY
    call gp_rows
    mov [GP_DIV], cl
    mov dword [GP_DIYP], DIY
    mov eax, gp_simkeep
    call gp_c
    popad
.sn:
    inc ebx
    jmp .sim
.built:
    mov eax, gp_lend_c
    call gp_c
    mov [GP_BUILT], eax
    call gp_clrn
    test eax, eax
    jz .next
    call gp_install
    popad
    ret
.none:
    call gp_clrn
.next:
    mov eax, [D8CAA + 16]               ; (D8CBA = one of our contests, e.g. built mid-season by gp_build: the native
    lea ebx, [GP_ST + ST_KO + KO_CON]   ; division play-off path of cseg_8ECAE would read it as a league record's
    cmp eax, ebx                        ; play-off, with a stale D8CC0: skip it)
    je .skip
    add ebx, KO_SIZE
    cmp eax, ebx
    je .skip
    popad
    jmp GP_LEND_NEXT
.skip:
    popad
    ret

gp_build:                               ; mid-season (4.0's engine.after_stage): play-off GP_BPI of the career
    pushad                              ; league's spec into slot 4, its first week GP_BWEEK + 1, its entrants from
    call gp_setup                       ; the career club's league as it stands (GP_IN; no early simulations)
    jz .x
    mov ax, [GP_BWEEK]
    mov [GP_IN + O_WEEK], ax
    mov eax, [GP_BPI]
    mov [GP_BPIC], eax
    mov eax, gp_build_c
    call gp_c
    mov [GP_BUILT], eax
    call gp_clrn
    test eax, eax
    jz .x
    call gp_install
.x:
    popad
    ret
GP_BPI: dd 0
GP_BWEEK: dd 0

gp_ours:                                ; ZF = 0 and GP_K = the ko index if DIY holds our contest of this season
    pushad
    mov al, [DIY + 2Dh]
    mov [GP_CID], al
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov eax, gp_ours_c
    call gp_c
    mov [GP_K], eax
    inc eax
    popad
    ret

gp_decisive:                            ; ZF = 0 if the match just played decides its tie (single, or a second leg)
    cmp word [DIY + 14Bh], 2
    jne .y
    cmp word [DIY + 149h], 0
    ret
.y:
    or esp, esp
    ret

gp_pair:                                ; the match's two clubs -> GP_A, GP_B
    mov esi, [A1R]
    mov ax, [esi]
    mov [GP_A], ax
    mov esi, [A2R]
    mov ax, [esi]
    mov [GP_B], ax
    ret

gp_draw:                                ; at cseg_2AE97's 'draw -> replay' mark (after historic's coin_draw, dplay's
    call GP_DRAW_NEXT                   ; dp_draw): a level tie of ours -> the better placed club
    pushad
    call gp_ours
    jz .x
    call gp_decisive
    jz .x
    test byte [D7R], 2                  ; (decided already)
    jnz .x
    call gp_pair
    mov eax, gp_draw_c
    call gp_c
    test eax, eax                       ; (a type-2 contest: the game's rules)
    js .x
    and byte [D7R], 0FEh
    or byte [D7R], 2
    or [D7R], al                        ; (1: the second club)
.x:
    popad
    ret

gp_rec:                                 ; at cseg_2AE97's end (the match's result), before dplay's dp_rec: a decisive
    pushad                              ; match of ours -> its tie's winner (the state)
    call gp_ours
    jz .x
    call gp_decisive
    jz .x
    test byte [D7R], 2
    jz .x
    call gp_pair
    movzx eax, byte [D7R]
    and eax, 1
    mov [GP_W], eax
    call gp_week
    mov eax, gp_rec_c
    call gp_c
.x:
    popad
    jmp GP_REC_NEXT
gp_recmov:                              ; (no dplay: the instruction it replaced)
    mov ax, [W11F9CC]
    ret

gp_perm:                                ; lib97 nc_adv's slot (NC_DPP; dplay's dp_perm after it): ecx = the next
    pushad                              ; round's clubs, NC_T = the winners in tie order -> CF = 0: list +2CDh and
    call gp_ours                        ; ecx = the next round's clubs, its legs / extra time / penalties words
    jz .no
    push es
    push ds
    pop es
    cld
    mov esi, NC_T
    mov edi, GP_PT
    mov ecx, 64
    rep movsb
    pop es
    mov eax, gp_perm_c
    call gp_c
    mov [GP_NC], eax
    test eax, eax
    jz .x
    push es
    push ds
    pop es
    cld
    mov ecx, eax
    mov esi, GP_PL
    mov edi, NCW + 2CDh
    rep movsb
    pop es
    movzx edx, word [NCW + 57h]         ; the next round's words from its round byte (as nc_bye decodes them)
    inc edx
    mov eax, [GP_RB]
    movzx ebx, al
    shr ebx, 6
    mov [NCW + 65h + edx * 2], bx
    movzx ebx, al
    shr ebx, 4
    and ebx, 3
    mov [NCW + 71h + edx * 2], bx
    movzx ebx, al
    shr ebx, 2
    and ebx, 3
    mov [NCW + 7Dh + edx * 2], bx
    mov eax, [GP_SKIP]                  ; (a game 3 nobody needs: one round less)
    sub [NCW + 59h], ax
.x:
    popad
    mov ecx, [GP_NC]
    test ecx, ecx
    jz .stc
    clc
    ret
.no:
    popad
    jmp [GP_PNEXT]
.stc:
    stc
    ret
gp_stc:
    stc
    ret

gp_bye:                                 ; lib97 bye_find's hook: al = contest id, cx = clubs -> CF = 0, esi = the
    push eax                            ; running contest's entry (id, 0FFh, clubs, byes, game rounds), else CF = 1
    push ebx
    mov ah, [SEASONPLAYING]
    xor ebx, ebx
.k:
    cmp ebx, 2
    jae .no
    imul esi, ebx, KO_SIZE
    add esi, GP_ST + ST_KO
    cmp word [esi], 4B47h
    jne .n
    cmp [esi + KO_SEAS], ah
    jne .n
    cmp byte [esi + KO_SLOT], 0         ; (built: not a play-off decided without a match)
    je .n
    cmp byte [esi + KO_BYE + 7], 0      ; (a type-2 contest: no byes of ours)
    jne .n
    cmp [esi + KO_CID], al
    jne .n
    test ch, ch
    jnz .n
    cmp [esi + KO_N], cl
    jne .n
    add esi, KO_BYE
    pop ebx
    pop eax
    clc
    ret
.n:
    inc ebx
    jmp .k
.no:
    pop ebx
    pop eax
    stc
    ret

gp_sync:                                ; after a career / .SEA load (the engine's save block): the running contests'
    pushad                              ; pointers D8CBA (slot 4) / D8CB6 (slot 3), which ProcessCareerFile rebuilds
    mov ah, [SEASONPLAYING]             ; from the league records, back from the state
    xor ebx, ebx
.k:
    cmp ebx, 2
    jae .x
    imul esi, ebx, KO_SIZE
    add esi, GP_ST + ST_KO
    cmp word [esi], 4B47h
    jne .n
    cmp [esi + KO_SEAS], ah
    jne .n
    movzx edx, byte [esi + KO_SLOT]
    lea ecx, [esi + KO_CON]
    mov [D8CAA + edx * 4], ecx
.n:
    inc ebx
    jmp .k
.x:
    popad
    ret

gp_sack:                                ; replaces SeasonFinished's `call cseg_3C07C` (a club career's season-end
    pushad                              ; screens; cseg_3E55C, the contract check, runs for national selectors only):
    cmp word [GAMETYPE], 4              ; (a group contest won, the Poule: the season record's 4th line = its record
    jne .nr                             ; name, result 1 = WINNERS; no trophy flag)
    mov ax, [CAREERTEAM]
    mov [GP_MGR], ax
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov eax, gp_pwin_c
    call gp_c
    test eax, eax
    jz .nr
    push eax
%if FORCE_ON
    mov ax, [CAREERTEAM]                ; (test builds: the review sees the career club as the slot-3 cup's winner)
    mov [DA11B], ax
%endif
    pushad
    call GETSEASON                      ; (GetCurrentSeasonPointer: A0)
    popad
    pop eax
    mov esi, [A0R]
    mov [esi + 34], eax
    mov byte [esi + 89], 1
.nr:
    mov eax, [D8CAA + 12]               ; (our slot-3 contest, the Poule, is no European cup for the season review:
    test eax, eax                       ; cseg_3D7CB credits the slot-3 cup's winner with D8CBE's trophy) D8CB6 = 0
    jz .e
    lea ebx, [GP_ST + ST_KO + KO_CON]
    cmp eax, ebx
    je .ec
    add ebx, KO_SIZE
    cmp eax, ebx
    jne .e
.ec:
    mov dword [D8CAA + 12], 0
.e:
    cmp word [GAMETYPE], 4              ; the career club relegated into the reserve (directly, or by a played
    jne .game                           ; play-out) is sacked first, as cseg_3E55C sacks (CONTINUA CARRIERA off,
    cmp word [SACKED], 0                ; job offers)
    jne .game
    mov edx, [D8CAA]
    test edx, edx
    jz .game
    mov [GP_LG], edx
    mov dword [GP_CFB], CFB
    mov eax, [SELTEAMS]
    mov [GP_SEL], eax
    mov eax, [GP_RSTP]
    mov [GP_RST], eax
    mov eax, [GP_RITP]
    mov [GP_RIT], eax
    mov al, [SLT + WORLD_BYTE]
    mov [GP_WORLD], al
    mov ax, [CAREERTEAM]
    mov [GP_MGR], ax
    mov dword [GP_SLT], SLT
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov eax, gp_sack_c
    call gp_c
    test eax, eax
    jz .game
    mov word [CURMSG], MSG_NORENEW
    call SHOWCHAIR
    mov word [SACKED], 1
.game:
    popad
    jmp C3C07C

gp_week:                                ; GP_WK = the current calendar entry's week
    push eax
    movzx eax, word [CAL_CUR]
    movzx eax, byte [CAL + eax + 1]
    mov [GP_WK], eax
    pop eax
    ret

gp_adv:                                 ; replaces the 4 `call cseg_8EA82` (the calendar advance, after an event is
    pushad                              ; done): a pending 'then_build' (a played or simulated knockout ended) due ->
    mov al, [SEASONPLAYING]             ; gp_build of its next play-off from this week (slot 4 free: its contest over)
    mov [GP_SEAS], al
    call gp_week
    mov eax, gp_adv_c
    call gp_c
    test eax, eax
    jz .x
    dec eax
    mov [GP_BPI], eax
    mov eax, [GP_WK]
    mov [GP_BWEEK], eax
    popad
    pushad
    call gp_build
.x:
    popad
    jmp C8EA82

gp_defer:                               ; 4.0's ba_<name> (split's after_stage, inside the league's match-day
    pushad                              ; processing: DIY holds the league, slot 4 can't be built there): play-off
    mov al, [SEASONPLAYING]             ; GP_BPI pending from week GP_BWEEK, built by gp_adv at the calendar advance
    mov [GP_SEAS], al
    mov eax, [GP_BPI]
    mov [GP_BPIC], eax
    mov eax, [GP_BWEEK]
    mov [GP_WK], eax
    mov eax, gp_defer_c
    call gp_c
    popad
    ret

gp_ssim:                                ; replaces `call cseg_915ED` (a division simulated at the season end; after
    call GP_SSIM_NEXT                   ; dplay's dp_ssim): a division simulated early for the career club's
    pushad                              ; play-off gets that simulation's results back (gp_restore)
    mov edx, [A4R]
    call gp_find
    jz .x
    mov al, [D7R]
    mov [GP_DIV], al
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov dword [GP_DIYP], DIY
    mov eax, gp_restore
    call gp_c
.x:
    popad
    ret

align 4
GP_REGS: times 15 dd 0
GP_NC: dd 0
GP_BUILT: dd 0
GP_PNEXT: dd 0                          ; (dplay's dp_perm, or gp_stc)
GP_RSTP: dd 0                           ; (pgroups' RS_TAB: link_reserve, or 0)
GP_RITP: dd 0                           ; (ripool's RI_TAB: link_reserve, or 0)
    db 'GPLOGPTR'                       ; (the harness: GP_LOG, GP_ST in obj2, their sizes; D8CB6, the euro cup won
    dd GP_LOG, GP_ST, LOG_SIZE, ST_SIZE ; flags D6C64 / D6C66 / D6C68)
    dd D8CAA + 12, EUW0, EUW1, EUW2, SEASREC   ; (+ the season records, 106 B each)
'''


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
    push eax                            ; split's kept stage table (gplay.c gp_keep: GP_IN.st)
    push es                             ; (es first: the C code's arguments right above the return address)
    push ds
    pop es
    cld
    push dword SP_MAGIC
    push eax
    push dword [SELTEAMS]
    push dword SP_KEEP
    push dword SP_ST
    push dword DIY
    call gp_keep
    add esp, 24
    pop es
    pop eax
    mov ebp, DIY
    call gp_rows
.x:
    popad
    ret

gp_rows:                                ; eax = a division, ebp = a league buffer (DIY layout): its final table into
    cmp eax, GD_N                       ; GP_IN (places in order: team, global number from the team record +2,
    jae .x                              ; wins, goals, points)
    movzx ecx, word [ebp + 31h]
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
    movzx esi, word [ebp + 6Dh + ebx * 2]   ; the place's row offset (row * 12h)
    mov eax, esi
    xor edx, edx
    push ecx
    mov ecx, 12h
    div ecx
    pop ecx
    mov ax, [ebp + 12Dh + eax * 2]
    mov [edi], ax
    mov edx, [ebp + esi + 2B3h]         ; its team record: the global number
    add edx, [SELTEAMS]
    mov ax, [edx + 2]
    mov [edi + 2], ax
    mov ax, [ebp + esi + 2B9h]
    mov [edi + 4], ax
    mov ax, [ebp + esi + 2BFh]
    mov [edi + 6], ax
    mov ax, [ebp + esi + 2C1h]
    mov [edi + 8], ax
    mov ax, [ebp + esi + 2C3h]
    mov [edi + 10], ax
    add edi, RSZ
    inc ebx
    jmp .r
.x:
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
    mov ax, [CAREERTEAM]                ; (GPLAY_FORCE test builds)
    mov [GP_IN + O_MGR], ax
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov eax, gp_played_c                ; the career club's played play-off: its results
    call gp_c
    mov eax, gp_season
    call gp_c
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
    mov eax, gp_end_c                   ; (the log; the state void)
    call gp_c
.clr:
    xor eax, eax
    mov ecx, GD_N
.z:
    mov [GP_IN + O_N + ecx - 1], al
    loop .z
.x:
    popad
    ret
''' + PLAY_ASM


BUILD_AFTER = {}         # compile_spec's output -> [(play-off index, split stage 'then' name)]: built by gp_build there
THEN = {}                # compile_spec's output -> per play-off its 'then_build' target's index + 1, or 0
T2_SPECS = set()         # compile_spec's outputs with a group contest (the Poule Scudetto): GP_GS saved ('GS')
GS_SIZE = 7 + 1 + 7 * 20 * 10   # (sizeof struct gp_gs)
SPEC_NAMES = {}          # compile_spec's output -> the play-offs' names ({lang: [long, short]}), for the contests


def _name(names, lang, key):
    v = names.get(lang) or names.get('*') or names.get('en') or next(iter(names.values()), None) or [key.upper()] * 2
    return [x.encode('latin-1') for x in (v if isinstance(v, list) else [v, v])]


def table_lines(tables):
    """GP_TAB: per country dd its league struct, db world, dd its spec; a 0 world ends it. Specs after it."""
    import mkseason
    lines, syms = ['GP_TAB:'], {}
    import engine
    for i, (world, lfile, spec) in enumerate(tables):
        lines.append(f'    dd GPL{i}\n    db {world}\n    dd GPS{i}')
        at = engine.LEAGUE_AT[lfile[1]] if isinstance(lfile, tuple) else mkseason.LEAGUE_AT[(world, lfile)]
        syms[f'GPL{i}'] = at if isinstance(at, tuple) else (1, at)   # (world 0's structs: (obj, offset), often obj2)
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
GP_PAGES = 8             # obj1 pages for the C code + glue + specs (World 2026-27's 20 countries; gplay-play; 4.0 ARG: 7)
GP_ST_SIZE = 2036       # (sizeof struct gp_state: the engine block's item 'GP', patch.py)
GP_BSS = 0x6000          # the C .bss pages (obj2 after careerworld's BSS): GP_IN at GT 32 / GD 16, GP_SS, PR, RS, GP_ST, RI, PS


def _sack_sites(p):
    """SeasonFinished: its call of cseg_3E55C (the contract check, national selectors only; its tail: currentMessage =
    WE_DIDNT_RENEW_YOUR_CONTRACT, call ShowChairmanMessage, youreSacked = 1, ret) and, after it, a club career's
    `push A5; call cseg_3C07C` (the season-end screens): gp_sack's site."""
    import sacups
    d1 = p.le.obj_bytes(1)
    head = [m.start() for m in re.finditer(rb'\x66\xa1.{4}\x66\x0b\xc0\x0f\x84.{4}\x66\xa1.{4}\x66\x0b\xc0\x0f\x85', d1, re.S)]
    out = []
    for h in head:
        m = re.compile(rb'\x66\xc7\x05(.{4})(..)\xe8(.{4})\x66\xc7\x05(.{4})\x01\x00\xc3', re.S).search(d1, h, h + 0xC0)
        if m:
            out.append((h, m))
    calls = lambda t: [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == t]
    out = [(h, m, calls(h)) for h, m in out]
    out = [x for x in out if len(x[2]) == 1]
    assert len(out) == 1, [hex(h) for h, _, _ in out]
    h, m, (c55c,) = out[0]
    a5 = struct.pack('<I', sacups.regs(d1)['A0'] + 20)
    k = d1.find(b'\xff\x35' + a5 + b'\xe8', c55c, c55c + 0x60)      # push A5; call cseg_3C07C
    assert k > 0, hex(c55c)
    site = k + 6
    u = lambda g: struct.unpack('<I', m.group(g))[0]
    e = [x for x in re.finditer(rb'\x66\x83\x3d(.{4})\x00\x74.\x66\x83\x3d\1\x02\x74.\x66\xc7\x05(.{4})\x01\x00\xeb.'
                                rb'\x66\xc7\x05(.{4})\x01\x00\xeb.\x66\xc7\x05(.{4})\x01\x00', d1, re.S)]
    assert len(e) == 1, len(e)                  # cseg_3D7CB: the slot-3 cup's winner -> the euro cup won flags by D8CBE
    eu = [struct.unpack('<I', e[0].group(g))[0] for g in (3, 2, 4)]   # (D6C64 EC, D6C66 CWC, D6C68 UEFA)
    w = re.search(rb'\x66\xa1(.{4})\x66\x39\x05(.{4})\x75.$', d1[e[0].start() - 24:e[0].start()], re.S)
    da11b = struct.unpack('<I', w.group(1))[0]          # (the slot-3 cup's winner, the review's compare)
    r_ = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    gm = [x for x in re.finditer(rb'\xc7\x05' + pk(r_['A0']) + rb'(.{4})\x66\xa1.{4}\x66\xa3' + pk(r_['A0'] - 32)
                                 + rb'\x66\xa1' + pk(r_['A0'] - 32) + rb'\x66\xbb\x6a\x00', d1, re.S)]
    assert len(gm) == 1, gm                             # GetCurrentSeasonPointer (A0 = the season record, 106 B)
    gs = [gm[0].start()]
    return dict(c3e55c=h, site=site, c3c07c=site + 5 + struct.unpack_from('<i', d1, site + 1)[0], euw=eu,
                da11b=da11b, getseason=gs[0], seasrec=struct.unpack('<I', gm[0].group(1))[0],
                msg=struct.unpack('<H', m.group(2))[0], show=m.end(3) + struct.unpack('<i', m.group(3))[0],
                CURMSG=u(1), SACKED=u(4))


def _adv_sites(p):
    """cseg_8EA82 (the career calendar advance: gameType 4 -> counters, cseg_94DB1) and its 4 callers."""
    import split
    d1 = p.le.obj_bytes(1)
    gt = struct.pack('<I', split.sites(p)['GAMETYPE'][1])
    m = [x.start() for x in re.finditer(rb'\x66\x83\x3d' + re.escape(gt) + rb'\x04\x75.\x66\x83\x05.{4}\x01\x66\x83\x05.{4}'
                                         rb'\x01\x66\x83\x05.{4}\x01\xff\x35', d1, re.S)]
    assert len(m) == 1, m
    calls = [i for i in range(len(d1) - 5) if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == m[0]]
    assert len(calls) == 4, calls
    return m[0], calls


def link_reserve(p, ri=None):
    """After pgroups.patch (and ripool.patch): gp_sack's reserve tables, pgroups.LABELS['RS_TAB'] and the off-file
    pool's RI_TAB (ri: ripool.patch's labels); none: their pointers stay 0."""
    import pgroups
    rs = getattr(pgroups, 'LABELS', {}).get('RS_TAB')
    if rs is not None and LABELS.get('GP_RSTP'):
        p.add_ptr(1, LABELS['GP_RSTP'], 1, rs)
    if ri and ri.get('RI_TAB') and LABELS.get('GP_RITP'):
        p.add_ptr(1, LABELS['GP_RITP'], *ri['RI_TAB'])


def names_lines(tables, area, lang):
    """GP_NMT: per GP_TAB entry dd its names; GPN<i>: per play-off dd long, short, its record line (pack 'record':
    {lang: name}, else the long name; relative to sacups.STR_BASE)."""
    import sacups
    lines = ['GP_NMT:'] + [f'    dd GPN{i}' for i in range(len(tables))]
    for i, (_, _, spec) in enumerate(tables):
        lines.append(f'GPN{i}:')
        for names, key, rec in SPEC_NAMES.get(spec, []):
            long_, short = _name(names, lang, key)
            record = _name(rec, lang, key)[0] if rec else long_   # (a group contest won: the season record's line)
            rl, rs, rr = (area.add(x + b'\0') - sacups.STR_BASE if area else 0 for x in (long_, short, record))
            lines.append(f'    dd {rl}, {rs}, {rr}')
        lines.append('    dd 0, 0, 0')
    lines += ['GP_THT:'] + [f'    dd GPT{i}' for i in range(len(tables))]      # ('then_build' per play-off)
    for i, (_, _, spec) in enumerate(tables):
        lines.append(f'GPT{i}: db ' + ', '.join(str(b) for b in (THEN.get(spec) or b'') + b'\0'))
    return '\n'.join(lines)


def patch(p, at, limit, tables, bss_at, area=None, lang='it'):
    """tables: mkseason.gplay_tables(). C + glue + specs in obj1 at..limit, the C .bss at obj2 bss_at (BSS_SIZE).
    area: the contest names' string area (the playable play-offs). Returns the end."""
    import bigtables
    import careerworld
    import cobj
    import dplay
    import lib97
    import pgroups
    import nasmcave
    import sacups
    import split
    cap, c9221f, end_site, c9228d, diy, ct, rel, pro, r = dplay._sites(p)
    ps = dplay._play_sites(p, r)
    tgt = lambda a: a + 5 + struct.unpack('<i', p.get(1, a + 1, 4))[0]   # (the current targets: dplay's, or the game's)
    assert p.get(1, cap, 1) == b'\xe8' and p.get(1, end_site, 1) == b'\xe8'
    for a in (*ps['lend'], ps['ssim'], ps['draw']):
        assert p.get(1, a, 1) == b'\xe8', hex(a)
    force = int(os.environ.get('GPLAY_FORCE') or 0)         # (test builds: the career club's place in its division)
    import mkseason as mks
    prom = mks.promedio_table()                     # Argentina's promedio history (GP_PROM_TAB) before the C code
    assert not any(p.get(1, at, len(prom)))
    p.put(1, at, prom)
    prom_at, at = at, (at + len(prom) + 15) & ~15
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gplay.c'), [f'-DGP_FORCE={force}'])
    syms, cend, bss = cobj.link(p, obj, at, (2, bss_at), externs={'GP_PROM_TAB': (1, prom_at)}, limit=limit)
    assert bss <= GP_BSS, hex(bss)                  # (patch.py: GP_BSS: the reserves' state, GD 16, GP_ST)
    keys = ('RSZ', 'GT_N', 'O_N', 'O_T', 'O_SPEC', 'O_MV', 'MSZ', 'GD_N')
    lay = dict(zip(keys, struct.unpack(f'<{len(keys)}I', p.get(1, syms['GP_LAYOUT'][1], 4 * len(keys)))))
    keys = ('O_MGR', 'O_WEEK', 'O_MDIV', 'O_GT', 'O_SIM', 'KO_SIZE', 'ST_KO', 'KO_SEAS', 'KO_CID', 'KO_N', 'KO_TEAM',
            'KO_BYE', 'KO_CON', 'ST_SIZE', 'LOG_SIZE', 'KO_SLOT')
    lay.update(zip(keys, struct.unpack(f'<{len(keys)}I', p.get(1, syms['GP_LAYOUT2'][1], 4 * len(keys)))))
    assert lay['ST_SIZE'] == GP_ST_SIZE, lay['ST_SIZE']             # (engine.save_item('GP'): patch.py)
    import mkseason
    sel = mkseason._hook_sites(p)[3]
    d2 = p.le.obj_bytes(2)
    lo = d2.find(mkseason.AU_CUP_SIG)                       # the contests' header: the game's Australian cup's
    assert lo >= 0 and d2.count(mkseason.AU_CUP_SIG) == 1
    h = bytearray(d2[lo:lo + 14])
    h[8], h[11], h[13] = 1, 0, 1                            # (no draw, no away goals)
    p.put(*syms['GP_HDR'], bytes(h))
    import sacups
    p.put(*syms['GP_HDR2'], bytes(d2[sacups.unique(d2, sacups.EUROCUP_HDR):][:0x27]))   # (group contests: type 2)
    s = careerworld.SITES
    tab_src, tab_syms = table_lines(tables)
    symbols = {k: (0, v) for k, v in lay.items()}
    symbols.update(tab_syms)
    symbols.update({k: syms[k] for k in ('GP_IN', 'GP_OUT', 'gp_season', 'gp_keep', 'GP_ST', 'GP_LOG', 'GP_NM', 'GP_DIYP', 'GP_K',
                                         'GP_W', 'GP_SKIP', 'GP_RB', 'GP_A', 'GP_B', 'GP_CID', 'GP_SEAS', 'GP_DIV',
                                         'GP_PT', 'GP_PL', 'gp_need', 'gp_simkeep', 'gp_restore', 'gp_lend_c', 'gp_ours_c',
                                         'gp_perm_c', 'gp_rec_c', 'gp_draw_c', 'gp_played_c', 'gp_end_c',
                                         'gp_build_c', 'GP_BPIC')})
    symbols.update({'A0R': (2, r['A0']), 'A1R': (2, r['A0'] + 4), 'A2R': (2, r['A0'] + 8),
                    'A4R': (2, r['A0'] + 16), 'D7R': (2, r['D7']), 'D0R': (2, r['A0'] - 32), 'D1R': (2, r['A0'] - 28),
                    'D2R': (2, r['A0'] - 24), 'SLT': s['slt'], 'SLTCOPY': s['sltcopy'],
                    'WORLD_BYTE': (0, careerworld.WORLD_BYTE), 'DIY': (2, diy), 'NCW': (2, diy), 'SELTEAMS': (2, sel),
                    'SP_ST': (0, split.ST), 'SP_KEEP': (0, split.OFF['h2h']), 'SP_MAGIC': (0, split.MAGIC),
                    'CAREERTEAM': (2, ct), 'ANIM_REL': (2, rel), 'ANIM_PRO': (2, pro),
                    'GP_CAP_NEXT': (1, tgt(cap)), 'GP_END_NEXT': (1, tgt(end_site)),
                    'GP_LEND_NEXT': (1, tgt(ps['lend'][0])), 'GP_SSIM_NEXT': (1, tgt(ps['ssim'])),
                    'GP_DRAW_NEXT': (1, tgt(ps['draw'])),
                    'C8B2D3': (1, sacups.SITES['c8b2d3']), 'C8EE5D': (1, ps['tail']), 'D8CAA': (2, ps['d8caa']),
                    'D6CDC': (2, ps['d6cdc']), 'CFB': (2, ps['cfb']), 'CAL': (2, ps['cal']), 'CAL_CUR': (2, ps['cal_cur']),
                    'SLOT4': (2, ps['slot4']), 'LIST4': (2, ps['list4']), 'W11F9CC': (2, ps['w11f9cc']),
                    'F846': (2, ps['f846']), 'SAVESEL': (1, ps['savesel']), 'RESTSEL': (1, ps['restsel']),
                    'C3ABB2': (1, ps['c3abb2']), 'NC_T': (1, lib97.LABELS['NC_T']), 'SDX_N': (0, 9),
                    'SEASONPLAYING': (2, s['season']),
                    'BAL': (0, pgroups.BALANCE), 'GAMETYPE': split.sites(p)['GAMETYPE'], 'NSUM': (0, bigtables.LIMIT if bigtables.ON[0] else 2000)})
    sk = _sack_sites(p)
    adv, adv_calls = _adv_sites(p)
    symbols['C8EA82'] = (1, adv)
    symbols.update({k: (2, sk[k]) for k in ('CURMSG', 'SACKED')})
    symbols.update({'MSG_NORENEW': (0, sk['msg']), 'SHOWCHAIR': (1, sk['show']), 'C3C07C': (1, sk['c3c07c'])})
    symbols.update({f'EUW{i}': (2, a) for i, a in enumerate(sk['euw'])})
    symbols.update({'DA11B': (2, sk['da11b']), 'GETSEASON': (1, sk['getseason']), 'SEASREC': (2, sk['seasrec'])})
    symbols.update({k: syms[k] for k in ('GP_CFB', 'GP_LG', 'GP_RST', 'GP_RIT', 'GP_SEL', 'GP_MGR', 'GP_WORLD', 'GP_SLT',
                                         'gp_sack_c', 'gp_forcecfb', 'gp_pwin_c', 'gp_adv_c', 'GP_WK', 'GP_TH',
                                         'gp_defer_c')})
    symbols['FORCE_ON'] = (0, int(bool(force)))
    rec_dp = p.get(1, ps['rec'], 1) == b'\xe8'                # dplay's `call dp_rec; nop` there, or the game's mov
    symbols['GP_REC_NEXT'] = (1, tgt(ps['rec'])) if rec_dp else (0, 0)
    after = {}                                              # 4.0 ARG: a stage title's knockout built after its stage
    for _, _, spec in tables:                               # (engine.after_stage: split calls it, pushad / popad)
        for i, name in BUILD_AFTER.get(spec, []):
            assert after.setdefault(name, i) == i, f'build_after {name}: two play-off indices'
    symbols['SP_WEEK'] = (2, split.sites(p)['WEEK'])
    stubs = ''.join(f'ba_{name}:\n    mov dword [GP_BPI], {i}\n    movzx eax, byte [SP_WEEK]\n'
                    f'    mov [GP_BWEEK], eax\n    jmp gp_defer\n' for name, i in sorted(after.items()))
                                                            # (deferred to the calendar advance, gp_adv: after_stage
                                                            # runs inside the league's match day, DIY = the league)
    asm = (ASM.replace('jmp GP_REC_NEXT', 'jmp GP_REC_NEXT' if rec_dp else 'jmp gp_recmov') + tab_src + '\n'
           + names_lines(tables, area, lang) + '\n' + stubs)
    glue = (cend + 15) & ~15
    code, fix = nasmcave.assemble(asm, glue, symbols)
    lab = nasmcave.labels(asm, glue, symbols)
    assert glue + len(code) <= limit, hex(glue + len(code))
    p.put(1, glue, code)
    import engine
    for name in after:
        engine.CALL_AT[name] = (1, lab[f'ba_{name}'])         # (split.late binds the stage's callback to it)
    for off, tobj, toff in fix:
        cobj.add_ptr(p, glue + off, tobj, toff)
    for site, target in ((cap, 'gp_cap'), (end_site, 'gp_end')) if tables else ():   # (relative calls: no fixups;
        p.put(1, site + 1, struct.pack('<i', lab[target] - (site + 5)))                # none: only pg_season)
    if tables and area is not None:                         # the playable play-offs (chained before dplay's hooks)
        for site, target in ((ps['lend'][0], 'gp_lend'), (ps['lend'][1], 'gp_lend'), (ps['ssim'], 'gp_ssim'),
                             (ps['draw'], 'gp_draw')):
            p.put(1, site + 1, struct.pack('<i', lab[target] - (site + 5)))
        if rec_dp:
            p.put(1, ps['rec'] + 1, struct.pack('<i', lab['gp_rec'] - (ps['rec'] + 5)))
        else:
            p.remove(1, ps['rec'] + 2)                       # mov ax, [dseg_11F9CC] (6 B) -> call gp_rec; nop
            p.put(1, ps['rec'], b'\xe8' + struct.pack('<i', lab['gp_rec'] - (ps['rec'] + 5)) + b'\x90')
        dpp = lib97.LABELS['NC_DPP']                         # lib97 nc_adv's slot: gp_perm, then dplay's dp_perm
        try:
            nxt = p.target(1, dpp)
            p.remove(1, dpp)
        except (KeyError, IndexError, AssertionError, StopIteration):
            nxt = (1, lab['gp_stc'])
        p.add_ptr(1, dpp, 1, lab['gp_perm'])
        p.add_ptr(1, lab['GP_PNEXT'], *nxt)
        p.add_ptr(1, lib97.LABELS['NC_BYEP'], 1, lab['gp_bye'])   # (bye_find: our contest's byes, its rounds)
        for a in adv_calls:                                  # (the calendar advance: 'then_build')
            assert p.get(1, a, 5) == p.le.obj_bytes(1)[a:a + 5], f'obj1+{a:#x} already hooked'
            p.put(1, a + 1, struct.pack('<i', lab['gp_adv'] - (a + 5)))
        assert p.get(1, sk['site'], 5) == p.le.obj_bytes(1)[sk['site']:sk['site'] + 5], 'the season-end call is hooked'
        p.put(1, sk['site'] + 1, struct.pack('<i', lab['gp_sack'] - (sk['site'] + 5)))   # (the reserve: sacked)
    import uefaq
    if uefaq.LABELS.get('UQ_EPP') and tables:              # a league-phase world: its European play-offs (uefaq.c ep_run)
        p.add_ptr(1, uefaq.LABELS['UQ_EPP'], 1, lab['GP_EPT'])
    assert struct.unpack('<I', p.get(1, syms['RS_STATE_SIZE'][1], 4))[0] == RS_SIZE   # (the engine block's 'RS')
    import ripool
    assert struct.unpack('<I', p.get(1, syms['RI_STATE_SIZE'][1], 4))[0] == ripool.RI_SIZE   # (the engine block's 'RI')
    kolay = dict(zip(('st_ko', 'size', 'slot', 'ntie', 'tw', 'tl', 'team', 'n'),
                     struct.unpack('<8I', p.get(1, syms['GP_KOLAY'][1], 32))))   # (4.0's gp_build glue: GP_ST.ko[0])
    LABELS.update(lab, GP_GS=syms['GP_GS'], GP_KOLAY=kolay, GP_IN=syms['GP_IN'], GP_OUT=syms['GP_OUT'], GP_ST=syms['GP_ST'], GP_LOG=syms['GP_LOG'], layout=lay, pg_season=syms['pg_season'], pg_place=syms['pg_place'], rs_season=syms['rs_season'], gp_stage=syms['gp_stage'], GP_SS=syms['GP_SS'], PR_STATE=syms['PR_STATE'],
                  RS_STATE=syms['RS_STATE'], ri_season=syms['ri_season'], ri_apply=syms['ri_apply'],
                  ri_cache=syms['ri_cache'], RI_STATE=syms['RI_STATE'], RI_MGR=syms['RI_MGR'],
                  RI_RULE=syms['RI_RULE'])
    print(f"exe: knockout play-offs (gplay): {len(tables)} countries, C obj1+{at:#x}..{cend:#x}, glue ..{glue + len(code):#x}, "
          f"GP_IN obj2+{syms['GP_IN'][1]:#x}, state GP_ST obj2+{syms['GP_ST'][1]:#x} ({lay['ST_SIZE']} B), "
          f"log obj2+{syms['GP_LOG'][1]:#x}, .bss {bss:#x}")
    return glue + len(code)
