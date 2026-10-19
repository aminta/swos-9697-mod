"""'Every country, every competition': the playable competitions of a release and their formats, EN + IT.

One renderer (the layout and every phrase, English and Italian) over a neutral model, so that a format reads the same
in every release; readers build the model:
- from_packs(dirs): career-world packs (pack.json + clubs.csv + ties.csv; World 2026-27);
- from_build9697(build): the 1996-97 base game + its packs (4.0's reader, to come).

Usage: python3 tools/complist.py world [--approx F] [--staged F] [--out F] PACK_DIR ...
  --approx F  JSON {country code: [{"en": ..., "it": ...}]}: the release notes' declared approximations (marked)
  --staged F  JSON {country code: {"en": ..., "it": ...}}: final texts of formats still being built (an HTML comment)
  --out F     write the document there (default stdout); --summary F: the short block for the release notes

MODEL (plain dicts): {'europe': {en, it} | None (the European cups' own formats, rendered once at the head),
'countries': [country]}; country = {code, name: {en, it}, continent, order, comps: [comp], europe: {first, places},
europe_extra: [{en, it}], approx: [{en, it}], staged: {en, it}}; every comp carries modes (['career', 'season',
'preset']), since (the version that introduced / changed it, or None), source ({en, it} or None: a footnote);
comp = {kind: 'league', levels: [[div]], special: [{en, it}]} | {kind: 'cup' | 'league_cup', name, clubs, size,
rounds: [round code], byes, real_pairs, ties, src ('real' / 'generated'), numbered, europe}; div = {name, clubs,
games, up, down, split, playoffs: [po]}. Round codes: single / single_et / two_legs (mkseason.ROUND).
"""
import csv
import json
import os
import sys

CONTINENTS = ['europe', 'north_america', 'south_america', 'asia', 'oceania', 'africa']   # (countries.CONTINENT)
CONT_NAME = {'europe': ('Europe', 'Europa'), 'north_america': ('North and Central America', 'Nord e Centro America'),
             'south_america': ('South America', 'Sud America'), 'asia': ('Asia', 'Asia'),
             'oceania': ('Oceania', 'Oceania'), 'africa': ('Africa', 'Africa')}

# ---------------------------------------------------------------------------------------------------- phrases
P = {
    'en': dict(title='Every country, every competition', clubs='{n} clubs', matchdays='{n} matchdays',
               rr={1: 'single round robin', 2: 'double round robin', 3: 'triple round robin',
                   4: 'quadruple round robin'},
               rest='one club rests each matchday', up=lambda n: f'{n} up', down=lambda n: f'{n} down', closed='no promotion or relegation',
               lowest='the lowest division of the world: nobody goes down',
               groups='{k} parallel groups of {sizes} (each club in the group of its area; promoted and relegated '
                      'clubs join the group of their area)',
               split='after {after} matchdays: {groups}', grp='{a}-{b} {rr}', grp_none='{a}-{b} no more matches',
               pts={'full': '', 'half_up': ', points halved (rounded up)', 'half_down': ', points halved (rounded down)',
                    'reset': ', from 0 points', 'h2h_half': ', from half the points won among them (rounded down)'},
               home={'balance': 'home order: the club that hosted the other fewer times',
                     'reverse1': 'home order: the return legs of the first meeting',
                     'reverse3': 'home order: the club that was away in their 3rd meeting', 'seeded': ''},
               reset='points and figures reset to 0', keep='(the Opening Round table is kept)',
               stage='stage {k}: ', po='{name}: {who}; {rounds}',
               kind={'promotion': 'promotion play-off', 'europe': 'European play-off', 'placement': 'placement play-off',
                     'playout': 'play-out', 'title': 'title play-off'},
               place='{div} {places}', places_one='{a}', places_rng='{a}-{b}', ord=lambda n: f'{n}{_sfx(n)}',
               legs={1: 'single match', 2: 'two legs'},
               host={'listed': 'home order as in the real schedule', 'better': 'the better placed at home (2nd leg)',
                     'drawn': 'home order drawn', 'neutral': 'neutral ground'},
               level={'better': 'level: the better placed goes through', 'et_pens': 'extra time and penalties',
                      'et_better': 'extra time, then the better placed', 'pens': 'penalties'},
               gap='not played when the two clubs are {n}+ points apart', same_club='not played if one club is on both sides',
               seeds='the {a}-{b} seeds of the season\'s rounds', winner_to='the winner to {div}',
               loser_to='the loser to {div}', reserve='the reserve (out of the world)',
               cup='{n} clubs', cup_from='from the {rnd}', real_cup='the real cup: {n} clubs (entering: {ins})',
               in_game='in the game:', cup_real=lambda k, t, season: 'the clubs still in the real '
               f'{season} cup, ' + ('all ' + str(t) if k == t and t > 1 else 'the only' if k == t else f'{k} of the {t}')
               + (' first-round pairs' if t > 1 else ' first-round pair') + ' as really drawn', cup_real0='the clubs still in the real {season} cup',
               cup_gen='every club of the league, drawn by the game',
               byes='{n} byes into the 2nd round',
               rounds={'single': 'single matches (a draw: penalties)', 'single_et': 'single matches, extra time and '
                       'penalties', 'two_legs': 'two legs (aggregate, then extra time and penalties)', 'two_legs_pens': 'two legs (aggregate, then penalties, no extra time)', 'two_legs_ag': 'two legs (away goals, then extra time and penalties)'},
               final='final: {r}', numbered='rounds numbered as in reality',
               finals={'single': 'single match (a draw: penalties)', 'single_et': 'single match, extra time and '
                       'penalties', 'two_legs': 'two legs (aggregate, then extra time and penalties)', 'two_legs_pens': 'two legs (aggregate, then penalties, no extra time)', 'two_legs_ag': 'two legs (away goals, then extra time and penalties)'},
               rounds_k='rounds {a}-{b}: {r}', round_k='round {a}: {r}', same='{k} rounds of {r}',
               modes={'career': 'career', 'season': 'season', 'preset': 'preset competitions'},
               only='only in: {m}', new='new in {v}', src='source: {s}', ueuro='The European cups',
               rnd={2: 'final', 4: 'semi-finals', 8: 'quarter-finals', 16: 'round of 16', 32: 'round of 32',
                    64: 'round of 64'},
               lcup_europe='the winner {e}', europe='Europe', eu_first='season 1: the real 2026-27 league-phase clubs'
               ' ({lst})', eu_none='season 1: no club in the league phases', eu_later='from season 2: {places} by the '
               'simulated association coefficients', eu_cup={'cc': 'Champions League', 'cwc': 'Europa League',
                                                            'uefa': 'Conference League'},
               approx='Declared approximation', staged='Being built', league='League', cupw='Cup',
               lcup='League cup', summary='{c} countries, {d} league divisions, {k} national cups, {l} league cups: '
               'every playable competition and its format, generated from the release build: [{f}]({f}).'),
    'it': dict(title='Ogni nazione, ogni competizione', clubs='{n} squadre', matchdays='{n} giornate',
               rr={1: 'girone di sola andata', 2: 'girone di andata e ritorno', 3: 'girone a tre turni',
                   4: 'girone a quattro turni'},
               rest='a ogni giornata una squadra riposa', up=lambda n: f'{n} promoss' + ('a' if n == 1 else 'e'),
               down=lambda n: f'{n} retrocess' + ('a' if n == 1 else 'e'),
               closed='niente promozioni né retrocessioni',
               lowest='l\'ultima divisione del mondo: nessuna retrocessione',
               groups='{k} gironi paralleli da {sizes} (ogni club nel girone della sua area; promosse e retrocesse '
                      'vanno nel girone della loro area)',
               split='dopo {after} giornate: {groups}', grp='{a}ª-{b}ª {rr}', grp_none='{a}ª-{b}ª nessun\'altra partita',
               pts={'full': '', 'half_up': ', punti dimezzati (per eccesso)', 'half_down': ', punti dimezzati (per difetto)',
                    'reset': ', da 0 punti', 'h2h_half': ', dalla metà dei punti fatti tra loro (per difetto)'},
               home={'balance': 'ordine in casa: chi ha ospitato l\'altra meno volte',
                     'reverse1': 'ordine in casa: il ritorno del primo incontro',
                     'reverse3': 'ordine in casa: chi era in trasferta nel 3° incontro', 'seeded': ''},
               reset='punti e statistiche azzerati', keep='(la classifica dell\'Opening Round resta salvata)',
               stage='fase {k}: ', po='{name}: {who}; {rounds}',
               kind={'promotion': 'play-off promozione', 'europe': 'play-off europeo', 'placement': 'spareggio piazzamenti',
                     'playout': 'play-out', 'title': 'play-off scudetto'},
               place='{div} {places}', places_one='{a}', places_rng='{a}-{b}', ord=lambda n: f'{n}ª',
               legs={1: 'gara unica', 2: 'andata e ritorno'},
               host={'listed': 'ordine in casa come nel calendario vero', 'better': 'in casa la meglio piazzata (al ritorno)',
                     'drawn': 'ordine in casa sorteggiato', 'neutral': 'campo neutro'},
               level={'better': 'in parità passa la meglio piazzata', 'et_pens': 'supplementari e rigori',
                      'et_better': 'supplementari, poi la meglio piazzata', 'pens': 'rigori'},
               gap='non si gioca se le due squadre sono a {n} o più punti', same_club='non si gioca se la stessa squadra è da entrambe le parti',
               seeds='le teste di serie {a}-{b} delle fasi della stagione', winner_to='la vincente in {div}',
               loser_to='la perdente in {div}', reserve='la riserva (fuori dal mondo)',
               cup='{n} squadre', cup_from='{rnd}', real_cup='la coppa vera: {n} squadre (ingressi: {ins})',
               in_game='nel gioco:', cup_real=lambda k, t, season: 'le squadre ancora in corsa nella '
               f'vera coppa {season}, ' + _it_pairs(k, t) + ' del primo turno come nel sorteggio vero',
               cup_real0='le squadre ancora in corsa nella vera coppa {season}',
               cup_gen='tutti i club del campionato, sorteggiati dal gioco',
               byes='{n} esenti fino al 2° turno',
               rounds={'single': 'gara unica (in parità: rigori)', 'single_et': 'gara unica, supplementari e rigori',
                       'two_legs': 'andata e ritorno (somma dei gol, poi supplementari e rigori)', 'two_legs_pens': 'andata e ritorno (somma dei gol, poi rigori senza supplementari)', 'two_legs_ag': 'andata e ritorno (gol in trasferta, poi supplementari e rigori)'},
               final='finale: {r}', numbered='turni numerati come nella realtà',
               finals={'single': 'gara unica (in parità: rigori)', 'single_et': 'gara unica, supplementari e rigori',
                       'two_legs': 'andata e ritorno (somma dei gol, poi supplementari e rigori)', 'two_legs_pens': 'andata e ritorno (somma dei gol, poi rigori senza supplementari)', 'two_legs_ag': 'andata e ritorno (gol in trasferta, poi supplementari e rigori)'},
               rounds_k='turni {a}-{b}: {r}', round_k='turno {a}: {r}', same='{k} turni: {r}',
               modes={'career': 'carriera', 'season': 'stagione', 'preset': 'competizioni predefinite'},
               only='solo in: {m}', new='novità della {v}', src='fonte: {s}', ueuro='Le coppe europee',
               rnd={2: 'dalla finale', 4: 'dalle semifinali', 8: 'dai quarti di finale', 16: 'dagli ottavi di finale',
                    32: 'dai sedicesimi di finale', 64: 'dai trentaduesimi di finale'},
               lcup_europe='la vincente {e}', europe='Europa', eu_first='stagione 1: i veri club 2026-27 delle fasi '
               'campionato ({lst})', eu_none='stagione 1: nessun club nelle fasi campionato',
               eu_later='dalla stagione 2: {places} secondo i coefficienti per federazione simulati',
               eu_cup={'cc': 'Champions League', 'cwc': 'Europa League', 'uefa': 'Conference League'},
               approx='Approssimazione dichiarata', staged='In costruzione', league='Campionato', cupw='Coppa',
               lcup='Coppa di lega', summary='{c} nazioni, {d} divisioni, {k} coppe nazionali, {l} coppe di lega: '
               'ogni competizione giocabile e la sua formula, generate dalla build della release: [{f}]({f}).'),
}

# the Italian play-offs (pack 'playoffs': 'ita', dplay.py): fixed text
ITA_PO = {'en': 'Serie B play-offs (3rd-8th: preliminary 5v8, 6v7 at the better placed; two-legged semi-finals and '
                'final; level: the better placed) and play-out (16th v 17th, two legs); Serie C play-off of 28 clubs '
                '(group phase, national phase, Final Four) for the fourth promotion',
          'it': 'play-off di Serie B (dalla 3ª all\'8ª: turno preliminare 5ª-8ª, 6ª-7ª in casa della meglio piazzata; '
                'semifinali e finale di andata e ritorno; in parità passa la meglio piazzata) e play-out (16ª contro '
                '17ª, andata e ritorno); play-off di Serie C a 28 squadre (fase a gironi, fase nazionale, Final Four) '
                'per la quarta promozione'}




def _it_art(n):
    """The Italian article before a number: gli 8, gli 11, i 16 (vowel sound: otto, undici, ottanta...)."""
    w = str(n)
    return 'gli' if w[0] == '8' or w == '11' else 'i'


def _it_pairs(k, t):
    if k == t == 1:
        return "l'unico accoppiamento"
    if k == t:
        return f"tutti {'e' if t <= 10 else _it_art(t)} {t} accoppiamenti"
    return f"{k} {'degli' if _it_art(t) == 'gli' else 'dei'} {t} accoppiamenti"


def _sfx(n):
    return 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


TITLE_MAX = 34      # the game's title '<country> <long name>' (DIY+4): a 35-byte field, the long-name pointer right after
                    # it (DIY+27h); longer, the copy overwrites the pointer (4.0: Argentina's 'CEK' record line, title garbage)
LANGS = ('it', 'en', 'fr', 'de')


def _fit(country, long_, short):
    """A long name that fits '<country> <long>' in TITLE_MAX: the long one, else the short one, else the longer of the
    two cut at a word (then at the limit)."""
    room = TITLE_MAX - len(country) - 1
    for x in (long_, short):
        if len(x) <= room:
            return x
    w = (short or long_)[:room + 1].rsplit(' ', 1)[0] if ' ' in (short or long_)[:room + 1] else (short or long_)[:room]
    return w.rstrip(' -.') or (short or long_)[:room]


def fit_titles(m):
    """pack.json m (in place): every name list [long, short] of a competition, its divisions and its play-offs gets a
    per-language long name whose title '<country> <long>' fits the game's field (TITLE_MAX). Every reader of a pack's
    names (mkseason, zones, fmtgame) uses this, so the struct names and the zone / FORMAT keys stay the same."""
    bn = m.get('button_names') or {}

    def fix(names):
        if not isinstance(names, dict) or not names:
            return
        for lang in LANGS:
            v = names.get(lang) or names.get('*') or next(iter(names.values()))
            if not isinstance(v, list) or not v:
                continue
            country = (bn.get(lang) or m.get('button') or '').upper()
            long_ = v[0]
            short = v[1] if len(v) > 1 else v[0]
            f = _fit(country, long_.upper(), short.upper()) if len(country) + 1 + len(long_) > TITLE_MAX else None
            if f is not None and f != long_.upper():
                names[lang] = [f] + list(v[1:])
    for c in m.get('competitions', []) or []:
        fix(c.get('names'))
        for dv in c.get('divisions', []) or []:
            if isinstance(dv, dict):
                fix(dv.get('names'))
        for po in c.get('ko_playoffs', []) if isinstance(c.get('ko_playoffs'), list) else []:
            if isinstance(po, dict):
                fix(po.get('names'))
    return m


FONT = set(" &'()-./0123456789:,!?+ABCDEFGHIJKLMNOPQRSTUVWXYZ")   # the characters the game's menu fonts draw (4.0)


def check_titles(m, clubs=()):
    """Problems of pack.json m (after fit_titles): a title '<country> <long>' over TITLE_MAX, or a character outside FONT in
    any name (competitions, divisions, play-offs, clubs). Davide: no stray characters may ever ship."""
    bad = []
    bn = m.get('button_names') or {}

    def chk(names, where):
        if not isinstance(names, dict):
            return
        for lang in LANGS:
            v = names.get(lang) or names.get('*') or next(iter(names.values()), None)
            if not isinstance(v, list):
                continue
            country = (bn.get(lang) or m.get('button') or '').upper()
            if len(country) + 1 + len(v[0]) > TITLE_MAX:
                bad.append(f"{m.get('id')} {where} {lang}: title over {TITLE_MAX}: {country} {v[0]}")
            for x in [country] + list(v):
                odd = sorted(set(x.upper()) - FONT)
                if odd:
                    bad.append(f"{m.get('id')} {where} {lang}: characters {odd} in {x!r}")
    for c in m.get('competitions', []) or []:
        chk(c.get('names'), c.get('key'))
        for i, dv in enumerate(c.get('divisions', []) or []):
            chk((dv or {}).get('names'), f"{c.get('key')} division {i}")
        for po in c.get('ko_playoffs', []) if isinstance(c.get('ko_playoffs'), list) else []:
            chk((po or {}).get('names'), po.get('key') if isinstance(po, dict) else '?')
    for name in clubs:
        odd = sorted(set(name.upper()) - FONT)
        if odd:
            bad.append(f"{m.get('id')} club {name!r}: characters {odd}")
    return bad


def load_pack(d):
    """pack.json of directory d, its titles fitted (fit_titles)."""
    return fit_titles(json.load(open(os.path.join(d, 'pack.json'), encoding='utf-8')))


def _nm(names, lang):
    v = names.get(lang) or names.get('*') or next(iter(names.values()))
    return v[0] if isinstance(v, list) else v


KEEP_UP = {'MLS', 'CPL', 'EFL', 'FA', 'SFL', 'ISL', 'IFL', 'AFC', 'KNVB', 'DFB', 'LFP', 'NPL', 'II', 'III', 'TFF',
           'SVB', 'UEFA', 'MX', 'USL', 'PSV', 'AZ', 'NK', 'FK', 'SK', 'IF', 'BK', 'IK', 'AIK', 'CSKA', 'HJK', 'KuPS'}


def _cname(s):
    """A competition's name as the game shows it (upper case keeps every acronym: LALIGA, POKAL NZS, LOI ...)."""
    return s


def _title(s):
    """'SCOTTISH PREMIERSHIP' -> 'Scottish Premiership'; abbreviations (FC, BC, MLS ...) stay upper case."""
    if not s.isupper():
        return s
    return ' '.join(w if w in KEEP_UP or (len(w) <= 2 and w.isalpha()) else
                    '-'.join(p.capitalize() for p in w.split('-')) for w in s.split(' '))


# ---------------------------------------------------------------------------------------------------- reader: packs
def from_packs(dirs, approx=None, staged=None, since=None, modes=('career',)):
    """The model of career-world packs. approx / staged: {country code: ...}; since: the release that brings them."""
    out = []
    for d in dirs:
        d = d.rstrip('/')
        m = json.load(open(os.path.join(d, 'pack.json')))
        if m.get('kind') != 'career':
            continue
        code = m['id'].rsplit('-', 1)[1].upper()
        clubs = list(csv.DictReader(open(os.path.join(d, 'clubs.csv'), encoding='utf-8')))
        tp = os.path.join(d, 'ties.csv')
        ties = list(csv.DictReader(open(tp, encoding='utf-8'))) if os.path.exists(tp) else []
        side = os.path.join(d, 'complist.json')         # the converter's facts (real / generated cups)
        info = json.load(open(side)) if os.path.exists(side) else {}
        bn = m.get('button_names') or {'*': m['button']}
        c = dict(code=code, name={'en': _title(bn.get('en', m['button'])), 'it': _title(bn.get('it', m['button']))},
                 continent=m['continent'], order=m['files']['league']['file'], comps=[], europe_extra=[],
                 approx=(approx or {}).get(code, []), staged=(staged or {}).get(code))
        common = dict(modes=list(modes), since=since, source=None)
        for comp in m['competitions']:
            if comp['type'] == 'league':
                c['comps'].append(dict(_league(comp, clubs), **common))
            elif comp['type'] == 'cup':
                k = 'league_cup' if comp['key'] == 'league_cup' else 'cup'
                c['comps'].append(dict(_cup(comp, ties, k, dict(info.get(k, {}), season=info.get('season'))),
                                       **common))
        lcd = os.path.join(os.path.dirname(d) + '-lc', os.path.basename(d))   # (staged league cups)
        if not any(x['kind'] == 'league_cup' for x in c['comps']) and os.path.exists(os.path.join(lcd, 'competition.json')):
            lt = os.path.join(lcd, 'ties.csv')
            lties = list(csv.DictReader(open(lt, encoding='utf-8'))) if os.path.exists(lt) else []
            c['comps'].append(dict(_cup(json.load(open(os.path.join(lcd, 'competition.json'))), lties, 'league_cup',
                                        dict(info.get('league_cup', {}), season=info.get('season'))), **common,
                                   staged_lc=True))
        fe = m.get('first_europe')
        if fe is not None:
            names = {r['key']: r['name'] for r in clubs}
            un = info.get('europe_names') or {}           # the UEFA names (Inter, Atalanta, Atleti ...)
            c['europe'] = dict(first={k: [un.get(x) or _title(names.get(x, x)) for x in v] for k, v in fe.items()},
                               places=m.get('europe_places', {}))
        out.append(c)
    out.sort(key=lambda c: (CONTINENTS.index(c['continent']), c['order']))
    return out


def _league(lg, clubs):
    divs = lg.get('divisions') or [{'teams': sum(1 for r in clubs if r['file'] == lg['clubs']
                                                and r['division'] not in ('reserve', '')),
                                    'promoted': 0, 'relegated': lg.get('relegated', 0), 'names': lg['names']}]
    par = lg.get('parallel')
    pars = par if isinstance(par, list) else ([par] if par else [])
    group_of = {q['first'] + k: q['first'] for q in pars for k in range(q['count'])}
    levels, seen = [], {}
    for i, dv in enumerate(divs):
        div = dict(name=dv['names'], clubs=dv['teams'], games=dv.get('games', lg.get('games', 2)),
                   up=dv.get('promoted', 0), down=dv.get('relegated', 0),
                   split=dv.get('split') or (lg.get('split') if i == 0 else None),
                   playoffs=[p for p in lg.get('ko_playoffs', []) if _po_div(p) == i])
        g = group_of.get(i)
        if g is not None and g in seen:
            levels[seen[g]].append(div)
        else:
            if g is not None:
                seen[g] = len(levels)
            levels.append([div])
    closed = all(d['up'] == 0 and d['down'] == 0 for lv in levels for d in lv) and len(divs) > 1
    return dict(kind='league', levels=levels, names=[dv['names'] for dv in divs], closed=closed,
                special=[ITA_PO] if lg.get('playoffs') == 'ita' else [], reserve=bool(lg.get('reserve')))


def _po_div(po):
    """The division a play-off is listed under: the lowest division index among its entrants."""
    ds = [e[0] for e in po.get('entrants', []) if isinstance(e, list)]
    return min(ds) if ds else 0


def _cup(cp, ties, kind, info):
    rows = [t for t in ties if t.get('competition') == cp['key']]
    r1 = [t for t in rows if t['round'] == '1']
    rounds = cp.get('rounds', [])
    size = 2 ** len(rounds)
    pairs = [t for t in r1 if t.get('away')]
    byes = len([t for t in r1 if not t.get('away')]) or (max(0, size // 2 - len(pairs)) if pairs else 0)
    return dict(kind=kind, name=cp['names'], clubs=2 * len(pairs) + byes if pairs else size, size=size, rounds=rounds,
                byes=byes, src=info.get('source', 'real' if pairs else 'generated'), real_pairs=info.get('real_pairs'),
                ties=info.get('ties', len(pairs)), season=info.get('season', ''), numbered=cp.get('round_names') == 'numbered',
                first_round=cp.get('first_round', 1), europe=cp.get('europe'), away_goals=bool(cp.get('away_goals')),
                real=info.get('real'))


# ---------------------------------------------------------------------------------------------------- renderer
def _matchdays(n, games):
    return (n if n % 2 else n - 1) * games


def _rr(t, k):
    return t['rr'].get(k, f'{k} x')


def _runs(codes, t, table):
    """['single_et', 'single_et', 'two_legs'] -> 'rounds 1-2: ...; round 3: ...' (one text when all the same)."""
    if not codes:
        return ''
    if all(x == codes[0] for x in codes):
        return table[codes[0]]
    out, a = [], 0
    for i in range(1, len(codes) + 1):
        if i == len(codes) or codes[i] != codes[a]:
            out.append((t['round_k'].format(a=a + 1, r=table[codes[a]]) if i - a == 1 else
                        t['rounds_k'].format(a=a + 1, b=i, r=table[codes[a]])))
            a = i
    return '; '.join(out)


def _split_text(sp, n, t):
    st = sp.get('stages') or [sp]
    parts, days, prev = [], 0, 0
    for k, s in enumerate(st):
        gs, mx = [], 0
        for g in s['groups']:
            a, b = g['places']
            r = {'none': 0, 'single': 1, 'double': 2}[g.get('rounds', 'single')]
            gs.append(t['grp_none'].format(a=a, b=b) if not r else
                      t['grp'].format(a=a, b=b, rr=_rr(t, r)) + t['pts'].get(g.get('points', 'full'), ''))
            mx = max(mx, _matchdays(b - a + 1, r) if r else 0)
        txt = t['split'].format(after=s['after'], groups=', '.join(gs))
        if s.get('reset'):
            txt = t['split'].format(after=s['after'], groups=t['reset'] + (' ' + t['keep'] if s.get('keep') else '')
                                    + ', ' + ', '.join(gs))
        h = t['home'].get(s.get('home', 'seeded'), '')
        parts.append((t['stage'].format(k=k + 1) if len(st) > 1 else '') + txt + ('; ' + h if h else ''))
        prev = s['after'] + mx
        days = prev
    return '; '.join(parts), days


def _who(po, names, t, lang):
    by = {}
    for e in po.get('entrants', []):
        if isinstance(e, list):
            by.setdefault(e[0], []).append(e[1])
    seeds = sorted(e['split_seed'] for e in po.get('entrants', []) if isinstance(e, dict) and 'split_seed' in e)
    txt = [t['seeds'].format(a=seeds[0], b=seeds[-1])] if seeds else []
    for dv, pls in by.items():
        pls = sorted(pls)
        rng = t['ord'](pls[0]) if len(pls) == 1 else \
            t['places_rng'].format(a=t['ord'](pls[0]), b=t['ord'](pls[-1])) if pls == list(range(pls[0], pls[-1] + 1)) \
            else ', '.join(t['ord'](p) for p in pls)
        txt.append(t['place'].format(div=_cname(_nm(names[dv], lang)), places=rng))
    return ' + '.join(txt) or '-'


def _po(po, names, t, lang):
    def one(r):
        h = t['host'].get(r.get('host', 'listed'), '')
        if r.get('legs', 1) == 1:                        # (a single match: no '2nd leg')
            h = h.replace(' (2nd leg)', '').replace(' (al ritorno)', '')
        bits = [t['legs'][r.get('legs', 1)], h,
                t['level'].get(r.get('level', 'et_pens'), '')]
        if r.get('gap'):
            bits.append(t['gap'].format(n=r['gap']))
        if r.get('skip_if_same'):
            bits.append(t['same_club'])
        return ', '.join(b for b in bits if b)
    rs = [one(r) for r in po['rounds']]
    if len(rs) == 1:
        rounds = rs[0]
    elif all(x == rs[0] for x in rs):
        rounds = t['same'].format(k=len(rs), r=rs[0])
    else:
        rounds = '; '.join(t['round_k'].format(a=i + 1, r=x) for i, x in enumerate(rs))
    kind = t['kind'].get(po.get('kind', 'promotion'), po.get('kind'))
    s = t['po'].format(name=f"{_cname(_nm(po['names'], lang))} ({kind})", who=_who(po, names, t, lang), rounds=rounds)
    wd, ld = po.get('winner_div'), po.get('loser_div')
    if po.get('kind') == 'promotion' and wd is not None:
        s += '; ' + t['winner_to'].format(div=_cname(_nm(names[wd], lang)))
    if ld == 'reserve':
        s += '; ' + t['loser_to'].format(div=t['reserve'])
    return s


def _div_line(dv, lg, t, lang, lowest, head=True):
    n, g = dv['clubs'], dv['games']
    bits = [t['clubs'].format(n=n)] if head else []
    if dv['split']:
        st = dv['split'].get('stages') or [dv['split']]
        first = st[0]['after'] // (n if n % 2 else n - 1)
        sp, days = _split_text(dv['split'], n, t)
        bits.append(f"{_rr(t, first)} ({t['matchdays'].format(n=st[0]['after'])}); {sp}")
        bits.append(t['matchdays'].format(n=days))
    else:
        bits.append(_rr(t, g) + ', ' + t['matchdays'].format(n=_matchdays(n, g)))
    if n % 2:
        bits.append(t['rest'])
    if lg['closed']:
        bits.append(t['closed'])
    else:
        if dv['up']:
            bits.append(t['up'](dv['up']))
        if dv['down']:
            bits.append(t['down'](dv['down']))
        elif lowest and not lg['reserve']:
            bits.append(t['lowest'])
    return '; '.join(bits)


REAL_RN = {   # Transfermarkt's round names -> (EN, IT) in the real cup's line
    'Qualifying Round': ('qualifying round', 'turno preliminare'), 'Preliminary Round': ('preliminary round', 'turno preliminare'),
    'First Round': ('1st round', '1° turno'), 'Second Round': ('2nd round', '2° turno'), 'Third Round': ('3rd round', '3° turno'),
    'Fourth Round': ('4th round', '4° turno'), '5th round': ('5th round', '5° turno'), 'Round of 64': ('round of 64', 'trentaduesimi'),
    'Round of 32': ('round of 32', 'sedicesimi'), 'Round of 16': ('round of 16', 'ottavi'), 'Last 16': ('round of 16', 'ottavi'),
    'Quarter-Finals': ('quarter-finals', 'quarti'), 'Semi-Finals': ('semi-finals', 'semifinali'), 'Final': ('final', 'finale')}


def _real_cup(real, t):
    """The real competition (regia 2026-10-19): its clubs and where they enter, as Transfermarkt lists it."""
    k = 1 if t['cup'].endswith('squadre') else 0
    ins = [f"{REAL_RN.get(r['tm'], (r['tm'].lower(),) * 2)[k]} {r['new']}" for r in real['rounds'] if r['new']]
    return t['real_cup'].format(n=real['clubs'], ins=', '.join(ins))


def _cup_line(cp, t):
    real = cp.get('real') and len(cp['real']['rounds']) > 1
    bits = ([_real_cup(cp['real'], t)] if real else []) + [(t['in_game'] + ' ' if real else '') + t['cup'].format(n=cp['clubs'])]
    if cp['size'] in t['rnd'] and cp['src'] == 'real':
        bits.append(t['cup_from'].format(rnd=t['rnd'][cp['size']]))
    season = cp.get('season') or '2026-27'
    if cp['src'] != 'real':
        bits.append(t['cup_gen'])
    elif cp['real_pairs'] is not None:
        bits.append(t['cup_real'](cp['real_pairs'], cp['ties'], season))
    else:
        bits.append(t['cup_real0'].format(season=season))
    if cp['byes']:
        bits.append(t['byes'].format(n=cp['byes']))
    rs = [r + '_ag' if r == 'two_legs' and cp.get('away_goals') else r for r in cp['rounds']]
    if len(rs) > 1:
        bits.append(_runs(rs[:-1], t, t['rounds']))
    if rs:
        bits.append(t['final'].format(r=t['finals'][rs[-1]]))
    if cp['numbered']:
        bits.append(t['numbered'])
    return '; '.join(bits)


def _tail(comp, t):
    """Modes / version / source marks after a competition's line."""
    out = []
    ms = comp.get('modes') or []
    if ms and set(ms) != {'career', 'season', 'preset'} and len(ms) < 3:
        out.append(t['only'].format(m=', '.join(t['modes'][x] for x in ms)))
    if comp.get('since'):
        out.append(t['new'].format(v=comp['since']))
    return (' (' + '; '.join(out) + ')') if out else ''


def _src(comp, lang, t):
    s = comp.get('source')
    return f"  - *{t['src'].format(s=s[lang] if isinstance(s, dict) else s)}*" if s else None


def render(model, lang, heading='##', show_modes=False):
    """Markdown of the model in one language. show_modes: mark competitions that only some game modes have."""
    t = P[lang]
    countries = model['countries'] if isinstance(model, dict) else model
    out = [f'{heading} {t["title"]}', '']
    eu = model.get('europe') if isinstance(model, dict) else None
    if eu:
        out += [f'{heading}# {t["ueuro"]}', '', eu[lang], '']
    cont = None
    for c in countries:
        if c['continent'] != cont:
            cont = c['continent']
            out += [f'{heading}# {CONT_NAME[cont][0 if lang == "en" else 1]}', '']
        out.append(f'**{c["name"][lang]}**')
        for comp in c['comps']:
            tail = _tail(comp, t) if show_modes else ''
            if comp['kind'] == 'league':
                names, nlv = comp['names'], len(comp['levels'])
                for k, lv in enumerate(comp['levels']):
                    low = k == nlv - 1
                    if len(lv) > 1 and not (k == 0 and comp['closed']):
                        nm = ' / '.join(_cname(_nm(d['name'], lang)) for d in lv)
                        sizes = ' + '.join(str(d['clubs']) for d in lv)
                        out.append(f'- {nm}: ' + t['groups'].format(k=len(lv), sizes=sizes) + '; '
                                   + _div_line(lv[0], comp, t, lang, low, head=False) + tail)
                    else:
                        for d in lv:
                            out.append(f"- {_cname(_nm(d['name'], lang))}: " + _div_line(d, comp, t, lang, low) + tail)
                    for d in lv:
                        for po in d['playoffs']:
                            out.append('  - ' + _po(po, names, t, lang))
                for sp in comp['special']:
                    out.append('  - ' + sp[lang])
            else:
                lab = t['cupw'] if comp['kind'] == 'cup' else t['lcup']
                out.append(f"- {_cname(_nm(comp['name'], lang))} ({lab}): " + _cup_line(comp, t) + tail)
            s = _src(comp, lang, t)
            if s:
                out.append(s)
        e = c.get('europe')
        if e is not None:
            first = '; '.join(f"{t['eu_cup'][k]} " + ', '.join(v) for k, v in e['first'].items() if v)
            later = ', '.join(f"{t['eu_cup'][k]} {n}" for k, n in e['places'].items() if n)
            out.append(f"- {t['europe']}: " + (t['eu_first'].format(lst=first) if first else t['eu_none'])
                       + ('; ' + t['eu_later'].format(places=later) if later else ''))
        for x in c.get('europe_extra') or []:
            out.append(f'  - {x[lang]}')
        for a in c.get('approx') or []:
            out.append(f"- *{t['approx']}*: {a[lang]}")
        if c.get('staged'):
            out.append(f"<!-- {t['staged']}: {c['staged'][lang]} -->")
        out.append('')
    return '\n'.join(out)


def summary(model, path, lang):
    countries = model['countries'] if isinstance(model, dict) else model
    comps = [comp for c in countries for comp in c['comps']]
    d = sum(len(lv) for comp in comps if comp['kind'] == 'league' for lv in comp['levels'])
    k = sum(1 for comp in comps if comp['kind'] == 'cup')
    lc = sum(1 for comp in comps if comp['kind'] == 'league_cup')
    return P[lang]['summary'].format(c=len(countries), d=d, k=k, l=lc, f=path)


BEGIN, END = '<!-- complist:begin -->', '<!-- complist:end -->'
LIMIT = 125000                                      # a GitHub release body's characters


def replace_block(text, block):
    """The release notes' generated block between the markers (appended at the end when missing)."""
    if BEGIN in text and END in text:
        a, b = text.index(BEGIN), text.index(END) + len(END)
        return text[:a] + BEGIN + '\n' + block + '\n' + END + text[b:]
    return text.rstrip('\n') + '\n\n' + BEGIN + '\n' + block + '\n' + END + '\n'


def write(model, notes, doc_path, link):
    """The document (EN, then IT) and the notes' block: the whole list when the notes stay under LIMIT, else the
    summary + link (the list in doc_path)."""
    doc = render(model, 'en') + '\n' + render(model, 'it')
    txt = open(notes, encoding='utf-8').read() if notes else ''
    inline = replace_block(txt, doc)
    if notes and len(inline) <= LIMIT:
        open(notes, 'w', encoding='utf-8').write(inline)
        return 'inline', len(inline)
    open(doc_path, 'w', encoding='utf-8').write(doc)
    if notes:
        block = summary(model, link, 'en') + '\n\n' + summary(model, link, 'it')
        open(notes, 'w', encoding='utf-8').write(replace_block(txt, block))
    return 'file', len(doc)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Every country, every competition (EN + IT).')
    ap.add_argument('mode', choices=['world', 'base'])
    ap.add_argument('dirs', nargs='+', help='world: career pack dirs; base: the build dir')
    ap.add_argument('--approx'), ap.add_argument('--staged'), ap.add_argument('--since')
    ap.add_argument('--out', help='the document (default: stdout, EN then IT)')
    ap.add_argument('--notes', help='release notes: the generated block between the complist markers')
    ap.add_argument('--link', help='the path of the document as linked from the notes')
    a = ap.parse_args()
    if a.mode != 'world':
        sys.exit('mode base: from_build9697 (4.0) to come')
    model = {'europe': None, 'countries': from_packs(a.dirs, json.load(open(a.approx)) if a.approx else None,
                                                     json.load(open(a.staged)) if a.staged else None, a.since)}
    if a.notes:
        how, n = write(model, a.notes, a.out or 'competitions.md', a.link or os.path.basename(a.out or 'competitions.md'))
        print(f'complist: {how}, {n} characters')
    elif a.out:
        open(a.out, 'w', encoding='utf-8').write(render(model, 'en') + '\n' + render(model, 'it'))
    else:
        print(render(model, 'en') + '\n' + render(model, 'it'))
