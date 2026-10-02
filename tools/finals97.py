"""Finals series of the NSL 1996-97 (top 6) and of the NSSL 1996-97 (top 4), with the real double chance (session 28l).

NSL (ozfootball Playoff.html, 1997 grand final page): two-leg ties 1v2 (major semi), 3v6, 4v5; Match 1 = winners of 3v6 and
4v5; Match 2 (preliminary final) = loser of 1v2 v winner of Match 1; Grand Final = winner of 1v2 v winner of Match 2.
NSSL (en.wikipedia 1996-97 National Summer Soccer League): 1v2 and 3v4 single matches; loser of 1v2 v winner of 3v4; final =
winner of 1v2 v that winner.

Engine (notes/STATUS.md 28j-28l): a division's play-off (div entry byte 5 = offset to [contest ptr][list ptr][n index
words][n x n deltas]) is built in career slot 4 for the player's division and played after the league, the clubs taken from
the standings ("promotion play-off" = places 1..n when nobody is promoted). The contest here is TYPE 2 (stages with explicit
team counts, as historic.py's cups): slot 4 accepts it after a one-byte change in cseg_8B2D3 (type 0 skipped instead of
"type != 1 skipped"). Before the draw of every round historic.hist_draw calls lib97.lib_pre, which calls fin_pre: it keeps
the 1v2 pair, then puts the right clubs in each round (list DIY+59h; scratch bytes DIY+59h+20.. are saved with the career).
"""
import struct

import nasmcave

TEAM_SIZE = 684
NSL_FIN, NSSL_FIN = 0xC4, 0xC5          # free contest ids (historic uses C1..C3)

# (id, country, league struct signature (after nsl97/nz97), clubs, standings place k of contest slot j, stage teams,
#  legs byte per stage, name)
DOUBLE_CHANCE = False       # option A (exact formats, type-2 contests + fin_pre): future goal, see notes/STATUS.md
# Option B (2.5): the native 4-club type-1 play-off (clone of country 25's contest): places 1-4 of the division, ties 1v4 and
# 2v3 (candidate order 0,3,1,2), then the final.
SIG_NSL = bytes((0x57, 0, 0x2C, 0x10, 0x50, 0x21, 0, 0, 0, 4, 2, 3, 0x35))
SIG_NSSL = bytes((0x61, 0, 0x3E, 0x10, 0x48, 0x21, 0, 0, 0, 4, 2, 4, 0x35))
DEFS = [  # (contest id, country, league struct signature, clubs, candidate order, rounds bytes, name)
    (NSL_FIN, 0x2C, SIG_NSL, 4, [0, 3, 1, 2], [0x94, 0x14], b'NSL FINALS'),
    (NSSL_FIN, 0x3E, SIG_NSSL, 4, [0, 3, 1, 2], [0x14, 0x14], b'NSSL PLAYOFFS'),
]
DRAWS = [(NSL_FIN, [0, 1, 2, 3]), (NSL_FIN, [0, 1]), (NSSL_FIN, [0, 1, 2, 3]), (NSSL_FIN, [0, 1])]   # fixed: no random draw

ASM = r'''
; fin_pre: called by lib_pre (hist_draw, before the fixed permutation): esi = DIY buffer, ecx = clubs in the round.
; list = esi+59h (team-table indices; after a round its winners in tie order). Scratch: list[20], [21] = the 1v2 pair,
; [22] = winner of 1v2, [23] = loser, [24] = round counter.
fin_pre:
    cmp byte [esi + 2Dh], NSL_ID
    je .go
    cmp byte [esi + 2Dh], NSSL_ID
    jne .r
.go:
    pushad
    lea edi, [esi + 59h]
    cmp ecx, 2
    je .later
    mov ax, [edi]                       ; round 1 (6 or 4 clubs): keep the 1v2 pair
    mov [edi + 20], ax
    mov byte [edi + 24], 1
    jmp .x
.later:
    mov al, [edi + 24]
    cmp al, 1
    jne .r3
    mov al, [edi]                       ; round 2: winners in tie order = [W 1v2, W 3v6 (W 3v4), W 4v5]
    mov [edi + 22], al
    mov ah, [edi + 20]
    cmp ah, al
    jne .l
    mov ah, [edi + 21]
.l:
    mov [edi + 23], ah                  ; loser of 1v2
    mov byte [edi + 24], 2
    cmp byte [esi + 2Dh], NSL_ID
    jne .nssl2
    mov al, [edi + 1]                   ; NSL Match 1: W 3v6 - W 4v5
    mov ah, [edi + 2]
    mov [edi], ax
    jmp .x
.nssl2:
    mov al, [edi + 23]                  ; NSSL preliminary: L 1v2 (home) - W 3v4
    mov ah, [edi + 1]
    mov [edi], ax
    jmp .x
.r3:
    cmp al, 2
    jne .r4
    mov byte [edi + 24], 3
    cmp byte [esi + 2Dh], NSL_ID
    jne .final
    mov ah, [edi]                       ; NSL preliminary final: L 1v2 (home) - W Match 1
    mov al, [edi + 23]
    mov [edi], ax
    jmp .x
.r4:
    cmp al, 3
    jne .x
    mov byte [edi + 24], 4
.final:
    mov ah, [edi]                       ; final: W 1v2 - W of the previous round
    mov al, [edi + 22]
    mov [edi], ax
.x:
    popad
.r:
    ret
'''


def code(p, at):
    """Assemble fin_pre at obj1:at; returns (end, fin_pre offset). Without the double chance it is a bare `ret`."""
    if not DOUBLE_CHANCE:
        p.put(1, at, b'\xc3')
        return at + 16, at
    symbols = {'NSL_ID': (0, NSL_FIN), 'NSSL_ID': (0, NSSL_FIN)}
    c, fix = nasmcave.assemble(ASM, at, symbols)
    labels = nasmcave.labels(ASM, at, symbols)
    assert not fix and not any(p.le.obj_bytes(1)[at:at + len(c)])
    p.put(1, at, c)
    return (at + len(c) + 15) & ~15, labels['fin_pre']


def _refs(p, lo):
    """Every single-target fixup record (original or added) pointing at obj2:lo -> [(obj, off)]."""
    out = []
    for gp, recs in enumerate(p.recs):
        for r in recs:
            if r[0] & 0x20 or r[1] & 3 or (r[0] & 0x0F) == 2:
                continue
            q = 4
            tobj = struct.unpack_from('<H', r, q)[0] if r[1] & 0x40 else r[q]
            q += 2 if r[1] & 0x40 else 1
            toff = struct.unpack_from('<I' if r[1] & 0x10 else '<H', r, q)[0]
            if tobj == 2 and toff == lo:
                obj = next(o for o in p.le.objs if o.page_idx - 1 <= gp < o.page_idx - 1 + o.npages)
                out.append((obj.idx, (gp - (obj.page_idx - 1)) * p.le.page_size + struct.unpack_from('<h', r, 2)[0]))
    return out


def structs(p, area, str_base, wc_header=None):
    """League structs with the play-off block of division 0 + the type-2 finals contests, all in the new obj2 page."""
    import re
    d1 = p.le.obj_bytes(1)
    for cid, country, sig, n, order, legs, name in DEFS:
        d2 = p.le.obj_bytes(2)
        los = [m.start() for m in re.finditer(re.escape(sig), d2)]
        if not los:                                     # NZ: nz97 built it in the new obj2 page
            import nz97
            los = [nz97.LEAGUE_AT]
        refs = [(lo, _refs(p, lo)) for lo in los]
        refs = [(lo, r) for lo, r in refs if r]
        assert len(refs) == 1, (hex(cid), [hex(x) for x in los])
        lo, old_refs = refs[0]
        nd = p.get(2, lo + 9, 1)[0]
        size = 13 + 6 * nd + 1 + 8 * nd
        league = bytearray(p.get(2, lo, size))
        assert bytes(league[:13]) == sig
        assert league[13:13 + 6][1:] == bytes(5), list(league[13:19])     # division 0: no promotion, no play-off yet
        # play-off block right after the struct: [contest][list][n words][n x n deltas]
        block_at = size
        league[13 + 1], league[13 + 2] = 0, n                # 0 promoted, n to the "promotion play-off" = places 1..n
        league[13 + 5] = block_at - (13 + 5)
        assert league[13 + 5] != 6
        block = bytes(8) + b''.join(struct.pack('<H', k) for k in order) + bytes(n * n)
        new = area.add(bytes(league) + block)
        for objn, off in old_refs:
            p.retarget(objn, off, 2, new)
        # the play-off contest: type 1 (cup), cloned from country 25's: header 14 B, rounds, 2 name dwords, n placeholder clubs
        hdr = bytes((cid, 1, country, 0x80, 0x80, 0x0b, 0, 0x11, 1, 1, n, 1, 0x35, 1)) + bytes(legs)
        rel = area.add(name + b'\0') - str_base
        hdr = bytearray(hdr)
        hdr[5] = len(hdr) - 5                           # names right after the rounds
        hdr[7] = len(hdr) + 8 - 7                       # then the clubs
        contest = area.add(bytes(hdr) + struct.pack('<II', rel, rel) + bytes(2 * n))
        # list for the player's division: n x (league ptr, division 0, standings place k)
        lst = area.add(bytes(12 * n))
        for j, k in enumerate(order):
            p.add_ptr(2, lst + 12 * j, 2, new)
            p.put(2, lst + 12 * j + 8, struct.pack('<I', k))
        p.add_ptr(2, new + block_at, 2, contest)
        p.add_ptr(2, new + block_at + 4, 2, lst)
        print(f'exe: finals {name.decode()}: league struct obj2+{new:#x} ({len(old_refs)} pointers), contest obj2+'
              f'{contest:#x}, {n} clubs, rounds {[hex(x) for x in legs]}')


def slot4_type(p):
    """cseg_8B2D3: the slot-3 and slot-4 type tests are two identical 18-byte blocks in a row (cseg_8B3DF, cseg_8B3F1):
    mov esi,[A0]; cmp byte [esi+1],1; jnz skip; jmp short build. In the second (slot 4) -> cmp byte [esi+1],0; jz skip,
    so type-2 cups pass too (type 0, a league, is still skipped)."""
    import re
    d1 = p.le.obj_bytes(1)
    blk = rb'\x8b\x35(.{4})\x80\x7e\x01\x01\x0f\x85(.{4})\xeb.'
    m = [x for x in re.finditer(blk + blk, d1, re.S)
         if x.group(1) == x.group(3) and x.start(2) + 4 + struct.unpack('<i', x.group(2))[0]
         == x.start(4) + 4 + struct.unpack('<i', x.group(4))[0]]
    assert len(m) == 1, len(m)
    site = m[0].start() + 18
    assert p.le.obj_bytes(1)[site + 9] == 1 and p.le.obj_bytes(1)[site + 11] == 0x85
    p.put(1, site + 9, b'\x00')
    p.put(1, site + 11, b'\x84')
    print(f'exe: slot 4 (division play-offs) accepts type-2 cups: obj1+{site:#x}')
