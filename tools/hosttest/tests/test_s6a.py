"""S6a (4.3, MC 15/11): world SEASONs - the gate sites' audit (internal/handoff/s6a-audit.md) as a static check.

test_s6a_sites (no build): every `cmp word [GAMETYPE], 4` / `call W_GT` (careerworld: `call w_gt`) in tools/*.py is
classified: W sites (a world rule: a career or a world SEASON) call W_GT, C sites (career-only: the career club's
menus, kits, sacking, records, supercups) keep the career test. A new gate site anywhere fails until it is put in one
list (each entry: module, the label the site follows - the nearest `name:` / `.local:` line above it)."""
import os
import re

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

W = {('benchnum', 'bn_world'), ('careerworld', 'w_noaway'), ('careerworld', 'w_tmap'), ('dplay', 'dp_find'),
     ('fmtpage', '.out'), ('gplay', '.nm'), ('gplay', 'gp_s3due'), ('gplay', 'gp_gf'), ('gplay', 'gp_adv'),
     ('gplay', 'gp_find'), ('gplay', 'gp_cup12'),
     ('lgreal', 'lg_init'), ('lpreal', 'lr_draw'), ('simdraw', 'sd_site'), ('statecup', 'sc_pick'),
     ('stoppage', 'st_caps'), ('winners', 'wn_load'), ('worldpool', 'wp_load'), ('zones', '.k'), ('ripool', 'ri_load'),
     ('ripool', '.x'), ('split', '.f')}
OWN = {('careerworld', 'w_gt'), ('split', '.clean')}   # w_gt itself; split's league init (gameType 3 or 4: the byte)
C = {('gplay', 'gp_notin'), ('gplay', 'cf_a6'), ('gplay', 'cf_mem'), ('gplay', 'gp_cdmem'),   # (S6a: the career
     # club's rules - CAREERTEAM / SEASONPLAYING: rule 11, the later seasons' fixed list, Coppa D membership)
     ('benchx', '.car'), ('benchx', 'bx_xnamed'), ('careerworld', 'w_ntw'), ('careerworld', 'w_nc'),
     ('careerworld', 'w_dok'), ('careerworld', 'w_se'), ('gplay', 'gp_mrec'), ('gplay', 'gp_sack'), ('gplay', '.e'),
     ('gplay', 'gp_sc'), ('gplay', 'gp_scgl'), ('gplay', 'vc5_lay'), ('gplay', '.e8'), ('kitcolors', 'km_mode'),
     ('kitcolors', 'km_keep'), ('kits', 'kk_club'), ('kits', 'kk_rec'), ('quietend', 'qe_call'), ('winners', '.close'),
     ('winners', '.x')}
LAB = re.compile(r'^(\.?[A-Za-z_][\w.]*):')


def _sites():
    out = []
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith('.py'):
            continue
        lab = None
        for n, ln in enumerate(open(os.path.join(TOOLS, f), errors='replace'), 1):
            m = LAB.match(ln)
            if m:
                lab = m.group(1)
            code = ln.split(';')[0]
            if 'cmp word [GAMETYPE], 4' in code:
                out.append((f[:-3], lab, n, 'C'))
            elif re.search(r'\bcall (W_GT|w_gt)\b', code):
                out.append((f[:-3], lab, n, 'W'))
    return out


def test_s6a_sites():
    bad, seen = [], {'W': set(), 'C': set()}
    for mod, lab, n, kind in _sites():
        key = (mod, lab)
        if key in OWN:
            continue
        seen[kind].add(key)
        want = 'W' if key in W else 'C' if key in C else None
        if want is None:
            bad.append(f'{mod}.py:{n} after {lab}: a new {kind} gate site, not classified (s6a-audit.md, this test)')
        elif want != kind:
            bad.append(f'{mod}.py:{n} after {lab}: {kind}, the audit says {want}')
    for kind, lst in (('W', W), ('C', C)):
        for key in sorted(lst - seen[kind]):
            bad.append(f'{key}: listed {kind}, no such site')
    assert not bad, bad
    return True, f"{len(seen['W'])} W sites call W_GT, {len(seen['C'])} C sites keep the career test"


def test_s6a_registry():
    """The SEASON picker's worlds = the registry's: s6sea.c s6_sea_pre lists a default world only when its record has
    M_SEASON, and swreg gives it to every world (SEASON_WORLDS) - with the release packs (world5tm-h3p)."""
    import sys
    sys.path.insert(0, TOOLS)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_seaw0
    test_seaw0._release_packs()
    if not os.environ.get('SEASON_PACKS'):
        return True, 'SKIP: no release packs'
    import swreg
    assert swreg.SEASON_WORLDS
    ws = swreg.worlds()
    no = [n for n, _, _, _, modes, _, _, _ in ws if not modes & swreg.M_SEASON]
    assert not no, f'worlds without M_SEASON: {no}'
    src = open(os.path.join(TOOLS, 's6sea.c')).read()
    assert 'if (!r || !(r[6] & M_SEASON))' in src and 'swe_sel_pre(M_SEASON)' in src, 's6_sea_pre: not the registry'
    return True, f'{len(ws)} worlds, all M_SEASON: ' + ', '.join(f'{n} ({y})' for n, _, _, _, _, y, _, _ in [
        (w[0], 0, 0, 0, 0, w[3], 0, 0) for w in ws])
