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
     ('gplay', 'gp_mgr'), ('gplay', 'gp_hum'),   # (S6a (c): a career's CAREERTEAM, else the SEASON's human clubs)
     ('benchx', '.car'), ('benchx', 'bx_xnamed'), ('careerworld', 'w_ntw'), ('careerworld', 'w_nc'),
     ('careerworld', 'w_dok'), ('careerworld', 'w_se'), ('gplay', 'gp_mrec'), ('gplay', 'gp_sack'), ('gplay', '.e'),
     ('gplay', 'gp_sc'), ('gplay', 'gp_scgl'), ('gplay', 'vc5_lay'), ('gplay', '.e8'), ('kitcolors', 'km_mode'),
     ('kitcolors', 'km_keep'), ('kits', 'kk_club'), ('kits', 'kk_rec'), ('quietend', 'qe_call'), ('winners', '.close'),
     ('winners', '.x'),
     ('gplay', '.free'), ('gplay', '.t'),
     ('nasmcave', None)}   # (rc4, MC 21/11: nasmcave's WGT_STUB - a world-less build's `call W_GT` becomes the pre-S6a
     # `cmp word [GAMETYPE], 4` = w_gt with world byte 0, ZF = 1 only in a career. Proof: test_wgt_stub (stub = cmp;
     # world build without W_GT errors; a defined W_GT wins; test_wgt_sites_were_cmp4))   # (S6a (A), 4.2: gp_install's slot-4 CAREERTEAM swap and gp_hrest_c - a career
     # keeps the original path (careerTeam, no flag reset); the other branch is a world SEASON's own (proof:
     # swostest world_season_ko 6/6, world_title_mlt / _ita))
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
CT_READS = {   # S6a (c), MC 15/11: GP_MGR / GP_IN.mgr and split's 'SH' block + FASE 1 capture take the manager's club
    # from gplay gp_mgr: CAREERTEAM in a career (its only read, behind GAMETYPE == 4), else the SEASON's own human
    # club from SELTEAMS (teamControls != 1, survives .SEA) or 0. Proof: swostest world_season_mgr (gp_gf / gp_adv /
    # Coppa D identical with CAREERTEAM 0 / two stale clubs, all-CPU + one-human, .SEA reload before the GF).
    ('?obj2', ''): (1, 'C'), ('?obj3', ''): (4, 'C'), ('careerworld', 'w_kits'): (1, 'C'),
    ('ctview', 'cv_init'): (1, 'C'), ('difficulty', 'SYMS.BU_ENTRY'): (6, 'C'),
    ('difficulty', 'SYMS.PREV_RET'): (4, 'C'), ('dplay', 'dp_end'): (1, 'C'), ('dplay', 'dp_lend'): (1, 'C'),
    ('gplay', 'cf_a6'): (1, 'C'), ('gplay', 'cf_mem'): (1, 'C'), ('gplay', 'gp_cdmem'): (1, 'C'),
    ('gplay', 'gp_mgr'): (1, 'C'), ('gplay', 'gp_notin'): (1, 'C'), ('gplay', 'gp_sack'): (1, 'C'),
    ('gplay', 'gp_sc'): (1, 'C'), ('lrank', 'lr_res'): (1, 'C'),
    ('t3', 't3_go'): (1, 'C'), ('t3', 't3_list'): (1, 'C'), ('t3', 't3_sign'): (1, 'C'),
    ('uprize', 'up_ko'): (1, 'C'), ('uprize', 'up_lp'): (1, 'C'),
    ('uprize', 'up_res'): (2, 'C'), ('winners', 'WN_FN'): (5, 'C'), ('xbrowse', 'vs_init'): (1, 'C'),
    ('xbrowse', 'xs_tail'): (1, 'C'),
    # S6a (A), 4.2 (Davide 16/11): gp_install's slot-4 cseg_8B2D3 call - push / poke / pop of CAREERTEAM around it,
    # the poke only when GAMETYPE != 4 (a world SEASON: its human club in the ko, else the ko's first entrant), so
    # the game's placeholder team words are a loaded club; a career's value never changes. Proof: world_season_ko
    ('gplay', 'gp_install'): (3, 'C'),
    # MC 17/11 (Shaved, tc1b / tc1c): careerTeam's ADDRESS as a constant in the career file's own save / load and the squad
    # numbers - never "who manages": all C. w_loadcopy 2 (since d54bd67, 3.3.3: a .CAR's competition dwords that are
    # careerTeam - selTeamsPtr re-based on the cache; LoadCareerFile only) and benchnum BN_TEAMS 2 (3.2.5: careerTeam's
    # record in the renumbering table, copies of PlayMatchMenuSwapPlayers' compare; bn_world: careers in squad-number
    # worlds) are NOT new: the nearest-label scan put them on uefaq SYMS.W_QON / shirtnum SPRIDX (constants, not code)
    # until tc1b exported the tails labels and benchnum its own. w_save_tail 1 is new (a346737): the inverse of w_loadcopy
    # on SaveCareerFile (the canonical file: careerTeam - NEWSEL -> careerTeam - OLDSEL).
    ('careerworld', 'tails.w_save_tail'): (1, 'C'), ('careerworld', 'tails.w_loadcopy'): (2, 'C'),
    ('benchnum', 'BN_TEAMS'): (2, 'C'),
    # MC 20/11 (4.2 rc1, 900681f vs 014efe8): 49 -> 50 sites. ONE new site, obj4 0x1292d = s7swap.c run()'s career-club
    # crossing, put_slot(S7_CTEAM, ...) (careerTeam's ADDRESS: the record moved to its new row, option B, MC 13/11) - the
    # same source line as before, the redraw C build (-Oz) emits its tail twice; reached only from s7_season (a career
    # whose registry is this build's): C. The other 5 labels are OLD sites re-attributed by the nearest-label scan (rc1
    # exports more labels; obj1 / obj2 / obj3 counts unchanged, obj4 +1): the same reads, C as listed above.
    ('s7swap', 'RI_HINTN'): (3, 'C'), ('fpmlv', 'FV_TF'): (3, 'C'), ('gkinj', 'SYMS.gk_903'): (1, 'C'),
    ('gplay', 'csyms.cup_rule'): (1, 'C'), ('practice', 'GAME.BOTT_O'): (1, 'C'), ('sreg', 'IMP.s7_imp_walk'): (1, 'C'),
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
    import fixroot
    build = fixroot.need(fixroot.build_dir('HT_S6_SYMS'), 'test_s6a_careerteam', 'ITALIAN.syms.json')
    import json
    if not {'split', 'ctview'} <= set(json.load(open(os.path.join(build, 'ITALIAN.syms.json')))):
        raise RuntimeError(f'{build} predates split / ctview labels (rebuild: tools/hosttest/mkfixtures.sh)')
    got = careerteam_reads(build)
    bad = [f'{m}.{lb}: {n} CAREERTEAM read(s), listed {CT_READS.get((m, lb), (0,))[0]} - a new read: C by default, '
           f'W only with a proof (CT_READS)' for (m, lb), n in sorted(got.items()) if n > CT_READS.get((m, lb), (0,))[0]]
    assert not bad, bad
    w = sorted(f'{m}.{lb} ({c})' for (m, lb), (_, c) in CT_READS.items() if c != 'C' and (m, lb) in got)
    return True, f'{sum(got.values())} CAREERTEAM reads in {len(got)} routines, all listed; W: {", ".join(w) or "none"}'
