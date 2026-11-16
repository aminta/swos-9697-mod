"""4.2 preseason friendlies (a), the engine (Motore): tools/frstep.c (+ frnd.c, frpick.c) linked into the obj4 band
FRND (swreg FRND_AT). Dormant unless on(): no byte of it (gplay.c GP_FRND 0; frtext / frstr gate FRSS.DAT and the
FORMAT page on it). Design: internal/handoff/motore-frnd-engine.md + motore-frnd-fable-review.md."""
import os


def on():
    """FRND=1 builds only until the engine's gates pass (then every career world)"""
    return os.environ.get('FRND') == '1'
