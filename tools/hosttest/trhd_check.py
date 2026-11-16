"""trhd_check.py: POSITION TRAITS (1) + (3) (the TRHD band, tools/trhead.py) against a Python model, on the host
(Unicorn on the relocated exe, no DOSBox; the prereg rule table D3 of internal/handoff/trhead-design.md).

  internal/hosttest/.venv/bin/python tools/hosttest/trhd_check.py BUILD_DIR

BUILD_DIR: ITALIAN.EXE + ITALIAN.syms.json of a TRHD_RUOLI=0 or 1 build (HOSTTEST_SYMS=1). The switch byte (TR_RU, the
stand-in of GP_RUOLI) is poked: every case runs with RUOLI NO and SI.
- tr_rec's arithmetic = the game's inGameTeamPlayerOffsets table (61 x i, 16 slots: asserted in the exe's data);
- tr_zone: every x / y of the zone edges +-1 (and far points), both teams' structures = the model's bits;
- tr_live: RUOLI x SWOS++ (SP_OK) x training (TRG) x practice (PR_D none / KIND 0 / KIND 1);
- tr_hdown (setpieces' sp_on stand-in): ZF, ebp = SPB, FK_ST, every other register, for RUOLI x CALCI PIAZZATI 0 / 1 /
  2 x SP_OK x file position 0..7 + 0xFF x the header's place x both teams;
- the header end to end through setpieces' own stubs (sp_jz, sp_fz, sp_head): the value the game stores as the ball's
  deltaZ, then the HEADING placement, and the whipped-cross bonus (TR_WF / TR_WT / TR_WK planted: (2) is not in yet);
- a substitution (t_sub): the game's own SubstitutePlayer record swap and GetPlayerPointerFromShirtNumber, then tr_rec /
  tr_dist: the on-pitch substitute's file position is the one read;
- tr_dist: esi = A1 and the compare's CF / ZF (the game's `ja`) for the limit 64 + TR_RST x HEADING of a TR_DM
  position in his own box, 64 for everyone else; ballDistance around every limit.
"""
import itertools
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EFLAGS

import diff_structural as ds
import setpieces as sp
import swreg
import trhead as tr
from lepatch import LEPatch

B2, B4 = ds.B2, ds.B4
TM_TOP, SPR, REC, PRK = None, ds.SCR + 0x30000, ds.SCR + 0x32000, 0x40
XS = sorted({0, 80, 81, 182, 183, 184, 192, 193, 194, 335, 336, 337, 477, 478, 479, 487, 488, 489, 590, 591, 700})


def zone(x, y, top, wz):
    """The model: the zone bits of (x, y) for the team of the top (True) / bottom structure."""
    d = y - tr.GOAL_TOP if top else tr.GOAL_BOT - y
    b = 8 if x < tr.MID_X else 0
    if d > 640:
        return b
    if tr.BOX_X0 <= x <= tr.BOX_X1:
        if 0 <= d <= tr.BOX_D:
            b |= 1
        elif d >= 640 - tr.BOX_D:
            b |= 2
    elif (x <= tr.WIDE_X0 or x >= tr.WIDE_X1) and d >= 640 - wz:
        b |= 4
    return b


def ys(wz):
    e = set()
    for v in (0, tr.BOX_D, 640 - tr.BOX_D, 640 - wz, 640, 320):
        for top in (True, False):
            for k in (-1, 0, 1):
                e.add(tr.GOAL_TOP + v + k if top else tr.GOAL_BOT - v - k)
    return sorted(y for y in e if 0 <= y < 1000)


class T:
    def __init__(self, build):
        self.img = ds.images(os.path.join(build, 'ITALIAN.EXE'))
        sj = json.load(open(os.path.join(build, 'ITALIAN.syms.json')))
        assert 'trhead' in sj, 'not a TRHD build (TRHD_RUOLI=0 / 1, HOSTTEST_SYMS=1)'
        self.L = {k: v[1] for k, v in sj['trhead'].items()}
        self.S = {k: v[1] for k, v in sj['setpieces'].items()}
        self.trg = sj['difficulty']['SYMS.TRG'][1]
        p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
        _, self.c = sp.find(p)
        _, c2 = tr.find(p)
        self.top = B2 + c2['TOP_O']
        self.bot = self.top + 0x91
        self.k, self.spk = tr.knobs(), sp.knobs()
        b = self.img[4]
        hm, dm = struct.unpack_from('<II', b, self.L['TR_HM'])
        assert (hm, dm) == (self.k['HMASK'], self.k['DMASK']), ('the build\'s masks are not this environment\'s', hm, dm)
        assert [self.L[n + 'j'] for n in tr.JT] == [swreg.TRHD_AT + 5 * i for i in range(len(tr.JT))], 'jump table'
        self.R = B4 + swreg.TRHD_END - 16
        tab = struct.pack('<16H', *(61 * i for i in range(16)))      # (tr_rec's x 61 = the game's own table,
        assert bytes(self.img[2]).count(tab) == 1, 'inGameTeamPlayerOffsets: 16 words 61 x i, once in obj2'   # every slot)
        self.allowed = tuple((B4 + lo, B4 + hi) for lo, hi in ((swreg.TRHD_AT, swreg.TRHD_END),
                                                               (swreg.SETPIECE_AT, swreg.SETPIECE_END)))
        self.n = self.bad = 0
        self.first = []

    def mach(self, seed, ru=1, ok=1, trg=0, pr=None, spw=0):
        m = ds.Mach(self.img, seed)
        m.w8(B4 + self.L['TR_RU'], ru)
        m.w8(B4 + self.S['SP_OK'], ok)
        m.w16(B4 + self.S['SP_W'], spw)
        m.w16(B2 + self.trg, trg)
        if pr is None:
            m.w32(B4 + self.S['PR_D'], 0)
        else:                                           # (a practice's KIND byte in the TRHD band's free tail)
            a = B4 + swreg.TRHD_END - PRK
            m.w32(B4 + self.S['PR_D'], a - (B4 + self.S['SPB']))
            m.w8(a, pr)
        return m

    def place(self, m, top, x, y, pos=7, hd=5, ordn=9):
        """A1 = a sprite at (x, y), A6 = the top / bottom structure, his record's position / HEADING."""
        team = self.top if top else self.bot
        m.w32(B2 + self.c['A1_O'], SPR)
        m.w32(B2 + self.c['A6T_O'], team)
        m.w16(SPR + 2, ordn)
        m.w16(SPR + 0x20, x)
        m.w16(SPR + 0x24, y)
        m.w32(team + 0x0A, REC)
        rec = REC + (ordn - 1) * 61
        m.w8(rec + tr.POS, pos)
        m.w8(rec + self.c['HDO'], hd)
        return team, rec

    def call(self, m, entry, regs=None):
        vals = {n: 0x11110000 * (i + 1) + 0x321 for i, (n, _) in enumerate(ds.GPR)}
        vals.update(regs or {})
        for n, rg in ds.GPR:
            m.uc.reg_write(rg, vals[n] & 0xFFFFFFFF)
        m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
        m.uc.reg_write(UC_X86_REG_EFLAGS, 0x202)
        m.w32(ds.STACK, self.R)
        log, err = ds.run(m, B4 + entry, self.R, self.allowed)
        st = ds.state(m)
        return st, vals, (err or (log and 'calls out') or (st['esp'] != ds.STACK + 4 and 'esp'))

    def chk(self, ok, *what):
        self.n += 1
        if not ok:
            self.bad += 1
            if len(self.first) < 12:
                self.first.append(' '.join(str(w) for w in what))

    def live(self, ru, ok, trg, pr):
        return bool(ru and ok and (not trg or pr))

    # ------------------------------------------------------------------------------------------------- the units
    def t_zone(self):
        m = self.mach('zone')
        spb = B4 + self.S['SPB']
        for top, x, y in itertools.product((True, False), XS, ys(self.k['WZ'])):
            self.place(m, top, x, y)
            st, v, err = self.call(m, self.L['tr_zone'], dict(esi=SPR, edi=self.top if top else self.bot, ebp=spb))
            want = zone(x, y, top, self.k['WZ'])
            self.chk(not err and st['eax'] == want and all(st[r] == v[r] for r in ('ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp')),
                     'tr_zone', top, x, y, hex(st['eax']), hex(want), err)

    def t_live(self):
        spb = B4 + self.S['SPB']
        for ru, ok, trg, pr in itertools.product((0, 1), (0, 1), (0, 1), (None, 0, 1)):
            m = self.mach('live', ru, ok, trg, pr)
            st, v, err = self.call(m, self.L['tr_live'], dict(ebp=spb))
            on = not st['flags'] & 0x40
            self.chk(not err and on == self.live(ru, ok, trg, pr) and all(st[r] == v[r] for r, _ in ds.GPR),
                     'tr_live', ru, ok, trg, pr, on, err)

    def spots(self, top, few=False):
        """(x, y, the model's bits) for places of each kind, for the team of that structure (few: 8 of them)."""
        if few:
            pts = [(336, 40), (193, 87), (478, 88), (336, 320), (336, 553), (478, 600), (192, 600), (150, 630)]
        else:
            pts = [(x, d) for x in (150, 193, 336, 478, 520) for d in (0, 40, 87, 88, 320, 552, 553, 600, 640)]
        return [(x, y, zone(x, y, top, self.k['WZ'])) for x, y in
                ((x, tr.GOAL_TOP + d if top else tr.GOAL_BOT - d) for x, d in pts)]

    def t_hdown(self):
        spb = B4 + self.S['SPB']
        for ru, spw, ok, trg in itertools.product((0, 1), (0, 1, 2), (0, 1), (0, 1)):
            m = self.mach('hd', ru, ok, trg, None, spw)
            for top, pos in itertools.product((True, False), list(range(8)) + [0xFF]):
                for x, y, z in self.spots(top):
                    self.place(m, top, x, y, pos)
                    m.w8(B4 + self.S['FK_ST'], 1)
                    st, v, err = self.call(m, self.L['tr_hdown'])
                    down = not st['flags'] & 0x40
                    fk = m.read(B4 + self.S['FK_ST'], 1)[0]
                    if self.live(ru, ok, trg, None):
                        wd = pos <= 7 and bool(self.k['HMASK'] >> pos & 1) and bool(z & 2)
                        wfk = 1 if wd or not spw else 0
                    else:
                        wd, wfk = bool(ok and not trg and spw), 1
                    self.chk(not err and down == wd and fk == wfk and st['ebp'] == spb
                             and all(st[r] == v[r] for r in ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi')),
                             'tr_hdown', ru, spw, ok, trg, top, pos, x, y, down, wd, fk, wfk, err)

    def t_header(self):
        """sp_jz / sp_fz (eax = the deltaZ the game stores) and sp_head (the placement + the whip bonus)."""
        c, k, sk = self.c, self.k, self.spk
        ball = B2 + c['BALL_O']
        kjz, kfz = (struct.unpack_from('<I', self.img[2], c[n])[0] for n in ('KJZ_O', 'KFZ_O'))
        assert (kjz, kfz) == (0xA000, 0x20000), (hex(kjz), hex(kfz))
        jzn = sk['JZ'] & 0xFFFFFFFF
        cases = itertools.product((0, 1), (0, 1, 2), (True, False), (3, 7), (0, 5), (0, 1, 2, 3))
        for ru, spw, top, pos, hd, whip in cases:
            m = self.mach('hdr', ru, 1, 0, None, spw)
            for x, y, z in self.spots(top, True):
                team, rec = self.place(m, top, x, y, pos, hd)
                wd = (bool(self.k['HMASK'] >> pos & 1) and bool(z & 2)) if ru else bool(spw)
                for stub, orig, new in (('sp_jz', kjz, jzn), ('sp_fz', kfz, sk['FZ'])):
                    st, v, err = self.call(m, self.S[stub])
                    self.chk(not err and st['eax'] == (new if wd else orig)
                             and all(st[r] == v[r] for r in ('ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp')),
                             stub, ru, spw, top, pos, x, y, hex(st['eax']), wd, err)
                # sp_head: the ball as the game left it after sp_jz (a straight jump header) or sp_fz (a flying one)
                for kind in ('jump', 'fly'):
                    dz0 = ((jzn if wd else kjz) if kind == 'jump' else (sk['FZ'] if wd else kfz))
                    m.w32(B2 + c['A2_O'], ball)
                    m.w32(B2 + c['A4_O'], rec)
                    m.w32(ball + c['DZO'], dz0)
                    m.w16(ball + 0x2C, 2000)
                    m.w16(B2 + c['CGT_O'], 5000)
                    # the whip: 0 none, 1 this team's 60 ticks ago, 2 the other team's, 3 this team's 101 ticks ago
                    m.w8(B4 + self.L['TR_WF'], 1 if whip else 0)
                    m.w32(B4 + self.L['TR_WT'], team if whip != 2 else team ^ 0x40)
                    m.w16(B4 + self.L['TR_WK'], 5000 - (101 if whip == 3 else 60))
                    st, v, err = self.call(m, self.S['sp_head'])
                    dz = struct.unpack('<I', m.read(ball + c['DZO'], 4))[0]
                    spd = struct.unpack('<H', m.read(ball + 0x2C, 2))[0]
                    wf = m.read(B4 + self.L['TR_WF'], 1)[0]
                    placed = wd and kind == 'jump'
                    wdz = (dz0 - hd * sk['JST']) & 0xFFFFFFFF if placed else dz0
                    wsp, wwf = 2000, (1 if whip else 0)
                    if placed and whip:
                        wwf = 0
                        if whip == 1:
                            wdz, wsp = (wdz - k['WHB']) & 0xFFFFFFFF, 2000 + k['WHS']
                    self.chk(not err and (dz, spd, wf) == (wdz, wsp, wwf) and st['esi'] == rec
                             and st['eax'] & 0xFF == hd and st['eax'] >> 8 == v['eax'] >> 8
                             and all(st[r] == v[r] for r in ('ebx', 'ecx', 'edx', 'edi', 'ebp')),
                             'sp_head', kind, ru, spw, top, pos, hd, whip, x, y, hex(dz), hex(wdz), spd, wsp, wf, wwf, err)

    def t_sub(self):
        """A substitution, by the game's own code: SubstitutePlayer's record swap (from `mov A0, offset
        inGameTeamPlayerOffsets` to the end of its 61-byte loop; D6 = the bench slot, D7 = the pitch slot) on a team of
        16 records, then (a) the game's GetPlayerPointerFromShirtNumber and tr_rec name the same record for every
        ordinal, (b) the pitch sprite's record is the substitute's (his own file position; the man who left: -1 on the
        bench), (c) tr_dist reads the substitute: a D for an A gets the reach, an A for a D loses it."""
        import difficulty as df
        from lepatch import LEPatch
        p = LEPatch(os.path.join(HERE, '..', '..', 'orig', 'ITALIAN.EXE'))
        d = p.le.obj_bytes(1)
        _, sym = df.find(p)
        d0 = sym['D0_'][1]
        a0, a4 = (2, d0 + 32), (2, d0 + 48)
        tab = bytes(self.img[2]).find(struct.pack('<16H', *(61 * i for i in range(16))))
        anc = [m.start() for m in re.finditer(rb'\xc6\x44\x1e\x2e\xff\x66\xc7\x05....\x3c\x00', d, re.S)]
        assert len(anc) == 1, ('SubstitutePlayer: position = -1 / mov D1, 60', anc)
        st = [m.start() for m in re.finditer(rb'\xc7\x05........', d[anc[0] - 0x80:anc[0]], re.S)
              if df._t(p, anc[0] - 0x80 + m.start() + 2) == a0 and df._t(p, anc[0] - 0x80 + m.start() + 6) == (2, tab)]
        assert len(st) == 1, ('SubstitutePlayer: mov A0, offset inGameTeamPlayerOffsets', st)
        start = anc[0] - 0x80 + st[0]
        en = [m.end() for m in re.finditer(rb'\x66\xff\x0d....\x79.', d[anc[0]:anc[0] + 0xA0], re.S)]
        assert len(en) == 1, ('SubstitutePlayer: dec D1 / jns', en)
        end = anc[0] + en[0]
        bt = [m.start() for m in re.finditer(rb'\xa1....\xa3....', d[anc[0] - 0x30:anc[0]], re.S)
              if df._t(p, anc[0] - 0x30 + m.start() + 6) == a0]
        assert len(bt) == 1, ('SubstitutePlayer: mov eax, benchTeamGame / mov A0, eax', bt)
        bench = df._t(p, anc[0] - 0x30 + bt[0] + 1)
        gp = [m.start() for m in re.finditer(rb'\x8b\x35....\x66\x8b\x46\x02\x66\xa3....\x66\x83\x2d....\x01\xc7\x05........', d, re.S)
              if df._t(p, m.start() + 30) == (2, tab) and df._t(p, m.start() + 26) == a4]
        assert len(gp) == 1, ('GetPlayerPointerFromShirtNumber', gp)
        B1 = ds.B1
        c, k = self.c, self.k
        for top, pitch, bslot, (pos_out, pos_in) in itertools.product((True, False), (1, 4, 10), (11, 15),
                                                                     ((7, 3), (3, 7), (3, 3), (6, 4))):
            m = self.mach('sub', 1, 1)
            team = self.top if top else self.bot
            x, y = 336, (tr.GOAL_TOP + 40 if top else tr.GOAL_BOT - 40)        # (in his own box)
            m.w32(team + 0x0A, REC)
            for i in range(16):                         # 16 records: slot i = position i % 8, HEADING 7, a name byte
                m.w8(REC + 61 * i + tr.POS, i % 8)
                m.w8(REC + 61 * i + c['HDO'], 7)
                m.w8(REC + 61 * i + 0x38, 0x41 + i)
            m.w8(REC + 61 * pitch + tr.POS, pos_out)
            m.w8(REC + 61 * bslot + tr.POS, pos_in)
            m.w16(B2 + d0 + 24, bslot)                  # D6: the man coming on (his index), D7: the pitch slot
            m.w16(B2 + d0 + 28, pitch)
            m.w32(B2 + bench[1], REC)
            m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
            log, err = ds.run(m, B1 + start, B1 + end, ((B1 + start, B1 + end),))
            got = (m.read(REC + 61 * pitch + tr.POS, 1)[0], m.read(REC + 61 * bslot + tr.POS, 1)[0],
                   m.read(REC + 61 * pitch + 0x38, 1)[0])
            self.chk(not err and not log and got == (pos_in, 0xFF, 0x41 + bslot), 'SubstitutePlayer swap', pitch, bslot, got, err)
            for ordn in range(1, 17):                   # (a) the game's pointer = tr_rec's
                m.w32(B2 + c['A1_O'], SPR)
                m.w32(B2 + c['A6T_O'], team)
                m.w16(SPR + 2, ordn)
                m.uc.reg_write(UC_X86_REG_ESP, ds.STACK)
                m.w32(ds.STACK, self.R)
                log, err = ds.run(m, B1 + gp[0], self.R, ((B1 + gp[0], B1 + gp[0] + 0x80),))
                g4 = struct.unpack('<I', m.read(B2 + a4[1], 4))[0]
                st_, v, e2 = self.call(m, self.L['tr_rec'], dict(esi=SPR, edi=team))
                self.chk(not err and not log and not e2 and g4 == st_['eax'] == REC + 61 * (ordn - 1),
                         'tr_rec v GetPlayerPointerFromShirtNumber', ordn, hex(g4), hex(st_['eax']), err, e2)
            m.w16(SPR + 2, pitch + 1)                   # (c) the pitch sprite keeps its ordinal: the substitute is read
            m.w16(SPR + 0x20, x)
            m.w16(SPR + 0x24, y)
            lim = 64 + 7 * k['RST'] if k['DMASK'] >> pos_in & 1 else 64
            for dist in (64, 65, lim, lim + 1):
                m.w32(SPR + 0x4A, dist)
                st_, v, err = self.call(m, self.L['tr_dist'])
                self.chk(not err and (not st_['flags'] & 0x41) == (dist > lim), 'tr_dist after a substitution',
                         top, pitch, bslot, pos_out, pos_in, dist, lim, err)

    def t_dist(self):
        c, k = self.c, self.k
        for ru, ok in ((0, 1), (1, 1), (1, 0)):
            m = self.mach('dist', ru, ok)
            for top, pos, hd in itertools.product((True, False), list(range(8)) + [0xFF], (-1, 0, 1, 3, 7, 9)):
                for x, y, z in self.spots(top, True):
                    self.place(m, top, x, y, pos, hd & 0xFF)
                    ext = self.live(ru, ok, 0, None) and pos <= 7 and k['DMASK'] >> pos & 1 and z & 1
                    lim = 64 + k['RST'] * min(7, max(0, hd)) if ext else 64
                    for dist in sorted({0, 64, 65, lim, lim + 1, 64 + 7 * k['RST'] + 1, 0xFFFFFFF0}):
                        m.w32(SPR + 0x4A, dist)
                        st, v, err = self.call(m, self.L['tr_dist'])
                        ja = not st['flags'] & 0x41             # (the game's `ja`: CF = 0 and ZF = 0 -> no contact)
                        self.chk(not err and ja == (dist > lim) and st['esi'] == SPR
                                 and all(st[r] == v[r] for r in ('eax', 'ebx', 'ecx', 'edx', 'edi', 'ebp')),
                                 'tr_dist', ru, ok, top, pos, hd, x, y, dist, lim, ja, err)


def main(build):
    t = T(build)
    out = []
    for name in ('t_zone', 't_live', 't_hdown', 't_header', 't_dist', 't_sub'):
        n0, b0 = t.n, t.bad
        getattr(t, name)()
        out.append(f'{name[2:]} {t.n - n0} cases, {t.bad - b0} different')
    for f in t.first:
        print('DIFF', f)
    used = len(bytes(t.img[4][swreg.TRHD_AT:swreg.TRHD_END]).rstrip(b'\0'))
    print(f'TRHD ({used} B used, knobs {t.k}): ' + '; '.join(out) + f': {"PASS" if not t.bad else "FAIL"}')
    return not t.bad


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)
