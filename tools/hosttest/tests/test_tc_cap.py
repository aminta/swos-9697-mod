"""Team cache, gate H3 (teamcache-fable-design.md 1.2 / 1.3 / 3): the capacity and the insert sites.
- TC_CAP x 684 + main block + 'EN' block <= SEL_ROOM for every build flavour: every `exe: .CAR trailer` line of the
  release's build.log (4 CD + 4 GOG + SWOS++) and of the host-test fixture root's logs; the 'FP' flavour (fixture port,
  fpad.SAVE_SIZE) also by arithmetic on top of the release's blocks. Design: TC_CAP = min(SEL_CAP, (SEL_ROOM - main -
  EN) // 684), computed per build by trailer.py (team cache 1a, 03ee3a8+) and logged as `exe: big cache save room: X B
  left at TC_CAP N teams (main M, EN E)`; it never drops below tcache.TC_FLOOR 159 (TC_FLOOR_FP 155 with 'FP'): the
  cap only grows across versions (MC 16/11).
- the game's 6 insert sites (design 1.3's table): in ref/swos.asm by text and in the exes by bytes (`add word
  [g_numSelectedTeams], 1` with its copy-count `mov word [D0], 341` within 0x60 B: before, after for cseg_3283C)."""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
import careerworld  # noqa: E402
import tcache  # noqa: E402
import tcaudit as T  # noqa: E402
import tc_rel  # noqa: E402

REF = os.path.join(os.path.expanduser('~'), 'swos-mod', 'ref', 'swos.asm')
TRAILER = re.compile(r"exe: \.CAR trailer \w\w \((\d+) B(?: \+ engine block EN (\d+) B: ([^;)]*))?")
CAPLINE = re.compile(r'exe: big cache save room: (-?\d+) B left at TC_CAP (\d+) teams \(main (\d+), EN (\d+)\)')
TEAM = 684


def flavours():
    """{(main, EN, has FP): [where]} from the build logs"""
    import fixroot
    rel, _, _, sd = tc_rel.release()
    logs = [os.path.join(d, 'build.log') for d in {rel, sd} if d]
    r = fixroot.root()
    if r != fixroot.LEGACY:
        logs += sorted(glob.glob(os.path.join(r, '*', 'build.log')) + glob.glob(os.path.join(r, '*.log')))
    out = {}
    for f in logs:
        if not os.path.exists(f):
            continue
        for m in TRAILER.finditer(open(f, errors='replace').read()):
            items = [x.strip() for x in (m[3] or '').split(',')]
            out.setdefault((int(m[1]), int(m[2] or 0), 'FP' in items), []).append(os.path.relpath(f, tc_rel.C))
    return out


def cap_for(main, en):
    """trailer.py's TC_CAP for these blocks (team cache 1a)"""
    return min(careerworld.SEL_CAP, (careerworld.SEL_ROOM - main - en) // TEAM)


def floor_for(fp):
    return tcache.TC_FLOOR_FP if fp else tcache.TC_FLOOR


def logged():
    """{(main, EN): {TC_CAP logged}} from the same logs as flavours()"""
    import fixroot
    rel, _, _, sd = tc_rel.release()
    logs = [os.path.join(d, 'build.log') for d in {rel, sd} if d]
    r = fixroot.root()
    if r != fixroot.LEGACY:
        logs += sorted(glob.glob(os.path.join(r, '*', 'build.log')) + glob.glob(os.path.join(r, '*.log')))
    out = {}
    for f in logs:
        if os.path.exists(f):
            for m in CAPLINE.finditer(open(f, errors='replace').read()):
                out.setdefault((int(m[3]), int(m[4])), set()).add(int(m[2]))
    return out


def test_tc_cap_arith():
    assert (careerworld.SEL_CAP, careerworld.SEL_ROOM) == (160, 160 * TEAM + 0x4280)
    assert (tcache.TC_FLOOR, tcache.TC_FLOOR_FP) == (159, 155), (tcache.TC_FLOOR, tcache.TC_FLOOR_FP)
    assert careerworld.B_SEL + careerworld.SEL_ROOM <= careerworld.B_STAGE
    assert careerworld.B_STAGE + T.FIXED + careerworld.SEL_ROOM <= careerworld.B_UQ      # the stage holds a whole file
    assert careerworld.SAVE_SIZE == 2 + careerworld.SEL_CAP * TEAM                       # the season-end parking
    fl = flavours()
    if not fl:
        return True, 'SKIP: no build.log with a .CAR trailer line (release dir / fixture root)'
    import fpad
    errs, msg = [], []
    for (main, en, fp), where in sorted(fl.items()):
        cap = cap_for(main, en)
        left = careerworld.SEL_ROOM - cap * TEAM - main - en
        msg.append(f"main {main} + EN {en}{' (FP)' if fp else ''}: TC_CAP {cap}, {left} B left ({len(where)} exes)")
        if left < 0 or cap < floor_for(fp):
            errs.append(f'{where[0]}: TC_CAP {cap} (main {main} + EN {en}) below TC_FLOOR {floor_for(fp)} or no room')
        if not fp:                                  # the same build with the fixture port's item: >= 155
            en_fp = en + 4 + fpad.SAVE_SIZE
            cfp = cap_for(main, en_fp)
            if cfp < tcache.TC_FLOOR_FP:
                errs.append(f'{where[0]} + FP ({fpad.SAVE_SIZE} B): TC_CAP {cfp} < TC_FLOOR_FP {tcache.TC_FLOOR_FP}')
            msg[-1] += f'; + FP: TC_CAP {cfp}, {careerworld.SEL_ROOM - cfp * TEAM - main - en_fp} B left'
    assert not errs, '; '.join(errs)
    return True, ' | '.join(msg)


def test_tc_cap_const():
    """the TC_CAP each build logged = the formula on its blocks, >= the floor"""
    lg = logged()
    if not lg:
        return True, 'SKIP: no build.log with a TC_CAP line (a build from before team cache 1a)'
    errs = []
    for (main, en), caps in lg.items():
        want = cap_for(main, en)
        if caps != {want} or want < tcache.TC_FLOOR_FP:
            errs.append(f'main {main} + EN {en}: logged {sorted(caps)}, formula {want}')
    assert not errs, '; '.join(errs)
    return True, 'TC_CAP ' + ', '.join(f'{sorted(c)} (main {m} + EN {e})' for (m, e), c in sorted(lg.items()))


# design 1.3: (procedure, ref line of the add, where its copy-count mov is)
SITES = [('cseg_323DE', 38734, 'before'), ('cseg_3252E', 38905, 'before'), ('cseg_3283C', 39013, 'after'),
         ('cseg_32E15', 39403, 'before'), ('cseg_32E15', 39461, 'before'), ('AddTeamToBuffer', 65419, 'before')]


def test_tc_sites_asm():
    if not os.path.exists(REF):
        return True, 'SKIP: ref/swos.asm missing'
    lines = open(REF, errors='replace').read().split('\n')
    adds = [k + 1 for k, x in enumerate(lines) if re.match(r'(add|inc)\s+(word ptr )?g_numSelectedTeams\b', x)]
    assert adds == [n for _, n, _ in SITES], ('the inserts of g_numSelectedTeams', adds)
    mov = re.compile(r'mov\s+word ptr D0, (155h|341)\b')
    for proc, n, where in SITES:
        p = next(k for k in range(n - 1, 0, -1) if re.match(r'\w+ proc near', lines[k]))
        assert lines[p].split()[0] == proc, (n, lines[p][:40])
        rng = range(n, n + 4) if where == 'after' else range(n - 40, n - 1)
        assert any(mov.match(lines[k]) for k in rng), f'{proc} line {n}: no copy-count mov {where}'
        other = range(n - 6, n - 1) if where == 'after' else range(n, n + 4)
        assert not any(mov.match(lines[k]) for k in other), f'{proc} line {n}: the mov is not only {where}'
    # every other writer of the count is a reset / a fixed value (design 1.3: no check there)
    w = [(k + 1, x.split(';')[0].strip()) for k, x in enumerate(lines) if re.match(r'mov\s+(word ptr )?g_numSelectedTeams\b', x)]
    vals = sorted({x.split(',')[1].strip() for _, x in w})
    assert vals == ['0', '1', 'ax'], vals
    assert [k for k, x in w if x.endswith('ax')] == [34355], 'RestoreSelectedTeams: the one count from a parked word'
    assert sorted(k for k, x in w if x.endswith(', 1')) == [81132, 126794]
    return True, f'6 insert sites + RestoreSelectedTeams (34355) + {len(w) - 1} resets'


def test_tc_sites_exe():
    rel, exes, spp, _ = tc_rel.release()
    paths = tc_rel.originals() + exes + spp
    if not paths:
        return True, 'SKIP: no exes (orig/, c/REL42*)'
    from le import LE
    want = [-63, -63, 8, -73, -73, -70]             # the mov's distance from the add, in code order (every language)
    for p in paths:
        L = T.exe_layout(LE(p))
        s = T.insert_sites(L)
        assert len(s) == 6 and [d for _, d in s] == want, (os.path.relpath(p, tc_rel.C), [(hex(a), d) for a, d in s])
        assert all(abs(d) < 0x60 for _, d in s)
        # none of the 6 sites (add + its mov) carries a patch's fixup-less jump: the bytes are the game's
        d1 = L['d1']
        assert all(d1[a:a + 3] == b'\x66\x83\x05' and d1[a + d:a + d + 3] == b'\x66\xc7\x05' for a, d in s)
    return True, (f'6 sites, unpatched, in {len(tc_rel.originals())} original + {len(exes)} release + {len(spp)} SWOS++ exes '
                  f'(SWOS++ patches at run time: its own loader is not seen here)')
