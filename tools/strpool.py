"""Room for new strings inside obj2 (the data object).

Contest/league names are stored as offsets from a string base in obj2, so
new names must live in obj2 too: obj1 and obj2 are not loaded at the same
distance as in the file. Space comes from strings nothing references
(Italian '.COPPA AFRICANA CLUB', 'COPPA SUDAMERICANA') and from the '*'
padding of the second 'COPPA EUFA' copy (UEFA cup name 2, kept as 'COPPA EUFA').
"""
import struct

# per exe language: never-referenced strings, and (string, which occurrence) whose '*' padding is reused (text kept)
SOURCES = {
    'it': ([b'.COPPA AFRICANA CLUB******\0', b'COPPA SUDAMERICANA*****\0'],
           [(b'COPPA EUFA***************\0', 1), (b'ERRORE DISCO' + b'*' * 26 + b'\0', 0)]),
    'en': ([b'.AFRICAN CLUBS CUP******\0', b'SOUTH AMERICAN CUP*****\0'],
           [(b'EUFA CUP***************\0', 1), (b'DISK ERROR' + b'*' * 26 + b'\0', 0),
            (b'EURO CW CUP************\0', 0)]),
    'de': ([b'.AFRIKAVEREINSPOKAL******\0', b'S\x9aDAMERIKAMEISTERSCHAFT*****\0'],
           [(b'EUFA-CUP***************\0', 1)]),
    'fr': ([b"COUPE D'AFRIQUE DES CLUBS\0", b'COUPE SUD-AMERICAINE\0'], []),
}
# French strings have no '*' padding: identical second copies used only as a contest's second name are
# freed by pointing that name at the first copy (same text on screen)
DUPLICATES = {
    'fr': [b'COPA AMERICA\0', b"COUPE D'ASIE\0", b"COUPE D'OCEANIE\0", b'COUPE EUFA\0'],
}

class StrPool:
    def __init__(self, p, lang='it', str_base=None):
        self.p = p
        d2 = p.le.obj_bytes(2)
        self.free = []
        self.placed = {}
        unused, padded = SOURCES[lang]
        for s in unused:
            i = d2.find(s)
            assert i >= 0 and d2.find(s, i + 1) < 0, s
            self.free.append([i, len(s)])
        for s, nth in padded:
            i = -1
            for _ in range(nth + 1):
                i = d2.find(s, i + 1)
            keep = len(s.rstrip(b'*\0'))
            p.put(2, i + keep, b'\0')
            self.free.append([i + keep + 1, len(s) - keep - 1])
        for s in DUPLICATES.get(lang, []):
            self._free_duplicate(s, str_base)

    def _free_duplicate(self, s, str_base):
        d2 = self.p.le.obj_bytes(2)
        first = d2.find(s)
        second = d2.find(s, first + 1)
        assert first >= 0 and second > first and d2.find(s, second + 1) < 0, s
        refs = [k for k in range(len(d2) - 3) if d2[k:k + 4] == struct.pack('<I', second - str_base)]
        assert len(refs) == 1, (s, refs)                     # one contest name dword ...
        assert d2[refs[0] - 4:refs[0]] == struct.pack('<I', first - str_base), s   # ... next to the first name
        self.p.put(2, refs[0], struct.pack('<I', first - str_base))
        self.free.append([second, len(s)])

    def reuse(self, s):
        """Use a string the exe already has (whole or as the tail of a longer one)."""
        i = self.p.le.obj_bytes(2).find(s + b'\0')
        assert i >= 0, s
        self.placed[s] = i
        return i

    def add(self, s):
        """Store s (NUL added) in the first slot it fits; return its obj2 offset."""
        if s in self.placed:
            return self.placed[s]
        z = s + b'\0'
        for slot in self.free:
            if slot[1] >= len(z):
                off = self.placed[s] = slot[0]
                self.p.put(2, off, z)
                slot[0] += len(z)
                slot[1] -= len(z)
                return off
        raise ValueError(f'no room for {s}')
