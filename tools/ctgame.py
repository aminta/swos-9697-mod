"""4.0.6 option C, P1 (Davide GO 03/11): the continental rounds as the game's own contests (ctgame.c) - the builder
P3's competition screens will open. obj3, the chain's end after ctview (patch.py: <= LT3_AT) + a zero-fill scratch
of CG_BSS at 0x1000 * patch.OBJ3_PAGES, above obj3's file pages (vsize only: no file or save bytes; DOS/4GW does
not zero it, ctgame.c clears what it uses).

The glue cg_native(st, buf) is cseg_8B2D3's first half - slot index 3 (D0), D1 = D2 = 0 as conti's ct_build: the
slot buffer into the work area (cseg_8B71C), the team list (cseg_31F58: the clubs into the team cache, as the game
loads them), the career's foreign market (cseg_8C607), the contest's init by type (cseg_883B8), the work area into
buf (cseg_8B7EA) - never its second half (cseg_8BF89, cseg_8B71C, cseg_8B8B8: the career calendar's days). The
game's work area (diyFileBufferCopy + DIY_competitionStart, B52h) and its D0..A6 are kept and put back: a build
leaves only the clubs it added to the team cache (g_numSelectedTeams up; P2 puts it back).

Test builds: CONTI_CGTEST=1 - conti's ct_build calls cg_selftest after it built the career club's game in slot 3
(the harness reads CG_T through the 'CGTRPTR' marker); CG_FILL_TEST=5A - the scratch filled with that byte first
(the MiSTer-like start)."""
import os
import re
import struct
import subprocess
import tempfile

CG_MAX = 0x1000                         # the code + table (obj3 chain room)
CG_BSS = 0x3000                         # the scratch (ctgame.c CG_END)
CG_TAB_MAX = 0x400
NRD = 8                                 # (conti.h)
LABELS = {}


def w16(b, o):
    return struct.unpack_from('<H', b, o)[0]

ASM = r"""
cg_native:                              ; cdecl (st, buf): cseg_8B2D3's first half into buf (slot index 3)
    pushad
    push es
    push ds
    pop es
    cld
    mov esi, DIYCOPY                    ; the work area -> the save area
    mov edi, CG_SAVE_
    mov ecx, 0B52h
    rep movsb
    sub esp, 60                         ; D0..D7, A0..A6
    mov esi, D0R
    mov edi, esp
    mov ecx, 15
    rep movsd
    mov eax, [esp + 60 + 40]
    mov [cg_st], eax
    mov eax, [esp + 60 + 44]
    mov [cg_buf], eax
    mov word [eax + 2Bh], 3             ; (cseg_8B2D3: the slot index into the buffer)
    call .regs
    mov eax, [cg_buf]                   ; A0 = the buffer: into the work area
    mov [A0R], eax
    call C8B71C
    call .regs                          ; A0 = the struct, A1 = the buffer
    call C31F58
    call .regs
    call C8C607
    call .regs
    mov dword [D0R], 0                  ; (D0 <-> D1 around the init)
    mov dword [D0R + 4], 3
    call C883B8
    call .regs
    mov word [W10EAB5], 3
    mov word [W10EED4], 3
    mov eax, [cg_st]
    mov al, [eax + 1]
    cbw
    mov edx, [cg_buf]
    mov [edx], ax                       ; the type
    mov [A0R], edx
    call C8B7EA                         ; the work area -> the buffer
    mov esi, esp
    mov edi, D0R
    mov ecx, 15
    rep movsd
    add esp, 60
    mov esi, CG_SAVE_                   ; the work area back
    mov edi, DIYCOPY
    mov ecx, 0B52h
    rep movsb
    pop es
    popad
    ret
cg_vsim:                                ; cdecl (buf): (CONTI_CGVIEW test builds) what the game's view does to the state
    pushad                              ; - buf into the work area (cseg_8B71C), the work area back into buf (cseg_8B7EA)
    mov eax, [esp + 36]
    mov [cg_buf], eax
    mov [cg_st], eax
    call cg_native.regs
    call C8B71C
    call cg_native.regs
    mov eax, [cg_buf]
    mov [A0R], eax
    call C8B7EA
    popad
    ret

cg_native.regs:
    mov dword [D0R], 3
    mov dword [D0R + 4], 0
    mov dword [D0R + 8], 0
    mov eax, [cg_st]
    mov [A0R], eax
    mov eax, [cg_buf]
    mov [A0R + 4], eax
    ret

align 4
cg_st: dd 0
cg_buf: dd 0
CG_TRACE: db 'CGTRPTR', 0             ; (the harness: CG_T, the scratch, CG_ERR)
    dd CG_T_, CG_SCR_, CG_ERR_, CG_G_
"""


def native_parts(p, c8b2d3):
    """cseg_8B2D3's calls and the two words it sets after the init (ndisasm of the exe's own bytes)."""
    code = p.get(1, c8b2d3, 0x420)
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(code)
    try:
        out = subprocess.run(['ndisasm', '-b32', '-o', str(c8b2d3), f.name], capture_output=True, text=True,
                             check=True).stdout
    finally:
        os.remove(f.name)
    calls, stores = [], []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        ins = parts[2]
        if ins.startswith('int3'):
            break
        m = re.match(r'call 0x([0-9a-f]+)$', ins)
        if m:
            calls.append(int(m.group(1), 16))
        m = re.match(r'mov \[0x([0-9a-f]+)\],ax$', ins)
        if m and len(calls) == 5:                   # (after cseg_883B8: dseg_10EAB5, dseg_10EED4)
            stores.append(int(m.group(1), 16))
    # 8B71C, (D2 != 0: 87D60), 31F58, 8C607, 883B8, 8B7EA | 8BF89, 8B71C, 8B8B8 (the calendar: not run)
    assert len(calls) == 9 and calls[0] == calls[7], [hex(x) for x in calls]
    stores = stores[:2]                             # (then mov word [D3], ax: the type)
    assert len(stores) == 2, [hex(x) for x in stores]
    names = ('C8B71C', 'C31F58', 'C8C607', 'C883B8', 'C8B7EA')
    return dict(zip(names, [calls[i] for i in (0, 2, 3, 4, 5)])), stores


def table(p):
    """CG_TAB (ctgame.c's layout) and its obj1 struct pointers [(offset in the table, obj1 offset)]."""
    import conti
    import sacups
    confs = conti.ready()
    d2 = p.le.obj_bytes(2)
    euro = sacups.unique(d2, sacups.EUROCUP_HDR)
    base = p.get(1, conti.TIE[0], 14)
    tie_id = base[0]
    st = {ci: (off, lst - off, n) for ci, off, lst, n in conti.STRUCTS}
    cups = [c for conf in confs for c in conti._read(conf, 'format')['cups'] if conti.supported(c)]
    assert len(cups) == len(conti.NAMES) == len(conti.SNAMES), (len(cups), len(conti.NAMES))
    head = bytearray(base + bytes((len(cups), 0)))
    ents, extra, ptrs = bytearray(), bytearray(), []
    ex0 = 16 + 32 * len(cups)
    for ci, c in enumerate(cups):
        j0 = conti.main_round(c)
        e = bytearray(struct.pack('<II', conti.NAMES[ci], conti.SNAMES[ci]))
        if ci in st and not c.get('stepladder'):
            off, h, n = st[ci]
            e += bytes((j0, h, n, 0)) + struct.pack('<I', 0)
            ptrs.append((16 + 32 * ci + 12, off))
            cid = p.get(1, off, 1)[0]
        else:
            e += bytes((0xFF, 0, 0, 0)) + struct.pack('<I', 0)
            cid = tie_id
        gs = []
        for j, rd in enumerate(c['rounds']):
            if rd['kind'] == 'groups' and j != j0 and j < NRD:
                body, n = conti.groups_body(d2[euro:euro + 47], cid, c['rounds'], j, c['key'])
                blob = bytes(body[:39]) + struct.pack('<II', conti.NAMES[ci], conti.SNAMES[ci])
                gs.append(ex0 + len(extra))
                extra += bytes((len(blob), n)) + blob
            else:
                gs.append(0)
        e += struct.pack(f'<{NRD}H', *(gs + [0] * (NRD - len(gs)))[:NRD])
        assert len(e) == 32
        ents += e
    tab = bytes(head + ents + extra)
    assert len(tab) <= CG_TAB_MAX, hex(len(tab))
    return tab, ptrs


def rng_sites(p):
    """obj2 offsets of the game's two random generators' states, 3 bytes each (swostest.rng_sites' pattern: Rand and
    Rand2 - `mov al, [seed]; mov [D0], al; and word [D0], 0FFh; jnz; add byte [randXorIndex], 1; mov al, [...]`)."""
    c = p.le.obj_bytes(1)
    fx = {f[1]: f[4] for f in p.le.fixups() if f[0] == 1 and f[3] == 2}
    out = []
    for m in re.finditer(rb'\xa0....\xa2....\x66\x81\x25....\xff\x00\x75.\x80\x05....\x01\xa0', c, re.S):
        o = m.start()
        sd, ix = fx.get(o + 1), fx.get(o + 23)
        if sd is not None and ix == sd + 1 and fx.get(o + 29) == ix:
            out.append(sd)
    assert len(out) == 2, out
    return out


def guard_table(p):
    """CG_GTAB (ctgame.c P2): u16 nkeep, nsum, then (address, length) x nkeep (put back at a view's close) + nsum
    (summed: the saved state besides the fixed part and the cache) - [(obj, offset, length)] for the pointers."""
    import engine
    import lib97
    import statespec
    import trailer
    career = trailer.INFO['CAREER'][1]
    c = p.le.obj_bytes(1)                       # careerFileBuffer + 16ABCh: cseg_87DA0 / the type-2 init's copy of
    fx = {f[1]: f[4] for f in p.le.fixups() if f[0] == 1 and f[3] == 2}   # the contest's [2Eh] (`mov al, [esi +
    hits = {fx.get(m.start() + 4) for m in re.finditer(rb'\x8a\x46\x2e\xa2', c)}   # 2Eh]; mov [..], al`), saved
    assert career + 0x16ABC in hits, ([hex(x) for x in hits if x is not None], hex(career))
    keep = [(2, career + 0x16ABC, 1)]
    keep += [(2, o, 3) for o in rng_sites(p)]
    if 'SR' in engine.ITEM_AT and engine.ITEM_AT['SR']:
        keep.append(engine.ITEM_AT['SR'] + (statespec.SR_SIZE,))
    if 'NC_WDON' in lib97.LABELS:
        keep.append((1, lib97.LABELS['NC_WDON'], 5))   # (NC_WDON, NC_DW, NC_RD, NC_DC: the national-cup chain's)
    sizes = {n: sz for n, _, sz, _, _ in engine.save_items()}
    summed = [(1, o, n) for o, n in trailer.INFO['items']]
    late = []
    for n, sz in sorted(sizes.items()):
        at = engine.ITEM_AT.get(n)
        if at:
            summed.append(tuple(at) + (sz,))
        else:
            late.append(n)
    rows = keep + summed
    tab = bytearray(struct.pack('<HH', len(keep), len(summed)))
    ptrs = []
    for o, off, n in rows:
        ptrs.append((len(tab), o, off))
        tab += struct.pack('<II', 0, n)
    room = sum(n for _, _, n in keep)
    assert room <= 0x3000 - 0x2BA0, ('ctgame CG_KEEP room', room)
    return bytes(tab), ptrs, late, room


def patch(p, at, scr_at, lang):
    """The builder at obj3:at (the chain's end), the scratch at obj3:scr_at (zero-fill, CG_BSS). Returns the end."""
    import cobj
    import conti
    import lp36
    import nasmcave
    import trailer
    import uefaq
    cl = conti.LABELS
    assert cl.get('syms') and uefaq.SYMS, 'ctgame: conti first'
    u = uefaq.SYMS
    fn, (w1, w2) = native_parts(p, u['C8B2D3'][1])
    tab, ptrs = table(p)
    t0 = at
    p.put(3, at, tab)
    for o, off in ptrs:
        p.add_ptr(3, at + o, 1, off)
    tab_at, at = at, (at + len(tab) + 15) & ~15
    gtab, gptrs, late, room = guard_table(p)
    p.put(3, at, gtab)
    for o, t_obj, t_off in gptrs:
        p.add_ptr(3, at + o, t_obj, t_off)
    gtab_at, at = at, (at + len(gtab) + 15) & ~15
    cs = cl['syms']
    ext = {k: cs[k] for k in ('CT_SPEC', 'CT_IN', 'CT_OUT', 'CT_SEG', 'CT_GREC', 'ct_resume')}
    ext.update(CG_TAB=(3, tab_at), CG_SCR=(3, scr_at), CG_NUMSEL=trailer.INFO['NUMSEL'], CG_SLOT3=u['SLOT3'],
               CG_GTAB=(3, gtab_at), CG_CAREER=trailer.INFO['CAREER'], CG_SELBASEV=(1, trailer.INFO['selbasev']),
               CG_WORK=lp36.LABELS['symbols']['DIYCOPY'], CG_DREG=u['D0R'])
    flags = ['-fno-zero-initialized-in-bss', f'-DCG_FIXED={trailer.INFO["FIXED"][1]}']
    if os.environ.get('CONTI_CGVIEW'):
        flags.append(f'-DCGVIEW={int(os.environ["CONTI_CGVIEW"])}')
    if os.environ.get('CONTI_CGTEST'):
        flags.append('-DCGTEST')
    if os.environ.get('CG_FILL_TEST'):
        flags.append(f'-DCG_FILL=0x{int(os.environ["CG_FILL_TEST"], 16):02X}')
    obj = cobj.compile_c(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ctgame.c'), flags)
    c0 = at
    syms, at, bss = cobj.link(p, obj, at, (3, scr_at), externs=ext, text_obj=3)
    c1 = at
    assert bss == 0, ('ctgame.c: no .bss (statics in its data)', bss)
    at = (at + 15) & ~15
    ls = lp36.LABELS['symbols']
    sym = {'DIYCOPY': ls['DIYCOPY'], 'D0R': u['D0R'], 'A0R': u['A0R'], 'W10EAB5': (2, w1), 'W10EED4': (2, w2),
           'CG_SAVE_': (3, scr_at + 0x0C60), 'CG_T_': syms['CG_T'], 'CG_SCR_': (3, scr_at), 'CG_ERR_': syms['CG_ERR'],
           'CG_G_': syms['CG_G']}
    sym.update({k: (1, v) for k, v in fn.items()})
    assert ls['DIY'][1] == ls['DIYCOPY'][1] + 0x41F, (ls['DIY'], ls['DIYCOPY'])   # (one B52h work area)
    code, fix, rel = nasmcave.assemble_obj(ASM, at, sym, 3)
    lab = nasmcave.labels(ASM, at, sym)
    assert not any(p.get(3, at, len(code)))
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    end = at + len(code)
    assert end - t0 <= CG_MAX, ('ctgame over its room', hex(end - t0))
    syms['cg_native'] = (3, lab['cg_native'])
    p.add_ptr(3, syms['CG_NAT'][1], 3, lab['cg_native'])
    if os.environ.get('CONTI_CGTEST'):                  # (test builds: conti's ct_build -> cg_selftest)
        p.add_ptr(1, cl['cg_testp'], 3, syms['cg_selftest'][1])
    if os.environ.get('CONTI_CGVIEW'):
        p.add_ptr(3, syms['CG_VSIM'][1], 3, lab['cg_vsim'])
    p.add_ptr(1, cl['cg_guardp'], 3, syms['cg_daily'][1])          # (P2: a day / a save closes an open view first)
    p.add_ptr(1, trailer.INFO['cg_guardp'], 3, syms['cg_guard'][1])
    LABELS.clear()
    LABELS.update(syms, tab=(3, tab_at), scr=(3, scr_at))
    print(f'exe: option C builder (ctgame): obj3+{t0:#x}..{end:#x} ({end - t0} B: table {len(tab)}, C {c1 - c0}, '
          f'glue {len(code)}), scratch obj3+{scr_at:#x}..+{CG_BSS:#x} (zero-fill)'
          + f'; guard: {w16(gtab, 0)} kept ({room} B), {w16(gtab, 2)} summed' + (f' (late, not summed: {late})' if late else '')
          + (' CGTEST' if os.environ.get('CONTI_CGTEST') else '') + (' CG_FILL' if os.environ.get('CG_FILL_TEST') else '')
          + (f' CGVIEW={os.environ["CONTI_CGVIEW"]}' if os.environ.get('CONTI_CGVIEW') else ''))
    return end
