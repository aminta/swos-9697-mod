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

NAMES = {'it': b'STORICI', 'en': b'CLASSICS', 'fr': b'CLASSIQUES', 'de': b'KLASSIKER'}

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

ASM = '''
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

    pre_call, season_call, select = _calls(p)
    symbols = {'COMP254': (2, comp + 4 * 254), 'WORLD_PRESET': (1, wpre), 'SELECT': (1, select)}
    code, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, pre_call + 1, struct.pack('<i', labels['hist_preset'] - (pre_call + 5)))
    # season: no historic league yet -> its call stays on the original world table
    print(f'exe: historic: {name.decode()} = country {CLASSICS}, {full.decode()} id {WC82_ID:#x} @ obj1+{wc82:#x}, '
          f'preset call obj1+{pre_call:#x} -> obj1+{labels["hist_preset"]:#x} (season call obj1+{season_call:#x} untouched)')
    return (at + len(code) + 3) & ~3
