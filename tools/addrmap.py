"""Build an address map ENGLISH.EXE -> ITALIAN.EXE for both objects.

swos.asm (swos-port) labels are ENGLISH.EXE virtual addresses. The Italian
build differs mostly by string lengths, so objects are shifted piecewise.
We mask every fixup target field (addresses differ between builds), then
anchor unique 24-byte windows and record piecewise-constant deltas.

Output: notes/addrmap.json = {"1": [[eng_start, delta], ...], "2": [...]}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from le import LE

WIN = 24
STRIDE = 16


def masked(le, objn):
    b = bytearray(le.obj_bytes(objn))
    o = le.obj(objn)
    for sobj, soff, typ, tobj, toff, *_ in le.fixups():
        if sobj != objn:
            continue
        n = 2 if typ == 2 else 4 if typ in (7, 8) else 6 if typ == 6 else 2
        for i in range(max(0, soff), min(len(b), soff + n)):
            b[i] = 0xAA
    return bytes(b)


def build(eng, ita, objn):
    e, i = masked(eng, objn), masked(ita, objn)
    # index Italian windows
    idx = {}
    for p in range(0, len(i) - WIN):
        w = i[p:p + WIN]
        idx[w] = -1 if w in idx else p
    anchors = []
    for p in range(0, len(e) - WIN, STRIDE):
        w = e[p:p + WIN]
        if w.count(0) > WIN // 2 or w.count(0xAA) > WIN // 2:
            continue
        q = idx.get(w, -1)
        if q >= 0:
            anchors.append((p, q - p))
    # compress into runs, dropping isolated outliers
    runs = []
    for k, (p, dlt) in enumerate(anchors):
        prev = anchors[k - 1][1] if k else None
        nxt = anchors[k + 1][1] if k + 1 < len(anchors) else None
        if dlt != prev and dlt != nxt:
            continue
        if not runs or runs[-1][1] != dlt:
            runs.append([p, dlt])
    return runs, len(anchors)


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(__file__), '..')
    eng = LE(os.path.join(root, 'orig/ENGLISH.EXE'))
    ita = LE(os.path.join(root, 'orig/ITALIAN.EXE'))
    out = {}
    for objn in (1, 2):
        runs, n = build(eng, ita, objn)
        out[str(objn)] = runs
        print(f'obj{objn}: {n} anchors, {len(runs)} runs')
    json.dump(out, open(os.path.join(root, 'notes/addrmap.json'), 'w'))
