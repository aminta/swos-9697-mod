"""Bound dwords: the ONE way a module's code is reached without a literal address (tcache 16/11; 4.2 x3all, MC 16/11:
gplay's glue -> gplay.c in obj3 and gplay.c's GP_SCDONE -> gplay3.c use the same generator).

A caller holds a dword (a slot: obj:off, a plain 0 or a placeholder fixup) and calls / reads through it; the owner
places its entries once its code is laid out. Table.ref() registers a slot for an entry - bound at once when the entry is
placed, else at place(). Table.check() before save: every registered slot holds a fixup to its entry, the dword's bytes
equal the fixup's offset, and the target lies inside the room its entry was placed with (a call through an unbound slot
would crash).

    T = bound.Table('tcache', ENTRIES)      T.ref(p, obj, off, 'tc_room')      T.place(p, {name: (obj, off)}, (obj, lo, hi))
    T.check(p) -> the number of slots"""
import struct


class Table:
    def __init__(self, name, entries=None):
        self.name = name
        self.entries = entries                  # the names callers may bind (None: any placed / to be placed)
        self.refs = []                          # [(obj, off, entry)]: the callers' dwords
        self.placed = {}                        # entry -> (obj, off)
        self.rooms = {}                         # entry -> (obj, lo, hi), the range it must lie in

    def reset(self):
        self.refs.clear()
        self.placed.clear()
        self.rooms.clear()

    def ref(self, p, obj, off, name):
        """the dword at obj:off gets bound to entry `name` - now if it is placed, else at place()"""
        assert self.entries is None or name in self.entries, (self.name, name)
        self.refs.append((obj, off, name))
        if name in self.placed:
            self.bind(p, obj, off, name)

    def bind(self, p, obj, off, name):
        t = self.placed[name]
        try:
            p.target(obj, off)                  # (a placeholder fixup: retarget it)
        except AssertionError:
            p.add_ptr(obj, off, t[0], t[1])     # (a plain 0 dword)
            return
        p.retarget(obj, off, t[0], t[1])
        p.put(obj, off, struct.pack('<I', t[1]))

    def place(self, p, entries, room, clear=False):
        """entries {name: (obj, off)} are laid out inside room (obj, lo, hi): every slot waiting for one is bound.
        clear: the table's earlier entries are dropped first (an owner placing all of its entries at once)."""
        if clear:
            self.placed.clear()
            self.rooms.clear()
        for name, t in entries.items():
            assert self.entries is None or name in self.entries, (self.name, name)
            t = tuple(t[:2])
            assert t[0] == room[0] and room[1] <= t[1] < room[2], (f'{self.name}: entry outside its room', name, t, room)
            self.placed[name], self.rooms[name] = t, tuple(room)
        for obj, off, name in self.refs:
            if name in entries:
                self.bind(p, obj, off, name)

    def check(self, p):
        """every slot bound to its entry, inside the entry's room; -> the number of slots"""
        for obj, off, name in self.refs:
            assert name in self.placed, (f'{self.name}: slot of an entry never placed', obj, hex(off), name)
            t = p.target(obj, off)
            assert struct.unpack('<I', p.get(obj, off, 4))[0] == (t[1] if t else -1), (f'{self.name}: dword != fixup', obj, hex(off))
            o, lo, hi = self.rooms[name]
            assert t is not None and tuple(t) == self.placed[name] and t[0] == o and lo <= t[1] < hi, \
                (f'{self.name}: unbound', obj, hex(off), name, t)
        return len(self.refs)
