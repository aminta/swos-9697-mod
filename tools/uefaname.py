"""4.1.2 (Marco, 12/11): the original 96/97 exes spell the UEFA Cup 'EUFA' - 'COPPA EUFA', 'EUFA CUP', 'COUPE EUFA',
'EUFA-CUP', two copies in obj2 in every language (CD and GOG). The 4 letters become 'UEFA' in place (same length).
strpool reuses the second copy's '*' padding (and French its whole second copy): only the bytes that still read
'EUFA' in the patched exe are rewritten, never a pool string placed over a freed copy."""

OLD, NEW = b'EUFA', b'UEFA'


def patch(p):
    d2 = p.le.obj_bytes(2)                 # (the original exe: where the strings were)
    n, i = 0, d2.find(OLD)
    while i >= 0:
        if p.get(2, i, 4) == OLD:          # (the patched bytes: still the cup's name)
            p.put(2, i, NEW)
            n += 1
        i = d2.find(OLD, i + 1)
    assert n >= 1, 'uefaname: no EUFA string left to fix'
    return n
