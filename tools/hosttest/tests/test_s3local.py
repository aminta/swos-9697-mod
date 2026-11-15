"""4.2 S3 x S7 (TRENTO, 15/11): the Serie B / Serie C play-off skip bits are LOCAL to each league struct's spec (GP_S3T row,
gplay.s3_local). A shaped S7 pack has one spec per struct, so the global ko_playoffs index (bit 26..28) skipped nothing there and
c_po's winner was promoted by gplay AND dplay. Checks on the shaped world (internal/world2526/world5tm-h3s7): the bits are the
play-offs' positions in struct 102's spec (b_po + b_pout in mask B, c_po in mask C), none in another struct, and below the
spec's play-off count. SKIP without the private world."""
import os
import sys

HOME = os.path.expanduser('~')
W = os.path.join(HOME, 'swos-mod', 'internal', 'world2526', 'world5tm-h3s7')
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def test_s3local():
    if not os.path.exists(W + '.txt'):
        return True, f'SKIP: {W}.txt missing'
    sys.path.insert(0, TOOLS)
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = ','.join(os.path.join(W, ln.split()[0].lower()) for ln in open(W + '.txt') if ' file ' in ln)
    try:
        import gplay
        import mkseason
        loc = gplay.s3_local()
        rows = {k: v for k, v in loc.items() if v != (0, 0)}
        assert list(rows) == [(5, 102)], rows
        mb, mc = rows[(5, 102)]
        for pk in mkseason.packs():
            if 'c_po' not in [po.get('key') for po in (pk.league or {}).get('ko_playoffs') or []]:
                continue
            keys = [po.get('key') for po in pk.po_resolved() if (pk.world, pk.po_local(po)[0]) == (5, 102)]
            assert mb == sum(1 << keys.index(k) for k in ('b_po', 'b_pout')), (mb, keys)
            assert mc == 1 << keys.index('c_po'), (mc, keys)
            assert mc < 1 << len(keys) and mb < 1 << len(keys)
            return True, f'struct 102: B bits {mb:#x}, C bit {mc:#x} of {len(keys)} play-offs (global bits 26..28 would skip nothing)'
        return False, 'no world-5 pack with ko_playoffs'
    finally:
        if old is None:
            os.environ.pop('SEASON_PACKS', None)
        else:
            os.environ['SEASON_PACKS'] = old
