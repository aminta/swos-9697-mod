"""SELECT KITS in a training game (4.0.6, Marco on 4.0.5).

TRAINING (the career squad screen) plays the club against itself: team A is careerTeam, team B currentTeam, a copy of
careerTeam's 75-byte header (cseg_64161), so both carry the club's name. kitcolors' SELECT KITS tells its two slots
apart by name (find_slot): at the kick-off both teams found slot 0 and wore team A's choice (both in the first kit when
A was set to it), and SEMPRE could write team B's kits into careerTeam.
- kt_find replaces find_slot (its head: a jmp here; the same contract, esi -> TeamFile, edi -> its slot or 0): the slot
  with the name AND the team pointer (fill_slot's +32) first, then the name alone as before. Training's two buffers
  map to slots 0 / 1; a friendly that reuses the buffers for two other clubs still differs by name (3.2.4's rule).
- (careers, the career cave's jump table) KM_MODE -> kt_mode: entry 23 (SOLO PARTITA / SEMPRE) hidden in a training
  game; KM_KEEP -> kt_keep: nothing kept in a training game (its kits are for that game only).
Code in obj3 after benchx (CONVENTIONS 23).
"""
import struct

import benchx
import kitcolors
import nasmcave

ASM = r"""
kt_find:                                ; find_slot: esi -> TeamFile; out: edi -> its slot, or 0
    push ecx
    mov edi, SLOTS                      ; the name and the team pointer
    cmp [edi + 32], esi
    jne .p2
    call .cmp
    je .ok
.p2:
    mov edi, SLOTS + SLOT_
    cmp [edi + 32], esi
    jne .n1
    call .cmp
    je .ok
.n1:                                    ; the name alone (kitcolors' own rule)
    mov edi, SLOTS
    call .cmp
    je .ok
    mov edi, SLOTS + SLOT_
    call .cmp
    je .ok
    xor edi, edi
.ok:
    pop ecx
    ret
.cmp:
    push esi
    push edi
    add esi, 5
    mov ecx, 17
    repe cmpsb
    pop edi
    pop esi
    ret

%ifdef XAT
kt_mode:                                ; KM_MODE (km_init: entry 23's state; [A0] -> entry 23 after it)
    call KM_MODE_
    cmp word [TRAIN], 0
    je .r
    mov esi, [A0]
    mov word [esi + 4], 1               ; (invisible)
.r: ret

kt_keep:                                ; KM_KEEP (km_ok: SEMPRE's write into careerTeam)
    cmp word [TRAIN], 0
    jne .r
    jmp KM_KEEP_
.r: ret
%endif
"""


def patch(p, at):
    """kt_* at obj3:at (after benchx); returns the end. Nothing when the exe has no SELECT KITS."""
    info = kitcolors.INFO
    if 'find_slot' not in info:
        return at
    fs, xat = info['find_slot'], info['xat']
    sym = {'SLOTS': info['slots'], 'SLOT_': (0, kitcolors.SLOT), 'TRAIN': benchx.INFO['TRAIN'], 'A0': (2, info['A0'])}
    src = ASM
    if xat is not None:
        assert p.get(1, xat + 5, 1) == p.get(1, xat + 10, 1) == b'\xe9'
        sym.update(KM_KEEP_=p.call_target(1, xat + 5), KM_MODE_=p.call_target(1, xat + 10))
        src = '%define XAT\n' + ASM
    code, fix, rel = nasmcave.assemble_obj(src, at, sym, 3)
    lab = nasmcave.labels(src, at, sym)
    assert not any(p.get(3, at, len(code))), hex(at)
    p.put(3, at, code)
    for o, t_obj, t_off in fix:
        p.add_ptr(3, at + o, t_obj, t_off)
    for o, t_obj, t_off in rel:
        p.add_rel(3, at + o, t_obj, t_off)
    head = bytes(p.get(1, fs, 6))                       # find_slot: push ecx / mov edi, SLOTS (its fixup at +2)
    assert head[:2] == b'\x51\xbf' and p.target(1, fs + 2) == info['slots'], head.hex()
    p.remove(1, fs + 2)
    p.branch(1, fs, 0xE9, 3, lab['kt_find'])
    if xat is not None:
        p.branch(1, xat + 5, 0xE9, 3, lab['kt_keep'])
        p.branch(1, xat + 10, 0xE9, 3, lab['kt_mode'])
    print(f'exe: kittrain: SELECT KITS in training games, obj3+{at:#x} ({len(code)} B), find_slot obj1+{fs:#x}'
          + (f', KM_KEEP / KM_MODE obj1+{xat + 5:#x}' if xat is not None else ''))
    return at + len(code)
