"""4.1.2 zone positions (split.py ZP_ASM, Enzo / Davide 12/11): harness scenarios, registered into swostest by
register() (swostest.py: the import line only).

Leagues in zones by membership (Argentina, Panama: 2 zones; the MLS: 2 conferences) are one table, the 2nd zone under
the 1st. The board must judge the club on its place IN ITS ZONE (scaled to the league: pz x N / z) and the season
record must show that place; at the season end the stage titles won (Apertura / Clausura / Trofeo) count as cups won.

Each scenario: a career season (world8485, W8485_ONE, no no-sacking poke) at one club, read-only memory logs:
competitionFileBuffer's table order (+6Dh), the chairman's warning stage (D6B58) and expected place (D6C50), GP_ST's
stage decisions, the season record. Checks:
- every mid-season warning comes (cseg_3CCF0) with the zone ratio (expected - zone place scaled) x 100 / N at -25% or
  below, or the scaled place in the league's last relegation places (+57h + +59h, min 1, when +5Fh), never while the
  club leads its zone;
- the club's row from selTeamNumber and the table's team numbers (team >> 8 = the pack ordinal), not the pack order;
- the record's league place byte (+56h) = the zone place;
- the season-end opinion = ShowChairmanOpinionAboutTheSeason's formula on the zone place, minus 2 per stage title won
  (the dec slots, or 'VINCITORI' on the record screen), with the expected place it uses (moreExpensiveTeamsCount) and
  two rules of the original game kept as they are: its ratio divides with edx cleared (a club below its expected place
  gets a noise ratio: _verdict), and each career competition (D8CAE / D8CB2 / D8CB6) whose FINAL the club reached, won
  or lost, takes 2 / 2 / 3 (a tournament among them is not modelled: then "no worse than" only);
- the opinion's career-competitions term (ShowChairmanOpinionAboutTheSeason: -2 / -2 / -3 for each of dseg_D8CAE /
  D8CB2 / D8CB6 where FindTeamInDIY < 2, i.e. a final reached, won or lost) is read from their DIY buffers at the
  opinion's screen;
- world_zone_mlt (control, no zones): Malta on this checkout and on ZONE_BASE (default: the 4.1.2 base d33bc3d built
  the same way): both follow the game's own rules on the whole table. (A pinned-RNG byte compare is no use: the two
  exes' seasons diverge.)
Env: W2627REL_DATA (the world data; default world5tm-403c19), ZONE_BUILD / ZONE_KBUILD / ZONE_BASE (ready builds).
Titles: GPLAY_KOFORCE=2 test builds (the career club wins the knockout ties it plays), never in a release.
"""
import json
import os
import struct
import sys

T = None
MSG = ['COMPLIMENTI', 'UNA BUONA', 'ALTERNA', 'NON BUONA', 'DELUDENTE']   # (IT texts of messages 13..17)


def _data():
    return os.environ.get('W2627REL_DATA') or os.path.join(T.MAIN, 'internal', 'world2526', 'world5tm-403c19')


def _build(name, env=None, branch=None):
    src = _data()
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    packs = ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])
    return T.build(name, env={'SEASON_PACKS': packs, **(env or {})}, branch=branch)


def _exe(kind):
    var = {'w': 'ZONE_BUILD', 'k': 'ZONE_KBUILD', 'base': 'ZONE_BASE'}[kind]
    if not os.environ.get(var):
        os.environ[var] = (_build('zonepos_w') if kind == 'w' else
                           _build('zonepos_wk2', {'GPLAY_KOFORCE': '2'}) if kind == 'k' else
                           _build('zonepos_base', branch=os.environ.get('ZONE_BASE_REF', 'd33bc3d')))
    return os.environ[var]


def _cfb(exe):
    sys.path.insert(0, os.path.join(T.ROOT, 'tools'))
    import careerworld
    import lepatch
    return careerworld.sites(lepatch.LEPatch(os.path.join(T.MAIN, 'orig', 'ITALIAN.EXE')))['cfb'] + 0x15F6A


# The season-end opinion's three career competitions (ShowChairmanOpinionAboutTheSeason): the flags dseg_D8CAE /
# D8CB2 / D8CB6 and their DIY buffers D8D0A / D985C / DA0E2, as offsets from the no-sacking word D6B62 (nosack_off).
CUPS, CUPB, CUPK = 0x214c, (0x21a8, 0x2cfa, 0x3580), (2, 2, 3)


def _addrs():
    """obj2 offsets (the original IT exe's patterns): selTeamNumber (the opinion's `mov ax, [selTeamNumber]` after
    `mov A6, offset competitionFileBuffer`) and moreExpensiveTeamsCount (GetMoreExpensiveTeamsCount's end: the D2
    the opinion uses)."""
    import re
    sys.path.insert(0, os.path.join(T.ROOT, 'tools'))
    import lepatch
    import sacups
    d1 = lepatch.LEPatch(os.path.join(T.MAIN, 'orig', 'ITALIAN.EXE')).le.obj_bytes(1)
    a0 = sacups.regs(d1)['A0']
    A = lambda x: re.escape(struct.pack('<I', x))
    cfb = _cfb(None)
    sel = {struct.unpack('<I', m.group(1))[0] for m in
           re.finditer(rb'\xc7\x05' + A(a0 + 24) + A(cfb) + rb'\x66\xa1(.{4})\x66\xa3' + A(a0 - 32), d1, re.S)}
    mec = [struct.unpack('<I', m.group(1))[0] for m in
           re.finditer(rb'\x66\xa1' + A(a0 - 20) + rb'\x66\xa3' + A(a0 - 24) + rb'\x66\xa3(.{4})\xc3', d1, re.S)]
    assert len(sel) == 1 and len(mec) == 1, (sel, mec)
    return sel.pop(), mec[0]
DEC = 0x7cc                     # offsetof(struct gp_state, dec) (i486 layout: gplay.c, clang -target i686)


def _run(tag, exe, team, rng=None):
    """One season; -> (ok, msg, session.log path, offsets)."""
    ns = T.nosack_off(os.path.join(exe, 'ITALIAN.EXE'))
    cfb = _cfb(exe)
    gp = T.gp_ptrs(exe)
    sel, mec = _addrs()
    hx = [f'{ns - 0xc:x}:4', f'{ns + 0xee:x}:2', f'{cfb + 0x6d:x}:60', f'{sel:x}:2', f'{cfb + 0x12d:x}:64',
          f'{cfb + 0x57:x}:10']
    if gp:
        hx += [f'{gp[1] + DEC:x}:36', f'{T.gp_eu(exe)[4]:x}:106']
    keys = ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K', 'W8485_ONE', 'W8485_TMO',
            'W8485_HEX', 'W8485_NOSACK', 'W8485_RNGSTEP', 'W8485_RECSHOT')
    keep = {k: os.environ.get(k) for k in keys}
    for k in ('W8485_NOSACK', 'W8485_RNGSTEP'):
        os.environ.pop(k, None)
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5',
                      W8485_K='108+', W8485_ONE='1', W8485_TMO='900', W8485_HEX=','.join(hx), W8485_RECSHOT='1')
    if rng:
        os.environ['W8485_RNGSTEP'] = rng
    tag0 = os.environ.get('SWOSTEST_SCENARIO')
    os.environ['SWOSTEST_SCENARIO'] = tag
    press0 = T.press

    def press(s_, scr, *a, **k):            # (the table at the season-end notes too: the opinion reads it there,
        try:                                #  after the last match day's pause)
            if 'NOTA DEL PRESIDENTE' in ' '.join(scr.texts()) or (a and a[0] == 'CONTINUA CARRIERA'):
                for o, n in [(ns + CUPS, 12), (cfb + 0x12d, 128), (sel, 2), (mec, 2)] + [(ns + b, 0x400) for b in CUPB]:
                    s_.log.append(f'HEX {o:x} {bytes(s_.result.obj2(o, n)).hex()}')
                s_.log.append(f'HEX {cfb + 0x6d:x} {bytes(s_.result.obj2(cfb + 0x6d, 60)).hex()}')
        except Exception:
            pass
        return press0(s_, scr, *a, **k)
    T.press = press
    try:
        ok, msg = T.world8485()
        path = os.path.join(T.RUNS, T.w84_tag() + '_1', 'session.log')
    finally:
        T.press = press0
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if tag0 is None:
            os.environ.pop('SWOSTEST_SCENARIO', None)
        else:
            os.environ['SWOSTEST_SCENARIO'] = tag0
    return ok, msg, path, (ns, cfb + 0x6d, gp and gp[1] + DEC, sel, mec)


def _verdict(p, e, n, t, c=0):            # ShowChairmanOpinionAboutTheSeason's club path, then the clamp
    # (c: the career competitions' term, 2 / 2 / 3 each reached a final.) The ratio as the game computes it:
    # `movsx eax, D0; imul 100; xor edx, edx; idiv N` - edx is cleared, not sign-extended, so a club BELOW its
    # expected place divides 2^32 + (e - p) x 100: the low word then reads as noise (Malta -100 / 12 -> 554Dh, kind;
    # Argentina -400 / 30 -> 887Bh, harsh). Breakpoint-checked at cseg_3C271 (12/11). The original game's own rule.
    d0 = (((e - p) * 100) & 0xffffffff) // n & 0xffff
    d0 -= 0x10000 if d0 & 0x8000 else 0
    d7 = 0
    if p != 0 and d0 < 30:
        d7 = 1 if d0 >= 10 else 2 if d0 > -10 else 3 if d0 > -30 else 4
    q = p * 100 // n
    d7 += (-1 if q <= 25 else 0) + (1 if q >= 75 else 0) - 2 * t - c
    return MSG[max(0, min(4, d7))]


def _find(b, team):
    """FindTeamInDIY's D1 for a league / cup DIY buffer (b = its bytes); None for a tournament (not modelled)."""
    w = lambda o: struct.unpack_from('<H', b, o)[0]
    n = w(0x31)
    if w(0) == 0:                           # league: the place in the sorted order (+109)
        for d1 in range(n):
            r = w(109 + 2 * d1) // 18
            if 301 + 2 * r + 2 <= len(b) and w(301 + 2 * r) == team:
                return d1
        return 0xffff
    if w(0) != 1:
        return None
    for d1 in range(n):                     # cup: the slot in the draw order (+717 bytes -> +589 team numbers)
        x = (struct.unpack_from('<b', b, 717 + d1)[0] * 2) & 0xffff
        if 589 + x + 2 <= len(b) and w(589 + x) == team:
            break
    else:
        return 0xffff
    if w(85) and d1 < 2:                    # (finished: 0 = the winner, 1 = the other finalist)
        return 0 if w(57) == team else 1
    d0 = w(79) * 2
    return d0 // 2 - 1 if d1 < d0 else 0xffff


def _cupterm(hexes, ns, cfbo, me):
    """The opinion's career-competitions term from the HEX dumps at its screen; None if a tournament is involved."""
    try:
        flags = hexes[ns + CUPS]
        team = struct.unpack_from('<H', hexes[cfbo - 0x6d + 0x12d], 2 * me)[0]
    except KeyError:
        return 0
    c = 0
    for i, (bo, k) in enumerate(zip(CUPB, CUPK)):
        if not struct.unpack_from('<I', flags, 4 * i)[0]:
            continue
        d1 = _find(hexes[ns + bo], team)
        if d1 is None:
            return None
        c += k if d1 < 2 else 0
    return c


def _read(log, country, key, offs):
    """The run's events: [(kind, value, place)] and the facts at the season-end opinion."""
    ns, cfbo, deco = offs[:3]
    sel, mec = offs[3:] if len(offs) > 3 else (None, None)
    pack = os.path.join(_data(), country)
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = pack
    import importlib
    import mkseason
    importlib.reload(mkseason)
    pk = next(iter(mkseason.packs()))
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    rows = [k for k in pk.league_clubs if pk.division[k] == pk.division[key]]
    me, n = rows.index(key), len(rows)
    ordk = {pk.where[k][1]: k for k in rows}            # (a table row's club: its team number >> 8 = the ordinal)
    pj = json.load(open(os.path.join(pack, 'pack.json'), encoding='utf-8'))
    div = next((x for c in pj['competitions'] for x in c.get('divisions', []) if x.get('split')), None)
    zones = div and div['split'].get('stages') and div['split']['stages'][0].get('zones')
    zof = lambda k: next((g for g, z in enumerate(zones) if k in z), -1) if zones else 0
    grp = [zof(k) for k in rows]
    z = grp.count(grp[me])
    cur, exp, titles, ev, at_msg, pend, hexes, rel = {}, 0, 0, [], None, None, {}, None
    for ln in open(log, errors='replace'):
        if ln.startswith('HEX '):
            _, o, v = ln.split()
            o, b = int(o, 16), bytes.fromhex(v)
            hexes[o] = b
            if o == cfbo - 0x6d + 0x57:         # (cseg_3CCF0's relegation places: +57h + +59h, min 1, if +5Fh)
                rel = struct.unpack_from('<H', b, 8)[0] and max(1, sum(struct.unpack_from('<HH', b)) & 0xffff)
            if o == cfbo and len(b) >= 2 * n:
                order = [struct.unpack_from('<H', b, 2 * k)[0] // 18 for k in range(n)]
                tl, sv = hexes.get(cfbo - 0x6d + 0x12d), hexes.get(sel)
                if tl and sv:                   # (the club's row from selTeamNumber, not the pack's order)
                    tn = [struct.unpack_from('<H', tl, 2 * k)[0] for k in range(min(n, len(tl) // 2))]
                    t = struct.unpack('<H', sv[:2])[0]
                    if t in tn:
                        me = tn.index(t)
                        grp = [zof(ordk.get(x >> 8)) for x in tn]
                if me in order:
                    pos = order.index(me)
                    pz = sum(1 for r in order[:pos] if grp[r] == grp[me])
                    cur = dict(comb=pos + 1, zone=pz + 1, scaled=pz * n // z)
                if pend:                    # (the table read at the opinion's own screen)
                    e2 = struct.unpack('<H', hexes[mec])[0] if mec in hexes else pend[2]
                    at_msg, pend = (pend[0], dict(cur), e2, pend[3], _cupterm(hexes, ns, cfbo, me)), None
            elif o == ns - 0xc:
                ev.append(('stage', struct.unpack('<H', b[2:4])[0], dict(cur), exp))
            elif o == ns + 0xee:
                exp = struct.unpack('<H', b)[0]
                ev.append(('exp', exp, dict(cur), exp))
            elif deco and o == deco:
                titles = sum(1 for i in range(3) if b[12 * i + 1] == 1 and b[12 * i + 2] == 1)
                ev.append(('titles', titles, dict(cur), exp))
            elif len(b) == 106 and b[0x56]:
                ev.append(('record', b[0x56], dict(cur), exp))
        elif ln.startswith('[record]'):       # (the stage titles the record lists as won: also a title won in the
            import re                       #  live play-off tie, which the dec slots do not hold yet)
            titles = max(titles, len(re.findall(r'(?:APERTURA|CLAUSURA|TROFEO)[^|]*\| VINCITORI', ln)))
        elif 'RIMUOVERTI DALLA TUA POSIZIONE' in ln:
            ev.append(('sacked', 1, dict(cur), exp))
        elif ln.startswith('[ns]') and any(m in ln.split('|')[2] for m in MSG) and at_msg is None and not pend:
            pend = (ln.split('|')[2].strip(), dict(cur), exp, titles)
    if pend:
        at_msg = pend + (_cupterm(hexes, ns, cfbo, me),)
    return dict(n=n, z=z, zones=bool(zones), ev=ev, at_msg=at_msg, rel=rel)


def _check_zoned(r, errs, want_titles=False):
    n = r['n']
    prev = 0
    for kind, v, cur, exp in r['ev']:
        if kind == 'stage':
            if v > prev and cur:            # (cseg_3CCF0: ratio <= -25%, or in the relegation places)
                ratio = int((exp - cur['scaled']) * 100 / n)
                low = r.get('rel') is not None and r['rel'] and cur['scaled'] >= n - r['rel']
                T.check(ratio <= -25 or low, f'warning {v} with the club {cur["zone"]} of its zone (expected {exp}, '
                        f'ratio {ratio}%: not -25% or below, not in the last {r.get("rel")} places)', errs)
                T.check(cur['zone'] != 1, f'warning {v} while leading its zone {cur}', errs)
            prev = v
        elif kind == 'exp':
            T.check(exp % (n // r['z']) == 0, f'expected place {exp} not scaled to the league ({n} / {r["z"]})', errs)
    recs = [(v, cur) for kind, v, cur, _ in r['ev'] if kind == 'record']
    T.check(recs, 'no season record written', errs)
    sacked = any(k == 'sacked' for k, *_ in r['ev'])
    if recs:
        v, cur = recs[-1]
        if r['at_msg']:                     # (the record shot comes after the new season's table: the place is the
            cur = r['at_msg'][1]            #  one at the season-end opinion)
        if not (sacked and v > n):          # (a sacking writes its own code: '- LICENZIATO -')
            T.check(cur and v == cur['zone'], f'record place {v}, the zone place {cur}', errs)
    if sacked:
        return 'sacked mid-season (every warning in-zone)'
    T.check(r['at_msg'], 'no season-end opinion', errs)
    if r['at_msg']:
        text, cur, exp, t, c = r['at_msg']
        p = cur.get('scaled', 0)
        if c is None:                       # (a tournament among the career competitions: only "no worse")
            top = _verdict(p, exp, n, t)
            got = next((i for i, m in enumerate(MSG) if m in text), 9)
            T.check(got <= MSG.index(top), f'opinion {text!r} worse than {top} (zone {cur}, expected {exp}, '
                    f'titles {t}, a tournament not modelled)', errs)
            want, c = f'<= {top}', '?'
        else:
            want = _verdict(p, exp, n, t, c)
            T.check(want in text, f'opinion {text!r}: expected {want} (zone {cur}, expected place {exp}, titles {t}, '
                    f'finals term {c})', errs)
        if want_titles:
            T.check(t >= 1, f'no stage title won in the forced build (titles {t})', errs)
            base = _verdict(p, exp, n, 0, 0 if c == '?' else c)
            return f'zone {cur}, titles {t}, finals term {c}: opinion {want} (without the titles: {base})'
        return f'zone {cur}, expected {exp}, finals term {c}: opinion {want}'
    return ''


def _zoned(tag, country, key, team, kind='w'):
    exe = _exe(kind)
    ok, msg, log, offs = _run(tag, exe, team)
    errs = []
    T.check(ok, f'the season: {msg}', errs)
    r = _read(log, country, key, offs)
    T.check(r['zones'], f'{country}: no zones in the pack', errs)
    s = _check_zoned(r, errs, kind == 'k')
    warns = sum(1 for k, v, *_ in r['ev'] if k == 'stage' and v)
    return not errs, '; '.join(errs) or f'{key}: {warns} warnings, all in-zone; {s}'


def register(mod):
    global T
    T = mod
    sc = mod.scenario

    @sc
    def world_zone_arg2():
        """4.1.2 zone positions: RIVER PLATE (Argentina, zone 2): warnings, record place and the season-end opinion
        on its place in its zone (not the combined table: Enzo's sacking)"""
        return _zoned('zone_arg2', 'arg', 'riverplate', 'SUDAMERICA,ARGENTINA,LIGA PROFESIONAL,RIVER PLATE')

    @sc
    def world_zone_arg1():
        """4.1.2 zone positions: BOCA JUNIORS (Argentina, zone 1: no longer over-rated by the combined table)"""
        return _zoned('zone_arg1', 'arg', 'bocajuniors', 'SUDAMERICA,ARGENTINA,LIGA PROFESIONAL,BOCA JUNIORS')

    @sc
    def world_zone_mls():
        """4.1.2 zone positions: LOS ANGELES (MLS, Western Conference = zone 2)"""
        return _zoned('zone_mls', 'usa', 'losangeles', 'NORDAMERICA,USA,?MLS WESTERN CONFERENCE,LOS ANGELES')

    @sc
    def world_zone_arg_titles():
        """4.1.2 stage titles: RIVER PLATE on a GPLAY_KOFORCE=2 test build (wins the Apertura / Clausura knockouts):
        the season-end opinion counts each title won as a cup (-2)"""
        return _zoned('zone_argt', 'arg', 'riverplate', 'SUDAMERICA,ARGENTINA,LIGA PROFESIONAL,RIVER PLATE', 'k')

    @sc
    def world_zone_pan_titles():
        """4.1.2 zone positions + stage titles: VERAGUAS UNITED (Panama, zone 2's strongest: it reaches the play-offs)
        on the GPLAY_KOFORCE=2 test build"""
        return _zoned('zone_pant', 'pan', 'veraguasunited', 'NORDAMERICA,PANAMA,VERAGUAS UNITED', 'k')

    @sc
    def world_zone_mlt():
        """4.1.2 control (no zones): FLORIANA (Malta) on this checkout and on the 4.1.2 base (ZONE_BASE): both follow
        the game's own rules on the whole table (warnings, expected place, record place, the season-end opinion)"""
        out, errs = [], []
        for tag, kind in (('zone_mltn', 'w'), ('zone_mlto', 'base')):
            ok, msg, log, offs = _run(tag, _exe(kind), 'EUROPA,MALTA,FLORIANA')
            if not ok:
                return False, f'{kind}: the season: {msg}'
            r = _read(log, 'mlt', 'floriana', offs)
            e = []
            T.check(not r['zones'] and r['z'] == r['n'], f'{kind}: Malta has zones?', e)
            out.append(f'{kind}: ' + _check_zoned(r, e))
            errs += [f'{kind}: {x}' for x in e]
        return not errs, '; '.join(errs) or ' / '.join(out)
