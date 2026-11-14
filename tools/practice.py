"""4.2 set-piece PRACTICE modes (Davide GO 14/11; Difficoltà's design, internal/handoff/42-sp-s3-freekicks.md; MC 14/11).

Step 1, the page: the career squad screen's TRAINING (squadMenu entry 6, its on-select dword an obj2 fixup) opens a
page of our own in obj4 (swreg.PRACTICE_AT..PRACTICE_END, MC's band): TRAINING / FREE KICK PRACTICE / PENALTY PRACTICE /
CORNER PRACTICE / ATTACK-DEFENCE (a switch) / BACK, 4 languages. pr_open shows it (A6 = PR_MENU, ShowMenu - the
fmtpage / DP page pattern; bteam's run-time squadMenu copy copies the retargeted entry); a row sets PR_GO and leaves
the page (g_exitMenu); back in pr_open:
- TRAINING -> entry 6's previous target, read from its fixup at patch time (SelectTraining or a known hook: MC 14/11
  rule 1, asserted), the training game as before; FREE KICK / PENALTY / CORNER -> PR_KIND 1 / 2 / 3 around the same
  call (step 2's engine reads it; 0 outside a practice);
- the switch flips PR_DEF (0 ATTACK: the human takes, 1 DEFENCE: the CPU takes) and shows the page again on its row;
- BACK -> nothing: ShowMenu's caller, the squad screen, with its cursor still on TRAINING.
Work state (PR_GO, PR_KIND, PR_DEF) in swe.c's .bss (PR_WORK: MC 14/11, not in the band)."""
import struct

import nasmcave

LABELS = {}
WORK_SZ = 16                            # (swe.c PR_WORK: GO +0, KIND +1, DEF +2; step 2: counters, the cycle index)
ROWS = {      # TRAINING, FREE KICK, PENALTY, CORNER, ATTACK, DEFENCE, BACK (the title = the squad screen's button)
    'it': ('ALLENAMENTO', 'PROVA PUNIZIONI', 'PROVA RIGORI', "PROVA CALCI D'ANGOLO", 'ATTACCO', 'DIFESA', 'INDIETRO'),
    'en': ('TRAINING MATCH', 'FREE KICK PRACTICE', 'PENALTY PRACTICE', 'CORNER PRACTICE', 'ATTACK', 'DEFENCE', 'BACK'),
    'fr': ('MATCH D ENTRAINEMENT', 'COUPS FRANCS', 'PENALTYS', 'CORNERS', 'ATTAQUE', 'DEFENSE', 'RETOUR'),
    'de': ('TRAININGSSPIEL', 'FREISTOESSE', 'ELFMETER', 'ECKBAELLE', 'ANGRIFF', 'ABWEHR', 'ZURUECK'),
}
TITLE = {'it': 'PRATICA', 'en': 'TRAINING', 'fr': 'ENTRAINEMENT', 'de': 'TRAINING'}
X, W, H, Y0, DY = 52, 200, 15, 40, 22   # the rows (menu coordinates), title at y 12
R_TRAIN, R_MODE, R_BACK = 1, 5, 6       # entry numbers (0 the title)

ASM = r"""
pr_open:                                ; squadMenu entry 6 (TRAINING), on select: the practice page
    mov dword [PR_MENU + 12], R_TRAIN_  ; (the default entry: the first row)
.show:
    pushad
    mov esi, S_ATT                      ; the switch's text
    cmp byte [DEF], 0
    je .t
    mov esi, S_DEF
.t: mov edi, MTXT
.c: lodsb
    stosb
    test al, al
    jnz .c
    popad
    mov byte [GO], 0
    mov dword [A6], PR_MENU
    call SHOW_MENU
    movzx eax, byte [GO]
    cmp al, 80h                         ; the switch: the page again, on its row
    jne .go
    mov dword [PR_MENU + 12], R_MODE_
    jmp .show
.go:
    test eax, eax                       ; BACK (or the menu left otherwise): the squad screen
    jz .x
    dec eax
    mov [KIND], al                      ; 0 training, 1 free kicks, 2 penalties, 3 corners
    call OLD_SEL                        ; entry 6's previous target (SelectTraining: the game, the squad screen)
    mov byte [KIND], 0
.x: ret

pr_go:                                  ; a row: al = PR_GO; leave the page
    mov [GO], al
    mov word [EXITM], 1
    ret
pr_r1: mov al, 1
    jmp pr_go
pr_r2: mov al, 2
    jmp pr_go
pr_r3: mov al, 3
    jmp pr_go
pr_r4: mov al, 4
    jmp pr_go
pr_mode:
    xor byte [DEF], 1
    mov al, 80h
    jmp pr_go
pr_back:
    xor eax, eax
    jmp pr_go
"""


def texts(lang):
    return (TITLE[lang],) + ROWS[lang]


def check_texts():
    """Width + font in all 4 languages (MC 14/11: no stray characters)."""
    from complist import px, font_odd
    bad = []
    for lang in ROWS:
        for t in texts(lang):
            if px(t) > W - 12 or font_odd(t):
                bad.append((lang, t, px(t), font_odd(t)))
    assert not bad, ('practice: texts', bad)


def old_target(p, sel_fix):
    """Entry 6's current on-select target (MC rule 1: SelectTraining or a known hook, else the build stops)."""
    t = [(to, oo) for so, s, _, to, oo, *_ in p.le.fixups() if so == 2 and s == sel_fix]
    assert len(t) == 1, ('practice: squadMenu entry 6 on-select fixup', t)
    tobj, toff = t[0]
    assert tobj == 1, ('practice: entry 6 targets obj', tobj)
    d1 = p.le.obj_bytes(1)
    head = d1[toff:toff + 5]
    ptg = toff + 5 + struct.unpack('<i', head[1:5])[0] if head[:1] == b'\xe8' else None
    # SelectTraining: call PlayTrainingGame (mov word [g_trainingGame], 1 at its head)
    ok = ptg is not None and d1[ptg:ptg + 3] == b'\x66\xc7\x05' and d1[ptg + 7:ptg + 9] == b'\x01\x00'
    assert ok, ('practice: entry 6 no longer targets SelectTraining (a new hook: add it to old_target)', hex(toff),
                head.hex())
    return tobj, toff


SITES = {}


def sites(p):
    """Before bteam (its ui_sites finds squadMenu by the two `mov dword [A6], squadMenu` bteam replaces): the page's
    game sites and squadMenu entry 6's on-select dword + its current target (SITES)."""
    import bteam
    import xbrowse
    u = bteam.ui_sites(p)
    pay = dict(xbrowse.PAYLOAD)
    pay[7] = 4
    d2 = p.le.obj_bytes(2)
    saved, xbrowse.PAYLOAD = xbrowse.PAYLOAD, pay
    try:
        _, ents = xbrowse.menu_parse(d2, u['menu'])
    finally:
        xbrowse.PAYLOAD = saved
    k, sel = ents[6][0] + 8, None           # the entry's typed fields: its type 13 dword
    while True:
        t = struct.unpack_from('<H', d2, k)[0]
        k += 2
        if t == 0:
            break
        if t == 13:
            sel = k
        k += pay[t]
    assert sel is not None, 'practice: squadMenu entry 6 has no on-select'
    SITES.clear()
    SITES.update(u, sel=sel, old=old_target(p, sel))


def patch(p, lang):
    """The page + code at obj4 swreg.PRACTICE_AT; squadMenu entry 6's on-select -> pr_open (sites() first; swe.c's
    PR_WORK from swe.LABELS: after swe.patch)."""
    import swe
    import swreg
    check_texts()
    u, sel = SITES, SITES['sel']
    old = old_target(p, sel)                # (MC rule 1: still the target read at sites(), nothing hooked it since)
    assert old == SITES['old'], ('practice: entry 6 retargeted between sites() and patch()', old, SITES['old'])
    work = swe.LABELS['PR_WORK']
    assert work[0] == 4, work
    at = swreg.PRACTICE_AT
    q = lambda s: ', '.join(str(c) for c in s.encode('latin-1')) + ', 0'
    tx = texts(lang)
    data = 'align 4\nPR_MENU:\n    dd 0, 0, 0, R_TRAIN_\n'
    data += f'    dw 0, 12, 304, 14\n    dw 4, 17h, 8, 0\n    dd S_T\n    dw 0\n'
    sels = ('pr_r1', 'pr_r2', 'pr_r3', 'pr_r4', 'pr_mode', 'pr_back')
    for i in range(6):
        up = i if i else 0xFF                               # (entry numbers: row i = entry i + 1)
        dn = i + 2 if i < 5 else 0xFF
        txt = 'MTXT' if i == 4 else f'S_{i}'
        col = '0Ch' if i == 5 else '0Eh'
        data += (f'    dw {X}, {Y0 + DY * i}, {W}, {H}, 2\n    db 255, 255, {up}, {dn}\n'
                 f'    dw 4, {col}, 8, 0\n    dd {txt}\n    dw 13\n    dd {sels[i]}\n    dw 0\n')
    data += '    dw -999\n'
    data += f'S_T: db {q(tx[0])}\n' + ''.join(f'S_{i}: db {q(tx[1 + i])}\n' for i in range(4))
    data += f'S_ATT: db {q(tx[5])}\nS_DEF: db {q(tx[6])}\nS_5: db {q(tx[7])}\n'
    data += 'MTXT: times 24 db 0\n'
    assert max(len(tx[5]), len(tx[6])) < 24
    src = f'%define R_TRAIN_ {R_TRAIN}\n%define R_MODE_ {R_MODE}\n' + ASM + data
    sym = {'A6': u['a6'], 'SHOW_MENU': (1, u['show']), 'EXITM': u['exitm'], 'OLD_SEL': old,
           'GO': (4, work[1]), 'KIND': (4, work[1] + 1), 'DEF': (4, work[1] + 2)}
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 4)
    lab = nasmcave.labels(src, at, sym)
    assert p.le.obj(4).npages * 0x1000 >= swreg.PRACTICE_END, 'practice: obj4 pages (patch.py)'
    left = swreg.PRACTICE_END - at - len(code)
    assert left >= 256, ('practice: past its obj4 band (MC: >= 256 B left; ask MC before more)', left)
    assert not any(p.get(4, at, swreg.PRACTICE_END - at)), 'practice: obj4 band not free'
    p.put(4, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(4, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(4, at + o, t_obj, t_off)
    p.remove(2, sel)                                    # squadMenu entry 6's on-select: SelectTraining -> pr_open
    p.add_ptr(2, sel, 4, lab['pr_open'])
    LABELS.clear()
    LABELS.update(lab)
    LABELS['PR_WORK'] = work
    LABELS['ENT6_SEL'] = (2, sel)
    print(f'exe: practice page (squadMenu entry 6 obj2+{sel:#x} -> obj4 pr_open; its old target obj1+{old[1]:#x}): '
          f'obj4+{at:#x} ({len(code)} B, {left} B left), work PR_WORK obj4+{work[1]:#x}')
