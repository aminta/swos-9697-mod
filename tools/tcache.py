"""4.2 team cache bound (MC 16/11, design internal/handoff/teamcache-fable-design.md; step 1a).

THE RULE (one for both caches; CONVENTIONS 26):
  The game keeps every club it plays with as a 684-byte record in a team cache, the count in g_numSelectedTeams
  (NUMSEL). There are two caches, told apart by the pointer in use (selTeamsPtr), never by the world:
    - the game's own (g_selectedTeams, 100 records; every mode, and careers not on the big cache), and
    - the big cache at careerworld B_SEL (NEWSEL, careerworld.SEL_CAP records; big-world careers today, every career
      from step 1b).
  Each cache has two numbers:
    - a MEMORY CAP, the records that fit (100 / SEL_CAP): a hard stop. An insert past it would overwrite what follows
      the cache (the game's pseudo registers / the stage), so tc_chk stops the game with the message
      "TEAM CACHE FULL (n) - PLEASE REPORT" (tc_full: text mode, DOS line, the game's EndProgram - as LoadFile's
      missing-file exit). The save on disk is untouched.
    - a SAVE BUDGET, the most records with which the whole trailer (main block + 'EN') still fits in the save room:
      trailer.py computes both (the game cache's: nmax, a world-0 career's 'EN' in 68400 B; the big cache's: TC_CAP,
      the full 'EN' in SEL_ROOM). What tc_room / tc_reserve answer.
  Mandatory inserts (the game's own loaders and everything that goes through them: gplay / dplay call cseg_32E15) only
  meet the memory cap. Optional features (friendlies, contest views, supercups, any future loader) ASK FIRST:
    tc_room()            records left = budget - NUMSEL - the world's reserve (0 if none);
    tc_reserve(list, n)  1 if the clubs of the word list not cached yet (FindTeamInCache, each once, 0xFFFF skipped)
                         fit in tc_room(), else 0 - then the feature is skipped cleanly, never half installed.
  The reserve (RESERVE[world], a byte per world) keeps room for a world's late mandatory installs, so an optional
  feature never eats it. Counts written without an insert are checked too (tc_clamp: count > memory cap -> tc_full):
  NUMSEL after a load (an engine after_process callback), ctgame.c's restore, RestoreSelectedTeams (careerworld's wl
  stub: tc_clamp_sel, the career's cache by SELBASEV). TC_HWM keeps the highest count since the exe started, TC_SKIP the optional installs refused (neither saved; the harness
  reads them). TC_FLOOR: the big cache's save budget never drops below 159 (155 with 'FP') - a build whose trailer grew
  past it fails (trailer.py), so a career saved by an earlier 4.2.x exe always loads in a later one.
  Adding teams in any new feature: tc_reserve / tc_room first, then the game's loaders. Never a constant.

Hooks (the 6 inserts of the original obj1, all `66 83 05 <NUMSEL> 01`, asserted on p.get() bytes):
  5 sites: the copy-count `mov word [D0], 155h` (9 B) in front of the copy -> `call tc_chk_n` + 4 nops;
  cseg_3283C: the add comes before its copy -> the add (8 B) -> `call tc_chk_add` + 3 nops.
  Each hooked instruction's absolute fixup at +3 is removed first (CONVENTIONS: fixups under overwritten code).
Place: obj3's chain (CONVENTIONS 23: mod code in obj3; 23bis: obj4 is the engine's - MC 16/11, option A), every build.
Callers never use a literal address: each one holds a dword that tcache binds once it is placed (ref(): p.retarget /
add_ptr to the entry; the trailer's after_process entry through engine.CALL_AT + trailer.late). check() at the end of
patch_exe asserts every registered dword is bound, non-zero and inside tcache's code. (The old swreg band for it,
obj4+0x1FC00..0x1FF00, was never used: folded into FRND, MC 16/11.)
"""
import re
import struct

import bound
import nasmcave

ENTRIES = ('tc_clamp', 'tc_room', 'tc_reserve', 'tc_full', 'tc_clamp_sel')    # what callers may bind (ref())
TABLE = bound.Table('tcache', ENTRIES)  # (4.2 x3all, MC 16/11: the shared bound-dword generator, tools/bound.py - gplay's too)
REFS = TABLE.refs                       # [(obj, off, entry)]: callers' dwords, bound at patch() (or at once after it)
PLACED = TABLE.placed                   # entry -> (3, off) once patch() ran
TC_FLOOR, TC_FLOOR_FP = 159, 155       # the big cache's save budget may never drop below these (trailer.py asserts it; 'FP'
                                        # builds: the fixture port's item; 4.2 rc4, MC 22/11: 'CB' too - the release items' floor
                                        # is 155, measured 21 B left; h3s7r test shapes carry CB without FP); a later exe must
                                        # load what an earlier one saved
RESERVE = {}                            # world -> records kept for its late mandatory installs (builders fill it)
MSG = 'TEAM CACHE FULL (%03d) - PLEASE REPORT'
LABELS = {}
INFO = {}

ASM = r"""
tc_cap:                                 ; eax = the memory cap of the cache in use
    mov eax, 100
    cmp dword [SELPTR], NEWSEL
    jne .r
    mov eax, SEL_CAP
.r:
    ret

tc_one:                                 ; one more record: NUMSEL < cap, else the stop; the high-water mark
    call tc_cap
    cmp ax, [NUMSEL]
    jbe tc_full
    mov ax, [NUMSEL]
    inc eax
    cmp ax, [TC_HWM]
    jbe .r
    mov [TC_HWM], ax
.r:
    ret

tc_chk_n:                               ; replaces `mov word [D0], 155h` in front of an insert's copy
    pushfd
    push eax
    call tc_one
    pop eax
    popfd
    mov word [D0], 155h
    ret

tc_chk_add:                             ; replaces cseg_3283C's `add word [NUMSEL], 1` (before its copy)
    push eax
    call tc_one
    pop eax
    add word [NUMSEL], 1
    ret

tc_clamp:                               ; a count written without an insert (all registers and flags kept)
    pushfd
    push eax
    call tc_cap
    cmp ax, [NUMSEL]
    jb tc_full
    pop eax
    popfd
    ret

tc_clamp_sel:                           ; RestoreSelectedTeams' count: against the CAREER's cache (SELBASEV), not
    pushfd                              ; selTeamsPtr - at the main menu w_mmi points it at the game's cache while a
    push eax                            ; big career's records stay at NEWSEL (FRIENDLY -> ContestInProgress parks
    mov eax, 100                        ; and restores the career's count; Fable review 16/11)
    cmp dword [SELBASEV], NEWSEL
    jne .c
    mov eax, SEL_CAP
.c:
    cmp ax, [NUMSEL]
    jb tc_full
    pop eax
    popfd
    ret

tc_room:                                ; cdecl u32 tc_room(void): records an optional feature may still add
    push edx
    mov eax, NMAX
    cmp dword [SELPTR], NEWSEL
    jne .b
    mov eax, TC_CAP
.b:
    movzx edx, word [NUMSEL]
    sub eax, edx
    jbe .z
%if WORLDS
    movzx edx, byte [SLT + WORLD_BYTE]
    cmp edx, N_WORLDS
    jae .r
    movzx edx, byte [TC_RES + edx]
    sub eax, edx
    ja .r
%else
    jmp .r
%endif
.z:
    xor eax, eax
.r:
    pop edx
    ret

tc_reserve:                             ; cdecl u32 tc_reserve(const u16 *list, u32 n): 1 = they fit, 0 = skip
    push ebx
    push esi
    push edi
    push ebp
    push dword [D0]                     ; (FindTeamInCache's pseudo registers)
    push dword [D1]
    push dword [A0]
    mov esi, [esp + 32]
    mov ecx, [esp + 36]
    xor ebp, ebp                        ; the clubs to add
    xor ebx, ebx                        ; index
.n:
    cmp ebx, ecx
    jae .d
    mov ax, [esi + 2 * ebx]
    cmp ax, 0FFFFh
    je .x
    xor edi, edi                        ; (each club once: an earlier equal word counted it)
.e:
    cmp edi, ebx
    jae .f
    cmp ax, [esi + 2 * edi]
    je .x
    inc edi
    jmp .e
.f:
    mov [D0], ax
    push ecx
    push esi
    call FTIC                           ; (ZF: cached; esi, ax, D0, D1, A0 changed)
    pop esi
    pop ecx
    jz .x
    inc ebp
.x:
    inc ebx
    jmp .n
.d:
    call tc_room
    cmp ebp, eax
    setbe al
    movzx eax, al
    test eax, eax
    jnz .y
    inc word [TC_SKIP]                  ; (an optional install refused: the harness reads it)
.y:
    pop dword [A0]
    pop dword [D1]
    pop dword [D0]
    pop ebp
    pop edi
    pop esi
    pop ebx
    ret

tc_full:                                ; the stop: text mode, the DOS line, the game's EndProgram
    movzx eax, word [NUMSEL]
    mov ecx, 3
.dg:
    xor edx, edx
    mov ebx, 10
    div ebx
    add dl, '0'
    mov [TC_NUM + ecx - 1], dl
    loop .dg
    mov ax, 2
    int 10h
    mov edx, TC_MSG
    mov ah, 9
    int 21h
    jmp ENDPROG

TC_HWM: dw 0
TC_SKIP: dw 0                           ; (optional installs refused by tc_reserve since the exe started)
TC_MSG: db MSG_HEAD
TC_NUM: db '000', MSG_TAIL, 13, 10, '$'
TC_RES: RES_BYTES
"""


def sites(p):
    """[(kind, off)]: 'n' = the copy-count mov (9 B) of an insert, 'add' = the add itself (cseg_3283C, mov after it).
    From the original obj1 (the 6 adds: exactly 6, each with its mov within 0x60 B before, or 8 B after)."""
    import sacups
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    d0 = r['A0'] - 32
    numsel = INFO['NUMSEL'][1]
    add = b'\x66\x83\x05' + struct.pack('<I', numsel) + b'\x01'
    mov = b'\x66\xc7\x05' + struct.pack('<I', d0) + b'\x55\x01'
    adds = [m.start() for m in re.finditer(re.escape(add), d)]
    assert len(adds) == 6, ('tcache: g_numSelectedTeams +1 sites', len(adds))
    out = []
    for a in adds:
        k = d.rfind(mov, a - 0x60, a)
        if k >= 0:
            out.append(('n', k))
        else:
            assert d[a + 8:a + 17] == mov, ('tcache: no copy-count mov at the insert', hex(a))
            out.append(('add', a))
    assert sum(k == 'add' for k, _ in out) == 1, out
    return out, d0


def verify_team(p):
    """(FindTeamInCache, EndProgram) from VerifyTeamLoaded: `call FindTeamInCache; jnz +1; ret; int3; call RingABell;
    call EndProgram; int3` (once; EndProgram = the game's exit, as LoadFile's missing-file path)."""
    d = p.le.obj_bytes(1)
    ms = [m for m in re.finditer(rb'\xe8(.{4})\x75\x01\xc3\xcc\xe8.{4}\xe8(.{4})\xcc', d, re.S)]
    assert len(ms) == 1, ('tcache: VerifyTeamLoaded', len(ms))
    f = ms[0].start() + 5 + struct.unpack('<i', ms[0].group(1))[0]
    assert d[f:f + 2] == b'\x66\xa1', d[f:f + 8].hex()
    e = ms[0].end() - 1 + struct.unpack('<i', ms[0].group(2))[0]
    assert d[e:e + 1] == b'\xe8', ('tcache: EndProgram starts with call StopAIL', d[e:e + 8].hex())
    return f, e


def ref(p, obj, off, name):
    """A caller's dword at obj:off (holding a placeholder fixup or none) gets bound to entry `name` - now if tcache is
    placed, else at patch(). The only way to reach tcache's code (no literal address)."""
    TABLE.ref(p, obj, off, name)


def _bind(p, obj, off, name):
    TABLE.bind(p, obj, off, name)               # (a placeholder fixup retargeted, or a plain 0 dword, e.g. ctgame.c's pointer)


def register():
    """Before trailer.patch: the load's count check (an engine after_process callback; trailer.late binds it)."""
    import engine
    TABLE.reset()
    engine.CALL_AT.pop('tc_clamp', None)
    engine.after_process('tc_clamp')


def check(p):
    """End of patch_exe: every caller's dword bound to tcache's code (a call through an unbound one would crash)."""
    import engine
    lo, hi = INFO['code']
    n = TABLE.check(p)                          # (every caller's dword: its fixup, its bytes, inside tcache's code)
    t = engine.CALL_AT.get('tc_clamp')
    assert t is not None and t[0] == 3 and lo <= t[1] < hi and t == PLACED['tc_clamp'], ('tcache: unbound', 'engine', t)
    return n + 1


def patch(p, at):
    """obj3:at, in obj3's chain after trailer.patch (its INFO: NUMSEL, the budgets). Returns the end."""
    import careerworld
    import trailer
    INFO.clear()
    INFO.update(NUMSEL=trailer.INFO['NUMSEL'], NMAX=trailer.INFO['nmax'], TC_CAP=trailer.INFO['tc_cap'])
    ss, d0 = sites(p)
    big = careerworld.BSS[0] is not None
    import mkseason
    worlds = bool(mkseason.worlds())
    nw = 0
    if worlds:
        assert 'slt' in careerworld.SITES, 'tcache: worlds without careerworld.patch (the world byte)'
        nw = max(w['n'] for w in mkseason.world_defs()) + 1
    res = [RESERVE.get(w, 0) for w in range(nw)]
    head, tail = MSG.split('%03d')
    hs = careerworld.sel_sites(p, d0)
    ftic, endp = verify_team(p)
    sym = {'NUMSEL': INFO['NUMSEL'], 'D0': (2, d0), 'D1': (2, d0 + 4), 'A0': (2, d0 + 32),
           'SELPTR': (2, hs['selptr']), 'SELBASEV': (1, trailer.INFO['selbasev']), 'NEWSEL': (2, careerworld.BSS[0] + careerworld.B_SEL) if big else (0, 0),
           'SEL_CAP': (0, careerworld.SEL_CAP), 'NMAX': (0, INFO['NMAX']), 'TC_CAP': (0, INFO['TC_CAP'] or 0),
           'FTIC': (1, ftic), 'ENDPROG': (1, endp),
           'WORLDS': (0, int(bool(worlds))), 'N_WORLDS': (0, nw),
           'MSG_HEAD': (0, "'" + head + "'"), 'MSG_TAIL': (0, "'" + tail + "'"),
           'RES_BYTES': (0, 'db ' + ', '.join(map(str, res)) if res else 'db 0')}
    if worlds:
        sym.update(SLT=careerworld.SITES['slt'], WORLD_BYTE=(0, careerworld.WORLD_BYTE))
    while True:                                 # (no pointer across an obj3 page: LE fixups are per page)
        code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
        if all((at + o) % 0x1000 <= 0x1000 - 4 for o, _, _ in fix + rel):
            break
        at += 4
    lab = nasmcave.labels(ASM, at, sym)
    end = at + len(code)
    assert not any(p.get(3, at, len(code))), 'tcache: obj3 room not free'
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    import engine
    INFO['code'] = (at, end)
    TABLE.place(p, {n: (3, lab[n]) for n in ENTRIES}, (3, at, end), clear=True)   # (binds every registered dword)
    engine.CALL_AT['tc_clamp'] = PLACED['tc_clamp']  # (trailer.late binds the after_process slot)
    for kind, off in ss:                        # (the patched bytes: nothing else hooks these instructions)
        n = 9 if kind == 'n' else 8
        want = (b'\x66\xc7\x05' + struct.pack('<I', d0) + b'\x55\x01' if kind == 'n'
                else b'\x66\x83\x05' + struct.pack('<I', INFO['NUMSEL'][1]) + b'\x01')
        assert bytes(p.get(1, off, n)) == want, ('tcache: site patched by someone else', kind, hex(off))
        p.remove(1, off + 3)
        p.branch(1, off, 0xE8, 3, lab['tc_chk_n' if kind == 'n' else 'tc_chk_add'], n=n)
    LABELS.clear()
    LABELS.update({k: (3, v) for k, v in lab.items()})   # (tools/hosttest test_tcache: the labels, symbols, numbers)
    LABELS['sym'] = {k: sym[k] for k in ('NUMSEL', 'D0', 'D1', 'A0', 'SELPTR', 'SELBASEV', 'NEWSEL', 'FTIC', 'ENDPROG')}
    LABELS['caps'] = {'nmax': INFO['NMAX'], 'tc_cap': INFO['TC_CAP'] or 0, 'sel_cap': careerworld.SEL_CAP,
                      'sites_n': sum(k == 'n' for k, _ in ss), 'sites_add': sum(k == 'add' for k, _ in ss)}
    print(f'exe: team cache bound (tcache): obj3+{at:#x}..{end:#x} ({len(code)} B); memory caps 100 / {careerworld.SEL_CAP if big else "-"}, save budgets {INFO["NMAX"]} / '
          f'{INFO["TC_CAP"] if big else "-"}; inserts obj1+' + ', '.join(f'{o:#x}{"+" if k == "add" else ""}' for k, o in ss))
    return end
