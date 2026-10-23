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
GPLAY_RLFORCE=code (signed) makes the career club's result in a play-off it is in that code for the season record lines
only (club_res: 1 WINNERS, -100 FINALIST, -101 / -102 semi / quarter-final, -110 - n round n).

pack.json league "ko_playoffs": [{ "key", "names": {lang: [long, short]},
  "kind": "promotion" | "europe" | "placement" | "playout" (the last round's losers go down to loser_div) |
          "stage_title" (4.0 ARG, + "stage": 0 / 1 a tournament's knockout, 2 the Trofeo: its champion and runner-up
          in GP_OUT.sres[stage], not the league's champion; built mid-season by gp_build, never by gp_need) |
          "title" (the champion = the last tie's winner, or the final group's 1st) | "continental" (its winner and
          runner-up take the continental places; the champion stays the table's 1st),
  "entrants": [[div, place] | {"div": d, "best_without_europe": true} | {"league_cup_winner": true, "if_places": [a, b]}
               | {"stage_place": s, "place": a, "div": d} (place a of split stage s's kept table, e.g. an Apertura)
               | {"split_seed": k, "stage": s, "div": d} (Malta: seed k 1..4 of the title decider of kept stage s and
                 the final table, for a 1v4 / 2v3 / final bracket with skip_if_same; gplay.c split_seed)],
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
  "host_by_record": bool (4.0 MLS: 'better' = the better record in the division's table - points, wins, goal
  difference, goals - not the better place: conference tables in one division, the MLS Cup at the better record),
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


def compile_spec(pos, ndiv, league_names=None):
    """pack.json 'ko_playoffs' -> the bytes gplay.c walks (ended by a 0); raises ValueError on a bad entry.
    league_names: the league's names ({lang: [long, short]}): a 'title' play-off's record line by default (the season
    record's '<league> WINNERS' when the career club wins it, gp_pwin_c)."""
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
                if not (0 <= d < ndiv and (0 <= s < 2 or 4 <= s < 8) and a >= 1):   # (4..7: GP_SS)
                    raise ValueError(f'{key}: entrant {e}')
                ents.append((3, d, a, s))
            elif isinstance(e, dict) and 'split_seed' in e:   # 4.0 MLT: seed k of the title decider (gplay.c
                d, s_, k = e.get('div', 0), e.get('stage', 0), e['split_seed']   # split_seed: kept stage s, final table)
                if not (0 <= d < ndiv and 0 <= s_ < 2 and 1 <= k <= 4):
                    raise ValueError(f'{key}: entrant {e}')
                ents.append((6, d, k, s_))
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
        flags = (1 if po.get('skip_qualified') else 0) | (2 if po.get('host_by_record') else 0) | ((win if win > 1 else 0) << 4)
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
    SPEC_NAMES[out] = [(po.get('names') or {}, po.get('key', '?'),
                        po.get('record') or (league_names if po.get('kind') == 'title' else None)) for po in pos]
    SPEC_STAGES[out] = [(po['stage'], po.get('names') or {}, po.get('key', '?')) for po in pos
                        if KINDS.get(po.get('kind')) == 8 and po.get('stage') in (0, 1, 2)]
    keys = [po.get('key') for po in pos]
    for po in pos:                      # 'then_build': the key of the play-off built when this one ends
        if po.get('then_build') is not None and po['then_build'] not in keys:
            raise ValueError(f"{po.get('key', '?')}: then_build {po['then_build']!r}: no such play-off key")
    import rnames
    rn = bytearray()
    for po in pos:
        names = po.get('round_names') or _default_rnames(po)
        if not (isinstance(names, list) and len(names) <= RN_KG and all(x in rnames.KEYS for x in names)):
            raise ValueError(f"{po.get('key')}: round_names: up to {RN_KG} of {' '.join(rnames.KEYS)} (one per game round)")
        rn += bytes(rnames.KEYS[x] for x in names) + bytes(RN_KG - len(names))
    RNAMES[out] = bytes(rn)
    THEN[out] = bytes(keys.index(po['then_build']) + 1 if po.get('then_build') is not None else 0 for po in pos)
    if any(po.get('kind') == 'title' and po['rounds'] and 'group' in po['rounds'][0] for po in pos):
        T2_SPECS.add(out)               # (a group contest played in a career: the engine block's item 'GS')
    BUILD_AFTER[out] = [(i, po['build_after']) for i, po in enumerate(pos) if po.get('build_after')]
    for i, name in BUILD_AFTER[out]:
        if KINDS.get(pos[i].get('kind')) != 8 or not isinstance(name, str):
            raise ValueError(f"{pos[i].get('key', '?')}: build_after (a split stage's 'then' name) needs kind stage_title")
    return out


PLAY_ASM = '''
%if STG_ON
gp_cal:                                 ; 4.0: replaces the career calendar's league row `mov word [esi + 4], 1` (its
    mov word [esi + 4], 1               ; second line hidden): the league day's stage / group short title as its first
                                        ; line (gp_scal_c; the pack title's short form, <= 16 like LIGA PROFESIONAL)
    pushad
    push es
    push ds
    pop es
    cld
    mov eax, [A6R]                      ; (the row: +1 its week)
    movzx eax, byte [eax + 1]
    push eax
    push dword STG_TAB
    mov eax, [SLOTS_]                   ; (slot 0: the league)
    push eax
    call gp_scal_c
    add esp, 12
    pop es
    test eax, eax
    jz .x
    mov esi, [esp + 4]
    mov [esi - 56 + 38], eax            ; (the first line: the league's short name -> the stage's; the second stays hidden)
.x: popad
    ret
%endif

gp_after:                               ; 4.0 after a career load (arg97's arg_load, after ProcessCareerFile)
    call gp_sync
%if CD_ON
    mov eax, [SLOTS_ + 8]               ; (the Coppa D in slot 2: its contest pointer back, ProcessCareerFile left 0)
    test eax, eax
    jz .ns1
    cmp byte [eax + 2Dh], CDS1_ID
    jne .nd
    mov dword [D8CAA + 8], CDS1
    jmp .ns1
.nd:
    call gp_cdmem                       ; (rc4: a Coppa D club with no Coppa D there: ProcessCareerFile rebuilt slot 2's
    jz .ns1                             ; pointer - the C. IT SERIE C - over an empty buffer whose stale winner, a club
    mov dword [D8CAA + 8], 0            ; not loaded after a job change, trapped the season end: no contest, as at
    pushad                              ; the season start)
    mov edi, [SLOTS_ + 8]
    push es
    push ds
    pop es
    cld
    mov ecx, 0B52h
    xor eax, eax
    rep stosb
    pop es
    sub edi, 0B52h
    mov word [edi + 39h], 0FFFFh
    mov ecx, [CD_NM]
    add ecx, STR_BASE_
    mov [edi + 27h], ecx
    popad
.ns1:
%endif
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    xor ebp, ebp                        ; (the career country's play-off names, as gp_sack finds them)
    mov edx, [D8CAA]
    test edx, edx
    jz .nm
    call gp_find
    jz .nm
    sub esi, GP_TAB
    mov eax, esi
    xor edx, edx
    mov ecx, 9
    div ecx
    mov ebp, [GP_NMT + eax * 4]
.nm:
    push dword 0
    call gp_fixload                     ; (phase 0: the knockouts' contest names)
    add esp, 4
    call gp_repoint
    push dword 1
    call gp_fixload                     ; (phase 1: the season records' league lines)
    add esp, 4
    ret

gp_fixload:                             ; [esp + 4] = the phase, ebp = GP_NM or 0
    push es
    push ds
    pop es
    cld
    push dword [esp + 8]
    push dword SLOTS_
    push dword STR_BASE_
    push dword SEASREC
    push ebp
    call gp_fixload_c
    add esp, 20
    pop es
    ret

gp_repoint:                             ; 4.0 after a career load (gp_after): the slot buffers' long-name
    push es                             ; pointers and titles from this exe's contest structs (gp_repoint_c)
    push ds
    pop es
    cld
    movzx eax, word [CAR_DIV]
    push eax
    push dword STR_BASE_
    push dword D8CAA
    push dword SLOTS_
    call gp_repoint_c
    add esp, 16
    pop es
    ret

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
    push eax
    mov eax, [GP_RNT + eax * 4]
    mov [GP_RN], eax
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

gp_calold:                              ; al = a slot: its calendar entries (an earlier contest's, e.g. the Apertura's
    pushad                              ; knockout before the Clausura's) get round byte FEh: cseg_8BC06 finds a round's
    movzx ecx, word [CAL - 4]           ; entry by (slot, round) from the start, and wrote the new contest's career
    mov edi, CAL                        ; match into the old one (the Trofeo never played; a later quit)
.l:
    test ecx, ecx
    jz .x
    cmp [edi], al
    jne .n
    mov byte [edi + 7], 0FEh
.n:
    movzx edx, word [edi + 2]
    test edx, edx
    jz .x
    add edi, edx
    dec ecx
    jmp .l
.x:
    popad
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
    mov al, [esi + KO_SLOT]
    call gp_calold
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
    mov al, 4                           ; (no replay days: a level tie is decided by gp_draw / its level)
    call CAL_NOREPLAY
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
    mov al, 3                           ; (no replay days)
    call CAL_NOREPLAY
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
    cmp dword [GP_LAST], 0              ; (the contest ended here: every later round decided without a match - the
    je .x                               ; game's own last-round path, cseg_28E76's +57h + 1 == +59h: its winner, +55h)
    mov ax, [NCW + 57h]
    inc ax
    mov [NCW + 59h], ax
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
    mov ax, [CAREERTEAM]
    mov [GP_MGR], ax
    mov eax, gp_perm_c
    call gp_c
    mov [GP_NC], eax
    mov eax, [GP_ALIVE]                 ; (the human-clubs count +4Bh by series, not by game: gp_perm_c)
    cmp eax, -1
    je .na
    mov [NCW + 4Bh], ax
.na:
    mov eax, [GP_NC]
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

gp_mrec:                                ; replaces ManagementRecordMenu's `call cseg_39392` (REGISTRO GESTIONE: the
    call C39392                         ; game's season record refresh re-reads lines 3 / 4 from the slot buffers - a
    pushad                              ; line of ours lost its name): ours again (gp_rl, the same lines)
    cmp word [GAMETYPE], 4
    jne .x
    call gp_rl
.x: popad
    ret

gp_rl:                                  ; the season record's extra lines (gp_sack, gp_mrec; career only): GP_MGR,
    mov ax, [CAREERTEAM]                ; GP_SEAS, the career league's names (GP_NM, GP_CMB), the record (GP_REC),
    mov [GP_MGR], ax                    ; gplay.c gp_rlines_c; ZF = 1 when the league is none of ours
    mov al, [SEASONPLAYING]
    mov [GP_SEAS], al
    mov edx, [D8CAA]
    test edx, edx
    jz .r
    call gp_find
    jz .r
    sub esi, GP_TAB
    mov eax, esi
    xor edx, edx
    mov ecx, 9
    div ecx
    mov ecx, [GP_CMT + eax * 4]         ; (its stage titles won together: GP_CMB)
    mov [GP_CMB], ecx
    mov eax, [GP_NMT + eax * 4]
    mov [GP_NM], eax
    pushad
    call GETSEASON                      ; (GetCurrentSeasonPointer: A0)
    popad
    mov eax, [A0R]
    mov [GP_REC], eax
    mov eax, gp_rlines_c                ; (the Poule, ARG's stage titles, a title play-off - written into GP_REC)
    call gp_c
    or esp, esp                         ; (ZF = 0)
.r: ret

gp_job:                                 ; replaces the club job offers' `call AddJobOffer` (cseg_5B705, D0 = the club's
    push eax                            ; team word): no offer from a club whose team file is not a real one - an
    mov al, [D0R]                       ; off-file pool's (ripool RS files: 0FDh; their clubs reach the leagues by
    cmp al, 0FDh                        ; promotion, the record stays in the pool: a job there trapped the next season,
    jae .no                             ; SAN LUIGI 2026-27) or a pseudo file 190..199 (the foreign market's pool,
    cmp al, 190                         ; the continental cups' guests)
    jb .ok
    cmp al, 199
    jbe .no
.ok:
    pop eax
    jmp ADDJOB
.no:
    pop eax
    ret

gp_sack:                                ; replaces SeasonFinished's `call cseg_3C07C` (a club career's season-end
    pushad                              ; screens; cseg_3E55C, the contract check, runs for national selectors only):
    cmp word [GAMETYPE], 4              ; (a group contest won, the Poule: the season record's 4th line = its record
    jne .nr                             ; name, result 1 = WINNERS; no trophy flag)
    call gp_rl
    jz .nr
%if FORCE_ON
    cmp dword [GP_RLPOULE], 0           ; (test builds: the review sees the career club as the slot-3 cup's winner)
    je .nr
    mov ax, [CAREERTEAM]
    mov [DA11B], ax
%endif
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
%if CD_ON
    mov dword [GP_CDT], 0               ; the Coppa Italia Serie D (cd_step_c): a career in its world
    cmp word [GAMETYPE], 4
    jne .ncd
    mov al, [SLT + WORLD_BYTE]
    cmp al, [CD_TAB]
    jne .ncd
    mov dword [GP_CDT], CD_TAB
    mov dword [GP_CDNM], CD_NM
    mov dword [GP_CDD], CD_DT
    mov dword [GP_SLT], SLT             ; (later seasons: the season's Serie D clubs)
    mov ax, [CAREERTEAM]
    mov [GP_MGR], ax
    mov dword [GP_CDFIRST], 0           ; (the world's first season: the real results)
    pushad
    call W_REC
    jz .nf
    mov al, [ebx + 42]
    cmp al, [SEASONPLAYING]
    jne .nf
    mov dword [GP_CDFIRST], 1
.nf:
    popad
    mov dword [GP_CDS1], CDS1 + CDS1_LIST
    mov dword [GP_CDFORCE], CDFORCE_
    mov eax, cd_step_c
    call gp_c
    test eax, eax
    jz .ncd
    cmp eax, 2
    je .s1
    mov dword [GP_BUILT], 1             ; (the career club's tie: slot 4)
    call gp_install
    jmp .ncd
.s1:
    pushad                              ; 4.0: the Coppa D from the 1/32 in slot 2 (CDS1, its list just written), as
    push es                             ; conti's ct_build: the slot's buffer cleared, cseg_8B2D3, no winner yet
    push ds
    pop es
    cld
    mov edi, [SLOTS_ + 8]
    mov ecx, 0B52h
    xor eax, eax
    rep stosb
    pop es
    mov dword [A0R], CDS1
    mov word [D0R], 2
    mov word [D1R], 0
    mov word [D2R], 0
    call C8B2D3
    mov eax, [SLOTS_ + 8]
    mov word [eax + 39h], 0FFFFh
    popad
.ncd:
%endif
    mov eax, gp_adv_c
    call gp_c
    test eax, eax
    jz .x
    dec eax
    mov [GP_BPI], eax
    mov eax, [GP_ADVWK]
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
    dd CD_ST                            ; (the Coppa Italia Serie D's state)
    dd GP_RLN, GP_RLC, GP_REC, GP_CMB, GP_NM, D8CAA   ; (the season record lines: gp_rlines_c's)
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
    mov eax, gp_champ                   ; a title play-off's winner = the champion in the qualifiers' top-9 list
    call gp_c
    movzx ecx, byte [GP_OUT]
    xor ebx, ebx
.m:
    cmp ebx, ecx
    jae .sec
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
.sec:
    mov eax, sec_post                   ; the second teams (gplay.c): holds, next clubs, B teams down
    call gp_c
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
CD_SIZE = 8 + 2 * 168 + 4 + 256 + 8 + 2 * 2 * (41 + 64)   # (sizeof struct cd_state: the engine block's item 'CD')
CD_RNAME = '''
    cmp byte [GP_ST + ST_KO + 6], 9     ; (gp_ko.kind: K_CUPD) a Coppa Italia Serie D tie: rnames.CD_NAMES by CD_ST's
    jne .ncd                            ; round
    movzx ebx, byte [CD_ST + 3]
    cmp ebx, 8
    jae .nb
    mov al, [CD_RN + ebx]
    pop ebx
    stc
    ret
.ncd:'''
CDS1_ID = 0xEF                          # 4.0: the Coppa D's slot-2 knockout (conti.IDS' last, unused there)


def cds1_src(p, cd, rl, rs):
    """The Coppa D from the 1/32 as a game knockout for slot 2 (64 clubs; header weeks = the round records', round
    bytes by legs; names rl / rs; its list written by cd_step_c at the 1/32): nasm source, labels CDS1 / CDS1_LIST."""
    import sacups
    import conti
    world, lfile, tab, nr, nt, cnames, cdt = cd
    assert CDS1_ID == conti.IDS[-1] and len(conti.STRUCTS) + 1 < len(conti.IDS)
    recs = [tab[8 * r:8 * r + 8] for r in range(nr)]
    r32 = next(r for r in range(nr) if recs[r][4] == 32)
    legs = tuple(0x94 if recs[r][2] == 2 else 0x14 for r in range(r32, nr))
    d2 = p.le.obj_bytes(2)
    h = sacups.knockout16(d2[sacups.unique(d2, sacups.CWC_HDR):][:28], CDS1_ID, 64, legs)
    h[3], h[4] = recs[r32][0], recs[nr - 1][1]
    CDS1_ROUNDS[:] = list(range(r32, nr))
    import dplay
    d1 = p.le.obj_bytes(1)
    t, calls, i = dplay._play_sites(p, sacups.regs(d1))['tail'], [], 0
    i = t
    while len(calls) < 5 and i < t + 0x200:             # cseg_8ECAE's tail: cseg_32E15, then the contest's start
        if d1[i] == 0xE8:
            calls.append(i + 5 + struct.unpack_from('<i', d1, i + 1)[0])
            i += 5
        else:
            i += 1
    assert len(calls) == 5, calls
    CDS1_CALLS[:] = calls[1:]
    return ('align 4\nCDS1_START: dd ' + ', '.join(f'C_S1_{k}' for k in range(4)) + ', 0\n'
            + 'align 4\nCDS1: db ' + ', '.join(map(str, h)) + f'\n    dd {rl}, {rs}\n'
            + f'CDS1_LIST equ {len(h) + 8}\n    times 64 dw 0FFFFh\nCDS1_ID equ {CDS1_ID}\n')


CDS1_ROUNDS = []                        # (rnames: the Coppa D rounds the slot-2 contest plays)
CAL1_SITE = []                          # (cseg_3563E's `mov eax, A6`: gp_cal1)
CDS1_CALLS = []                         # (cseg_8ECAE tail's start calls: cseg_8B71C, cseg_27436, cseg_8B8B8, cseg_8B7EA)
CUP12 = '''
gp_cdmem:                               ; ZF = 0 when the career club is a Coppa Italia Serie D entrant (cd_member_c),
    pushad                              ; every register kept
    xor ebx, ebx
    cmp word [GAMETYPE], 4
    jne .r
    mov al, [SLT + WORLD_BYTE]
    cmp al, [CD_TAB]
    jne .r
    mov dword [GP_CDT], CD_TAB
    mov dword [GP_CDD], CD_DT
    mov dword [GP_SLT], SLT
    push es
    push ds
    pop es
    cld
    movzx eax, word [CAREERTEAM]
    push eax
    call CD_MEMBER
    add esp, 4
    pop es
    mov ebx, eax
.r: test ebx, ebx
    popad
    ret

gp_cal1:                                ; 4.0 A: cseg_3563E's `mov eax, A6` (the career calendar's list of entries):
    mov eax, [A6R]                      ; a Coppa D club's COPPA ITALIA entries (slot 1: the game plays the cup
    cmp byte [eax], 1                   ; through them, the club is not in it) are left out of the list (replay
    jne .r                              ; days: lib97 cal_noreplay removes them at the install)
    call gp_cdmem
    jz .r
    inc word [D6R]                      ; (cseg_3570C's next entry, without using a list line)
    mov word [D7R], 0
    movzx ecx, word [eax + 2]
    add eax, ecx
    mov [A6R], eax
    mov [A4R], eax
    add esp, 4
    jmp CAL1_LOOP
.r: ret

gp_vc1:                                 ; 4.0 (rule 11): VISUAL. COMPETIZ.'s `mov eax, [D8CAA + 4]` (slot 1 shown when
    mov eax, [D8CAA + 4]                ; not 0): a Coppa D club does not see the COPPA ITALIA it is not in (the cup is
    test eax, eax                       ; still played for its winner)
    jz .r
    call gp_cdmem
    jz .r
    xor eax, eax
.r: ret

gp_cup12:                               ; 4.0: InitNewSeason's `call cseg_8B2D3` of slots 1 / 2 (the country's cup and
    pushad                              ; league cup): a Coppa Italia Serie D club gets neither (cd_member_c), the slot
    cmp word [GAMETYPE], 4              ; cleared (Davide's Schio: COPPA ITALIA / C. IT SERIE C rows never played)
    jne .game
    cmp word [D0R], 2                   ; (4.0 A: slot 1 stays the COPPA ITALIA - the game plays it through the
    jne .game                           ; calendar and the season end needs its winner; slot 2 becomes the Coppa D's)
    call gp_cdmem
    jz .game
    movzx eax, word [D0R]
    mov dword [D8CAA + eax * 4], 0
    mov edi, [SLOTS_ + eax * 4]         ; (the slot's buffer: no contest - cleared whole, as conti's ct_build: a
    push es                             ; stale buffer kept last season's winner, a club of another Serie D group
    push ds                             ; not loaded after a job change -> the season end's VerifyTeamLoaded int 3,
    pop es                              ; rc4 AVOLA; no winner; its long-name pointer = the Coppa D's: the season
    cld                                 ; record's league-cup line reads COPPA ITALIA SERIE D, TEST 8's CJARLINS)
    mov ecx, 0B52h
    xor eax, eax
    rep stosb
    pop es
    sub edi, 0B52h
    mov word [edi + 39h], 0FFFFh
    mov ecx, [CD_NM]
    add ecx, STR_BASE_
    mov [edi + 27h], ecx
    popad
    ret
.game:
    popad
    jmp C8B2D3
'''
LASTREST = '''
gp_lastrest:                            ; 4.0.1: cseg_8EC2B's loop (careerFinished when no calendar entry left has a match of
    mov esi, [A0R]                      ; the career club, +6) also keeps an unplayed day of the career LEAGUE (slot 0, a
    mov al, [esi + 6]                   ; league in a career): the career club's rest on the last match day of an odd group
    test al, al                         ; (oddtables) or a split's odd group - else FINISH SEASON came a day early, the
    jnz .r                              ; league ended (cseg_8ECAE: gplay's / dplay's play-offs) only at the season end and
    cmp byte [esi], 0                   ; its Poule / play-off was never played; the day is now played as any rest day
    jne .r                              ; (cseg_8E841)
    cmp word [GAMETYPE], 4
    jne .r
    mov al, 1                           ; (slot 0 of a career is its league; the D8CAA test never held: that pointer is
.r:                                     ; the contest definition, its first byte the id - the FR course lost its Poule)
    ret                                 ; (the game's `or al, al / jnz` follows)
'''

GP_RNAME = '''
gp_rname:                               ; rnames' rn_round (an FE contest, RN_CDP): ko[0] of this season in slot 4 ->
    cmp word [GP_ST + ST_KO], 4B47h     ; CF = 1, al = its round's name, else CF = 0 (the game's); every register but
    jne .no                             ; al and the flags kept
    push ebx
    mov bl, [SEASONPLAYING]
    cmp [GP_ST + ST_KO + KO_SEAS], bl
    jne .nb
    cmp byte [GP_ST + ST_KO + KO_SLOT], 0
    je .nb
CD_PART
    mov ebx, [GP_CALDP]                 ; 4.0: a calendar being built (rnames RN_CALD = its entry's round + 1): that
    test ebx, ebx                       ; round, from the contest's first (the current one while it is built)
    jz .cur
    mov ebx, [ebx]
    test ebx, ebx
    jz .cur
    dec ebx
    push eax
    movzx eax, byte [GP_ST + ST_KO + KO_GCUR]
    add ebx, eax
    pop eax
    jmp .rn
.cur:
    movzx ebx, byte [GP_ST + ST_KO + KO_GCUR]   ; the pack's 'round_names' by game round (GP_ST.rn, gplay.c)
.rn:
    cmp ebx, 12
    jae .nb
    mov bl, [GP_ST + ST_RN + ebx]
    test bl, bl
    jz .nb
    mov al, bl
    pop ebx
    stc
    ret
.nb:
    pop ebx
.no:
    clc
    ret
GP_CALDP: dd 0                          ; (rnames.RN_CALD's address, or 0)
'''
def _default_rnames(po):
    """A knockout play-off without 'round_names' (Serie D's single-match semi-finals and final): its rounds named from
    the end - F, SF, QF, R16 - when it ends in one tie and has no group / best-of-three round; else none (the game's)."""
    rs = po.get('rounds') or []
    if not rs or len(rs) > 4 or len(rs[-1].get('ties') or []) != 1 or \
            any('group' in r or r.get('legs', 1) not in (1, 2) or not r.get('ties') for r in rs):
        return []
    return ['R16', 'QF', 'SF', 'F'][4 - len(rs):]


RNAMES = {}              # compile_spec's output -> per play-off KG bytes: its game rounds' rnames indices (0: the game's)
RN_KG = 12               # (gplay.c KG)
SPEC_STAGES = {}         # compile_spec's output -> its stage titles (kind stage_title): [(stage, names, key)]
REC_PX = 144             # the season record's competition column (ManagementRecordMenu: x 0, width 144, small font)
AND = {'it': 'E', 'en': 'AND', 'fr': 'ET', 'de': 'UND'}


def combined(parts, lang):
    """Several stage titles won in one season -> one record line (Davide 2026-10-20: 'TORNEO APERTURA E CLAUSURA'
    style, fitted to REC_PX): parts = [(long, short)] in stage order. The long names with their shared first words
    once, else the short names, 'A, B E C', else 'A/B/C', the same with their first words only, else each short name
    cut (a '.' after it) until it fits."""
    import complist
    conj = AND.get(lang, 'AND')
    join = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + f' {conj} ' + xs[-1]
    cands = []
    words = [p[0].split() for p in parts]
    k = 0
    while all(len(w) > k + 1 and w[k] == words[0][k] for w in words):
        k += 1
    if k:
        cands.append(' '.join(words[0][:k]) + ' ' + join([' '.join(w[k:]) for w in words]))
    shorts = [p[1] for p in parts]
    first = [x.split()[0] for x in shorts]             # (their first words: 'TROFEO CAMP.' -> 'TROFEO')
    cands += [join(shorts), '/'.join(shorts), join(first), '/'.join(first)]
    for c in cands:
        if complist.px(c) <= REC_PX:
            return c
    n = max(len(x) for x in shorts)
    while n > 3:
        n -= 1
        c = '/'.join(x if len(x) <= n else x[:n].rstrip() + '.' for x in shorts)
        if complist.px(c) <= REC_PX:
            return c
    raise ValueError(f'combined stage titles {shorts}: no name fits {REC_PX} px')


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


def _top9(p):
    """cseg_927A2 (the season end's top 9 of a country's top division): `mov [A1], offset records; mov [A3], offset
    team words; mov [A2], offset DIY` -> ((obj, records), (obj, team words))."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    pk = lambda x: re.escape(struct.pack('<I', x))
    m = [x.start() for x in re.finditer(rb'\xc7\x05' + pk(r['A0'] + 4) + rb'.{4}\xc7\x05' + pk(r['A0'] + 12) + rb'.{4}'
                                        rb'\xc7\x05' + pk(r['A0'] + 8), d1, re.S)]
    assert len(m) == 2, m                       # (the first: cseg_927A2; the second: another list of the season end)
    return p.target(1, m[0] + 6), p.target(1, m[0] + 16)
GP_PAGES = 13            # obj1 pages for the C code + glue + specs (World 2026-27's 20 countries; gplay-play; 4.0 ARG: 7; the record lines: 12; longtable's code: 13)
GP_ST_SIZE = 2048       # (sizeof struct gp_state: the engine block's item 'GP', patch.py)
WN_SIZE = 4 + 4 * 40    # (sizeof struct wn_state: the engine block's item 'WN', the WINNERS page's last season)
GP_BSS = 0x6000          # the C .bss pages (obj2 after careerworld's BSS): GP_IN at GT 32 / GD 16, GP_SS, PR, RS, GP_ST, RI, PS


def _cardiv(p):
    """dseg_D6CDC: the career club's division (CareerGameListCommon's league row: [names + D6CDC * 8 + 4])."""
    d1 = p.le.obj_bytes(1)
    m = [x.start() for x in re.finditer(rb'\x66\xa1....\x66\xa3....\x66\xc1\x25....\x03\x8b\x35....\x0f\xb7\x1d....'
                                     rb'\x8b\x44\x1e\x04', d1, re.S)]
    assert len(m) == 1, ('the league row: mov ax, [D6CDC] ... mov eax, [esi+ebx+4]', [hex(x) for x in m])
    return p.target(1, m[0] + 2)[1]


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


def _job_site(p):
    """cseg_5B705's club job offer: `pop D0; call AddJobOffer` (AddJobOffer: `cmp numNewJobOffers, 5; jz ...;
    mov ax, numNewJobOffers; mov [D2], ax`) -> (site of the call, AddJobOffer)."""
    d1 = p.le.obj_bytes(1)
    f = [m.start() for m in re.finditer(rb'\x66\x83\x3d.{4}\x05\x0f\x84.{4}\x66\xa1.{4}\x66\xa3', d1, re.S)]
    hit = [(i, a) for a in f for i in range(len(d1) - 5)
           if d1[i] == 0xE8 and i + 5 + struct.unpack_from('<i', d1, i + 1)[0] == a and d1[i - 6:i - 4] == b'\x8f\x05']
    assert len(hit) == 1, hit
    return hit[0]


def _mrec_site(p):
    """ManagementRecordMenu's `call cseg_39392` (if not youreSacked: the season record refresh - cseg_3D7CB, the
    trophy flags, lines 3 / 4 re-read from the slot buffers - then `mov A6, management_record_menu`): (site, cseg_39392)."""
    d1 = p.le.obj_bytes(1)
    f = [m.start() for m in re.finditer(rb'\x66\x83\x3d.{4}\x04\x0f\x85.{4}\xe8.{4}\xe8', d1, re.S)]
    assert len(f) == 1, f
    calls = [m.start() for m in re.finditer(rb'\x66\x0b\xc0\x75\x05\xe8(.{4})\xc7\x05', d1, re.S)
             if m.start() + 10 + struct.unpack('<i', m.group(1))[0] == f[0]]
    assert len(calls) == 1, calls
    return calls[0] + 5, f[0]


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
    multi = [len(SPEC_STAGES.get(spec, [])) >= 2 for _, _, spec in tables]       # (stage titles won together: one
    lines += ['GP_CMT:'] + [f'    dd GPC{i}' if multi[i] else '    dd 0' for i in range(len(tables))]   # name per mask
    for i, (_, _, spec) in enumerate(tables):                                     # of stages 0..2; only where there
        if not multi[i]:                                                          # are two)
            continue
        st = {stg: _name(names, lang, key) for stg, names, key in SPEC_STAGES.get(spec, [])}
        row = []
        for m in range(8):
            ok = bin(m).count('1') >= 2 and all(x in st for x in range(3) if m & 1 << x) and area
            got = [st[x] for x in range(3) if m & 1 << x] if ok else []
            row.append(area.add(combined([(a.decode('latin-1'), b.decode('latin-1')) for a, b in got], lang)
                                .encode('latin-1') + b'\0') - sacups.STR_BASE if ok else 0)
        lines.append(f'GPC{i}: dd ' + ', '.join(map(str, row)))
    lines += ['GP_THT:'] + [f'    dd GPT{i}' for i in range(len(tables))]      # ('then_build' per play-off)
    for i, (_, _, spec) in enumerate(tables):
        lines.append(f'GPT{i}: db ' + ', '.join(str(b) for b in (THEN.get(spec) or b'') + b'\0'))
    lines += ['GP_RNT:'] + [f'    dd GPR{i}' for i in range(len(tables))]      # ('round_names': KG per play-off)
    for i, (_, _, spec) in enumerate(tables):
        lines.append(f'GPR{i}: db ' + ', '.join(str(b) for b in (RNAMES.get(spec) or b'') + b'\0'))
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
    if os.environ.get('GPLAY_KOFORCE'):                     # (test builds: the career club's knockout ties forced)
        print(f"exe: GPLAY_KOFORCE={os.environ['GPLAY_KOFORCE']} (test build: the career club {'loses' if os.environ['GPLAY_KOFORCE'] == '1' else 'wins'} "
              'its played knockout ties)')
    import mkseason as mks
    prom = mks.promedio_table()                     # Argentina's promedio history (GP_PROM_TAB) before the C code
    assert not any(p.get(1, at, len(prom)))
    p.put(1, at, prom)
    prom_at, at = at, (at + len(prom) + 15) & ~15
    sec = mks.second_table()                        # the second teams' table (SEC_TAB) before the C code
    assert not any(p.get(1, at, len(sec)))
    p.put(1, at, sec)
    sec_at, at = at, (at + len(sec) + 15) & ~15
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gplay.c'), [f'-DGP_FORCE={force}', f"-DSEC_FORCE={int(os.environ.get('SEC_FORCE') or 0)}",
                                f"-DSEC_FORCE_B={int(os.environ.get('SEC_FORCE_B') or 0xFFFF)}",
                                f"-DGP_RLFORCE={int(os.environ.get('GPLAY_RLFORCE') or 0)}",
                                f"-DGP_KOFORCE={int(os.environ.get('GPLAY_KOFORCE') or 0)}"]
                               + (['-DHDR_TEST'] if os.environ.get('HDR_TEST') else []))   # (test builds: GROUP n headers)
    top_r, top_w = _top9(p)                          # (cseg_927A2's top-9 list: gp_champ)
    import mkseason                             # 4.0 group headers' labels (zones.header_labels, the exe language)
    import zones
    hlt = area.add(zones.header_labels(lang, [e if os.sep in e else os.path.join(mkseason.PACKS, e)
                                              for e in mkseason.ENABLED]))
    syms, cend, bss = cobj.link(p, obj, at, (2, bss_at), externs={'GP_PROM_TAB': (1, prom_at), 'SEC_TAB': (1, sec_at),
                                                                   'GP_TOPR': top_r, 'GP_TOPW': top_w,
                                                                   'SEC_SLT': careerworld.SITES['slt'],
                                                                   'SEC_COPY': careerworld.SITES['sltcopy'],
                                                                   'GP_HLT': (2, hlt)}, limit=limit)
    assert bss <= GP_BSS, hex(bss)                  # (patch.py: GP_BSS: the reserves' state, GD 16, GP_ST)
    keys = ('RSZ', 'GT_N', 'O_N', 'O_T', 'O_SPEC', 'O_MV', 'MSZ', 'GD_N')
    lay = dict(zip(keys, struct.unpack(f'<{len(keys)}I', p.get(1, syms['GP_LAYOUT'][1], 4 * len(keys)))))
    keys = ('O_MGR', 'O_WEEK', 'O_MDIV', 'O_GT', 'O_SIM', 'KO_SIZE', 'ST_KO', 'KO_SEAS', 'KO_CID', 'KO_N', 'KO_TEAM',
            'KO_BYE', 'KO_CON', 'ST_SIZE', 'LOG_SIZE', 'KO_SLOT', 'ST_RN', 'KO_GCUR')
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
    symbols.update({k: syms[k] for k in ('GP_IN', 'GP_OUT', 'gp_season', 'gp_champ', 'gp_keep', 'GP_ST', 'GP_LOG', 'GP_NM', 'GP_DIYP', 'GP_K',
                                         'GP_W', 'GP_SKIP', 'GP_RB', 'GP_ALIVE', 'GP_LAST', 'GP_A', 'GP_B', 'GP_CID', 'GP_SEAS', 'GP_DIV',
                                         'GP_PT', 'GP_PL', 'gp_need', 'gp_simkeep', 'gp_restore', 'gp_lend_c', 'gp_ours_c',
                                         'gp_perm_c', 'gp_rec_c', 'gp_draw_c', 'gp_played_c', 'gp_end_c',
                                         'gp_build_c', 'GP_BPIC', 'sec_post')})
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
                    'CAL_NOREPLAY': (1, lib97.LABELS['cal_noreplay']),
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
    mrec, c39392 = _mrec_site(p)
    symbols['C39392'] = (1, c39392)
    job, addjob = _job_site(p)
    symbols['ADDJOB'] = (1, addjob)
    symbols.update({k: syms[k] for k in ('GP_CFB', 'GP_LG', 'GP_RST', 'GP_RIT', 'GP_SEL', 'GP_MGR', 'GP_WORLD', 'GP_SLT',
                                         'gp_sack_c', 'gp_forcecfb', 'gp_pwin_c', 'gp_rlines_c', 'GP_RLN', 'GP_RLC', 'GP_RLPOULE', 'GP_REC', 'GP_CMB', 'gp_adv_c', 'GP_ADVWK', 'GP_WK', 'GP_TH', 'GP_RN',
                                         'gp_defer_c', 'cd_step_c', 'gp_scal_c', 'gp_repoint_c', 'gp_fixload_c', 'CD_ST', 'GP_CDT', 'GP_CDNM', 'GP_CDD',
                                         'GP_CDFIRST')})
    symbols['CD_MEMBER'] = syms['cd_member_c']
    symbols['GP_CDS1'] = syms['GP_CDS1']
    symbols['GP_CDFORCE'] = syms['GP_CDFORCE']
    symbols['CDFORCE_'] = (0, int(os.environ.get('CD_FORCE') or 0))   # (test builds only)
    symbols['FORCE_ON'] = (0, int(bool(force)))
    import longtable                                          # 4.0 stage titles (table, calendar): the table in area
    stg = longtable.stage_table(lang, b'\0' * 2 + struct.pack('<4HIH', split.ST, split.ST + split.OFF['frozen'],
                                                                  split.ST + split.OFF['grp'], split.MAGIC, 0,
                                                                  split.WEEKS)) if area is not None else None
    cal_site = None
    if stg:
        import dplay
        stg_tab = area.add(stg)
        p.add_ptr(2, stg_tab + 10, 2, dplay._sites(p)[5])     # (the header's career-team pointer)
        d1 = p.le.obj_bytes(1)
        hits = [m.start() + 11 for m in re.finditer(rb'\x66\x83\x46\x16\x08\x8b\x35....\x66\xc7\x46\x04\x01\x00', d1, re.S)]
        assert len(hits) == 2, ('career calendar rows', hits)
        cal_site = hits[:1]                                   # (CareerGameListCommon's league row, cseg_362DE; the
                                                              # second is another row kind: its esi - 56 is a team)
        symbols.update({'STG_TAB': (2, stg_tab), 'SLOTS_': (2, split.sites(p)['SLOTS']), 'A6R': (2, r['A0'] + 24)})
        LABELS['STG_TAB'] = (2, stg_tab)
    symbols['STG_ON'] = (0, int(bool(stg)))
    import sacups
    symbols.update({'SLOTS_': (2, split.sites(p)['SLOTS']), 'STR_BASE_': (2, sacups.STR_BASE), 'CAR_DIV': (2, _cardiv(p))})
    rec_dp = p.get(1, ps['rec'], 1) == b'\xe8'                # dplay's `call dp_rec; nop` there, or the game's mov
    symbols['GP_REC_NEXT'] = (1, tgt(ps['rec'])) if rec_dp else (0, 0)
    after = {}                                              # 4.0 ARG: a stage title's knockout built after its stage
    for _, _, spec in tables:                               # (engine.after_stage: split calls it, pushad / popad)
        for i, name in BUILD_AFTER.get(spec, []):
            assert after.setdefault(name, i) == i, f'build_after {name}: two play-off indices'
    symbols['SP_WEEK'] = (2, split.sites(p)['WEEK'])
    symbols.update({'SP_STO': (0, split.ST), 'SP_MAGIC_': (0, split.MAGIC), 'SP_WEEKS': (0, split.WEEKS)})
                                                            # (SP_STO, not SP_MAGIC: gp_keep pushes SP_MAGIC = the
                                                            # magic value; redefined as the offset, Malta's kept
                                                            # Opening table was refused and its decider never built)
    stubs = ''.join(f'ba_{name}:\n    mov dword [GP_BPI], {i}\n    call gp_lastwk\n'
                    f'    mov [GP_BWEEK], eax\n    jmp gp_defer\n' for name, i in sorted(after.items()))
    stubs += '''gp_lastwk:                              ; 4.0: eax = the week of the league's last played day (split's weeks table in
    movzx eax, byte [SP_WEEK]           ; DIY: ARG's Apertura knockout starts in the gap before the Clausura, not after
    push ecx                            ; its first day - Davide 2026-10-20), else the game's week
    cmp word [DIY + SP_STO], SP_MAGIC_
    jne .x
    movzx ecx, word [DIY + 1C1h]
    jecxz .x
    movzx eax, byte [DIY + SP_WEEKS + ecx - 1]
.x: pop ecx
    ret
'''
                                                            # (deferred to the calendar advance, gp_adv: after_stage
                                                            # runs inside the league's match day, DIY = the league)
    cds = mkseason.cupd_tables() if mkseason.worlds() else []
    assert len(cds) <= 1, 'cupd: one world with a Coppa Italia Serie D'
    symbols['CD_ON'] = (0, int(bool(cds)))
    cd_src = ''
    if cds:                                                   # (cupd.py: CD_TAB, its names)
        world, lfile, tab, nr, nt, cnames, cdt = cds[0]
        import careerworld as cw_
        symbols['W_REC'] = (1, cw_.LABELS['w_rec'])
        long_, short = _name(cnames, lang, 'cup_d')
        rl, rs = (area.add(x + b'\0') - sacups.STR_BASE if area else 0 for x in (long_, short))
        import rnames
        cd_src = (f'CD_TAB: db {world}, {nr}, {lfile}, 0\n    db ' + ', '.join(str(b) for b in tab)
                  + f'\nCD_NM: dd {rl}, {rs}\nCD_DT: db ' + ', '.join(str(b) for b in cdt)
                  + '\nCD_RN: db ' + ', '.join(str(x) for x in rnames.CD_NAMES) + '\n')
    if cds:
        a0_ = r['A0']
        pk_ = lambda x: re.escape(struct.pack('<I', x))
        d1c = p.le.obj_bytes(1)
        ms = [m for m in re.finditer(rb'\xa1' + pk_(a0_ + 24) + rb'\x8b\x35(.{4})\x89\x06\x83\x05(.{4})\x04', d1c, re.S)
              if m.group(1) == m.group(2)]
        assert len(ms) == 1 and d1c[ms[0].start() - 19:ms[0].start() - 17] == b'\x66\xa1', ms
        CAL1_SITE[:] = [ms[0].start()]
        symbols.update({'CAL1_LOOP': (1, ms[0].start() - 19), 'D6R': (2, a0_ - 8), 'D7R': (2, a0_ - 4),
                        'A4R': (2, a0_ + 16)})
        cd_src += CUP12 + cds1_src(p, cds[0], rl, rs)
        symbols.update({f'C_S1_{k}': (1, c) for k, c in enumerate(CDS1_CALLS)})
    cd_src += nasmcave.sub(GP_RNAME, 'CD_PART', CD_RNAME if cds else '')
    asm = (nasmcave.sub(ASM, 'jmp GP_REC_NEXT', 'jmp GP_REC_NEXT' if rec_dp else 'jmp gp_recmov') + tab_src + '\n'
           + names_lines(tables, area, lang) + '\n' + stubs + cd_src + LASTREST)
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
    if cds and not os.environ.get('NO_CUP12'):               # InitNewSeason's slot-1 / slot-2 installs -> gp_cup12 (NO_CUP12: test builds)
        d1o = p.le.obj_bytes(1)
        d0 = struct.pack('<I', r['A0'] - 32)
        sites = [i for i in range(len(d1o) - 5) if d1o[i] == 0xE8 and
                 i + 5 + struct.unpack_from('<i', d1o, i + 1)[0] == sacups.SITES['c8b2d3'] and
                 d1o[i - 6:i] == b'\xff\x35' + struct.pack('<I', r['A0'] + 24) and   # (push A6: InitNewSeason's)
                 any(d1o[j:j + 9] == b'\x66\xc7\x05' + d0 + bytes([k, 0]) for j in range(i - 40, i) for k in (1, 2))]
        assert len(sites) == 4, [hex(x) for x in sites]       # (InitNewSeason; ProcessCareerFile's rebuild after a load)
        for site in sites:
            assert p.get(1, site, 1) == b'\xe8', hex(site)
            p.put(1, site + 1, struct.pack('<i', lab['gp_cup12'] - (site + 5)))
        d1v = p.le.obj_bytes(1)                               # VISUAL. COMPETIZ. (cseg_3760C): its slot-1 test
        vc = [m.start() for m in re.finditer(rb'\xa1' + re.escape(struct.pack('<I', ps['d8caa'] + 4)) +
                                             rb'\x0b\xc0\x0f\x85', d1v)]
        assert len(vc) == 2, vc                               # (the first: SquadInit's)
        p.remove(1, vc[1] + 1)
        p.put(1, vc[1], b'\xe8' + struct.pack('<i', lab['gp_vc1'] - (vc[1] + 5)))
        cal1 = CAL1_SITE[0]                                   # cseg_3563E's `mov eax, A6` (5 B, a fixup) -> call
        p.remove(1, cal1 + 1)
        p.put(1, cal1, b'\xe8' + struct.pack('<i', lab['gp_cal1'] - (cal1 + 5)))
    d1o = p.le.obj_bytes(1)                                   # cseg_8EC2B's loop: `mov esi, [A0] / mov al, [esi+6]` (9 B,
    a0b = struct.pack('<I', r['A0'])                          # A0's fixup) -> call gp_lastrest + 4 nops
    lr = [m.start() + 13 for m in re.finditer(re.escape(b'\x8b\x35' + a0b + b'\x8a\x46\x04\x0a\xc0\x75') + b'.' +
                                              re.escape(b'\x8b\x35' + a0b + b'\x8a\x46\x06\x0a\xc0\x75'), d1o, re.S)]
    assert len(lr) == 1 and bytes(p.get(1, lr[0], 9)) == d1o[lr[0]:lr[0] + 9], [hex(x) for x in lr]
    p.remove(1, lr[0] + 2)
    p.put(1, lr[0], b'\xe8' + struct.pack('<i', lab['gp_lastrest'] - (lr[0] + 5)) + b'\x90' * 4)
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
        import rnames
        if 'gp_rname' in lab and rnames.LABELS.get('RN_CDP'):   # (the Coppa D's and the packs' round names)
            p.add_ptr(1, rnames.LABELS['RN_CDP'], 1, lab['gp_rname'])
            if 'GP_CALDP' in lab and rnames.LABELS.get('RN_CALD'):
                p.add_ptr(1, lab['GP_CALDP'], 1, rnames.LABELS['RN_CALD'])
        for a in adv_calls:                                  # (the calendar advance: 'then_build')
            assert p.get(1, a, 5) == p.le.obj_bytes(1)[a:a + 5], f'obj1+{a:#x} already hooked'
            p.put(1, a + 1, struct.pack('<i', lab['gp_adv'] - (a + 5)))
        assert p.get(1, job, 5) == p.le.obj_bytes(1)[job:job + 5], 'the club job offers call is hooked'
        p.put(1, job + 1, struct.pack('<i', lab['gp_job'] - (job + 5)))   # (no job at an off-file / pool club)
        assert p.get(1, mrec, 5) == p.le.obj_bytes(1)[mrec:mrec + 5], 'ManagementRecordMenu call is hooked'
        p.put(1, mrec + 1, struct.pack('<i', lab['gp_mrec'] - (mrec + 5)))   # (REGISTRO GESTIONE: our lines again)
        assert p.get(1, sk['site'], 5) == p.le.obj_bytes(1)[sk['site']:sk['site'] + 5], 'the season-end call is hooked'
        p.put(1, sk['site'] + 1, struct.pack('<i', lab['gp_sack'] - (sk['site'] + 5)))   # (the reserve: sacked)
    for cs in cal_site or []:                                 # (6 bytes, no address: no fixup)
        assert bytes(p.get(1, cs, 6)) == b'\x66\xc7\x46\x04\x01\x00'
        p.put(1, cs, b'\xe8' + struct.pack('<i', lab['gp_cal'] - (cs + 5)) + b'\x90')
    import uefaq
    if uefaq.LABELS.get('UQ_EPP') and tables:              # a league-phase world: its European play-offs (uefaq.c ep_run)
        p.add_ptr(1, uefaq.LABELS['UQ_EPP'], 1, lab['GP_EPT'])
    assert struct.unpack('<I', p.get(1, syms['RS_STATE_SIZE'][1], 4))[0] == RS_SIZE   # (the engine block's 'RS')
    import ripool
    assert struct.unpack('<I', p.get(1, syms['RI_STATE_SIZE'][1], 4))[0] == ripool.RI_SIZE   # (the engine block's 'RI')
    kolay = dict(zip(('st_ko', 'size', 'slot', 'ntie', 'tw', 'tl', 'team', 'n'),
                     struct.unpack('<8I', p.get(1, syms['GP_KOLAY'][1], 32))))   # (4.0's gp_build glue: GP_ST.ko[0])
    LABELS.update(lab, GP_TOPW=top_w, GP_TOPR=top_r, CD_ST=syms['CD_ST'], GP_GS=syms['GP_GS'], GP_KOLAY=kolay, GP_IN=syms['GP_IN'], GP_OUT=syms['GP_OUT'], GP_ST=syms['GP_ST'], GP_LOG=syms['GP_LOG'], layout=lay, pg_season=syms['pg_season'], pg_place=syms['pg_place'], rs_season=syms['rs_season'], gp_stage=syms['gp_stage'], gp_overall=syms['gp_overall'], gp_stitle_c=syms['gp_stitle_c'], gp_hplan_c=syms['gp_hplan_c'], gp_hlabel_c=syms['gp_hlabel_c'], GP_HP=syms['GP_HP'], GP_HGP=syms['GP_HGP'], GP_HG=syms['GP_HG'], GP_HV=syms['GP_HV'], GP_HF=syms['GP_HF'], GP_HL=syms['GP_HL'], GP_HON=syms['GP_HON'], GP_OV_ORD=syms['GP_OV_ORD'], GP_OV_ROWS=syms['GP_OV_ROWS'], GP_OV_N=syms['GP_OV_N'], GP_OV_ANNUAL=syms['GP_OV_ANNUAL'], GP_SS=syms['GP_SS'], PR_STATE=syms['PR_STATE'],
                  RS_STATE=syms['RS_STATE'], ri_season=syms['ri_season'], ri_apply=syms['ri_apply'],
                  ri_cache=syms['ri_cache'], RI_STATE=syms['RI_STATE'], RI_MGR=syms['RI_MGR'],
                  RI_RULE=syms['RI_RULE'], cd_season=syms['cd_season'],
                  gp_wn_c=syms['gp_wn_c'], GP_WNSRC=syms['GP_WNSRC'], GP_SEAS=syms['GP_SEAS'],   # (winners.py)
                  WN_ST=syms['WN_ST'], GP_MGR=syms['GP_MGR'])
    assert struct.unpack('<I', p.get(1, syms['WN_SIZE'][1], 4))[0] == WN_SIZE   # (the engine block's 'WN')
    if cds:
        assert struct.unpack('<I', p.get(1, syms['CD_STSZ'][1], 4))[0] == CD_SIZE   # (the engine block's 'CD')
    print(f"exe: knockout play-offs (gplay): {len(tables)} countries, C obj1+{at:#x}..{cend:#x}, glue ..{glue + len(code):#x}, "
          f"GP_IN obj2+{syms['GP_IN'][1]:#x}, state GP_ST obj2+{syms['GP_ST'][1]:#x} ({lay['ST_SIZE']} B), "
          f"log obj2+{syms['GP_LOG'][1]:#x}, .bss {bss:#x}")
    return glue + len(code)
