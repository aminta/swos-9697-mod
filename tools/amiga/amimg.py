"""Amiga SWOS2 image helper: unpacked image + relocs (base $100000)."""
import struct, os
ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'amiga', 'work')
BASE = 0x100000
class Img:
    def __init__(s):
        s.d = open(os.path.join(ROOT, 'SWOS2.bin'), 'rb').read()
        r = open(os.path.join(ROOT, 'SWOS2.REL.bin'), 'rb').read()
        s.rel = [e - 1 for e in struct.unpack('>%dI' % (len(r) // 4), r)]   # offsets of relocated longs
        s.relset = set(s.rel)
    def l(s, a): return struct.unpack('>I', s.d[a-BASE:a-BASE+4])[0]
    def w(s, a): return struct.unpack('>H', s.d[a-BASE:a-BASE+2])[0]
    def b(s, a): return s.d[a-BASE]
    def cstr(s, a):
        o = a - BASE; e = s.d.index(b'\0', o); return s.d[o:e].decode('latin-1')
    def isptr(s, a): return (a - BASE) in s.relset
    def refs(s, target):
        return [BASE + o for o in s.rel if struct.unpack('>I', s.d[o:o+4])[0] == target]
