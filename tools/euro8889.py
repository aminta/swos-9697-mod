"""European cups 1988-89 for the DDR in Season mode (session 29, Davide 2026-10-08).

A DDR club in Season plays its league (slot 0), the FDGB-Pokal (slot 1) and, when it was in Europe in 1988-89, the European
cup of that year (slot 2): BFC Dynamo the Champions Cup, Carl Zeiss Jena the Cup Winners' Cup, Dynamo Dresden and Lokomotive
Leipzig the UEFA Cup. Real participants and real brackets (en.wikipedia 1988-89 European Cup / Cup Winners' Cup / UEFA Cup;
euro8889.json). The foreign clubs have their real 1988-89 squads (weltfussball.de, euro8889_squads.txt).

Engine:
- the DDR country table is [Oberliga, -2, FDGB-Pokal, <a cup>, -1]; InitNewSeason loads that last entry into slot 2;
  euro_slot2 (replacing the `mov [A0], eax` before it) swaps it for the cup of the first human-controlled DDR club
  that played in Europe, or skips slot 2 when there is none.
- every cup is a fixed team list (contest struct cloned from the game's own Cup Winners' Cup) and a fixed draw per round
  (historic.DRAWS): the real bracket positions of the winners. Champions Cup: 31 clubs, the holder (PSV) straight into the
  second round (bye club, as in the FA Cup 1871-72).
- foreign clubs live in TEAM.094 (Champions Cup), 095 (Cup Winners' Cup), 096 (UEFA Cup); the three files share global
  numbers 1850..1911 (only one cup runs in a Season), disjoint from the DDR clubs (1786..1817). They overlap Italy's block
  (TEAM.020, 1850..1923): no Italian club of the 1996-97 game is ever in a DDR Season, and the numbers only matter inside one
  contest / career, like the shared historic base.
"""
import json
import os
import random
import re
import struct


def _sn(s):
    """c1c2.swos_name with the German sharp s kept as SS (NFKD would drop it)."""
    import c1c2
    return c1c2.swos_name(s.replace('ß', 'ss'))
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'euro8889.json'), encoding='utf-8'))
ROOT = os.path.join(HERE, '..')

CC_ID, CWC_ID, UEFA_ID = 0xC8, 0xC9, 0xCA
FILES = {'cc': 94, 'cwc': 95, 'uefa': 96}
BASES = {'cc': 1850, 'cwc': 1850, 'uefa': 1850}            # global number bases (see the module doc)
IDS = {'cc': CC_ID, 'cwc': CWC_ID, 'uefa': UEFA_ID}
TEAM_SIZE = 684

CODE_COUNTRY = {'ALB': 0, 'AUT': 1, 'BEL': 2, 'BUL': 3, 'CYP': 5, 'TCH': 6, 'DEN': 7, 'FIN': 12, 'FRA': 13, 'GDR': 14,
                'FRG': 14, 'GRE': 15, 'HUN': 16, 'ISL': 17, 'IRL': 18, 'ITA': 20, 'LUX': 23, 'MLT': 24, 'NED': 25,
                'NIR': 26, 'NOR': 27, 'POL': 28, 'POR': 29, 'ROU': 30, 'SCO': 33, 'ESP': 35, 'SWE': 36, 'SUI': 37,
                'TUR': 38, 'URS': 31, 'WAL': 40, 'YUG': 41}
NAME_CODE = {'Austria': 'AUT', 'Belgium': 'BEL', 'Bulgaria': 'BUL', 'Cyprus': 'CYP', 'Czechoslovakia': 'TCH',
             'Denmark': 'DEN', 'East Germany': 'GDR', 'Finland': 'FIN', 'France': 'FRA', 'Greece': 'GRE',
             'Hungary': 'HUN', 'Iceland': 'ISL', 'Ireland': 'IRL', 'Italy': 'ITA', 'Luxembourg': 'LUX', 'Malta': 'MLT',
             'Netherlands': 'NED', 'Northern Ireland': 'NIR', 'Norway': 'NOR', 'Poland': 'POL', 'Portugal': 'POR',
             'Romania': 'ROU', 'Scotland': 'SCO', 'Soviet Union': 'URS', 'Spain': 'ESP',
             'Sweden': 'SWE', 'Switzerland': 'SUI', 'Turkey': 'TUR', 'West Germany': 'FRG', 'Yugoslavia': 'YUG'}
ALIAS = {'Budapest Honvéd': 'Budapesti Honvéd'}
DDR_CLUB = {'BFC Dynamo': 'bfc', 'Carl Zeiss Jena': 'jena', 'Lokomotive Leipzig': 'lok', 'Dynamo Dresden': 'dresden'}
# DDR club (key in ddr89) -> its cup (1 CC, 2 CWC, 3 UEFA)
DDR_CUP = {'bfc': 'cc', 'jena': 'cwc', 'lok': 'uefa', 'dresden': 'uefa'}
CUP_INDEX = {'cc': 1, 'cwc': 2, 'uefa': 3}
SHORT_NAMES = {'it': {'cc': b'COPPA CAMPIONI', 'cwc': b'COPPA COPPE', 'uefa': b'COPPA UEFA'},
               'en': {'cc': b'EUROPEAN CUP', 'cwc': b'CUP WINNERS CUP', 'uefa': b'UEFA CUP'},
               'fr': {'cc': b'C. DES CHAMPIONS', 'cwc': b'C. DES COUPES', 'uefa': b'COUPE UEFA'},
               'de': {'cc': b'LANDESMEISTER', 'cwc': b'POKALSIEGER', 'uefa': b'UEFA-POKAL'}}
NAMES = {'it': {'cc': b'COPPA DEI CAMPIONI 1988-89', 'cwc': b'COPPA DELLE COPPE 1988-89', 'uefa': b'COPPA UEFA 1988-89'},
         'en': {'cc': b'EUROPEAN CUP 1988-89', 'cwc': b'CUP WINNERS CUP 1988-89', 'uefa': b'UEFA CUP 1988-89'},
         'fr': {'cc': b'COUPE DES CHAMPIONS 1988-89', 'cwc': b'COUPE DES COUPES 1988-89', 'uefa': b'COUPE UEFA 1988-89'},
         'de': {'cc': b'LANDESMEISTERCUP 1988-89', 'cwc': b'POKALSIEGERCUP 1988-89', 'uefa': b'UEFA-POKAL 1988-89'}}
# club names over 16 characters (the record has 17 bytes with the terminator)
SHORT = {'HEART OF MIDLOTHIAN': 'HEARTS', 'DNIPRO DNIPROPETROVSK': 'DNIPRO', 'TATABANYAI BANYASZ': 'TATABANYA',
         'VICTORIA BUCURESTI': 'VICTORIA BUCUR.', "ST PATRICK'S ATHLETIC": "ST PATRICK'S", 'EINTRACHT FRANKFURT': 'E. FRANKFURT',
         'PEZOPORIKOS LARNACA': 'PEZOPORIKOS', 'VITORIA DE GUIMARAES': 'V. GUIMARAES', 'RED STAR BELGRADE': 'CRVENA ZVEZDA',
         'INTERNACIONAL BRATISLAVA': 'INTER BRATISLAVA', 'INTERNACIONL BRATISLAVA': 'INTER BRATISLAVA'}
FINALS = {'cwc': ('Barcelona', 'Sampdoria'), 'uefa': ('Napoli', 'Stuttgart')}   # first named = first leg at home


def code_of(name, code):
    if code in NAME_CODE:
        return NAME_CODE[code]
    return code


def spec(cup):
    """{'clubs': [(name, country code)] in contest order, 'rounds': legs bytes, 'draws': [perm per round], 'bye': bool}"""
    if cup == 'cc':
        codes = DATA['cc_codes']
        r1 = [n for _, n in sorted(DATA['cc']['1'])]
        club = lambda n: (n, codes[ALIAS.get(n, n)])
        clubs = [club(n) for n in r1] + [club('PSV Eindhoven')]
        assert len(clubs) == 31
        draws = [list(range(30)), list(range(8)) + [15] + list(range(8, 15)), list(range(8)), list(range(4)), [0, 1]]
        return dict(clubs=clubs, rounds=[0x94] * 4 + [0x14], draws=draws, bye=True)
    rows = DATA[cup]
    names = ['First round', 'Second round', 'Quarter-finals', 'Semi-finals'] if cup == 'cwc' else \
            ['First round', 'Second round', 'Third round', 'Quarter-finals', 'Semi-finals']
    clubs, winners, draws = [], [], []
    prev = None
    for title in names:
        ties = rows[title]
        if prev is None:
            for t in ties:
                clubs += [(t['a'], code_of(t['a'], t['ca'])), (t['b'], code_of(t['b'], t['cb']))]
            draws.append(list(range(len(ties) * 2)))
        else:
            perm = []
            for t in ties:
                for side in ('a', 'b'):
                    assert t[side] in prev, (cup, title, t[side])
                    perm.append(prev.index(t[side]))
            draws.append(perm)
        prev = [t[t['win']] for t in ties]
    first, second = FINALS[cup]
    assert first in prev and second in prev, (cup, prev)
    draws.append([prev.index(first), prev.index(second)])
    n = len(draws)
    rounds = [0x94] * (n - 1) + [0x94 if cup == 'uefa' else 0x14]
    return dict(clubs=clubs, rounds=rounds, draws=draws, bye=False)


def swos_club(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper()
    s = s.replace('.', '').strip()
    s = SHORT.get(s, s)
    assert len(s) <= 16, s
    return s


def ddr_key(name):
    return DDR_CLUB.get(name)


def cup_clubs(cup):
    """[(file, ordinal) or None per contest slot], foreign records list"""
    return spec(cup)['clubs']


SQUADS = os.path.join(HERE, 'euro8889_squads.txt')
# Wikipedia name -> weltfussball slug where the names differ too much for the fuzzy match
SLUG = {'17 Nëntori': 'kf-tirane', 'Sparta Prague': 'ac-sparta-praha', 'Steaua București': 'fcsb', 'Valur': 'valur-reykjavik',
        'AEL': 'ae-larissa', 'HJK': 'hjk-helsinki', 'Vitosha Sofia': 'levski-sofia', 'Red Star Belgrade': 'crvena-zvezda',
        'AGF': 'aarhus-gf', 'Fram': 'fram-reykjavik', 'Omonia': 'omonia-nikosia', 'Roda JC': 'roda-jc-kerkrade',
        'Grasshopper': 'grasshopper-club-zuerich', 'Békéscsaba': 'bekescsaba-1912-eloere-se', 'Kuusysi Lahti': 'fc-kuusysi-old',
        'Tatabányai Bányász': 'tatabanya-fc', 'Antwerp': 'royal-antwerp-fc', 'Žalgiris Vilnius': 'fk-zalgiris',
        'Dukla Prague': 'fk-pribram', 'Internazionale': 'inter', 'ÍA': 'ia-akranes', 'Újpesti Dózsa': 'ujpest-fc',
        'Bordeaux': 'girondins-bordeaux', 'Dunajská Streda': 'fc-dac-1904', 'TPS': 'tps-turku', 'RŠD Velež': 'velez-mostar',
        'APOEL': 'apoel-nikosia', 'Athletic Bilbao': 'athletic-club', 'PAOK': 'paok-saloniki', 'Slavia Sofia': 'slavia-sofia',
        'Trakia Plovdiv': 'botev-plovdiv'}


def _norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s.replace('fc', '').replace('-', ''))


SLUG_OF = {}


def coaches():
    out = {}
    for line in open(os.path.join(HERE, 'euro8889_coaches.txt'), encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        cup, slug, coach = line.rstrip('\n').split('|')
        out[(cup, slug)] = coach
    return out


def squads():
    """{(cup, Wikipedia club name): [(player, role)]} (role T = a coach the site lists: becomes a filler)."""
    import difflib
    by = {}
    for line in open(SQUADS, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        cup, slug, players = line.rstrip('\n').split('|', 2)
        by[(cup, slug)] = [tuple(x.rsplit(':', 1)) for x in players.split(';')]
    out = {}
    for cup in ('cc', 'cwc', 'uefa'):
        slugs = [s for c, s in by if c == cup]
        for name, _ in spec(cup)['clubs']:
            if ddr_key(name):
                continue
            slug = SLUG.get(name) or max(slugs, key=lambda s: difflib.SequenceMatcher(None, _norm(name), _norm(s)).ratio())
            assert (cup, slug) in by, (cup, name, slug)
            out[(cup, name)] = by[(cup, slug)]
            SLUG_OF[(cup, name)] = slug
        assert len({id(v) for v in out.values() if True}) >= 0
    used = {}
    for (cup, name), v in out.items():
        assert id(v) not in used, (cup, name, used.get(id(v)))
        used[id(v)] = name
    return out


def build_teams():
    """{file: TEAM bytes} of the foreign clubs: real 1988-89 squads (euro8889_squads.txt). Template record = the same
    club in the 1996-97 game when it is there (kit, slots, skills), else a club of its country; players already in
    the game (any team file, same name) keep their record, the others take the slot's skills of the template."""
    import difflib
    import glob
    import c1c2
    rng = random.Random(1988)
    known, country_teams = {}, {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'orig', 'DATA', 'TEAM.0[0-9][0-9]'))):
        d = open(f, 'rb').read()
        recs = [d[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE] for k in range(struct.unpack('>H', d[:2])[0])]
        country_teams[int(f[-3:])] = recs
        for r in recs:
            for j in range(16):
                p = r[76 + j * 38:76 + (j + 1) * 38]
                known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
    sq = squads()
    co = coaches()
    files, report = {}, []
    for cup in ('cc', 'cwc', 'uefa'):
        out = []
        for name, code in [c for c in spec(cup)['clubs'] if not ddr_key(c[0])]:
            teams = country_teams.get(CODE_COUNTRY[code]) or country_teams[14]
            names = [t[5:22].split(b'\0')[0].decode('latin1') for t in teams]
            sname = swos_club(name)
            best = max(range(len(teams)), key=lambda k: difflib.SequenceMatcher(None, _norm(sname), _norm(names[k])).ratio())
            same = difflib.SequenceMatcher(None, _norm(sname), _norm(names[best])).ratio() >= 0.8
            t = teams[best] if same else rng.choice(teams)
            r = bytearray(t)
            i = len(out)
            r[0], r[1] = FILES[cup], i
            struct.pack_into('>H', r, 2, BASES[cup] + i)
            r[5:22] = sname.encode('latin1').ljust(17, b'\0')
            r[25] = 0
            coach = co.get((cup, SLUG_OF[(cup, name)]), '')
            r[36:59] = _sn(coach).encode('latin1').ljust(23, b'\0')[:23] if coach else bytes(23)
            pools = {c: [] for c in 'GDMA'}
            for who, role in sq[(cup, name)]:
                pools['M' if role == 'T' else role].append('?' if role == 'T' else who)
            borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
            filler = [p for tt in teams for p in [tt[76 + j * 38:76 + (j + 1) * 38] for j in range(16)]]
            reused = 0
            for j in range(16):
                p0 = 76 + j * 38
                cls = c1c2.CLASS[t[p0 + 26] >> 5]
                src = next((x for x in borrow[cls] if pools[x]), None)
                who = pools[src].pop(0) if src else '?'
                if who == '?':                              # no name: a player of the country from the game
                    q = bytearray(rng.choice(filler))
                else:
                    pname = _sn(who)
                    if pname in known:
                        q = bytearray(known[pname])
                        reused += 1
                    else:
                        q = bytearray(t[p0:p0 + 38])
                        q[3:26] = pname.encode('latin1').ljust(23, b'\0')[:23]
                q[2] = t[p0 + 2]
                q[26] = (q[26] & 0x1f) | (t[p0 + 26] & 0xe0)
                r[p0:p0 + 38] = q
            out.append(bytes(r))
            report.append((cup, sname, names[best] if same else '-', reused))
        files[FILES[cup]] = struct.pack('>H', len(out)) + b''.join(out)
    same = sum(1 for x in report if x[2] != '-')
    print(f'TEAM.094-096: European cups 1988-89, {len(report)} clubs, {same} on their own 1996-97 record, '
          f'{sum(x[3] for x in report)} players already in the game')
    return files


def contest_teams(cup):
    """(file, ordinal) list in contest order."""
    import ddr89
    sp = spec(cup)
    foreign = {}
    out = []
    for name, code in sp['clubs']:
        k = ddr_key(name)
        if k:
            out.append((ddr89.FILE, ddr89._ORD[k]))
        else:
            out.append((FILES[cup], len(foreign)))
            foreign[name] = 1
    return out


def draws():
    """historic.DRAWS entries (contest id, permutation)."""
    out = []
    for cup in ('cc', 'cwc', 'uefa'):
        for perm in spec(cup)['draws']:
            out.append((IDS[cup], perm))
    return out


# --- exe ----------------------------------------------------------------------------------------------------------
HOOK_ASM = '''
euro_slot2:                             ; replaces `mov [A0], eax` before slot 2 is loaded in InitNewSeason
    mov [A0], eax
    cmp byte [COMPCOUNTRY], DDR_FILE
    jne .ret
    pushad
    mov esi, [SELTEAMS]
    movzx ecx, word [NUMSEL]
.n:
    test ecx, ecx
    jz .none
    cmp byte [esi + 4], 1               ; computer-controlled
    je .skip
    cmp byte [esi], DDR_FILE
    jne .skip
    movzx eax, byte [esi + 1]
    cmp eax, 14
    jae .skip
    movzx eax, byte [EURO_MAP + eax]
    test eax, eax
    jnz .found
.skip:
    add esi, 684
    dec ecx
    jmp .n
.found:
    mov eax, [EURO_PTRS + eax * 4]
    mov [A0], eax
    popad
    ret
.none:
    popad
    add esp, 4
    jmp SKIP_SLOT2
.ret:
    ret
EURO_MAP: MAP_BYTES
align 4
EURO_PTRS: dd 0, CUP_CC, CUP_CWC, CUP_UEFA
'''


def hook_sites(p):
    """(site of `mov [A0], eax` before slot 2, skip target, compCountryNumber, selTeamsPtr, g_numSelectedTeams) in obj1 / obj2."""
    import sacups
    d1 = p.le.obj_bytes(1)
    r = sacups.regs(d1)
    a0 = struct.pack('<I', r['A0'])
    a6 = struct.pack('<I', r['A0'] + 24)
    d0 = struct.pack('<I', r['D7'] - 28)
    d1_ = struct.pack('<I', r['D7'] - 24)
    d2_ = struct.pack('<I', r['D7'] - 20)
    pat = (rb'\x8b\x35' + re.escape(a6) + rb'\x8b\x06\xa3' + re.escape(a0) + rb'\x66\xc7\x05' + re.escape(d0) + rb'\x02\x00'
           + rb'\x66\xc7\x05' + re.escape(d1_) + rb'\x00\x00\x66\xc7\x05' + re.escape(d2_) + rb'\x00\x00\xff\x35' + re.escape(a6)
           + rb'\xe8.{4}\x8f\x05' + re.escape(a6) + rb'(?=\x66\xc7\x05.{4}\x00\x00\x66\xc7\x05)')
    ms = list(re.finditer(pat, d1, re.S))
    assert len(ms) == 1, len(ms)
    m = ms[0]
    site = m.start() + 8                                    # the `a3 <A0>` (mov [A0], eax)
    skip = m.end()
    assert d1[site] == 0xa3
    # compCountryNumber: mov al,[esi+2]; mov byte [D7], al; mov [comp], al
    c = re.search(rb'\x8a\x46\x02\xa2' + re.escape(struct.pack('<I', r['D7'])) + rb'\xa2(.{4})', d1, re.S)
    comp = struct.unpack('<I', c.group(1))[0]
    # tail: mov ax,[num]; mov [D0],ax; sub word [D0],1; mov eax,[sel]; mov [A0],eax
    t = re.search(rb'\x66\xa1(.{4})\x66\xa3' + re.escape(d0) + rb'\x66\x83\x2d' + re.escape(d0) + rb'\x01\xa1(.{4})\xa3' +
                  re.escape(a0), d1, re.S)
    num, sel = struct.unpack('<I', t.group(1))[0], struct.unpack('<I', t.group(2))[0]
    return site, skip, comp, sel, num, r


def structs(p, lang, area, at, str_base):
    """Contest structs of the three cups; returns (cave end, {cup: obj1 offset}, names)."""
    import sacups
    d2 = p.le.obj_bytes(2)
    cwc = sacups.unique(d2, sacups.CWC_HDR)
    uefa = sacups.unique(d2, sacups.UEFA_HDR)
    euro = sacups.unique(d2, sacups.EUROCUP_HDR)
    name_of = {'cc': euro + 39, 'cwc': cwc + 20, 'uefa': uefa + 20}
    ptrs, names = {}, {}
    for cup in ('cc', 'cwc', 'uefa'):
        sp = spec(cup)
        teams = contest_teams(cup)
        h = bytearray(d2[cwc:cwc + 14])
        h[0], h[10] = IDS[cup], len(teams)
        h += bytes(sp['rounds']) + b'\0'
        h[5] = len(h) - 5
        h[7] = len(h) + 8 - 7
        nm = NAMES[lang][cup] if os.environ.get('EURO_ALWAYS') != '3' else NAMES[lang][cup].ljust(44)   # room for the diagnostic
        rel = area.add(nm + b'\0') - str_base
        names[cup] = rel + str_base
        short = area.add(SHORT_NAMES[lang][cup] + b'\0') - str_base
        body = bytes(h) + struct.pack('<II', rel, short) + b''.join(bytes(t) for t in teams)
        ptrs[cup] = at
        p.put(1, at, body)
        at = (at + len(body) + 3) & ~3
    structs.names = names
    return at, ptrs


DIAG_ASM = '''
euro_slot2:                             ; DIAGNOSTIC build (EURO_ALWAYS=3): UEFA Cup for every DDR club; its name shows
    mov [A0], eax                       ; "NN " (g_numSelectedTeams) + per selected team: ordinal letter (A = 0) or '-'
    cmp byte [COMPCOUNTRY], DDR_FILE    ; for a non-DDR team, and its teamControls digit
    jne .ret
    pushad
    mov esi, [SELTEAMS]
    movzx ecx, word [NUMSEL]
    mov edi, DBG_STR
    mov eax, ecx
    mov bl, 10
    div bl
    add al, '0'
    mov [edi], al
    add ah, '0'
    mov [edi + 1], ah
    mov byte [edi + 2], ' '
    add edi, 3
    cmp ecx, 14
    jbe .c
    mov ecx, 14
.c:
    test ecx, ecx
    jz .end
.l:
    mov al, '-'
    cmp byte [esi], DDR_FILE
    jne .x
    mov al, [esi + 1]
    add al, 'A'
.x:
    mov [edi], al
    mov al, [esi + 4]
    add al, '0'
    mov [edi + 1], al
    add edi, 2
    add esi, 684
    dec ecx
    jnz .l
.end:
    mov byte [edi], 0
    mov eax, [EURO_PTRS + 12]
    mov [A0], eax
    popad
.ret:
    ret
align 4
EURO_PTRS: dd 0, CUP_CC, CUP_CWC, CUP_UEFA
'''
