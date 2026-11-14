"""4.2 set pieces 1+2 (Davide GO 14/11; design internal/handoff/setpieces-wingplay-design.md sections 1, 2): an
OPTIONS switch CALCI PIAZZATI / SET PIECES: CLASSICI (the original game) / NUOVI, for every match (physics and keeper
rules, both sides; SWOS++ keeps the original).

NUOVI:
- headers go down: the jump header's ball deltaZ (kBallJumpHeaderDeltaZ 0xA000, up) -> SP_JZ minus HEADING x SP_JST
  (HEADING = placement: a good header keeps the ball under the bar from further out); the flying header's
  (kFlyingHeaderBallDeltaZ 0x20000) -> SP_FZ;
- the header contact window's ceiling (ball z <= 15, the jump and the static header) -> SP_CEIL;
- the keeper: catch band ballDefensiveZ 13..27 -> 13..SP_BAND; no 6-yard-box bypass of the word29 gate (he comes for a
  ball in his 6-yard box only with rand16 < word29, as elsewhere in the box; both sites: the run to the landing spot and
  the catch);
- the CPU header gate (DecideWhetherCpuPlayerFires): ball within 900 instead of 648 (squared) when the ball is in the
  air (z >= 8), and facing right / left (2 / 6) accepted with the ball wide (x outside the penalty area's 193..478).

CLASSICI (SP_W 0): every stub does the original instruction(s) only (tools/hosttest/diff_structural.py proves it).

Room (MC 14/11): obj4 SETPIECE_AT..SETPIECE_END (swreg). LE padding (DE): every obj1 hook region swallows an
instruction with an absolute operand (1 fixup removed : 1 added), and the stubs reach obj2 through two base dwords (SPB:
obj2's and obj1's, the band's only fixups), read PC-relative: [ebp] = obj2's base, then [reg + constant offset].

Test switches (modver TEST_VARS, never in a release build): SP_TEST=0 / 1 (the stubs in, SP_W's start value until the
OPTIONS row exists); SP_JZ / SP_JST / SP_FZ / SP_CEIL / SP_BAND / SP_CPU (tuning, M3).
"""
import os
import re
import struct

import nasmcave

TAG = b'SETP'


def on():
    return bool(os.environ.get('SP_TEST'))


def _iv(k, d):
    v = os.environ.get(k)
    return int(v, 0) if v else d


def knobs():
    return dict(JZ=_iv('SP_JZ', -0x800), JST=_iv('SP_JST', 0x400), FZ=_iv('SP_FZ', 0x8000), CEIL=_iv('SP_CEIL', 17),
                BAND=_iv('SP_BAND', 22), CPU=_iv('SP_CPU', 900))


def _one(d, pat, name, n=1):
    m = [x.start() for x in re.finditer(pat, d, re.S)]
    assert n is None or len(m) == n, (name, [hex(x) for x in m])
    return m


def find(p):
    """The sites (obj1 offsets, from the exe's own bytes) and the obj2 offsets the stubs read."""
    import difficulty as df
    d = p.le.obj_bytes(1)
    o2 = p.le.obj_bytes(2)
    t = lambda o: df._t(p, o)
    _, sym = df.find(p)
    a2, a4 = sym['A2_'], sym['A4_']
    a5 = (2, sym['D0_'][1] + 4 * 13)
    d7 = (2, sym['D0_'][1] + 4 * 7)
    val = lambda o: struct.unpack_from('<I', o2, t(o + 1)[1])[0] if t(o + 1) and t(o + 1)[0] == 2 else None
    hz = [o for o in _one(d, rb'\xa1....\x8b\x35....\x89\x46.', 'mov eax, deltaZ', None) if t(o + 7) == a2]
    jz = [o for o in hz if val(o) == 0xA000]
    assert len(jz) == 1, ('kBallJumpHeaderDeltaZ', jz)
    jz = jz[0]
    assert d[jz - 10:jz - 8] == b'\xc7\x05' and t(jz - 8) == a2, 'PlayerHittingJumpHeader: mov A2, offset ballSprite'
    ball = t(jz - 4)
    fz = [o for o in hz if val(o) == 0x20000 and jz < o < jz + 0x600]
    assert len(fz) == 1, ('kFlyingHeaderBallDeltaZ', fz)
    fz = fz[0]
    dz = d[jz + 13]
    assert d[fz + 13] == dz, 'deltaZ offset'
    hd = [o + 10 for o in _one(d, rb'\xc7\x05........\x8b\x35....\x8a\x46', 'mov esi, A4 / mov al, heading', None)
          if jz < o < fz and t(o + 12) == a4]
    assert len(hd) == 1, ('PlayerHittingJumpHeader: heading', hd)
    hd = hd[0]
    ceil = [o for o in _one(d, rb'\x8b\x35....\x66\x83\x7e.\x0f\x0f\x87', 'contact ceiling', 2) if t(o + 2) == a2]
    assert len(ceil) == 2 and d[ceil[0] + 9] == d[ceil[1] + 9], 'the two contact ceilings'
    zo = d[ceil[0] + 9]
    band = _one(d, rb'\x66\x83\x3d....\x1b\x0f\x8f', 'catch band')[0]
    assert d[band + 14:band + 17] == b'\x66\x83\x3d' and t(band + 17) == t(band + 3) and d[band + 21] == 12, 'band low 12'
    gka = _one(d, rb'\x66\xa1....\x66\x0b\xc0\x75.\x8b\x35....\x8b\x46', '6-yard bypass', 2)
    assert t(gka[0] + 2) == t(gka[1] + 2), 'ballInGoalkeeperArea'
    cpu = _one(d, rb'\x8b\x35....\x81\x7e\x4a\x88\x02\x00\x00\x0f\x87', 'CPU header gate')[0]
    assert t(cpu + 2) == a5, 'mov esi, A5'
    fb = _one(d, rb'\x66\x83\x3d....\x05\x74.\xe9', 'facing bottom')[0]
    ft = [o for o in _one(d, rb'\x66\x83\x3d....\x01\x0f\x85', 'facing top', None) if cpu - 0x40 < o < cpu]
    assert len(ft) == 1 and fb < ft[0] < cpu and t(fb + 3) == t(ft[0] + 3) == d7, ('facing top', ft)
    ft = ft[0]
    for k in (ball, a2, a4, a5, d7, t(band + 3), t(gka[0] + 2), t(jz + 1), t(fz + 1)):
        assert k and k[0] == 2, k
    s = dict(JZ=jz, FZ=fz, HD=hd, CEIL0=ceil[0], CEIL1=ceil[1], BAND=band, GKA0=gka[0], GKA1=gka[1], CPU=cpu, FB=fb,
             FT=ft)
    c = dict(BALL_O=ball[1], A2_O=a2[1], A4_O=a4[1], A5_O=a5[1], D7_O=d7[1], BDZ_O=t(band + 3)[1],
             GKA_O=t(gka[0] + 2)[1], KJZ_O=t(jz + 1)[1], KFZ_O=t(fz + 1)[1], DZO=dz, ZO=zo, HDO=d[hd + 8])
    return s, c


# (region length, stub) per site; FB / FT keep their own branches after the call
HOOKS = (('JZ', 5, 'sp_jz'), ('FZ', 5, 'sp_fz'), ('HD', 9, 'sp_head'), ('CEIL0', 11, 'sp_ceil'),
         ('CEIL1', 11, 'sp_ceil'), ('BAND', 8, 'sp_band'), ('GKA0', 9, 'sp_gka'), ('GKA1', 9, 'sp_gka'),
         ('CPU', 13, 'sp_cpu'), ('FB', 15, 'sp_fb'), ('FT', 14, 'sp_ft'))

ASM = r"""
; ---- the base: ebp = SPB (PC-relative: no fixup); [ebp] = obj2's base (the band's only fixup)
SPB: dd O2BASE
    dd O1BASE                           ; ([ebp + 4]: obj1's base, for SWOS++'s flag)
TAGS: db 'SETP'
SP_W: db SP_START                       ; the option: 0 CLASSICI, 1 NUOVI
SP_SV: db SP_START                      ; (the save item, M2)
    dw 0
sp_base:
    call .n
.n: pop ebp
    sub ebp, .n - SPB
    ret

; ---- ZF = 1: the original game (CLASSICI, or SWOS++); in ebp = SPB; every register kept
sp_on:
    push ecx
    mov ecx, [ebp + 4]
    cmp byte [ecx + SWOSPP_O], 0FFh     ; (0FFh = no SWOS++)
    jne .z
    cmp byte [ebp + SP_W - SPB], 0
    jmp .x
.z: cmp ecx, ecx
.x: pop ecx
    ret

; ---- headers go down (replaces `mov eax, kBallJumpHeaderDeltaZ` / `mov eax, kFlyingHeaderBallDeltaZ`)
sp_jz:
    push ebp
    call sp_base
    mov eax, [ebp]
    mov eax, [eax + KJZ_O]
    call sp_on
    jz .x
    mov eax, JZ_NEW
.x: pop ebp
    ret
sp_fz:
    push ebp
    call sp_base
    mov eax, [ebp]
    mov eax, [eax + KFZ_O]
    call sp_on
    jz .x
    mov eax, FZ_NEW
.x: pop ebp
    ret

; ---- HEADING = placement (replaces `mov esi, A4` / `mov al, [esi + heading]` in PlayerHittingJumpHeader, after the
;      deltaZ is set): a jump header's ball deltaZ = JZ_NEW - heading x JZ_STEP
sp_head:
    push ebp
    call sp_base
    mov esi, [ebp]
    mov esi, [esi + A4_O]
    mov al, [esi + HDO]
    call sp_on
    jz .x
    push ebx
    push ecx
    mov ebx, [ebp]
    mov ebx, [ebx + A2_O]               ; (the ball)
    cmp dword [ebx + DZO], JZ_NEW       ; (a jump header: flying / lob headers have their own deltaZ)
    jne .y
    movzx ecx, al
    and ecx, 7
    imul ecx, ecx, JZ_STEP
    sub [ebx + DZO], ecx
.y: pop ecx
    pop ebx
.x: pop ebp
    ret

; ---- the contact window's ceiling (replaces `mov esi, A2` / `cmp word [esi + z], 15`, then `ja`)
sp_ceil:
    push ebp
    call sp_base
    mov esi, [ebp]
    mov esi, [esi + A2_O]
    call sp_on
    jz .c
    cmp word [esi + ZO], CEIL_NEW
    pop ebp
    ret
.c: cmp word [esi + ZO], 15
    pop ebp
    ret

; ---- the keeper's catch band top (replaces `cmp ballDefensiveZ, 27`, then `jg`)
sp_band:
    push ebp
    push eax
    push ecx
    call sp_base
    mov eax, 27
    call sp_on
    jz .c
    mov eax, BAND_NEW
.c: mov ecx, [ebp]
    cmp [ecx + BDZ_O], ax
    pop ecx
    pop eax
    pop ebp
    ret

; ---- the 6-yard-box bypass of the word29 gate (replaces `mov ax, ballInGoalkeeperArea` / `or ax, ax`, then `jnz`)
sp_gka:
    push ebp
    call sp_base
    push ecx
    mov ecx, [ebp]
    mov ax, [ecx + GKA_O]
    pop ecx
    call sp_on
    jz .c
    xor ax, ax                          ; (NUOVI: no bypass)
.c: or ax, ax
    pop ebp
    ret

; ---- the CPU header gate (replaces `mov esi, A5` / `cmp [esi + ballDistance], 648`, then `ja`)
sp_cpu:
    push ebp
    push eax
    call sp_base
    mov esi, [ebp]
    mov eax, 648
    call sp_on
    jz .c
    cmp word [esi + BALL_O + ZO], 8     ; (the ball in the air)
    jb .c
    mov eax, CPU_NEW
.c: mov esi, [esi + A5_O]
    cmp [esi + 4Ah], eax
    pop eax
    pop ebp
    ret

; ---- the CPU header facing (FB replaces `cmp D7, 5` before `jz facing` / `jmp no_fire`; FT `cmp D7, 1` before `jnz
;      no_fire`): NUOVI also accepts right / left (2 / 6) with the ball wide; ZF = 1 accepted
sp_fb:
    push ebp
    push eax
    call sp_base
    mov eax, [ebp]
    mov ax, [eax + D7_O]
    call sp_on
    jz .c
    call sp_wide
    jz .x
.c: cmp ax, 5
.x: pop eax
    pop ebp
    ret
sp_ft:
    push ebp
    push eax
    call sp_base
    mov eax, [ebp]
    mov ax, [eax + D7_O]
    call sp_on
    jz .c
    call sp_wide
    jz .x
.c: cmp ax, 1
.x: pop eax
    pop ebp
    ret
sp_wide:                                ; ax = direction; ZF = 1: 2 / 6 and the ball's x outside 193..478
    push ecx
    cmp ax, 2
    je .d
    cmp ax, 6
    jne .no
.d: mov ecx, [ebp]
    movsx ecx, word [ecx + BALL_O + 20h]
    cmp ecx, 193
    jl .yes
    cmp ecx, 478
    jg .yes
.no:test esp, esp                       ; (ZF = 0)
    jmp .x
.yes:cmp ecx, ecx
.x: pop ecx
    ret
"""


def patch(p, lang):
    if not on():
        return None
    import controls
    import difficulty as df
    import modver
    import swreg
    assert modver.is_test(), 'SP_TEST: test builds only (until the OPTIONS row)'
    s, c = find(p)
    sw = controls.locate(p)['SWOSPP']
    assert sw[0] == 1, sw
    k = knobs()
    start = int(os.environ.get('SP_TEST') or 0)
    assert start in (0, 1), 'SP_TEST=0 (CLASSICI) / 1 (NUOVI)'
    sym = {**{n: (0, v) for n, v in c.items()}, 'O2BASE': (2, 0), 'O1BASE': (1, 0), 'SWOSPP_O': (0, sw[1]), 'SP_START': (0, start),
           'JZ_NEW': (0, k['JZ'] & 0xFFFFFFFF), 'JZ_STEP': (0, k['JST']), 'FZ_NEW': (0, k['FZ']),
           'CEIL_NEW': (0, k['CEIL']), 'BAND_NEW': (0, k['BAND']), 'CPU_NEW': (0, k['CPU'])}
    at = swreg.SETPIECE_AT
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 4)
    lab = nasmcave.labels(ASM, at, sym)
    assert len(fix) == 2 and not rel, ('setpieces: two fixups (SPB) only', fix, rel)
    left = swreg.SETPIECE_END - at - len(code)
    assert left >= swreg.SETPIECE_MIN, ('setpieces: band room', left)
    assert p.le.obj(4).npages * 0x1000 >= swreg.SETPIECE_END, 'setpieces: obj4 pages (patch.py)'
    assert not any(p.get(4, at, swreg.SETPIECE_END - at)), 'setpieces: band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    d = p.le.obj_bytes(1)
    fb_f = s['FB'] + 10 + struct.unpack_from('<b', d, s['FB'] + 9)[0]          # (jz facing)
    fb_n = s['FB'] + 15 + struct.unpack_from('<i', d, s['FB'] + 11)[0]         # (jmp no_fire)
    ft_n = s['FT'] + 14 + struct.unpack_from('<i', d, s['FT'] + 10)[0]         # (jnz no_fire)
    skip = set(filter(None, os.environ.get('SP_SKIP', '').split(',')))
    for key, n, l in HOOKS:
        if key in skip:
            continue
        df._hook(p, s[key], n, n, lab[l])
    if 'FB' not in skip:                                # call sp_fb / jz facing / jmp no_fire / 3 nops
        o = s['FB']
        r8 = fb_f - (o + 7)
        assert -128 <= r8 < 128
        p.put(1, o + 5, struct.pack('<Bb', 0x74, r8) + b'\xe9' + struct.pack('<i', fb_n - (o + 12)) + b'\x90' * 3)
    if 'FT' not in skip:                                # call sp_ft / jnz no_fire / 3 nops
        o = s['FT']
        p.put(1, o + 5, b'\x0f\x85' + struct.pack('<i', ft_n - (o + 11)) + b'\x90' * 3)
    LABELS.clear()
    LABELS.update(lab)
    SITES.clear()
    SITES.update(s)
    print(f'exe: set pieces (SP_TEST={start}): code obj4+{at:#x} ({len(code)} B, {left} B left), {len(HOOKS)} obj1 sites')
    return at + len(code)


LABELS = {}
SITES = {}
