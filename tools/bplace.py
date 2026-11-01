"""4.0.5 (Davide): a level tie decided by the better league placing says so on its result line. The mod's play-offs
(gplay gp_draw / dplay dp_draw at cseg_2AE97's 'draw -> replay' mark) decide a level single match (after extra time or
without it) or a level aggregate with result flags 2 (decided) and 1 (the second club) and no 8 (penalties) / 10h (away
goals) - a combination the original game never stores (its level ties end on penalties, away goals or a replay; historic's
coin toss sets 8). The result line (cseg_289AC: the green line under the score on the result screen, D0 = 0, and the
round's results list, D0 != 0 - each text a wide / narrow pair, the formatter skips to the narrow one) showed only
'D.T.S.' / 'A.E.T.', nothing without extra time, or '%a WIN 2-2 ON AGG.' for a level aggregate.

bp_two replaces the two-leg branch's `test word [D7], 2` (D2 / D3 = the aggregate, A2 = the winner), bp_one the single
match's `test word [D7], 4` (D4 = the score): on that combination with a level score the line is ours - 'PASSA %a
(MIGL. PIAZZ.)' (IT, after extra time 'D.T.S. - PASSA ...' on the wide line), EN / FR / DE their own - through the game's
formatter (cseg_28D56); else the original test, its flags returned. Widths in the small font with a 16-character name:
wide <= 229 px (the game's own longest wide line: 257), narrow <= 198 px (its narrow: 209).
"""
import os
import re
import struct

import nasmcave
import sacups

TEXTS = {   # (wide, narrow) without extra time, (wide, narrow) after extra time
    'it': (('PASSA %a (MIGL. PIAZZ.)', 'PASSA %a (MIGL. PIAZZ.)'),
           ('D.T.S. - PASSA %a (MIGL. PIAZZ.)', 'PASSA %a (MIGL. PIAZZ.)')),
    'en': (('%a THROUGH (BETTER PLACED)', '%a THROUGH (PLACING)'),) * 2,
    'fr': (('%a QUALIFIE (MIEUX CLASSE)', '%a PASSE (CLASSEMENT)'),) * 2,
    'de': (('%a WEITER (BESSER PLATZIERT)', '%a WEITER (TABELLE)'),) * 2,
}

ASM = r"""
bp_two:                                 ; cseg_289AC's two legs: replaces `test word [D7], 2` (D2 / D3 the aggregate)
    push eax
    test word [D7_], 2
    jz .n
    test word [D7_], 18h                ; (penalties / away goals: the game's texts)
    jnz .n
    mov ax, [D2_]
    cmp ax, [D3_]
    je bp_ours
.n: pop eax
    test word [D7_], 2
    ret

bp_one:                                 ; its single match: replaces `test word [D7], 4` (D4 the score, home in its
    push eax                            ; high byte; D0 / D1 there are the penalties)
    test word [D7_], 2
    jz .n
    test word [D7_], 18h
    jnz .n
    mov ax, [D4_]
    cmp al, ah
    je bp_ours
.n: pop eax
    test word [D7_], 4
    ret

bp_ours:                                ; a level tie the better placed (A2) won: our pair, the game's formatter
    pop eax
    mov dword [A0_], BP_TXT
    test word [D7_], 4
    jz .f
    mov dword [A0_], BP_TXT_ET
.f: add esp, 4
    jmp FMT
"""


def find(p):
    """The two sites in cseg_289AC and its formatter (cseg_28D56), in the original exe."""
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    D7 = r['D7']
    t = lambda b: rb'\x66\xf7\x05' + re.escape(struct.pack('<I', D7)) + bytes([b]) + rb'\x00'
    two = [m for m in re.finditer(t(2) + rb'\x0f\x84....' + t(4) + rb'\x75.' + t(8) + rb'\x75.' + t(0x10) +
                                  rb'\x75.\xc7\x05' + re.escape(struct.pack('<I', r['A0'])) + rb'....(\xe9....)', d, re.S)]
    one = [m for m in re.finditer(t(4) + rb'\x75.' + t(8) + rb'\x0f\x85....' + t(0x40) + rb'\x0f\x84....\xc7\x05' +
                                  re.escape(struct.pack('<I', r['A0'])), d, re.S)]
    assert len(two) == 1 and len(one) == 1, (len(two), len(one))
    j = two[0].start(1)
    fmt = j + 5 + struct.unpack_from('<i', d, j + 1)[0]
    return dict(two=two[0].start(), one=one[0].start(), fmt=fmt, D7=D7, D0=D7 - 28, A0=r['A0'])


def patch(p, at, lang):
    """Code + texts at obj1:at; returns the end."""
    s = find(p)
    d = p.le.obj_bytes(1)
    for k in ('two', 'one'):
        assert bytes(p.get(1, s[k], 9)) == d[s[k]:s[k] + 9], ('bplace site already patched', k)
    D0 = s['D0']
    (w0, n0), (w1, n1) = TEXTS[lang]
    pair = lambda w, n: ', '.join(str(b) for b in w.encode() + b'\0' + n.encode() + b'\0')
    src = ASM + f'BP_TXT: db {pair(w0, n0)}\nBP_TXT_ET: db {pair(w1, n1)}\n'
    sym = {'D7_': (2, s['D7']), 'D2_': (2, D0 + 8), 'D3_': (2, D0 + 12), 'D4_': (2, D0 + 16),
           'A0_': (2, s['A0']), 'FMT': (1, s['fmt'])}
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for k, lbl in (('two', 'bp_two'), ('one', 'bp_one')):
        o = s[k]
        p.remove(1, o + 3)                               # (the test's D7 fixup)
        p.put(1, o, b'\xe8' + struct.pack('<i', lab[lbl] - (o + 5)) + b'\x90' * 4)
    LABELS.update(lab)
    print(f'exe: better placed on the result line: code obj1+{at:#x} ({len(code)} B), sites obj1+{s["two"]:#x} / '
          f'+{s["one"]:#x}')
    return at + len(code)


LABELS = {}

FORCE_ASM = r"""
bf_one:                                 ; (BPLACE_FORCE) cseg_2AE97's single match (both variants: cseg_2B28C's with extra
    mov ax, [D1_]                       ; time, the decisive one): replaces `mov ax, [D1]` after the 90 minutes' result
    cmp ax, [D2_]                       ; (cseg_2B7D8), before `cmp [D2], ax`: level (the lower side up)
    jae .a
    mov ax, [D2_]
    mov [D1_], ax
    jmp .x
.a: mov [D2_], ax
.x: mov ax, [D1_]
    ret

bf_two:                                 ; its second leg: replaces `mov ax, [D3]` before `cmp [D4], ax` (the aggregate):
    push ecx                            ; level (the lower side's second-leg goals up)
    mov ax, [D3_]
    mov cx, [D4_]
    cmp ax, cx
    je .p
    ja .h
    sub cx, ax
    add [D1_], cx
    add [D3_], cx
    jmp .p
.h: sub ax, cx
    add [D2_], ax
    add [D4_], ax
.p: pop ecx
    mov ax, [D3_]
    ret

bf_et:                                  ; its extra time (`call cseg_2B81B`): no goals
    call ETX
    mov word [D3_], 0
    mov word [D4_], 0
    ret
"""


def force(p, at):
    """BPLACE_FORCE (test builds only): every decisive match cseg_2AE97 settles - a single match (cseg_2B28C's with
    extra time, or the other) or a second leg - level after 90 minutes / on aggregate, no goals in extra time: the mod's
    play-offs go to the better placed (gp_draw / dp_draw), the game's cups to penalties. Code at obj1:at; returns the end
    (at itself without the switch)."""
    if not os.environ.get('BPLACE_FORCE'):
        return at
    d = p.le.obj_bytes(1)
    r = sacups.regs(d)
    D0 = r['D7'] - 28
    P = lambda a: re.escape(struct.pack('<I', a))
    Dn = lambda k: P(D0 + 4 * k)
    et = [m for m in re.finditer(rb'\x80\x0d' + P(r['D7']) + rb'\x04(?:\xff\x35....){9}\xe8(....)', d, re.S)]
    etx = {m.end() + struct.unpack('<i', m.group(1))[0] for m in et}
    assert len(et) == 2 and len(etx) == 1, (len(et), etx)
    two = [m.start() for m in re.finditer(rb'\x66\xa1' + Dn(3) + rb'\x66\x39\x05' + Dn(4) + rb'\x0f\x85', d, re.S)]
    assert len(two) == 1, two
    res = None                                           # (cseg_2B7D8: the call right before the two-leg branch's sum)
    one = []
    for m in re.finditer(rb'\x66\xa1' + Dn(1) + rb'\x66\x39\x05' + Dn(2) + rb'\x0f[\x84\x85]', d, re.S):
        calls = [c for c in re.finditer(rb'\xe8(....)', d[m.start() - 0x30:m.start()], re.S)]
        if calls and abs(m.start() - two[0]) < 0x800:
            c = calls[-1]
            tgt = m.start() - 0x30 + c.end() + struct.unpack('<i', c.group(1))[0]
            if res is None or tgt == res:
                res = tgt
                one.append(m.start())
    assert len(one) == 2, [hex(x) for x in one]
    sym = {'D1_': (2, D0 + 4), 'D2_': (2, D0 + 8), 'D3_': (2, D0 + 12), 'D4_': (2, D0 + 16), 'ETX': (1, etx.pop())}
    code, fix = nasmcave.assemble(FORCE_ASM, at, sym)
    lab = nasmcave.labels(FORCE_ASM, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    for o, lbl in [(x, 'bf_one') for x in one] + [(two[0], 'bf_two')]:
        assert bytes(p.get(1, o, 6)) == d[o:o + 6], ('BPLACE_FORCE site already patched', lbl, hex(o))
        p.remove(1, o + 2)
        p.put(1, o, b'\xe8' + struct.pack('<i', lab[lbl] - (o + 5)) + b'\x90')
    for m in et:
        o = m.end() - 5
        assert bytes(p.get(1, o, 5)) == d[o:o + 5], 'BPLACE_FORCE extra-time call already patched'
        p.put(1, o, b'\xe8' + struct.pack('<i', lab['bf_et'] - (o + 5)))
    print(f'exe: BPLACE_FORCE (test build: decisive matches level, no extra-time goals) obj1+{at:#x}, '
          f'sites {[hex(x) for x in one + two]}')
    return at + len(code)
