"""4.0.6 (Davide): the computer's teams by the human rules - two OPTIONS rows, ON by default: ROSSI ALLA CPU (cards)
and INFORTUNI ALLA CPU (injuries carried over: step B, the row only for now).

The original game never sends off a computer team's player (a team with no player and no coach controlling it,
TeamGeneralInfo +4 / +6 both 0): TrySendingOffThePlayer (the straight red) returns 'no card' for it, so a last-man foul
(87.5% a straight red for a human team) is a plain free kick; TryBookingThePlayer (the yellow) does not book it at all
when plg_D3_param is 0 (a friendly: PlayFriendly passes D3 = 0) and otherwise books its player only while his Sprite.cards
is 0 - one yellow each, never the second ('don't book cheating scum CPU'). ON: the three CPU exits go the human way (same
odds, same budget team1/2NumAllowedInjuries, same card tables); OFF: the original.

The options: the words CC_W (cards) and CC_I (injuries), 0 = ON, 1 = OFF (each row's string table lists ON first), 0 at
every start (the game's own options are not saved either: SetDefaultOptions at start, a career file brings its own);
saved with a career as the engine item 'CC' (4 bytes; a save without it - older, or any other build's - loads them 0 =
ON); CC_SH keeps the session's values for a new career (trailer's new_career_defaults zeroes the items: engine.after_new
puts them back). The OPTIONS menu's 20 entries are all used (19 = the CONTROLS button): the rows are added to the
unpacked menu (g_currentMenu, 6500 bytes; no STDMENUTEXT in it, so its end pointer is the entries' end) as entries
20 / 21 and 22 / 23, copies of the game-length row (1 / 2) 24 and 12 px above it, in the free space under the title, by
the menu's init / on-return functions (after controls' ct_optinit / ct_optret). Not under SWOS++ (controls' rule: its
own options; both rules stay ON there).

CARDS_FORCE=red / yellow (test builds only, modver TEST_VARS): see force().
"""
import os
import re
import struct

import nasmcave

LABEL = {'it': 'ROSSI ALLA CPU', 'en': 'CPU RED CARDS', 'fr': 'ROUGES A LA CPU', 'de': 'ROTE KARTEN CPU'}
LABEL_I = {'it': 'INFORTUNI ALLA CPU', 'en': 'CPU INJURIES', 'fr': 'BLESSURES CPU', 'de': 'VERLETZUNGEN CPU'}

ASM = r"""
cc_init:                                ; OPTIONS' init: the previous one (controls), then our rows
    call PREV_INIT
    jmp cc_add
cc_ret:                                 ; (and on return to OPTIONS: the menu is unpacked again)
    call PREV_RET
cc_add:
    pushad
    cmp byte [SWOSPP], 0FFh             ; SWOS++ running: no rows
    jne .x
    mov ebx, MENU_
    cmp word [ebx + 10h], 20            ; (the game's 20 entries, nothing after them)
    jne .x
    lea eax, [ebx + 16h + 20 * 38h]
    cmp [ebx + 12h], eax
    jne .x
    mov edi, eax                        ; entries 20 / 21 and 22 / 23 = copies of the game-length row (1 / 2)
    lea esi, [ebx + 16h + 1 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    lea esi, [ebx + 16h + 1 * 38h]
    mov ecx, 2 * 38h
    rep movsb
    mov edi, eax
    mov word [edi + 2], 20              ; red cards: 24 px above the game length
    sub word [edi + 16h], 24
    mov dword [edi + 26h], S_LR
    mov word [edi + 38h + 2], 21
    sub word [edi + 38h + 16h], 24
    mov dword [edi + 38h + 26h], TAB_R
    mov dword [edi + 38h + 2Ah], cc_tog_r
    mov word [edi + 38h + 0Ah], 17FFh   ; (up: none, down: 23)
    mov word [edi + 38h + 12h], 17FFh
    mov word [edi + 70h + 2], 22        ; injuries: 12 px above it
    sub word [edi + 70h + 16h], 12
    mov dword [edi + 70h + 26h], S_LI
    mov word [edi + 0A8h + 2], 23
    sub word [edi + 0A8h + 16h], 12
    mov dword [edi + 0A8h + 26h], TAB_I
    mov dword [edi + 0A8h + 2Ah], cc_tog_i
    mov word [edi + 0A8h + 0Ah], 0215h  ; (up: 21, down: the game length's value 2 - and its up: 23)
    mov word [edi + 0A8h + 12h], 0215h
    mov byte [ebx + 16h + 2 * 38h + 0Ah], 23
    mov byte [ebx + 16h + 2 * 38h + 12h], 23
    mov word [ebx + 10h], 24
    add dword [ebx + 12h], 4 * 38h
.x: popad
    ret

cc_tog_r:                               ; a value (fire), as ChangeChairmanScenes; both words to the session copy
    mov eax, CC_W
    jmp cc_tog
cc_tog_i:
    mov eax, CC_I
cc_tog:
    xor word [eax], 1
    mov eax, [CC_W]
    mov [CC_SH], eax
    jmp DRAWITEM

cc_load:                                ; after a career load (engine.after_load): the save's values, 0 = ON when the
    mov eax, [CC_W]                     ; save has no 'CC'
    mov [CC_SH], eax
    ret
cc_new:                                 ; after a new career's defaults (engine.after_new, its items zeroed): the
    mov eax, [CC_SH]                    ; session's values back
    mov [CC_W], eax
    ret

cc_b:                                   ; TryBookingThePlayer, plg_D3_param != 0, a CPU player: replaces `jnz no card`
    jz PCT                              ; after `or ax, ax` (his Sprite.cards): none yet - the game books him too
cc_a:                                   ; plg_D3_param 0, a CPU team: the original `jmp no card`
    cmp word [CC_W], 0
    jne NOCARD
    jmp PCT
cc_c:                                   ; TrySendingOffThePlayer: replaces `jz no red` after the coach test
    jnz SENDOFF                         ; (a human team)
    cmp word [CC_W], 0
    jne NORED
    jmp SENDOFF

align 4
CC_W: dw 0                              ; (the engine item 'CC': red cards, injuries - 0 = ON)
CC_I: dw 0
CC_SH: dd 0                             ; (the session's values: a new career zeroes the item)
TAB_R: dd CC_W                          ; (the game's string tables: variable, first index, its strings)
    dw 0
    dd S_ON, S_OFF
TAB_I: dd CC_I
    dw 0
    dd S_ON, S_OFF
"""


def find(p):
    """TryBookingThePlayer / TrySendingOffThePlayer's CPU exits, the OFF / ON strings, CallDrawMenuItem."""
    d = p.le.obj_bytes(1)
    tb = [m.start() for m in re.finditer(rb'\x66\xa1....\x66\x0b\xc0\x75\x23\x8b\x35....\x66\x8b\x46\x04\x66\x0b\xc0'
                                         rb'\x75\x45\x8b\x35....\x66\x8b\x46\x06\x66\x0b\xc0\x75\x36\xe9', d, re.S)]
    ts = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x04\x66\x0b\xc0\x75\x13\x8b\x35....\x66\x8b\x46\x06'
                                         rb'\x66\x0b\xc0\x0f\x84', d, re.S)]
    assert len(tb) == 1 and len(ts) == 1, (tb, ts)
    tb, ts = tb[0], ts[0]
    rel = lambda o, n: o + n + struct.unpack_from('<i', d, o + n - 4)[0]
    s = dict(a=tb + 0x29, b=tb + 0x59, c=ts + 0x1C)
    pct, nocard = tb + 0x5F, rel(tb + 0x29, 5)
    assert d[s['b']:s['b'] + 2] == b'\x0f\x85' and rel(s['b'], 6) == nocard and s['b'] + 6 == pct, 'TryBooking'
    assert d[s['c']:s['c'] + 2] == b'\x0f\x84', 'TrySendingOff'
    s.update(PCT=pct, NOCARD=nocard, SENDOFF=s['c'] + 6, NORED=rel(s['c'], 6))
    tg = [rel(m.start() + 8, 5) for m in re.finditer(rb'\x66\x83\x35....\x01\xe9', d, re.S)]   # ChangeAutoReplays...
    assert len(set(tg)) == 1 and len(tg) >= 5, tg
    s['DRAWITEM'] = tg[0]
    return s


def strings(p, hdr):
    """The exe's OFF / ON strings: the last OFF / ON row's string table (chairmanScenesStrTable: dd variable, dw 0,
    dd OFF, dd ON) among the tables the packed OPTIONS menu (obj2:hdr) points to."""
    fx = {(so, s): (t, o) for so, s, _, t, o, *_ in p.le.fixups()}
    d2 = p.le.obj_bytes(2)
    tabs = sorted({o for (so, s), (t, o) in fx.items() if so == 2 and hdr <= s < hdr + 0x400 and t == 2
                   and (2, o) in fx and (2, o + 6) in fx and (2, o + 10) in fx and (2, o + 14) not in fx
                   and d2[o + 4:o + 6] == b'\0\0'})
    assert len(tabs) == 1, [hex(x) for x in tabs]          # (the tables follow each other: only the last one has
    return fx[(2, tabs[0] + 6)], fx[(2, tabs[0] + 10)]     # no pointer after its ON - chairman's)


def patch(p, at, lang):
    """Code + label at obj1:at; returns the end."""
    import controls
    import engine
    import zones
    from complist import px
    s = find(p)
    d = p.le.obj_bytes(1)
    for k in 'abc':
        assert p.get(1, s[k], 6) == d[s[k]:s[k] + 6], ('cpucards site already patched', k)
    sym0 = controls.locate(p)
    hdr = controls.menu_header(p, sym0['OMBD'][1])
    prev = [struct.unpack('<I', bytes(p.get(2, hdr + k, 4)))[0] for k in (0, 4)]
    assert all(p.target(2, hdr + k) == (1, v) for k, v in zip((0, 4), prev)), 'OPTIONS init / return in obj1'
    off, on = strings(p, hdr)
    label, label_i = LABEL[lang], LABEL_I[lang]
    for x in (label, label_i):
        assert px(x) <= 138 and re.fullmatch(r'[A-Z ]+', x), x
    db = lambda x: ', '.join(str(b) for b in x.encode() + b'\0')
    src = ASM + f'S_LR: db {db(label)}\nS_LI: db {db(label_i)}\n'
    sym = {'PREV_INIT': (1, prev[0]), 'PREV_RET': (1, prev[1]), 'SWOSPP': sym0['SWOSPP'], 'MENU_': zones._current_menu(p),
           'DRAWITEM': (1, s['DRAWITEM']), 'S_ON': on, 'S_OFF': off}
    sym.update({k: (1, s[k]) for k in ('PCT', 'NOCARD', 'SENDOFF', 'NORED')})
    code, fix = nasmcave.assemble(src, at, sym)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(1, at, len(code)))
    p.put(1, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(1, at + o, t_obj, t_off)
    p.put(1, s['a'], b'\xe9' + struct.pack('<i', lab['cc_a'] - (s['a'] + 5)))
    for k in 'bc':
        p.put(1, s[k], b'\xe9' + struct.pack('<i', lab['cc_' + k] - (s[k] + 5)) + b'\x90')
    for k, l in ((0, 'cc_init'), (4, 'cc_ret')):
        p.retarget(2, hdr + k, 1, lab[l])
        p.put(2, hdr + k, struct.pack('<I', lab[l]))
    engine.ITEM_AT['CC'] = (1, lab['CC_W'])
    engine.CALL_AT['cc_load'] = (1, lab['cc_load'])
    engine.CALL_AT['cc_new'] = (1, lab['cc_new'])
    LABELS.update(lab)
    print(f'exe: CPU cards / injuries by the human rules (OPTIONS: {label} / {label_i}): code obj1+{at:#x} ({len(code)} B), sites '
          f'{[hex(s[k]) for k in "abc"]}')
    return at + len(code)


LABELS = {}


def force(p):
    """CARDS_FORCE=red / yellow (test builds only): every tackle that reaches its man is a foul, every foul outside the
    penalty area takes PlayerTacklingTestFoul's last-man branch (cseg_79444: no card-chance test) and its card is always the straight red / the yellow."""
    mode = os.environ.get('CARDS_FORCE')
    if not mode:
        return
    assert mode in ('red', 'yellow'), mode
    d = p.le.obj_bytes(1)
    m = [x for x in re.finditer(rb'\x66\x39\x05....\x73.\xe8....\x66\x83\x3d....\x20\x72.\xe8....\x75.\xe8....\xff\x35'
                                rb'....\xe8....\x8f\x05....\xc3(\xe8....\x66\x83\x3d....\x20)\x72', d, re.S)]
    assert len(m) == 1, len(m)
    lm = m[0].start(1)                                   # cseg_79444
    jz = [i for i in range(lm - 0x80, lm) if d[i] == 0x74 and i + 2 + struct.unpack_from('<b', d, i + 1)[0] == lm]
    assert len(jz) == 1, jz
    jb = m[0].end()                                      # `jb yellow`
    p.put(1, jz[0], b'\xeb')
    p.put(1, jb - 1, b'\xeb' if mode == 'yellow' else b'\x90')
    if mode == 'red':
        p.put(1, jb, b'\x90')
    t = [x for x in re.finditer(rb'\x81\x7e\x4a\x20\x03\x00\x00\x0f\x87....\x8b\x35....\x66\x8b\x46\x60\x66\x0b\xc0\x74(.)',
                                d, re.S)]                # (the tackled player's ball distance > 800: out; the tackle
    assert len(t) == 1, len(t)                           #  state 0: a foul, else the good-tackle / direction tests)
    ja = t[0].start() + 7
    foul = t[0].end() + struct.unpack('<b', t[0].group(1))[0]
    p.put(1, ja, b'\xe9' + struct.pack('<i', foul - (ja + 5)) + b'\x90')   # every tackle that touches: a foul
    print(f'exe: CARDS_FORCE={mode} (test build: every tackle a foul, every foul outside the box a last-man foul, its '
          f'card the {mode}) obj1+{ja:#x} / +{jz[0]:#x} / +{jb - 1:#x}')
