"""Session's default no-sacking word (MC 17/11, rule 0): nosack_pin sets the chairman's word (nosack_off, dseg_D6B62)
at a pause when it is not 1, leaves it when it is, finds the offset once per exe (NOSACK_CACHE), and an exe without
the pattern turns it off for that session with one log line - never a FAIL. The red twins: a word already 1 is not
poked; a session with no result pokes nothing. Uses the original exe (orig/ITALIAN.EXE of this checkout or of the
main one)."""
import os
import sys
import tempfile

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, TOOLS)


def _exe():
    for root in (os.path.join(TOOLS, '..'), os.path.expanduser('~/swos-mod')):
        p = os.path.join(root, 'orig', 'ITALIAN.EXE')
        if os.path.exists(p):
            return p
    return None


class _Res:
    def __init__(self, word):
        self.base2 = 0x10000
        self.mem = {}
        self.word = word

    def read(self, lin, n):
        return self.word if n == 2 else bytes(n)


class _S:
    def __init__(self, exe, word):
        self.nosack_exe, self.nosack_at, self.log, self.pokes = exe, None, [], []
        self.result = _Res(word) if word is not None else None

    def poke(self, lin, data):
        self.pokes.append((lin, bytes(data)))


def test_nosack_pin():
    import swostest
    exe = _exe()
    if not exe:
        return True, 'SKIP: no orig/ITALIAN.EXE'
    off = swostest.nosack_off(exe)
    s = _S(exe, b'\x00\x00')
    swostest.nosack_pin(s)
    if s.pokes != [(0x10000 + off, b'\x01\x00')]:
        return False, f'word 0: pokes {s.pokes}, want one at base2 + {off:#x}'
    calls = []
    real = swostest.nosack_off
    swostest.nosack_off = lambda e: calls.append(e) or real(e)
    try:
        s2 = _S(exe, b'\x01\x00')
        swostest.nosack_pin(s2)
        if s2.pokes:
            return False, f'red twin: word already 1 poked {s2.pokes}'
        if calls:
            return False, 'the offset searched again for the same exe (NOSACK_CACHE)'
        s3 = _S(exe, None)
        swostest.nosack_pin(s3)
        if s3.pokes:
            return False, 'red twin: no result, poked'
    finally:
        swostest.nosack_off = real
    with tempfile.NamedTemporaryFile(suffix='.EXE') as f:
        f.write(b'MZ' + bytes(64))
        f.flush()
        s4 = _S(f.name, b'\x00\x00')
        swostest.nosack_pin(s4)
        swostest.nosack_pin(s4)
        if s4.pokes or s4.nosack_at is not False or len([x for x in s4.log if x.startswith('nosack:')]) != 1:
            return False, f'an exe without the pattern: pokes {s4.pokes}, at {s4.nosack_at}, log {s4.log}'
    return True, f'word 0 poked at base2 + {off:#x}, word 1 left, cached, no result nothing, no pattern: off + 1 log'


def test_session_default():
    """Session's default is on, SWOSTEST_NOSACK=0 and nosack=False turn it off (the source line, Session not started)"""
    import inspect
    import swostest
    src = inspect.getsource(swostest.Session.__init__)
    if "os.environ.get('SWOSTEST_NOSACK', '1') != '0') if nosack is None else bool(nosack)" not in src:
        return False, 'Session.__init__: the default / opt-out line changed'
    if 'nosack_pin(self)' not in inspect.getsource(swostest.Session.send):
        return False, 'Session.send: nosack_pin not called at a pause'
    return True, 'default on; SWOSTEST_NOSACK=0 / nosack=False off; send pins at every pause'
