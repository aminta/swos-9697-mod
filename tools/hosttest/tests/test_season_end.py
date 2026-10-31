"""Season end (gplay.py gp_end, after each division of a league; the whole processing at its last division: the
play-offs' results, gp_season, the champion, the moves into SLTCOPY, sec_post): fixtures se_<country> = snapshots at
careerworld.w_season_end / gplay.gp_end of a career's first season end (ht_snapshot). Every run of gp_end: each club
moves at most one level and the moves balance (as many up as down); at least one fixture really moves clubs."""
import glob
import json
import os

from emu import Machine

FIX = os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 'hosttest', 'fixtures')
BUILD = os.path.join(os.path.expanduser('~'), 'swos-mod', 'c', os.environ.get('HT_FIX', 'HT20'), 'SWOS')


def test_gp_end_moves():
    out, bad, moved = [], [], 0
    for d in sorted(glob.glob(os.path.join(FIX, 'se_*'))):
        for js in sorted(glob.glob(os.path.join(d, '*.json'))):
            meta = json.load(open(js))
            if meta['label'] != 'gplay.gp_end':
                continue
            k = int(os.path.basename(js)[:-5])
            m = Machine(d, k)
            m.dos_files(BUILD)
            b = m.read('careerworld.sites.sltcopy', 4096)
            m.call('gplay.gp_end', max_insn=300_000_000)
            a = m.read('careerworld.sites.sltcopy', 4096)
            dl = [((a[i] - b[i] + 128) % 256) - 128 for i in range(4096) if a[i] != b[i]]
            moved += bool(dl)
            if any(abs(x) > 1 for x in dl) or sum(dl):
                bad.append((os.path.basename(d), k, dl))
            out.append(f'{os.path.basename(d)}/{k}: {dl or "-"}')
    if not out:
        return False, 'no se_* fixtures'
    return not bad and moved > 0, f'unbalanced / long moves {bad}; ' if bad else '' + '; '.join(out)
