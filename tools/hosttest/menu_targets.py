"""menu_targets.py EXE... - MC gate 21/11 (the MiSTer reset): every A6 menu store that leads to SHOW_MENU in the
DRIBBLING toggle (df_rtog: setpieces.py's copy, `lea eax, [ebp + DP_MENU - SPB]; mov ecx, [ebp]; mov [ecx + A6_O],
eax`, and difficulty.py's copy, `mov dword [A6_], DP_MENU`) must resolve to a real DP_MENU header (dd 0, 0, 0,
DP_V0), and the CUSTOM step's `call DP_FALL` must land in the 42-drp band's code (DRIB1V1). A build whose toggle
cannot reach the page (DIFF_TRACE after 25c0e2d: `.p: pop ebp; jmp df_draw`) has no store: PASS (no page path).
Red twin: a DIFF_TRACE exe before 25c0e2d (c/TESTMISTER1911/press2) -> FAIL (DP_MENU = DF_W, zeros).
Exit 1 on any FAIL. Scope: the DRIBBLING page path only (the other SHOW_MENU modules: next gate step)."""
import os, re, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import lepatch, swreg
import difficulty as dfm

V0 = len(dfm.DP_ROWS) + 1
TOG = rb'\x66\x40\x66\x83\xf8\x02\x76\x02\x31\xc0'      # (df_rtog: inc ax; cmp ax, 2; jbe .s; xor eax, eax)


def check(path):
    """Every page-open site (`lea eax, [ebp + DP_MENU - base]` within 12 B after a call into DRIB1V1's code: the
    setpieces / gameplay toggles, any module) must point at a real DP_MENU header (dd 0, 0, 0, DP_V0) for one
    0x100-aligned band base - unless it is dead code: setpieces' toggle whose CUSTOM step `.p` is `pop ebp; jmp`."""
    p = lepatch.LEPatch(open(path, 'rb').read())
    o4 = p.le.obj_bytes(4)
    dead = set()
    for h in [x.start() for x in re.finditer(TOG, o4)]:      # (the toggle's `je .p`: .p = pop ebp; jmp -> no page)
        j = re.search(rb'\x74(.)', o4[h + 10:h + 30], re.S)
        if j:
            t = h + 10 + j.end() + struct.unpack('b', j.group(1))[0]
            if o4[t] == 0x5D and o4[t + 1] in (0xE9, 0xEB):
                dead.update(range(t, t + 0x60))
    out, bad = [], False
    for m in re.finditer(rb'\x8d\x85(....)', o4, re.S):
        a = m.start()
        calls = [a - 12 + k for k in range(12) if o4[a - 12 + k] == 0xE8 and k <= 7]
        tg = [c + 5 + struct.unpack_from('<i', o4, c + 1)[0] for c in calls]
        if not any(swreg.DRIB1V1_AT <= t < swreg.DRIB1V1_END for t in tg):
            continue
        d = struct.unpack('<i', m.group(1))[0]
        hdr = [B for B in range(0, len(o4), 0x100) if 0 <= B + d <= len(o4) - 16
               and struct.unpack_from('<4I', o4, B + d) == (0, 0, 0, V0)]
        if a in dead:
            out.append(f'{a:#x}: page open after `.p: pop ebp; jmp` - unreachable')
        elif len(hdr) == 1:
            out.append(f'{a:#x}: DP_MENU obj4+{hdr[0] + d:#x} (base {hdr[0]:#x})')
        else:
            bad = True
            out.append(f'{a:#x}: lea disp {d:#x} reaches no DP_MENU header ({len(hdr)} candidate bases)')
    if not out:
        return 'FAIL', 'no page-open site found (unknown shape)'
    return ('FAIL' if bad else 'PASS'), '; '.join(out)


if __name__ == '__main__':
    bad = 0
    for e in sys.argv[1:]:
        v, m = check(e)
        bad += v != 'PASS'
        print(f'{v:5} {e}: {m}')
    sys.exit(1 if bad else 0)
