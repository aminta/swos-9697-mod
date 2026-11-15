"""practice_car's gate (MC 14/11 gate 4, narrowed MC 15/11): the bytes a set-piece practice changes in the career save
(.CAR) must be bytes a plain training game changes too. Two halves of one career: the control (the plain training game)
and the practice, each saved before (PRA0) and after (PRA1). A practice-only byte is allowed only inside a NAMED field
whose bytes the control changed too - the same field with a value one byte longer:
- a player record's name (record + 3 .. + 25, 23 bytes, NUL-padded): 'ROBERT DRAMEH' / 'SIMONE PULISIC' in one slot;
- a line-up order array (11..16 distinct entries < 32, the same set in both halves, in another order).
Anything else - a byte next to a stat the control changed included - is a failure."""

NAME_CHARS = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .'-_") | set(range(0xC0, 0x100))
NAME_LEN = 23                   # PlayerFile name: record + 3 .. + 25
ORDER_MIN, ORDER_MAX = 11, 16


def diff(d0, d1):
    """{offset: (before, after)} of two saves."""
    return {i: (d0[i], d1[i]) for i in range(min(len(d0), len(d1))) if d0[i] != d1[i]}


def name_field(i, a, b):
    """(start, end) of the player-name field holding offset i in both saves a, b (the halves' PRA1), or None: a name
    starts at the same offset in both (a non-name byte before it), runs at most 23 bytes, and i lies in it or is its
    NUL padding."""
    for d in (a, b):
        if d[i] not in NAME_CHARS and d[i] != 0:
            return None
    j = i
    while j > 0 and (b[j - 1] in NAME_CHARS):
        j -= 1
    if j == i and b[i] == 0:            # (i is padding: its name ends before it)
        while j > 0 and b[j - 1] == 0 and i - j < NAME_LEN:
            j -= 1
        while j > 0 and b[j - 1] in NAME_CHARS:
            j -= 1
    if i - j >= NAME_LEN or b[j] not in NAME_CHARS or a[j] not in NAME_CHARS:
        return None
    if j > 0 and (a[j - 1] in NAME_CHARS or b[j - 1] in NAME_CHARS):
        return None
    end = j + NAME_LEN
    for d in (a, b):                    # a name: printable then NUL padding to the field's end
        k = j
        while k < end and d[k] in NAME_CHARS:
            k += 1
        if k - j < 3 or any(d[x] for x in range(k, end)):
            return None
    return j, end


def order_field(i, a, b):
    """(start, end) of a line-up order array holding i in both saves, or None (11..16 distinct entries < 32, the same
    set in both, not the same order)."""
    for n in range(ORDER_MAX, ORDER_MIN - 1, -1):
        for s in range(max(0, i - n + 1), i + 1):
            wa, wb = a[s:s + n], b[s:s + n]
            if len(wa) == n and max(wa) < 32 and len(set(wa)) == n and sorted(wa) == sorted(wb) and wa != wb:
                return s, s + n
    return None


def classify(ctrl, pr, ctrl1, pr1):
    """ctrl / pr: diff() of the control / practice halves; ctrl1 / pr1: their PRA1 bytes. -> (fail, info): fail =
    [offset] not in a named field the control changed too; info = [(offset, 'field name (start..end)')]."""
    fail, info = [], []
    for i in sorted(set(pr) - set(ctrl)):
        for kind, f in (('player name', name_field), ('line-up order', order_field)):
            r = f(i, ctrl1, pr1)
            if r and any(j in ctrl for j in range(*r)):
                info.append((i, f'{kind} {r[0]:#x}..{r[1] - 1:#x}'
                                + (f' (record {r[0] - 3:#x})' if kind == 'player name' else '')))
                break
        else:
            fail.append(i)
    return fail, info
