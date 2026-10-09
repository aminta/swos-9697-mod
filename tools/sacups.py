"""South American club cups: Copa Libertadores, Supercopa, Copa CONMEBOL.

Added (not replacing anything) to the South America continent entry, so they
show as cup buttons in "choose preset competition" and in the career world
view, like the three European cups do.

Contest struct layout (reversed from the European cups):
  [0] contest id   [1] type (1 knockout, 2 groups + knockout)   [2] country (FF = any)
  [3],[4] months   [5] name dwords at +5+[5]   [7] team list at +7+[7]
  [8] 1 = fixed team list   type 1: [10] teams, [14..] one byte per round
  names: two dwords, obj2 string offset - STR_BASE (strings must be in obj2)
  team list: (team file number, team index) byte pairs
Knockout rounds: 0x94 = two legs, 0x14 = final (single match), as the CWC.
Libertadores copies the Champions Cup header with its own stages (20 teams, 5 groups of 4, round of 16).
"""
import struct

import nasmcave

COMP_SLOTS = [None]                           # obj2 offset of dseg_D8CAA (slot contest ptrs)
COMP_TABLE = [None]                           # obj2 offset of competitionsTable, set by patch()
INTL_LIST = [None]                            # (obj1 offset of the relocated international contests list, code refs)
LIB_ID, SUP_ID, CON_ID = 0x6c, 0x6d, 0x6e     # unused ids (0x6c..0x7b free)
INT_ID = 0x6f                                 # Intercontinental Cup
CN_SOUTH_AMERICA = 82
STR_BASE = None                               # obj2 offset contest names are relative to (0x16F8), set by patch.patch_italy

ARG, BOL, BRA, CHI, COL, ECU, PAR, PER, URU, VEN = 43, 45, 46, 48, 49, 50, 64, 65, 71, 77

# 1997 editions; groups/pairings are consecutive. Libertadores (session 27, real 1997 format, tools/lib97.py): 21 clubs,
# 20 in 5 groups of 4 (two countries per group), the holder (River Plate, 1996) last: it plays no group and enters the
# round of 16 (lib97.lib_bye / lib_pre); top 3 of each group + the holder = 16.
LIBERTADORES = [
    (BOL, 1), (PAR, 5), (BOL, 8), (PAR, 2),        # Bolivar, Guarani, Oriente Petrolero, Cerro Porteno
    (ARG, 39), (ECU, 4), (ARG, 32), (ECU, 2),      # Velez, El Nacional, Racing Club, Emelec
    (CHI, 7), (VEN, 13), (CHI, 14), (VEN, 12),     # Colo Colo, Minerven, U. Catolica, Mineros de Guayana
    (BRA, 12), (PER, 12), (BRA, 8), (PER, 1),      # Gremio, Sporting Cristal, Cruzeiro, Alianza Lima
    (URU, 17), (COL, 14), (URU, 16), (COL, 10),    # Penarol, Millonarios, Nacional, Deportivo Cali
    (ARG, 33),                                     # River Plate (holder): round of 16
]
LIB_N = len(LIBERTADORES)
LIB_GROUPS = LIB_N - 1                        # clubs in the group stage (the holder is the last)
# type-2 stages from +0Eh: count, then (teams, groups, teams per group) per stage (the first stage's teams = the
# contest's team count [0Fh]), the winners' count, padding; from +22h one byte per stage: bits 7-6 legs (2 = two legs),
# 5-4 extra time, 3-2 penalties -> 0x84 = two legs, no extra time, penalties (1997: aggregate, then penalties)
LIB_STAGES = bytes([5, LIB_N, 5, 4, 16, 0, 16, 8, 0, 8, 4, 0, 4, 2, 0, 2, 1, 0, 0, 0, 0, 0x84, 0x84, 0x84, 0x84])
SUPERCOPA = [
    (ARG, 33), (URU, 16), (ARG, 8), (PAR, 7),      # River - Nacional, Boca - Olimpia
    (ARG, 24), (BRA, 9), (ARG, 32), (BRA, 20),     # Independiente - Flamengo, Racing - Sao Paulo
    (ARG, 16), (CHI, 7), (ARG, 39), (BRA, 8),      # Estudiantes - Colo Colo, Velez - Cruzeiro
    (BRA, 19), (URU, 17), (BRA, 12), (COL, 2),     # Santos - Penarol, Gremio - Atl. Nacional
]
CONMEBOL = [
    (BRA, 1), (BOL, 12), (ARG, 26), (PAR, 5),      # Atl. Mineiro - The Strongest, Lanus - Guarani
    (BRA, 22), (PER, 15), (ARG, 11), (ECU, 2),     # Vasco - Universitario, Colon - Emelec
    (BRA, 14), (VEN, 2), (ARG, 20), (CHI, 2),      # Internacional - Caracas, Gimnasia - Cobreloa
    (CHI, 15), (URU, 8), (COL, 10), (COL, 13),     # U. de Chile - Defensor, Dep. Cali - Santa Fe
]
NAMES = {LIB_ID: b'COPA LIBERTADORES', SUP_ID: b'SUPERCOPA', CON_ID: b'COPA CONMEBOL',
         INT_ID: b'COPPA INTERCONTINENTALE'}
# Tokyo, November 1996: Juventus - River Plate (Juventus' TEAM.020 index is looked up by name)
INTERCONTINENTAL = [('JUVENTUS', 20), (ARG, 33)]
NAME_SITES = []                               # (contest id, obj1 offset of its two name dwords), set by patch()

EUROCUP_HDR = bytes.fromhex('0002ff40202200280101010203350410')
CWC_HDR = bytes.fromhex('0101ff40200f001501002001350194949494')
UEFA_HDR = bytes.fromhex('0201ff40200f001501002001350194949494')
COPA_HDR = bytes.fromhex('1f02528890210027')


def unique(hay, needle):
    i = hay.find(needle)
    assert i >= 0 and hay.find(needle, i + 1) < 0, needle.hex()
    return i


def teams(lst, n=16):
    assert len(lst) == n
    return b''.join(bytes(t) for t in lst)


def team_index(fileno, name):
    import os
    d = open(os.path.join(os.path.dirname(__file__), '../c/SWOS/DATA/TEAM.%03d' % fileno), 'rb').read()
    names = [d[2 + i * 684 + 5:2 + i * 684 + 22].split(b'\0')[0].decode('latin1') for i in range(struct.unpack('>H', d[:2])[0])]
    return names.index(name)


def knockout16(cwc, cid, teams=16, rounds=(0x94, 0x94, 0x94, 0x14)):
    h = bytearray(cwc[:14])
    h[0], h[10] = cid, teams
    h += bytes(rounds) + b'\0'                   # default rounds 16-8-4-2, terminator
    h[5] = len(h) - 5
    h[7] = len(h) + 8 - 7
    return h


def intercontinental(cwc):
    h = knockout16(cwc, INT_ID, 2, (0x14,))
    h[3], h[4] = 0x58, 0x60      # months x 8 from January (12+ = next year): December, window to January
    return h


def patch(p, pool, cave, caf):
    d2 = p.le.obj_bytes(2)
    o1base, o2base = p.le.obj(1).base, p.le.obj(2).base
    euro = unique(d2, EUROCUP_HDR)
    cwc = unique(d2, CWC_HDR)
    copa = unique(d2, COPA_HDR)
    name = STR_BASE + struct.unpack_from('<I', d2, euro + 39)[0]          # Champions Cup name: a real string
    assert d2[name:name + 4].isupper() and 0 < d2.find(b'\0', name) - name < 40

    # contest structs, names after them
    euro79 = d2[euro:euro + 79]
    lib = bytearray(euro79[:47])
    lib[0] = LIB_ID
    assert lib[0x0e:0x12] == bytes([4, 16, 4, 4]) and lib[5] == 0x22 and len(LIB_STAGES) == 0x27 - 0x0e   # names stay at +27h
    lib[0x0e:0x27] = LIB_STAGES
    assert lib[8] == 1 and lib[9] == 1 and lib[0x0a] == 1
    lib[9] = 0              # every round through the draw hook (historic.hist_draw: fixed 1997 bracket), not seeded
    lib[0x0a] = 0           # no away goals (contest [0Ah] -> competition [5Dh]: 0 off, 1 after 90', 2 after e.t.)
    structs = [(LIB_ID, lib, 39, LIBERTADORES),
               (SUP_ID, knockout16(d2[cwc:cwc + 28], SUP_ID), 19, SUPERCOPA),
               (CON_ID, knockout16(d2[cwc:cwc + 28], CON_ID), 19, CONMEBOL),
               (INT_ID, intercontinental(d2[cwc:cwc + 28]), 16,
                [(20, team_index(20, INTERCONTINENTAL[0][0])), INTERCONTINENTAL[1]])]
    at = cave
    layout = []
    for cid, body, name_at, lst in structs:
        blob = bytes(body[:name_at]) + bytes(8) + teams(lst, len(lst))
        assert blob[5] + 5 == name_at and blob[7] + 7 == name_at + 8
        layout.append((cid, at, name_at))
        p.put(1, at, blob)
        at += len(blob)
    for cid, off, name_at in layout:
        rel = pool.add(NAMES[cid]) - STR_BASE
        p.put(1, off + name_at, struct.pack('<II', rel, rel))
    NAME_SITES[:] = [(cid, off + name_at) for cid, off, name_at in layout]   # patch.short_names: 2nd dword
    at = (at + 3) & ~3

    # South America continent: [WC qualification, Copa America, -1] + countries
    refs = [f for f in p.le.fixups() if f[3] == 2 and f[4] == copa and f[0] == 2]
    sa = [f[1] - 4 for f in refs if d2[f[1] + 4:f[1] + 8] == b'\xff' * 4]
    assert len(sa) == 1, sa
    sa = sa[0]
    wcq = p.target(2, sa)
    countries = d2[sa + 12:d2.index(b'\xff', sa + 12) + 1]
    sa_new = at
    ptrs = [wcq, (2, copa)] + [(1, off) for _, off, _ in layout]
    for k, (tobj, toff) in enumerate(ptrs):
        p.add_ptr(1, at + 4 * k, tobj, toff)
    at += 4 * len(ptrs)
    p.put(1, at, b'\xff' * 4 + countries)
    at = (at + 4 + len(countries) + 3) & ~3
    cont = [f for f in p.le.fixups() if f[3] == 2 and f[4] == sa]
    assert len(cont) == 1, cont
    p.retarget(cont[0][0], cont[0][1], 1, sa_new)
    assert cont[0][0] == 2
    COMP_TABLE[0] = cont[0][1] - 4 * CN_SOUTH_AMERICA

    # Europe continent: [252 (WC qualification id, not a pointer), European Championship, CC, CWC, UEFA, -1] + countries
    fx2 = {f[1]: (f[3], f[4]) for f in p.le.fixups() if f[0] == 2}
    eu = [o - 8 for o, t in fx2.items() if t == (2, euro) and fx2.get(o + 4) == (2, cwc)
          and struct.unpack_from('<I', d2, o + 12)[0] == 0xffffffff]
    assert len(eu) == 1, eu
    eu = eu[0]
    assert struct.unpack_from('<I', d2, eu)[0] == 252 and eu not in fx2
    eu_countries = d2[eu + 24:d2.index(b'\xff', eu + 24) + 1]
    eu_new = at
    p.put(1, at, struct.pack('<I', 252))
    for k, o in enumerate(range(eu + 4, eu + 20, 4)):
        p.add_ptr(1, at + 4 + 4 * k, *fx2[o])
    p.add_ptr(1, at + 20, 1, layout[3][1])        # + Intercontinental Cup
    p.put(1, at + 24, b'\xff' * 4 + eu_countries)
    at = (at + 28 + len(eu_countries) + 3) & ~3
    cont_eu = [f for f in p.le.fixups() if f[3] == 2 and f[4] == eu]
    assert len(cont_eu) == 1 and cont_eu[0][0] == 2, cont_eu
    p.retarget(2, cont_eu[0][1], 1, eu_new)

    # international contests list (dseg_C707E): starts with worldCup, europeanChampionships, copaAmerica, euroCup
    fx2 = {f[1]: (f[3], f[4]) for f in p.le.fixups() if f[0] == 2}
    lst = [f[1] - 8 for f in refs if fx2.get(f[1] + 4) == (2, euro)]
    assert len(lst) == 1, lst
    lst = lst[0]
    entries = []
    while d2[lst + 4 * len(entries):lst + 4 * len(entries) + 4] != b'\xff' * 4:
        entries.append(p.target(2, lst + 4 * len(entries)))
    entries += [(1, off) for _, off, _ in layout]
    lst_new = at
    for k, (tobj, toff) in enumerate(entries):
        p.add_ptr(1, at + 4 * k, tobj, toff)
    at += 4 * len(entries)
    p.put(1, at, b'\xff' * 4)
    at += 4
    code = [f for f in p.le.fixups() if f[3] == 2 and f[4] == lst]
    assert len(code) == 3 and all(f[0] == 1 for f in code), code
    for f in code:
        p.retarget(1, f[1], 1, lst_new)
    INTL_LIST[0] = (lst_new, [f[1] for f in code])

    print(f'exe: SA cups @ obj1+{cave:#x} (ids {LIB_ID:#x}-{CON_ID:#x}), SA table obj2+{sa:#x} -> obj1+{sa_new:#x}, '
          f'intl list obj2+{lst:#x} ({len(entries) - 3}+3) -> obj1+{lst_new:#x}')
    cups = [off for _, off, _ in layout][:3]
    import re
    d1 = p.le.obj_bytes(1)
    r = regs(d1)
    a1, a0 = (re.escape(struct.pack('<I', r[k])) for k in ('A1', 'A0'))
    m = [x for x in re.finditer(rb'\xc7\x05' + a1 + rb'(.{4})\xa1(.{4})\x39\x05' + a0 + rb'\x75', d1, re.S)]
    assert len(m) == 1
    COMP_SLOTS[0] = struct.unpack('<I', m[0].group(2))[0]
    at = career_hooks(p, cups, at, [off for _, off, _ in layout], caf)
    return qualify_hook(p, cups, at, layout[3][1] + 24, caf['q'])


# --- career: the player's club enters an SA cup ------------------------------
# InitializeNewSeason tries cseg_8D661 (A0 = cup, D7 = 0/1/2) on the three euro
# cup copies; a hit loads the cup into season slot 3 and sets dseg_E092F = D7.
# ProcessCareerFile (loading a save) maps dseg_E092F back to the slot-3 contest.
# Both chains are extended with D7/E092F = 3, 4, 5 for the SA cups.
# dseg_D8CBE (trophy flag, reputation, prize) is set to the euro cup of the same rank (Lib 0, Sup 1, CON 2).
SA_SLOT_BASE = 3
MARK3_GLOBAL, MARK3 = 1847, 0x3353   # 1.2: someLeaguesTable[1847..1849] = 'S3' + balance byte: "this career is set up"
TABLES = [None]          # (someLeaguesTable, leaguesTableCopy) obj2 offsets
SAVE_ITEMS = [None]      # [(obj1 offset, size)] of the SA lists + Intercontinental pair, saved by trailer.py
SAVED_GLOBAL = 1740      # 1.0/1.1 saves: someLeaguesTable[1740..1842]: 'S2' + 3 lists + Intercontinental pair + balance byte
                         # (cseg_9487A: sum must be 0); session-12 saves: 'SA' + 3 lists + balance byte (1740..1838);
                         # global numbers 1730..1849 belong to no team
LISTS_OUT = [None]       # career code's lists_out, called at season end

# ITA bytes (obj-relative offsets as stored in the file), see notes/STATUS.md


def regs(d1):
    """InitializeNewSeason tail, ProcessCareerFile slot-3 test and the pseudo registers they use.

    mov word [E092F],-1; jmp done; found: mov ax,[D7]; mov [E092F],ax   (ITA 66c705 790a0200 ffff eb0c 66a1 d3150300 ...)
    cmp word [E092F],2; jz map; jmp out; map: mov eax,[A0]
    D0..D7 and A0..A6 are consecutive dwords (translated 68000 registers): A0 = D7 + 4, A1 = A0 + 4.
    """
    import re
    m = [x for x in re.finditer(rb'\x66\xc7\x05(.{4})\xff\xff\xeb\x0c\x66\xa1(.{4})\x66\xa3(.{4})', d1, re.S)
         if x.group(1) == x.group(3)]
    assert len(m) == 1, len(m)
    e092f, d7 = (struct.unpack('<I', m[0].group(k))[0] for k in (1, 2))
    load = [x for x in re.finditer(rb'\x66\x83\x3d' + re.escape(struct.pack('<I', e092f)) + rb'\x02\x74\x02\xeb\x0a\xa1(.{4})',
                                   d1, re.S)]
    assert len(load) == 1, len(load)
    a0 = struct.unpack('<I', load[0].group(1))[0]
    assert a0 == d7 + 4
    return {'init': m[0].start(), 'load': load[0].start(), 'E092F': e092f, 'D7': d7, 'A0': a0, 'A1': a0 + 4, 'A4': a0 + 16}


class Asm:
    """Tiny x86-32 emitter for the few instruction forms we need."""

    def __init__(self, at):
        self.at, self.code, self.fix = at, bytearray(), []

    def here(self):
        return self.at + len(self.code)

    def mov_mem32_imm(self, mem, tobj, toff):        # mov dword [mem], offset tobj:toff
        self.fix += [(len(self.code) + 2, 2, mem), (len(self.code) + 6, tobj, toff)]
        self.code += b'\xc7\x05' + struct.pack('<II', mem, toff)

    def mov_mem16_imm(self, mem, imm):               # mov word [mem], imm16
        self.fix.append((len(self.code) + 3, 2, mem))
        self.code += b'\x66\xc7\x05' + struct.pack('<IH', mem, imm & 0xffff)

    def cmp_mem16_imm8(self, mem, imm):              # cmp word [mem], imm8
        self.fix.append((len(self.code) + 3, 2, mem))
        self.code += b'\x66\x83\x3d' + struct.pack('<Ib', mem, imm)

    def call(self, target):
        self.code += b'\xe8' + struct.pack('<i', target - (self.here() + 5))

    def jz(self, target):
        self.code += b'\x0f\x84' + struct.pack('<i', target - (self.here() + 6))

    def jmp(self, target):
        self.code += b'\xe9' + struct.pack('<i', target - (self.here() + 5))

    def emit(self, p):
        for k, b in enumerate(self.code):
            p.put(1, self.at + k, bytes((b,)))
        for off, tobj, toff in self.fix:
            p.add_ptr(1, self.at + off, tobj, toff)
        return self.here()


def hook(p, at, length, fixup_at, target):
    """Replace `length` bytes at obj1:at with jmp target + nops."""
    p.remove(1, fixup_at)
    j = struct.pack('<i', target - (at + 5))
    p.put(1, at, b'\xe9' + j + b'\x90' * (length - 5))


CAREER_ASM = '''
; InitializeNewSeason, after the three euro cups (replaces "mov [E092F],-1; jmp done")
init_sa:
    cmp word [MARK3_AT], MARK3          ; InitCareer zeroes the table: no mark = a new career (first-season lists)
    je .lists_ok
    call dword [NEW_CAREER_PTR]         ; trailer.new_career_defaults: every saved list + the mark
.lists_ok:
    cmp dword [PLAYER_CUP], 0           ; no national cup (all SA countries): slot 1 is free
    jne .intercontinental
    mov byte [SLOT1 + 2Dh], 0           ; forget last season's slot-1 contest (checked on load)
    mov ax, [SEL]
    mov esi, SUPLIST
    mov ecx, 16
.insup:
    cmp [esi], ax
    je .supercopa
    add esi, 2
    loop .insup
    jmp .intercontinental
.supercopa:                             ; former champion: Supercopa in slot 1, as the game loads a national cup
    push word [SLOT1 + 3Dh]
    push word [SLOT1 + 3Fh]
    push word [SLOT1 + 41h]
    mov dword [A0], SUP
    mov word [D0], 1
    mov word [D1], 0
    mov word [D2], 0
    call CSEG_8B2D3
    call GET_SEASON
    mov eax, [SLOT1 + 27h]
    sub eax, STR_BASE
    mov esi, [A0]
    mov [esi + 1Ah], eax
    pop word [SLOT1 + 41h]
    pop word [SLOT1 + 3Fh]
    pop word [SLOT1 + 3Dh]
.intercontinental:
    call int_step
.slot3:
    mov dword [A0], LIB
    mov word [D7], 3
    call CHECK
    jz .found
    cmp dword [PLAYER_CUP], SUP         ; already playing it in slot 1
    je .con
    mov dword [A0], SUP
    mov word [D7], 4
    call CHECK
    jz .found
.con:
    mov dword [A0], CON
    mov word [D7], 5
    call CHECK
    jz .found
;EXTRA_CHAIN                            ; cafcups.CUPS (CAF, CONCACAF): D7 = 6, 7, ...
    mov word [E092F], -1
    jmp DONE
.found:                                 ; trophy flag, reputation and prize (dseg_D8CBE) as the euro cup of the
    movzx ebx, word [D7]                ; same rank: Libertadores = Champions Cup, Supercopa = CWC, CONMEBOL = UEFA,
    movzx ax, byte [KINDS - 3 + ebx]    ; extra cups per cafcups.CUPS
    mov [CUP_KIND], ax
    jmp FOUND

; ProcessCareerFile, replaces "cmp [E092F],-1; jz out": restore a Supercopa in slot 1
load_slot1:                             ; the lists were restored by trailer.load_trailer (.CAR trailer / old saves)
    cmp dword [PLAYER_CUP], 0
    jne .euro
    cmp byte [SLOT1 + 2Dh], SUP_ID
    jne .euro
    mov dword [PLAYER_CUP], SUP
.euro:
    cmp dword [PLAYER_CUP2], 0
    jne .euro2
    cmp byte [SLOT2 + 2Dh], INT_ID
    jne .euro2
    mov dword [PLAYER_CUP2], INT
.euro2:
    cmp dword [SLOT4_CUP], 0            ; no play-offs: restore an Intercontinental in slot 4
    jne .euro3
    cmp byte [SLOT4 + 2Dh], INT_ID
    jne .euro3
    mov dword [SLOT4_CUP], INT
.euro3:
    cmp word [E092F], -1
    je LOAD_OUT
    jmp LOAD_CONT

; ProcessCareerFile, replaces "cmp [E092F],2; jz map; jmp out": slot 3 = SA cup for E092F 3..5, extra cups 6..
load_slot3:
    cmp word [E092F], 2
    je LOAD_MAP
    mov dword [A0], LIB
    cmp word [E092F], 3
    je LOAD_MAP
    mov dword [A0], SUP
    cmp word [E092F], 4
    je LOAD_MAP
    mov dword [A0], CON
    cmp word [E092F], 5
    je LOAD_MAP
;EXTRA_LOAD
    jmp LOAD_OUT

; InitializeNewSeason "found" (a euro or SA cup in slot 3): mov ax,[D7]; mov [E092F],ax replaced
euro_found:
    cmp word [MARK3_AT], MARK3          ; a new career whose club starts in a European cup: same set-up as init_sa
    je .lists_ok                        ; (before 2.7 only the no-European-cup branch did it: no 'S3' mark until a
    call dword [NEW_CAREER_PTR]         ; reload, and the lists of a career loaded earlier in the session stayed)
.lists_ok:
    call int_step
    mov ax, [D7]
    mov [E092F], ax
    jmp DONE

int_step:                               ; Intercontinental Cup in slot 2 for last season's CC / Libertadores winner
    cmp dword [PLAYER_CUP2], 0          ; slot 2 (league cup) free: Italy, all SA countries...
    jne .ret
    mov byte [SLOT2 + 2Dh], 0
    mov ax, [SEL]
    cmp [INTLIST], ax                   ; Champions Cup / Libertadores winner of last season
    je .play_int
    cmp [INTLIST + 2], ax
    jne .ret
.play_int:
    push word [SLOT2 + 3Dh]
    push word [SLOT2 + 3Fh]
    push word [SLOT2 + 41h]
    mov dword [A0], INT
    mov word [D0], 2
    mov word [D1], 0
    mov word [D2], 0
    call CSEG_8B2D3
    call GET_SEASON
    mov eax, [SLOT2 + 27h]
    sub eax, STR_BASE
    mov esi, [A0]
    mov [esi + 1Eh], eax
    pop word [SLOT2 + 41h]
    pop word [SLOT2 + 3Fh]
    pop word [SLOT2 + 3Dh]
.ret:
    ret

; InitializeNewSeason, replaces "call cseg_8DAC3" (slot 4 = the division's play-offs): countries with a
; league cup have no free slot 2, so the Intercontinental goes to slot 4 when the division has no play-offs.
; cseg_8B2D3 only builds placeholder teams in slot 4 (play-offs get theirs at the league's end, cseg_8ECAE):
; build the cup as slot 2 (league cup parked in slot 4's buffer), then swap the two buffers.
int4_step:
    call CSEG_8DAC3
    cmp dword [SLOT4_CUP], 0            ; play-offs in slot 4
    jne .ret
    mov byte [SLOT4 + 2Dh], 0           ; forget last season's slot-4 contest (checked on load)
    cmp dword [PLAYER_CUP2], INT        ; already in slot 2
    je .ret
    mov ax, [SEL]
    cmp [INTLIST], ax
    je .play_int
    cmp [INTLIST + 2], ax
    jne .ret
.play_int:
    push dword [PLAYER_CUP2]
    mov esi, SLOT2
    mov edi, SLOT4
    mov ecx, SLOT_SIZE
    call copy
    mov dword [A0], INT
    mov word [D0], 2
    mov word [D1], 0
    mov word [D2], 0
    call CSEG_8B2D3
    mov esi, SLOT2                      ; Intercontinental -> slot 4, league cup back in slot 2
    mov edi, SLOT4
    mov ecx, SLOT_SIZE
.swap:
    mov al, [esi]
    mov ah, [edi]
    mov [edi], al
    mov [esi], ah
    inc esi
    inc edi
    dec ecx
    jnz .swap
    mov word [SLOT4 + 2Bh], 4           ; slot number (cseg_8B2D3)
    mov ax, [LEAGUE_SUBS]               ; substitution rules of the league, as cseg_8ECAE does for play-offs
    mov [SLOT4 + 3Dh], ax
    mov ax, [LEAGUE_SUBS + 2]
    mov [SLOT4 + 3Fh], ax
    mov ax, [LEAGUE_SUBS + 4]
    mov [SLOT4 + 41h], ax
    pop dword [PLAYER_CUP2]
    mov dword [SLOT4_CUP], INT
.ret:
    ret

; cseg_8ECAE (league end: play-off teams into slot 4), replaces "cmp dword [D8CBA],0; jz out"
playoffs:
    cmp dword [SLOT4_CUP], 0
    je PLAYOFF_OUT
    cmp dword [SLOT4_CUP], INT          ; the Intercontinental is not a play-off
    je PLAYOFF_OUT
    jmp PLAYOFF_CONT

; From 1.2 every saved list lives in the .CAR trailer (trailer.py), written when the career is saved: the season end has
; nothing to store. (1.0/1.1 kept them in someLeaguesTable[1740..1842]; trailer.load_trailer reads and clears that block.)
lists_out:
    ret
copy32:                                 ; byte copies through DS only (no movs: ES is not ours)
    mov ecx, 32
copy:
    push esi
    push edi
.b:
    mov al, [esi]
    mov [edi], al
    inc esi
    inc edi
    dec ecx
    jnz .b
    pop edi
    pop esi
    ret
KINDS: KIND_BYTES
'''


def career_hooks(p, cups, cave, cups_all=None, caf=None):
    """cups = obj1 offsets of the Libertadores, Supercopa, CONMEBOL structs; caf = cafcups.career_info()."""
    import re
    d1 = p.le.obj_bytes(1)
    lib, sup, con = cups
    r = regs(d1)
    init, load = r['init'], r['load']
    e092f = struct.unpack_from('<I', d1, init + 3)[0]
    assert struct.unpack_from('<I', d1, load + 3)[0] == e092f
    # the euro chain just before: mov dword [A0], uefaCupCopy / mov word [D7], 2 / call cseg_8D661 / jz found
    a0 = struct.unpack_from('<I', d1, init - 26 + 2)[0]
    d7 = struct.unpack_from('<I', d1, init - 16 + 3)[0]
    assert d1[init - 26:init - 24] == b'\xc7\x05' and d1[init - 16:init - 13] == b'\x66\xc7\x05'
    assert d1[init - 7] == 0xe8 and d1[init - 2] == 0x74
    check = init - 2 + struct.unpack_from('<i', d1, init - 6)[0]          # cseg_8D661
    found = init + 11                                                     # mov ax,[D7]; mov [E092F],ax
    done = found + 12                                                     # call cseg_8DAC3
    assert d1[init + 9:init + 11] == b'\xeb\x0c'
    assert struct.unpack_from('<I', d1, load + 13)[0] == a0
    load_map, load_out = load + 12, load + 12 + 10                        # mov eax,[A0] ; @@out
    assert d1[load + 10:load + 12] == b'\xeb\x0a'
    # ProcessCareerFile start of the mapping: cmp word [E092F],-1; jz out; mov dword [A0], euroCupCopy
    load0 = load - 0x3c
    assert d1[load0:load0 + 3] == b'\x66\x83\x3d' and d1[load0 + 7:load0 + 9] == b'\xff\x74'
    assert load0 + 10 + d1[load0 + 9] == load_out and d1[load0 + 10:load0 + 12] == b'\xc7\x05'
    # InitializeNewSeason slot 1 (national cup): push word [slot1+3Dh] x3; mov esi,[A6]; mov eax,[esi]; add [A6],4;
    # mov [A0],eax; mov word [D0],1; [D1],0; [D2],0; ... call cseg_8B2D3 ... call GetCurrentSeasonPointer;
    # mov eax,[slot1+27h]; sub eax, STR_BASE; mov esi,[A0]; mov [esi+1Ah],eax
    m = [x for x in re.finditer(rb'\x66\xff\x35(.{4})\x66\xff\x35(.{4})\x66\xff\x35(.{4})\x8b\x35(.{4})\x8b\x06\x83\x05', d1, re.S)]
    def slot_of(x):
        k = d1.find(b'\x66\xc7\x05', x.end())
        return struct.unpack_from('<H', d1, k + 7)[0]
    m2 = [x for x in re.finditer(rb'\x66\xff\x35(.{4})\x66\xff\x35(.{4})\x66\xff\x35(.{4})\x8b\x35(.{4})\x8b\x06\xa3', d1, re.S)]
    m2 = [x for x in m2 if slot_of(x) == 2]
    assert len(m2) == 1, len(m2)
    slot2 = struct.unpack('<I', m2[0].group(1))[0] - 0x3d
    m = [x for x in m if slot_of(x) == 1]
    assert len(m) == 1, len(m)
    w = [struct.unpack('<I', g)[0] for g in m[0].groups()]
    slot1 = w[0] - 0x3d
    assert w[1:3] == [slot1 + 0x3f, slot1 + 0x41]
    blk = m[0].end()
    k = d1.find(b'\x66\xc7\x05', blk)
    d0, d1v, d2 = (struct.unpack_from('<I', d1, k + 9 * n + 3)[0] for n in range(3))
    assert [struct.unpack_from('<H', d1, k + 9 * n + 7)[0] for n in range(3)] == [1, 0, 0]
    calls = [i for i in range(k, k + 0x80) if d1[i] == 0xe8]
    c8b2d3 = calls[0] + 5 + struct.unpack_from('<i', d1, calls[0] + 1)[0]
    getseason = calls[1] + 5 + struct.unpack_from('<i', d1, calls[1] + 1)[0]
    assert d1[calls[1] + 5] == 0xa1 and struct.unpack_from('<I', d1, calls[1] + 6)[0] == slot1 + 0x27
    assert d1[calls[1] + 10:calls[1] + 15] == b'\x2d' + struct.pack('<I', STR_BASE)
    player_cup = COMP_SLOTS[0] + 4                                        # dseg_D8CAE = slot-1 contest ptr
    k = d1.find(b'\x66\xa1' + struct.pack('<I', d7) + b'\x66\xa3', check)     # cseg_8D661: mov [dseg_D8CBE], D7
    assert 0 < k - check < 0x200
    cup_kind = struct.unpack_from('<I', d1, k + 8)[0]
    # InitCareer: mov [A0], offset someLeaguesTable; mov word [D0], 1999 (clear loop)
    m = [x for x in re.finditer(rb'\xc7\x05' + struct.pack('<I', a0) + rb'(.{4})\x66\xc7\x05.{4}\xcf\x07', d1, re.S)]
    assert len(m) == 1, len(m)
    table = struct.unpack('<I', m[0].group(1))[0]
    saved = table + SAVED_GLOBAL
    # cseg_8CC0A: mov [D0], 1999; mov [A0], offset someLeaguesTable; mov [A1], offset leaguesTableCopy
    m = [x for x in re.finditer(rb'\xc7\x05' + struct.pack('<I', a0) + struct.pack('<I', table) + rb'\xc7\x05.{4}(.{4})', d1, re.S)]
    copies = {struct.unpack('<I', x.group(1))[0] for x in m}
    assert len(copies) == 1, copies
    copies_base = copies.pop()
    saved_copy = copies_base + SAVED_GLOBAL
    defaults = b''.join(p.get(1, off, n) for off, n in ((lib + 47, 2 * LIB_N), (sup + 27, 32), (con + 27, 32))) + p.get(1, cups_all[3] + 24, 4)
    sel = struct.unpack_from('<I', d1, check + 0x2d + 2)[0]               # cseg_8D661: mov ax,[selTeamNumber]
    assert d1[check + 0x2d:check + 0x2f] == b'\x66\xa1'

    # cseg_8ECAE: cmp dword [D8CBA],0; jz out; mov eax,[D8CC0]; mov [A6],eax; mov [A5],offset list; mov [A4],offset slot4
    slot4_cup = COMP_SLOTS[0] + 16
    m = [x for x in re.finditer(rb'\x83\x3d' + re.escape(struct.pack('<I', slot4_cup)) + rb'\x00\x0f\x84(.{4})\xa1', d1, re.S)]
    assert len(m) == 1, len(m)
    po = m[0].start()
    po_out = po + 13 + struct.unpack('<i', m[0].group(1))[0]
    assert d1[po_out] == 0xc3
    k = d1.find(b'\xc7\x05', po + 13)
    k = d1.find(b'\xc7\x05', k + 10)
    assert k - po < 0x30
    slot4 = struct.unpack_from('<I', d1, k + 6)[0]
    assert slot4 == slot2 + 0x443, (hex(slot4), hex(slot2))
    # its tail: mov ax,[league+3Dh]; mov [slot4+3Dh],ax (x3)
    k = d1.find(b'\x66\xa3' + struct.pack('<I', slot4 + 0x3d), po)
    assert 0 < k - po < 0x300 and d1[k - 6:k - 4] == b'\x66\xa1'
    league_subs = struct.unpack_from('<I', d1, k - 4)[0]
    assert d1[k + 6:k + 8] == b'\x66\xa1' and struct.unpack_from('<I', d1, k + 8)[0] == league_subs + 2
    c8dac3 = done + 5 + struct.unpack_from('<i', d1, done + 1)[0]
    assert d1[done] == 0xe8

    symbols = {'PLAYER_CUP': (2, player_cup), 'SLOT1': (2, slot1), 'SEL': (2, sel), 'A0': (2, a0), 'D0': (2, d0),
               'D1': (2, d1v), 'D2': (2, d2), 'D7': (2, d7), 'E092F': (2, e092f), 'LIB': (1, lib), 'SUP': (1, sup),
               'CON': (1, con), 'SUPLIST': (1, sup + 27), 'SUP_ID': (0, SUP_ID), 'STR_BASE': (2, STR_BASE),
               'CSEG_8B2D3': (1, c8b2d3), 'GET_SEASON': (1, getseason), 'CHECK': (1, check), 'FOUND': (1, found),
               'PLAYER_CUP2': (2, player_cup + 4), 'SLOT2': (2, slot2), 'INT': (1, cups_all[3]),
               'INTLIST': (1, cups_all[3] + 24), 'INT_ID': (0, INT_ID),
               'CUP_KIND': (2, cup_kind), 'SAVED': (2, saved), 'SAVED_COPY': (2, saved_copy), 'MARK': (0, 0x4153), 'MARK2': (0, 0x3253), 'LIBLIST': (1, lib + 47), 'CONLIST': (1, con + 27),
               'DEFAULT_BYTES': (0, 'db ' + ', '.join(str(b) for b in defaults)),
               'SLOT4_CUP': (2, slot4_cup), 'SLOT4': (2, slot4), 'SLOT_SIZE': (0, 0x443), 'LEAGUE_SUBS': (2, league_subs),
               'CSEG_8DAC3': (1, c8dac3), 'PLAYOFF_OUT': (1, po_out), 'PLAYOFF_CONT': (1, po + 13),
               'DONE': (1, done), 'LOAD_OUT': (1, load_out), 'LOAD_CONT': (1, load0 + 10), 'LOAD_MAP': (1, load_map)}
    chain, load_map_lines = [], []
    for k, off in enumerate(caf['structs']):
        symbols[f'XCUP{k}'] = (1, off)
        chain += [f'    mov dword [A0], XCUP{k}', f'    mov word [D7], {6 + k}', '    call CHECK', '    jz .found']
        load_map_lines += [f'    mov dword [A0], XCUP{k}', f'    cmp word [E092F], {6 + k}', '    je LOAD_MAP']
    symbols['KIND_BYTES'] = (0, 'db ' + ', '.join(str(x) for x in [0, 1, 2] + caf['kinds']))
    symbols['NEW_CAREER_PTR'] = (1, caf['new_career_ptr'])     # filled by trailer.patch (assembled after us)
    symbols['MARK3_AT'] = (2, table + MARK3_GLOBAL)
    symbols['MARK3'] = (0, MARK3)
    TABLES[0] = (table, copies_base)
    SAVE_ITEMS[0] = [(lib + 47, 2 * LIB_N), (sup + 27, 32), (con + 27, 32), (cups_all[3] + 24, 4)]   # Lib, Sup, CON, INT pair
    asm = CAREER_ASM.replace(';EXTRA_CHAIN', '\n'.join(chain)).replace(';EXTRA_LOAD', '\n'.join(load_map_lines))
    code, fix = nasmcave.assemble(asm, cave, symbols)
    labels = nasmcave.labels(asm, cave, symbols)
    LISTS_OUT[0] = labels['lists_out']
    p.put(1, cave, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, cave + off, tobj, toff)
    hook(p, init, 11, init + 3, labels['init_sa'])
    p.remove(1, found + 2)                                                # mov ax,[D7]; mov [E092F],ax (12 B)
    hook(p, found, 12, found + 8, labels['euro_found'])
    hook(p, load0, 10, load0 + 3, labels['load_slot1'])
    hook(p, load, 12, load + 3, labels['load_slot3'])
    p.put(1, done + 1, struct.pack('<i', labels['int4_step'] - (done + 5)))    # call cseg_8DAC3 -> int4_step
    hook(p, po, 13, po + 2, labels['playoffs'])
    print(f'exe: Intercontinental slot 4: call obj1+{done:#x} -> int4_step, play-offs obj1+{po:#x} (slot4 buf obj2+{slot4:#x}, '
          f'league subs obj2+{league_subs:#x})')
    print(f'exe: career hooks InitializeNewSeason obj1+{init:#x}, ProcessCareerFile obj1+{load0:#x}/{load:#x}, '
          f'Supercopa -> slot 1 (slot1 buf obj2+{slot1:#x}, cseg_8B2D3 obj1+{c8b2d3:#x})')
    return cave + len(code)


# --- season end: next season's qualifiers from the SA league standings -------
# cseg_91428 (season end) calls cseg_92D55 first; that call is redirected to
# sa_qualify, which for each country runs cseg_915ED (the engine's own
# foreign-league path = the world-view simulation, so tables match what the
# player sees), reads the final table from DIY_competitionStart (+6Dh: row
# offsets in finishing order, rows 12h bytes; +12Dh: team number per row)
# and writes the teams into the cup lists, then jumps on to cseg_92D55.
# The player's own top division is read from season slot 0 instead (same
# layout, cseg_8B71C copies it into DIY_competitionStart), i.e. the real table.
# Supercopa keeps its fixed list (former Libertadores winners).
LIB_Q = [  # 5 groups of 4 = champion and runner-up of two countries (1997 pairings)
    (BOL, 1), (PAR, 1), (BOL, 2), (PAR, 2),
    (ARG, 1), (ECU, 1), (ARG, 2), (ECU, 2),
    (CHI, 1), (VEN, 1), (CHI, 2), (VEN, 2),
    (BRA, 1), (PER, 1), (BRA, 2), (PER, 2),
    (URU, 1), (COL, 1), (URU, 2), (COL, 2),
]
CON_Q = [  # consecutive pairs meet in round 1
    (ARG, 3), (VEN, 3), (BRA, 3), (BOL, 3), (ARG, 4), (ECU, 3), (BRA, 4), (PER, 3),
    (CHI, 3), (URU, 3), (COL, 3), (PAR, 3), (ARG, 5), (CHI, 4), (BRA, 5), (URU, 4),
]

QUALIFY_ASM = '''
sa_qualify:
    mov dword [A4], LIB             ; cseg_92D55 without its first instruction (A4 = euroCupCopy):
    call CSEG_92D55 + 10            ; ends the cup (played or simulated), winner -> [HOLDER]
    mov ax, [HOLDER]
    mov [LIBWIN], ax
    mov esi, QTABLE
.country:
    mov eax, [esi]
    cmp eax, -1
    je .done
    mov edi, SLOT0                  ; player's own top division: the table actually played
    cmp eax, [PLAYER_LEAGUE]
    jne .simulate
    cmp word [PLAYER_DIV], 0
    je .read
.simulate:
    mov [A4], eax
    mov word [D7], 0
    push esi
    call CSEG_915ED
    pop esi
    mov edi, DIY
.read:
    movzx ecx, byte [esi+4]
    add esi, 5
.entry:
    movzx eax, byte [esi]
    movzx eax, word [edi + 6Dh - 2 + eax*2]
    xor edx, edx
    mov ebx, 12h
    div ebx
    mov ax, [edi + 12Dh + eax*2]
    mov ebx, [esi+1]
    mov [ebx], ax
    add esi, 5
    dec ecx
    jnz .entry
    jmp .country
.done:
    mov ax, [LIBWIN]                ; holder: straight to the round of 16 (21st club, lib97)
    cmp ax, -1
    je .end
    mov [LIBLIST + 2 * LIB_GROUPS], ax
    mov esi, LIBLIST                ; also qualified through its league? that berth goes to its country's 3rd...
    mov ecx, LIB_GROUPS
.inlib:
    cmp [esi], ax
    je .berth
    add esi, 2
    loop .inlib
    mov edi, CONLIST                ; in the CONMEBOL list? its place goes to the next club of its country
    mov ecx, 16
.incon:
    cmp [edi], ax
    je .conplace
    add edi, 2
    loop .incon
    jmp .supercopa
.berth:
    call .ctry
    jc .supercopa
    movzx edx, byte [SPARE_TAB + ebx*2 + 1]
    mov cx, [CONLIST + edx*2]       ; ... the 3rd moves up from the CONMEBOL list ...
    mov [esi], cx
    mov cx, [SPARE + ebx*2]         ; ... and the next club takes its CONMEBOL place
    mov [CONLIST + edx*2], cx
    jmp .supercopa
.conplace:
    call .ctry
    jc .supercopa
    mov cx, [SPARE + ebx*2]
    mov [edi], cx
    jmp .supercopa
.ctry:                              ; al = country -> ebx = its SPARE_TAB row (CF = none)
    xor ebx, ebx
.cl:
    cmp [SPARE_TAB + ebx*2], al
    je .cf
    inc ebx
    cmp ebx, SPARE_N
    jb .cl
    stc
    ret
.cf:
    clc
    ret
.supercopa:                         ; former champions: a new one takes the last place
    mov esi, SUPLIST
    mov ecx, 16
.insup:
    cmp [esi], ax
    je .end
    add esi, 2
    loop .insup
    mov [SUPLIST + 30], ax
.end:
    call CSEG_92D55                 ; the real Champions Cup end: its winner -> [HOLDER]
    mov ax, [HOLDER]                ; next season's Intercontinental: Champions Cup winner ...
    cmp ax, 0FFFFh
    je .nocc
    mov [INTLIST], ax
.nocc:
    mov ax, [LIBWIN]                ; ... vs Libertadores winner
    cmp ax, 0FFFFh
    je .nolib
    mov [INTLIST + 2], ax
.nolib:
    call LISTS_OUT
    ret
LIBWIN: dw 0FFFFh
SPARE_TAB: SPARE_TAB_BYTES          ; per country: db country, CONMEBOL list position of its 3rd
SPARE: times SPARE_N dw 0           ; per country: the club after its last CONMEBOL rank (season-end table)
'''


def qualify_hook(p, cups, cave, intlist, extra_q=()):
    d1 = p.le.obj_bytes(1)
    lib, sup, con = cups
    # cseg_915ED: call nullsub; mov eax,[A4]; mov [A0],eax; mov ax,[D7]; mov [D0],ax
    f915 = unique(d1, bytes.fromhex('e8faffffff a1') )
    assert d1[f915 + 10] == 0xa3 and d1[f915 + 15:f915 + 17] == b'\x66\xa1'
    a4 = struct.unpack_from('<I', d1, f915 + 6)[0]
    d7 = struct.unpack_from('<I', d1, f915 + 17)[0]
    # cseg_927A2: mov [A2], offset DIY_competitionStart; mov eax,[A2]; add eax,6Dh
    sig = bytes.fromhex('83c06d')
    hits = [i for i in range(len(d1) - 3) if d1[i:i + 3] == sig and d1[i - 5] == 0xa1 and d1[i - 15:i - 13] == b'\xc7\x05'
            and d1[i - 13:i - 9] == d1[i - 4:i]]
    diys = {p.target(1, h - 9) for h in hits}      # cseg_927A2 and two similar readers
    assert len(diys) == 1, diys
    diy_obj, diy = diys.pop()
    assert diy_obj == 2
    # season end: call cseg_92D55; call cseg_9307A; call cseg_9339D; mov word [careerFileBuffer], 0
    site = [i for i in range(len(d1) - 24) if d1[i] == 0xe8 and d1[i + 5] == 0xe8 and d1[i + 10] == 0xe8
            and d1[i + 15:i + 18] == b'\x66\xc7\x05' and d1[i + 22:i + 24] == b'\x00\x00'
            and d1[i + 24:i + 26] == b'\x66\xa1']
    tgt = lambda i: i + 5 + struct.unpack_from('<i', d1, i + 1)[0]
    site = [i for i in site if 0 < tgt(i + 5) - tgt(i) < 0x1000 and 0 < tgt(i + 10) - tgt(i + 5) < 0x1000]
    assert len(site) == 1, site
    site = site[0]
    c92d55 = site + 5 + struct.unpack_from('<i', d1, site + 1)[0]

    code_at = cave
    # cseg_3AA17: mov [A1], offset competitionFileBuffer; mov eax,[dseg_D8CAA]; cmp [A0],eax; jnz; mov ax,[dseg_D6CDC]
    import re
    r = regs(d1)
    a1, a0 = (re.escape(struct.pack('<I', r[k])) for k in ('A1', 'A0'))
    m = [x for x in re.finditer(rb'\xc7\x05' + a1 + rb'(.{4})\xa1(.{4})\x39\x05' + a0 + rb'\x75.\x66\xa1(.{4})', d1, re.S)]
    assert len(m) == 1, len(m)
    slot0, pleague, pdiv = (struct.unpack('<I', g)[0] for g in m[0].groups())
    # cseg_92F1C stores the Champions Cup winner: mov al,[esi+2CDh] ... mov [dseg_18070F],ax
    k = d1.find(bytes.fromhex('8a86cd020000'), c92d55)
    assert 0 < k - c92d55 < 0x400
    while True:
        k = d1.find(b'\x66\xa3', k + 1)
        holder = struct.unpack_from('<I', d1, k + 2)[0]
        if holder not in (a4, d7) and not r['A0'] - 0x40 <= holder < r['A0'] + 0x40:   # skip the D0..A6 pseudo registers
            break
    assert d1[c92d55:c92d55 + 2] == b'\xc7\x05' and d1[c92d55 + 10] == 0xa1
    # holder rule (session 27): per SA country its 3rd's CONMEBOL position and a spare club (the rank after its last
    # CONMEBOL rank), read at season end with the other ranks into SPARE
    spare_c = list(dict.fromkeys(c for c, _ in LIB_Q))
    spare_q = [(c, max(r for c2, r in LIB_Q + CON_Q if c2 == c) + 1) for c in spare_c]
    third = [CON_Q.index((c, 3)) for c in spare_c]
    spare_tab = 'db ' + ', '.join(f'{c}, {t}' for c, t in zip(spare_c, third))
    symbols = {'LISTS_OUT': (1, LISTS_OUT[0]), 'LIB': (1, lib), 'LIBLIST': (1, lib + 47), 'CONLIST': (1, con + 27), 'SUPLIST': (1, sup + 27), 'HOLDER': (2, holder), 'LIB_N': (0, LIB_N),
               'LIB_GROUPS': (0, LIB_GROUPS), 'SPARE_N': (0, len(spare_c)), 'SPARE_TAB_BYTES': (0, spare_tab),
               'SLOT0': (2, slot0), 'PLAYER_LEAGUE': (2, pleague), 'PLAYER_DIV': (2, pdiv), 'A4': (2, a4), 'D7': (2, d7), 'DIY': (2, diy), 'CSEG_915ED': (1, f915),
               'CSEG_92D55': (1, c92d55), 'QTABLE': (1, 0), 'INTLIST': (1, intlist)}
    code, _ = nasmcave.assemble(QUALIFY_ASM, code_at, symbols)
    spare = nasmcave.labels(QUALIFY_ASM, code_at, symbols)['SPARE']
    extra_q = list(extra_q) + [(spare, spare_q)]
    # qualification table: per country dd league, db n, n x (db rank, dd dest)
    table = bytearray()
    ptrs = []                       # (offset in table, tobj, toff)
    per = {}
    for base, lst in [(lib + 47, LIB_Q), (con + 27, CON_Q)] + extra_q:   # + CAF cups, + SPARE
        for pos, (c, rank) in enumerate(lst):
            per.setdefault(c, []).append((rank, base + 2 * pos))
    for c, entries in per.items():
        league = p.target(*p.target(2, COMP_TABLE[0] + 4 * c))     # country tables of new countries live in obj1
        ptrs.append((len(table), *league))
        table += bytes(4) + bytes((len(entries),))
        for rank, dest in entries:
            table += bytes((rank,))
            ptrs.append((len(table), 1, dest))
            table += bytes(4)
    table += b'\xff' * 4

    table_at = (code_at + len(code) + 3) & ~3
    symbols['QTABLE'] = (1, table_at)
    code, fix = nasmcave.assemble(QUALIFY_ASM, code_at, symbols)
    p.put(1, code_at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, code_at + off, tobj, toff)
    p.put(1, table_at, table)
    for off, tobj, toff in ptrs:
        p.add_ptr(1, table_at + off, tobj, toff)
    p.put(1, site + 1, struct.pack('<i', code_at - (site + 5)))
    print(f'exe: season-end qualifiers @ obj1+{code_at:#x} ({len(code)} B code, {len(per)} countries), '
          f'hook call obj1+{site:#x} (cseg_92D55 obj1+{c92d55:#x}, DIY obj2+{diy:#x})')
    return table_at + len(table)
