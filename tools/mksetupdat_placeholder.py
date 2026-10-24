"""Writes tools/setup_calibrated.dat: a PLACEHOLDER calibrated SETUP.DAT (GOG factory + 'joypad and keyboard' + a plausible
one-pad calibration), until the real one made with the original SETUP.EXE (CrossOver, a real pad) replaces it - swap = overwrite
tools/setup_calibrated.dat and rerun tools/mkpatcher.py (nothing else). Layout (ref/swos.asm setupDatBuffer, 105 bytes, words
little endian): +6 g_inputControls (1 keyboard only, 2 joypad, 3 joypad + keyboard, 4 keyboard + joypad, 5 two joypads),
+30/+32 joy1 centre X/Y, +38..+44 joy1 min Y / min X / max X / max Y, +46..+52 joy1 X-left / X-right / Y-top / Y-bottom divisors,
+92 / +94 g_numLoopsJoy1 / 2 (the read loop's count; 0 = 65536 reads per frame), +101 / +102 joy1 fire 1 / 2 (FFh / FEh)."""
import os, struct
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = bytearray(open(os.path.join(ROOT, 'orig', 'setup-factory', 'GOG.DAT'), 'rb').read())
assert len(d) == 105 and d[6] == 1
w = lambda at, v: d.__setitem__(slice(at, at + 2), struct.pack('<H', v))
w(6, 3)
w(30, 600); w(32, 600)                      # centre X / Y
w(38, 60); w(40, 60); w(42, 1200); w(44, 1200)   # min Y, min X, max X, max Y
w(46, 4); w(48, 5); w(50, 4); w(52, 5)      # divisors ((centre - min) / 127, (max - centre) / 127)
w(92, 2400); w(94, 0)                       # numLoopsJoy1 (0 for joy 2: one pad)
d[101], d[102] = 0xFF, 0xFE
open(os.path.join(ROOT, 'tools', 'setup_calibrated.dat'), 'wb').write(d)
print(len(d), 'bytes written')
