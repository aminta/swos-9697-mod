"""The real S7 Italy pack the host tests read (one constant, MC 15/11): HT_S7PACK, else internal/s7pack-real/ita
(from the 42-tactics merge on: the h3p rebuild with real tactics; the h2 one kept as s7pack-real/ita.h2-20261113)."""
import os

S7PACK = os.environ.get('HT_S7PACK') or os.path.join(os.path.expanduser('~'), 'swos-mod', 'internal', 's7pack-real', 'ita')
