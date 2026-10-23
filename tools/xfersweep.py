"""python3 tools/xfersweep.py BUILD WORLD TEAMPATH BUYER ACTION: new career, a poked third-party offer, ACTION; bank / squad
names / order before, after, and after a save + reload. Prints a DEAL and a RELOAD line (world_transfer_* scenarios parse
them). LIST_ROW=n: our player listed on the transfer market first (his offer follows), as in a sale."""
import os, re, struct, sys, shutil
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # (this checkout)
exe, world, team, buyer, action = sys.argv[1:6]
sys.path.insert(0, W + '/tools'); os.chdir(W); sys.argv = ['x']
import swostest as T, lepatch, xtra
from le import LE
le = LE(open(os.path.join(exe, 'ITALIAN.EXE'), 'rb').read()); d1 = le.obj_bytes(1)
t1 = {f[1]: f[4] for f in le.fixups() if f[0] == 1 and f[3] == 2}
m = re.search(rb'\xc6\x46\x0d\x00\x66\x83\x05(.{4})\x01', d1, re.S); nof = t1[m.start(1)]
c = list(re.finditer(rb'\xc7\x05(.{4})(.{4})\xa1.{4}\x01\x05\1', d1[m.start() - 600:m.start()], re.S)); rec = t1[m.start() - 600 + c[-1].start(2)]
a = re.search(rb'\xc7\x05(.{4})(.{4})\x66\xa1(.{4})\x66\xa3.{4}\x66\x83\x2d.{4}\x01\x8b\x35\1.{0,40}?\xcc\xeb\xfe', d1, re.S)
tmsp, cnp = struct.unpack('<I', a.group(2))[0], struct.unpack('<I', a.group(3))[0]
ct = xtra.sites(lepatch.LEPatch(os.path.join(exe, 'ITALIAN.EXE')))[2]
LBL = {'accept': 'ACCETTA OFFERTA', 'reject': 'RIFIUTA OFFERTA', 'more': "CHIEDI DI PIU'", 'consider': 'CONSIDERA'}
def squad(s):
    n = struct.unpack('<H', s.result.obj2(cnp, 2))[0]; o = list(s.result.obj2(tmsp, 32))[:n]
    blk = s.result.obj2(ct + 76, 32 * 38)
    names = [blk[38 * k + 3:38 * k + 26].split(b'\0')[0].decode('latin1') for k in o if k < 32]
    return n, o, names
def bank(s):
    T.walk(s, 'TRASFERIMENTI', 3); b = next((x for x in s.screen().texts() if x.startswith('BANCA')), '?')
    T.walk(s, 'ESCI', 3); return b
def pick(s, label):
    sc = s.screen(); i = sc.find(label, exact=True)
    for k in (sc.path(i) or []): s.send(k + ' dump:0.5')
    return s.send('fire dump:4')
res = {}
run = None
with T.Session('sweep2', exe, {}, 'dump:2', 600) as s:
    run = s.box.run
    s.wait()
    for t in ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', world] + team.split(','):
        if all(T.press(s, s.screen(), x) is None for x in t.split('|')): print('RESULT MISSING', t); raise SystemExit
    s.send('fire dump:3')
    n0, o0, names0 = squad(s); b0 = bank(s)
    pl = 5
    if os.environ.get('LIST_ROW'):                       # our player on the transfer list first, then his offer
        T.walk(s, 'TRASFERIMENTI', 3); T.walk(s, 'AGG. GIOCATORE AL CALCIOMERC.', 3)
        T.walk(s, int(os.environ['LIST_ROW']), 3)
        for _ in range(3):
            if 'VISUALIZZA MONDO' in s.screen().texts(): break
            T.walk(s, 'ESCI', 3)
        nl = struct.unpack('<H', s.result.obj2(0x17064, 2))[0]; lst = list(struct.unpack('<5H', s.result.obj2(0x17066, 10)))
        print('LISTED', nl, [hex(x) for x in lst], flush=True)
        if nl: pl = lst[0] & 0xFF
    s.poke(s.result.base2 + rec, struct.pack('<HBBBBHHHBB', int(buyer, 0), pl, 0xFF, 0xFF, 0xFF, 1300, 0, 0, 10, 0))
    s.poke(s.result.base2 + nof, struct.pack('<H', 1)); s.send('dump:0.5')
    for st in ('TRASFERIMENTI', 'VISUAL. OFFERTE', 2): T.walk(s, st, 3)
    sold = next((x for x in s.screen().texts() if x in names0), '?')
    r = pick(s, LBL[action])
    if r.outcome == 'dump' and action == 'more' and 'OFFERTA TERZE PARTI' in s.screen().texts():
        r = pick(s, 'ACCETTA OFFERTA')
    if r.outcome != 'dump':
        print('RESULT TRAP', s.result); raise SystemExit
    for _ in range(4):                                  # back to the career menu
        if 'VISUALIZZA MONDO' in s.screen().texts(): break
        T.press(s, s.screen(), 'ESCI') or s.send('fire dump:2')
    n1, o1, names1 = squad(s); b1 = bank(s)
    T.walk(s, 'ESCI', 3)                                # career menu -> main menu -> SALVA CARRIERA
    T.walk(s, 'SALVA CARRIERA', 2); s.send(T.name_entry('SWP') + ' dump:3')
    saved = os.path.join(run, 'SWOS', 'SWP.CAR')
print('LISTED_AFTER', struct.unpack('<H', open(saved,'rb').read()[:0] or b'\0\0')[0] if False else '', end=''); print('DEAL', action, 'sold', sold, 'players', n0, '->', n1, 'bank', b0, '->', b1, 'gone', sold not in names1,
      'new', sorted(set(names1) - set(names0)), 'removed', sorted(set(names0) - set(names1)), 'names0', names0, 'order_ok', len(set(o1)) == n1, flush=True)
if os.path.exists(saved):
    with T.Session('sweep2_reload', exe, {'W84A.CAR': saved}, 'dump:2', 300) as s:
        s.wait(); s.send(T.LOAD1 + ' dump:3')
        n2, o2, names2 = squad(s); b2 = bank(s)
    print('RELOAD players', n2, 'same_names', names2 == names1, 'bank', b2, 'order_ok', len(set(o2)) == n2, flush=True)
else:
    print('RELOAD no save', os.listdir(os.path.join(run, 'SWOS'))[:5])
