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


# MC 15/11 item 2: a site that reads CAREERTEAM (the career club's team word) is C by default; a W site (world SEASONs
# too) may read it only with a proof. The guard reads the BUILT exe: every LE fixup that targets CAREERTEAM and is not
# one of the original exe's, attributed to the nearest preceding label of ITALIAN.syms.json (HOSTTEST_SYMS=1 builds;
# code before any label of its object: '?objN'). Each (module, label) has its count and class here: 'C' = reached only in a
# career (a C gate, or a career-only menu / path), 'W:<proof>' = reached from a W site in a world SEASON with the
# scenario that proves it, 'W?' = reached from a W site, proof pending (MC item 2). A new read, or one more than
# listed, FAILs. HT_S6_SYMS=<build dir> (default c/HTW, mkfixtures.sh's release-recipe build).
CT_READS = {   # (W?: gp_gf / gp_adv - GP_MGR; split sp_shsel (the 'SH' block) / sp_freeze (FASE 1 capture), via split .f)
    ('?obj2', ''): (1, 'C'), ('?obj3', ''): (4, 'C'), ('careerworld', 'w_kits'): (1, 'C'),
    ('ctview', 'cv_init'): (1, 'C'), ('difficulty', 'SYMS.BU_ENTRY'): (6, 'C'),
    ('difficulty', 'SYMS.PREV_RET'): (4, 'C'), ('dplay', 'dp_end'): (1, 'C'), ('dplay', 'dp_lend'): (1, 'C'),
    ('gplay', 'cf_a6'): (1, 'C'), ('gplay', 'cf_mem'): (1, 'C'), ('gplay', 'gp_adv'): (1, 'W?'),
    ('gplay', 'gp_after'): (1, 'C'), ('gplay', 'gp_cdmem'): (1, 'C'), ('gplay', 'gp_end'): (2, 'C'),
    ('gplay', 'gp_gf'): (1, 'W?'), ('gplay', 'gp_install'): (2, 'C'), ('gplay', 'gp_notin'): (1, 'C'),
    ('gplay', 'gp_perm'): (1, 'C'), ('gplay', 'gp_rl'): (1, 'C'), ('gplay', 'gp_sack'): (1, 'C'),
    ('gplay', 'gp_sc'): (1, 'C'), ('gplay', 'gp_setup'): (1, 'C'), ('gplay', 't2_body'): (1, 'C'),
    ('lrank', 'lr_res'): (1, 'C'), ('shirtnum', 'SPRIDX'): (2, 'C'), ('split', 'sp_freeze'): (1, 'W?'),
    ('split', 'sp_shsel'): (1, 'W?'), ('t3', 't3_go'): (1, 'C'), ('t3', 't3_list'): (1, 'C'),
    ('t3', 't3_sign'): (1, 'C'), ('uefaq', 'SYMS.W_QON'): (2, 'C'), ('uprize', 'up_ko'): (1, 'C'),
    ('uprize', 'up_lp'): (1, 'C'), ('uprize', 'up_res'): (2, 'C'), ('winners', 'WN_FN'): (5, 'C'),
    ('xbrowse', 'vs_init'): (1, 'C'), ('xbrowse', 'xs_tail'): (1, 'C'),
}


def careerteam_reads(build):
    """Counter {(module, label): reads} of the mod's CAREERTEAM reads in build/ITALIAN.EXE (see CT_READS)"""
    import bisect
    import collections
    import json
    import sys
    sys.path.insert(0, TOOLS)
    import dplay
    import lepatch
    o = lepatch.LEPatch(os.path.join(TOOLS, '..', 'orig', 'ITALIAN.EXE'))
    ct = dplay._sites(o)[5]

    def srcs(p):
        return {(so, s) for so, s, _, t, off, *_ in p.le.fixups() if t == 2 and off == ct}
    b = lepatch.LEPatch(os.path.join(build, 'ITALIAN.EXE'))
    sy = json.load(open(os.path.join(build, 'ITALIAN.syms.json')))
    assert sy['gplay']['CAREERTEAM'] == [2, ct], ('CAREERTEAM', sy['gplay'].get('CAREERTEAM'), ct)
    lab = {1: [], 3: [], 4: []}
    for m, d in sy.items():
        for nm, v in d.items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[1], int) and (v[0] or 1) in lab:
                lab[v[0] or 1].append((v[1], m, nm))
    for k in lab:
        lab[k].sort()
    out = collections.Counter()
    for so, s in sorted(srcs(b) - srcs(o)):
        ls = lab.get(so, [])
        i = bisect.bisect_right(ls, (s, '\x7f', '\x7f')) - 1
        out[(ls[i][1], ls[i][2]) if i >= 0 else (f'?obj{so}', '')] += 1
    return out


def test_s6a_careerteam():
    """MC 15/11 item 2: the mod's CAREERTEAM reads in the built exe = CT_READS (no new read, no W site's without a
    proof entry)"""
    build = os.environ.get('HT_S6_SYMS') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', 'HTW', 'SWOS')
    if not os.path.exists(os.path.join(build, 'ITALIAN.syms.json')):
        return True, f'SKIP: no HOSTTEST_SYMS build {build}'
    import json
    if not {'split', 'ctview'} <= set(json.load(open(os.path.join(build, 'ITALIAN.syms.json')))):
        return True, f'SKIP: {build} predates split / ctview labels (rebuild: tools/hosttest/mkfixtures.sh)'
    got = careerteam_reads(build)
    bad = [f'{m}.{lb}: {n} CAREERTEAM read(s), listed {CT_READS.get((m, lb), (0,))[0]} - a new read: C by default, '
           f'W only with a proof (CT_READS)' for (m, lb), n in sorted(got.items()) if n > CT_READS.get((m, lb), (0,))[0]]
    assert not bad, bad
    w = sorted(f'{m}.{lb} ({c})' for (m, lb), (_, c) in CT_READS.items() if c != 'C' and (m, lb) in got)
    return True, f'{sum(got.values())} CAREERTEAM reads in {len(got)} routines, all listed; W: {", ".join(w) or "none"}'
