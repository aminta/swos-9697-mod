"""Team cache, gate H1 (teamcache-fable-design.md 1.8, leg 1, static). On the built release exes (4 CD + 4 GOG + SWOS++;
tc_rel.release()): every LE fixup whose target is inside the game's cache [OLDSEL, + 68400) or the big one [NEWSEL,
+ SEL_ROOM) must be on the whitelist (tcaudit.fixup_kind):
  - selTeamsPtr's initial value (obj2 data) and SELBASEV's default (trailer.py `SELBASEV: dd SELBUF`, obj1 data);
  - the OLDSEL / NEWSEL constants of careerworld's stubs: mov / cmp dword [selTeamsPtr | SELBASEV], X; cmp eax, X;
    mov esi / edi, NEWSEL (w_save_tail's copy source) - the cache's first byte only;
  - swe.c's DIY code (obj4 below swreg.REG_AT): diy_size and the 'WM' block after a DIY file's records, OLDSEL + 0..4;
  - the END of the fixed part: ctgame.c's hash of careerFileBuffer runs an index from -95153, so the compiler's base is
    careerFileBuffer + 95153 = OLDSEL (found by this gate; not in the design's list - it is not a cache use).
A new fixup fails. Plus the source rule: no module spells the game's cache as NUMSEL + 2 / SELBUF, except swe.c's DIY
code and SELBASEV's default."""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))
import tcaudit as T  # noqa: E402
import tc_rel  # noqa: E402

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def short(p):
    return os.path.relpath(p, tc_rel.C)


def check(paths, need_new):
    errs, kinds, n = [], {}, 0
    for p in paths:
        L, fx = T.exe_fixups(p)
        n += len(fx)
        if need_new and (L['new'] is None or L['selbasev'] is None):
            errs.append(f'{short(p)}: no big cache / SELBASEV found')
            continue
        for sobj, soff, which, off, kind, ctx in fx:
            if kind is None:
                errs.append(f'{short(p)}: obj{sobj}+{soff:#x} -> {which}SEL+{off:#x} is not on the whitelist ({ctx})')
            else:
                kinds.setdefault(kind, set()).add(os.path.basename(p))
        for must in ("selTeamsPtr's initial value",) + (("SELBASEV's default (trailer.py: dd SELBUF)",) if need_new else ()):
            if not any(k == must for _, _, _, _, k, _ in fx):
                errs.append(f'{short(p)}: missing: {must}')
    return errs, kinds, n


def test_tc_fixups_release():
    rel, exes, spp, sd = tc_rel.release()
    if rel is None:
        return True, 'SKIP: no c/REL42* with the 4 CD + 4 GOG exes (TC_REL=dir)'
    errs, kinds, n = check(exes + spp, True)
    assert not errs, f'{len(errs)}: ' + '; '.join(errs[:12])
    return True, (f'{short(rel)}: {len(exes)} exes + {len(spp)} SWOS++' + (f' ({short(sd)})' if spp and sd != rel else '')
                  + f', {n} fixups into the caches, all whitelisted ({len(kinds)} kinds)'
                  + ('' if spp else '; NO SWOS++ exe found'))


def test_tc_fixups_orig():
    """control: the original game has exactly two - selTeamsPtr's initial value and ProcessCareerFile's mov"""
    exes = tc_rel.originals()
    if not exes:
        return True, 'SKIP: no orig/ exes'
    for p in exes:
        L, fx = T.exe_fixups(p)
        assert L['new'] is None and L['selbasev'] is None, p
        assert sorted(k for *_, k, _ in fx) == ['mov dword [selTeamsPtr / SELBASEV], OLDSEL', "selTeamsPtr's initial value"], (p, fx)
    return True, f'{len(exes)} original exes: 2 fixups each'


def test_tc_fixups_whitelist_control():
    """planted fixups the whitelist must refuse / accept (forms on synthetic bytes, layout of a real exe)"""
    rel, exes, spp, _ = tc_rel.release()
    if rel is None:
        return True, 'SKIP: no release exes'
    from le import LE
    le = LE(exes[0])
    L = T.exe_layout(le)
    old, new, selptr, sbv = L['old'], L['new'], L['selptr'], L['selbasev']
    at = 0x40                                       # a source offset for the planted bytes, no real fixup next to it
    L = dict(L, fx={k: v for k, v in L['fx'].items() if not (at - 16 <= k[1] <= at + 4)})

    def kind(pre, toff, sobj=1, fix=None):
        b = bytearray(0x80)
        b[at - len(pre):at] = pre
        L2 = dict(L, fx={**L['fx'], **({(sobj, at - 4): fix} if fix else {})})
        return T.fixup_kind(le, L2, sobj, at, toff, bytes(b))
    ok = [(b'\xc7\x05\0\0\0\0', old, 1, (2, selptr)), (b'\xc7\x05\0\0\0\0', new, 1, (1, sbv)), (b'\x81\x3d\0\0\0\0', new, 1, (1, sbv)),
          (b'\x81\x3d\0\0\0\0', new, 1, (2, selptr)), (b'\x3d', new, 1, None), (b'\x3d', old, 1, None), (b'\xbe', new, 1, None),
          (b'\x8d\x89', old + 4, 4, None), (b'\xb9' + struct.pack('<i', -T.FIXED) + b'\x0f\xb6\x91', old, 3, None)]
    bad = [(b'\x8b\x0d', old, 1, None),                         # mov ecx, [OLDSEL]: the cache read directly
           (b'\xc7\x05\0\0\0\0', old, 1, (2, selptr + 8)),      # mov dword [another variable], OLDSEL
           (b'\xc7\x05\0\0\0\0', old + T.TEAM, 1, (2, selptr)), # a record's address
           (b'\x3d', new + T.TEAM, 1, None), (b'\xbe', old, 1, None), (b'\xbe', new + 2, 1, None),
           (b'\x8d\x89', old + 5, 4, None), (b'\x8d\x89', old + 4, 3, None), (b'\x8d\x89', new, 4, None),
           (b'\x0f\xb6\x91', old, 3, None),                     # obj3 indexing the game's cache with no -95153 index
           (b'\xb9' + struct.pack('<i', -T.FIXED) + b'\x0f\xb6\x91', old + 1, 3, None)]
    errs = [f'refused: {x[0].hex()} -> {x[1] - old:#x} obj{x[2]}' for x in ok if kind(*x) is None]
    errs += [f'accepted: {x[0].hex()} -> {x[1] - old:#x} obj{x[2]} as {kind(*x)}' for x in bad if kind(*x) is not None]
    # obj4 above swe.c's band is not swe's DIY code
    if T.fixup_kind(le, L, 4, T.SWE_CODE + 0x10, old + 1, bytes(T.SWE_CODE + 0x80)) is not None:
        errs.append('accepted: obj4 above swreg.REG_AT')
    assert not errs, '; '.join(errs)
    return True, f'{len(ok)} allowed forms accepted, {len(bad) + 1} planted violations refused'


# the source rule: a line that spells the game's cache (NUMSEL + 2, SELBUF) -> allowed only where listed (file, text)
SRC_PAT = re.compile(r'(?i)numsel\w*(\[\w*\])?\s*\+\s*2\b|SELBUF')
SRC_OK = [('trailer.py', 'SELBASEV: dd SELBUF'), ('trailer.py', "'SELBUF': (2, numsel + 2)"), ('trailer.py', "'MARK', 'SELBUF')})"),
          ('swe.c', 'static u32 diy_size(void)'), ('swe.c', 'const u8 *b = SWE_NUMSEL + 2 + 684 * *(u16 *)SWE_NDIY;')]
SRC_SKIP = ('swostest.py',     # the harness (reads the running game's memory; not part of the exe)
            'tcaudit.py')      # this audit


def src_hits(root):
    out = []
    for f in sorted(os.listdir(root)):
        if not f.endswith(('.py', '.c', '.h', '.asm', '.inc')) or f in SRC_SKIP:
            continue
        for k, line in enumerate(open(os.path.join(root, f), errors='replace'), 1):
            if SRC_PAT.search(line):
                out.append((f, k, line.strip()))
    return out


def test_tc_source_rule():
    hits = src_hits(TOOLS)
    bad = [h for h in hits if not any(h[0] == f and t in h[2] for f, t in SRC_OK)]
    assert not bad, 'the game cache used outside swe.c DIY / SELBASEV default: ' + '; '.join(f'{f}:{k}: {t[:90]}' for f, k, t in bad[:8])
    missing = [x for x in SRC_OK if not any(h[0] == x[0] and x[1] in h[2] for h in hits)]
    assert not missing, ('the allowed uses moved (update SRC_OK)', missing)
    # control: the pattern sees the spellings a module would use
    for t in ('mov esi, NUMSEL + 2', "sym['X'] = (2, numsel + 2)", 'u8 *c = SWE_NUMSEL + 2;', 'lea eax, [SELBUF + ebx]',
              "trailer.INFO['SELBUF']", 'b = (u8 *)S7_NUMSEL+2;'):
        assert SRC_PAT.search(t), t
    for t in ('cmp word [NUMSEL], 2', 'n = numsel * 2', 'mov eax, [SELBASEV]', 'NUMSEL + 20'):
        assert not SRC_PAT.search(t), t
    return True, f'{len(hits)} lines spell the game cache, all in the {len(SRC_OK)} allowed places'
