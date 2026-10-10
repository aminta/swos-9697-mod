"""SWOS regression harness: runs the game in a private DOSBox-X, feeds it a key script, checks the outcome.

  python3 tools/swostest.py list                     scenarios
  python3 tools/swostest.py run [NAME...]            run scenarios (all when none given); exit code 1 on a failure
  python3 tools/swostest.py keys EXE CAR|- 'KEYS' [-shots S] [-t T] [-name NAME]
        ad-hoc run: EXE = a build dir (ITALIAN.EXE + DATA) or an .EXE file (DATA from c/SWOS); CAR = a save to copy
        in (or -); KEYS = the script below; window screenshots every S s into runs/NAME/shots; T = timeout (s);
        -name NAME = run dir (default keys)
  Env: SWOSTEST_BUILD = build dir under test, else SWOSTEST_BRANCH = git branch/commit to build, else this checkout.

Key script: space-separated keys fire up down left right esc enter space bspace a-z 0-9, and 'dump'. 'key:s' waits
s seconds (default 0.5) before the key, counted in menu frames (RATE GetKey calls per s), so the script follows the
game: loading and simulating do not use it up. After a screen change wait >= 1-2 s (a menu that is still starting
drops a key). 'dump' stops the game in the debugger: 32 MB memory dump (MEMDUMP.BIN) and the run ends there.

How it works
- Work tree internal/swostest/ (git-ignored): base/ = c/SWOS game files without exes and saves (made once),
  runs/<name>/SWOS = base + the exe under test + copies of the saves. c/SWOS and the dosbox-swos*.conf files are never
  touched: each run has its own conf and DOSBox-X process (a window opens; it does not need focus).
- The exe is patched in its run copy only (test_exe): intro skipped, menus read the latched last key, and a key
  feeder on a new obj1 page (called instead of GetKey by MenuCheckControls and InputTextKeyLoop) types the script:
  each key goes into keyBuffer and is held for HOLD calls through SetKeyboardControlFlags, like a real key press.
- DOSBox-X runs under a pty with -break-start and BPINT 3, core=dynamic, cycles=max: the mod's `int 3; jmp $` traps
  and the 'dump' step break into the debugger; the runner sees the code view (CD03), writes MEMDUMP.BIN and reads EIP;
  obj1/obj2 linear bases are found in the dump (they move with the exe size). No break before the timeout = hang or a
  script that went astray (runs/<name>/shots/final.png shows where).
- Oracles: saves written by the game, checked in Python (car_info, W1 block, cup lists), the outcome, the dump.
"""
import hashlib, os, pty, re, select, shutil, signal, struct, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN = os.path.expanduser('~/swos-mod')               # main checkout: c/, orig/, internal/ live there
WORK = os.path.join(MAIN, 'internal', 'swostest')
DOSBOX = '/Applications/dosbox-x.app/Contents/MacOS/dosbox-x'
ISO = os.path.join(MAIN, 'orig', 'swos9697ita.iso')
BREAK = re.compile(rb'[0-9A-F]{4}:([0-9A-F]{8}) +CD03')

CONF = """[sdl]
output=surface
[dosbox]
machine=svga_s3
memsize=32
[cpu]
core={core}
cputype=pentium
cycles={cycles}
[mixer]
nosound=true
[sblaster]
sbtype=sb16
[autoexec]
mount c .
imgmount d {iso} -t iso
c:
cd \\SWOS
{exe}
exit
"""


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]


def setup():
    """base/ = c/SWOS minus exes, saves and backups (once)."""
    base = os.path.join(WORK, 'base')
    if os.path.isdir(base):
        return base
    src = os.path.join(MAIN, 'c', 'SWOS')
    shutil.copytree(src, base, ignore=shutil.ignore_patterns('*.CAR', '*.EXE', '*.BAK', '*.SEA', 'desktop.ini'))
    for f in ('DOS4GW.EXE', 'SETUP.EXE'):
        shutil.copy(os.path.join(src, f), base)
    return base


def build(name, env=None, branch=None):
    """Build the IT exe + team files into internal/swostest/builds/<name> (from this checkout or a git branch)."""
    out = os.path.join(WORK, 'builds', name)
    src = ROOT
    if branch:                                       # a throw-away worktree of that branch, links to the ignored dirs
        src = os.path.join(WORK, 'src', name)
        if not os.path.isdir(src):
            subprocess.run(['git', '-C', MAIN, 'worktree', 'add', '--detach', src, branch], check=True)
        else:
            subprocess.run(['git', '-C', src, 'checkout', '-q', '--detach', branch], check=True)
        for d in ('orig', 'ref', 'c', 'internal'):
            if not os.path.exists(os.path.join(src, d)):
                os.symlink(os.path.join(MAIN, d), os.path.join(src, d))
    os.makedirs(os.path.join(out, 'DATA'), exist_ok=True)
    code = ("import sys,io,contextlib; sys.path.insert(0,'tools'); import patch\n"
            "out=sys.argv[1]\n"
            "with contextlib.redirect_stdout(io.StringIO()):\n"
            "    r=patch.patch_teams('orig/DATA/TEAM.020',out+'/DATA/TEAM.020'); patch.write_new_teams('orig/DATA',out+'/DATA')\n"
            "    patch.patch_exe('orig/ITALIAN.EXE',out+'/ITALIAN.EXE',r,'it')\n")
    subprocess.run([sys.executable, '-c', code, out], cwd=src, check=True, env=dict(os.environ, **(env or {})))
    return out


def prepare(name, exe_dir, cars, steps):
    """runs/<name>/SWOS = base + exe_dir (ITALIAN.EXE + DATA, or an .EXE file) + saves {dos name: source path}."""
    run = os.path.join(WORK, 'runs', name)
    if os.path.isdir(run):
        shutil.rmtree(run)
    game = os.path.join(run, 'SWOS')
    shutil.copytree(setup(), game)
    if os.path.isfile(exe_dir):
        shutil.copytree(os.path.join(MAIN, 'c', 'SWOS', 'DATA'), os.path.join(game, 'DATA'), dirs_exist_ok=True)
        shutil.copy(exe_dir, os.path.join(game, 'ITALIAN.EXE'))
    else:
        shutil.copytree(exe_dir, game, dirs_exist_ok=True, ignore=shutil.ignore_patterns('log.txt'))
    for dos, src in cars.items():
        shutil.copy(src, os.path.join(game, dos))
    return run, test_exe(os.path.join(game, 'ITALIAN.EXE'), steps)


SCAN = {'fire': 0x1D, 'up': 0x48, 'down': 0x50, 'left': 0x4B, 'right': 0x4D, 'esc': 0x01, 'enter': 0x1C,
        'space': 0x39, 'bspace': 0x0E, 'dump': 0xFF}
SCAN.update({ch: sc for row, base in (('1234567890', 0x02), ('qwertyuiop', 0x10), ('asdfghjkl', 0x1E),
                                      ('zxcvbnm', 0x2C)) for sc, ch in enumerate(row, base)})
HOLD = 3                                               # GetKey calls a typed key stays held
RATE = 30                                              # GetKey calls per second in the menus (calibrated)


def steps_of(text):
    """'fire down:2 down fire:10' -> [(scan code, GetKey calls to wait before it)]; ':s' = seconds before the key
    (default 0.5), counted only while the game polls the keyboard (not while it loads or simulates)."""
    out = []
    for tok in text.split():
        k, _, t = tok.partition(':')
        out.append((SCAN[k.lower()], max(1, round(float(t or 0.5) * RATE))))
    return out


def test_exe(exe, steps):
    """Test builds only (the exe under test is patched in its run copy):
    - intro skipped (skipIntro test -> jmp);
    - menus also read the latched last key (MenuCheckControls' 'two joypads' branch, normally only for
      g_inputControls == 5), so one typed key = one menu action however briefly it is held;
    - key feeder: the `call GetKey` of MenuCheckControls and InputTextKeyLoop (the last 2 of 12) go to a stub on a new obj1 page that, when the key buffer is empty, puts the
      script's next scan code into keyBuffer after its wait (counted in GetKey calls, so the script follows the game,
      not the wall clock: loading and simulating do not consume it). Text input (save names) reads GetKey too."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    from lepatch import LEPatch, add_object_page
    import nasmcave
    data = open(exe, 'rb').read()
    le = LE(data)
    c = le.obj_bytes(1)
    fx = {soff: (tobj, toff) for sobj, soff, _, tobj, toff, *_ in le.fixups() if sobj == 1}
    one = lambda pat: (lambda m: (m[0].start() if len(m) == 1 else sys.exit(f'{exe}: {pat!r} x{len(m)}')))(
        list(re.finditer(pat, c, re.S)))
    i9 = one(rb'\x66\x83\x3d....\x09\x74.\xa0....\x0f\xb7\x1d....\x88\x83')   # Int9KeyboardHandler
    keycount, keybuf = fx[i9 + 3], fx[c.index(b'\x88\x83', i9) + 2]
    k = one(rb'\xe4\x60\x66\x0f\xb6\xc0\x66\x8b\x1d....\x66\x89\x1d....\x66\xa3')   # in al, 60h ...
    scancode, prevscan = fx[k + 9], fx[k + 16]
    e8 = c.index(b'\x66\x83\x05', i9) + 8                  # add keyCount, 1; call SetKeyboardControlFlags
    assert c[e8] == 0xE8
    setkbd = e8 + 5 + struct.unpack_from('<i', c, e8 + 1)[0]
    getkey = [s for s, t in fx.items() if t == keycount and c[s - 2:s] == b'\x66\xa1']
    assert len(getkey) == 1
    gk = c.rindex(b'\xff\x35', 0, getkey[0]) - 14 * 6     # 15 pushes before the body
    assert all(c[gk + 6 * k:gk + 6 * k + 2] == b'\xff\x35' for k in range(15)), hex(gk)
    calls = [i for i in range(len(c) - 5) if c[i] == 0xE8 and i + 5 + struct.unpack_from('<i', c, i + 1)[0] == gk]
    assert len(calls) == 12, len(calls)
    calls = calls[-2:]          # MenuCheckControls, InputTextKeyLoop (the others: match, replays, highlights)
    mcc = one(rb'\x66\x83\x3d....\x05\x0f\x85....\x66\x83\x3d....\xff\x0f\x84')
    intro = one(rb'\x66\x83\x3d....\x00\x75.\xe8....\x75')

    o1 = le.obj(1)
    page = o1.npages * le.page_size
    data = add_object_page(data, 1)
    tmp = exe + '.tmp'
    open(tmp, 'wb').write(data)
    p = LEPatch(tmp)
    os.remove(tmp)
    p.set_vsize(1, page + le.page_size)
    p.put(1, intro + 8, b'\xEB')
    p.put(1, mcc + 8, b'\x90' * 6)
    src = """
stub:   pushad
        inc dword [calls]
        cmp word [hold], 0
        je .idle
        dec word [hold]
        jnz .go
        movzx eax, byte [cur]           ; release after HOLD calls (screens that read the held state)
        or al, 0x80
        call emu
        jmp .go
.idle:  cmp word [KEYCOUNT], 0
        jne .go
        mov esi, [ptr]
        movzx eax, word [esi]
        or eax, eax
        jz .go
        dec word [esi+2]
        jnz .go
        add esi, 4
        mov [ptr], esi
        cmp al, 0xFF
        jne .key
        int 3                           ; 'dump' step: the runner's BPINT 3 stops here (EIP in this page)
        jmp .go
.key:   mov [KEYBUF], al                ; latched (menus' last key, text input) ...
        mov word [KEYCOUNT], 1
        mov [cur], al
        call emu                        ; ... and held, like Int9KeyboardHandler
        mov word [hold], HOLD
.go:    popad
        jmp GETKEY
emu:    mov bx, [SCANCODE]
        mov [PREVSCAN], bx
        mov [SCANCODE], ax
        call SETKBD
        ret
ptr:    dd script
calls:  dd 0                            ; GetKey calls (read from the dump)
hold:   dw 0
cur:    db 0, 0
script:
""" + ''.join(f'        dw {k:#x}, {w}\n' for k, w in steps) + '        dw 0, 0\n'
    sym = {'KEYCOUNT': keycount, 'KEYBUF': keybuf, 'GETKEY': (1, gk), 'SCANCODE': scancode, 'PREVSCAN': prevscan,
           'SETKBD': (1, setkbd), 'HOLD': (0, HOLD)}
    code, fix = nasmcave.assemble(src, page, sym)
    assert len(code) < le.page_size, 'script too long'
    p.put(1, page, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, page + off, tobj, toff)
    for i in calls:
        p.put(1, i + 1, struct.pack('<i', page - (i + 5)))
    p.save(exe)
    d2 = le.obj_bytes(2)
    anchor = d2.find(b'SERIE A\0') - 32                # constant strings: finds obj2 in a memory dump
    fixed = next(o for o in range(0x1000, len(c), 16)            # 48 code bytes with no fixup: finds obj1 in a dump
                 if not any(o - 3 <= f < o + 48 for f in range(o - 3, o + 48) if f in fx) and len(set(c[o:o + 48])) > 8)
    return {'page': page, 'calls': page + nasmcave.labels(src, 0, sym)['calls'], 'code': (fixed, c[fixed:fixed + 48]),
            'anchor': (anchor, d2[anchor:anchor + 64])}


class Dosbox:
    """DOSBox-X under a pty: debugger reachable, int 3 traps caught."""

    def __init__(self, run, timeout, shots=0, exe='ITALIAN.EXE'):
        self.run, self.timeout, self.shots = run, timeout, shots
        conf = CONF.format(cycles=os.environ.get('CYCLES', 'max'), core=os.environ.get('CORE', 'dynamic'), iso=ISO, exe=exe)
        open(os.path.join(run, 'test.conf'), 'w').write(conf)
        self.screen, self.eip = b'', None
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(run)
            os.environ['TERM'] = 'xterm'
            os.execv(DOSBOX, [DOSBOX, '-conf', 'test.conf', '-fastlaunch', '-break-start',
                              '-time-limit', str(int(timeout) + 120)])

    def pump(self, t):
        end = time.time() + t
        got = 0
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if r:
                try:
                    b = os.read(self.fd, 65536)
                except OSError:
                    return -1                          # process gone
                if not b:
                    return -1
                self.screen += b
                got += len(b)
        return got

    def cmd(self, text, wait=1.0):
        os.write(self.fd, text.encode() + b'\r')
        return self.pump(wait)

    def alive(self):
        return os.waitpid(self.pid, os.WNOHANG) == (0, 0)

    def go(self):
        """Run until DOSBox-X exits ('exit'), an int 3 breaks into the debugger ('break': a trap or a 'dump' step) or
        the timeout ('timeout' = hang without a trap, or the script did not get where expected)."""
        self.pump(3)
        self.cmd('BPINT 3')
        os.write(self.fd, b'\x1b[15~')                 # F5 = run
        self.pump(1)
        mark = len(self.screen)
        start, nshot = time.time(), 0
        while True:
            n = self.pump(0.5)
            if n < 0 or not self.alive():
                return 'exit'
            m = BREAK.search(self.screen, mark)    # the debugger's code view redrawn on an int 3 (CD03)
            if m:
                self.eip = int(m.group(1), 16)
                return 'break'
            el = time.time() - start
            if self.shots and el >= nshot * self.shots:
                self.shot('t%03d' % int(el))
                nshot += 1
            if el > self.timeout:
                return 'timeout'

    def shot(self, tag):
        exe = os.path.join(WORK, 'bin', 'winid')            # window id of a pid (screencapture -l needs it)
        if not os.path.exists(exe):
            os.makedirs(os.path.dirname(exe), exist_ok=True)
            subprocess.run(['swiftc', '-O', os.path.join(ROOT, 'tools', 'swostest_winid.swift'), '-o', exe], check=True)
        win = subprocess.run([exe, str(self.pid)], capture_output=True, text=True)
        wid = win.stdout.strip()
        if wid and wid != '0':
            os.makedirs(os.path.join(self.run, 'shots'), exist_ok=True)
            subprocess.run(['screencapture', '-x', '-o', '-l', wid, os.path.join(self.run, 'shots', tag + '.png')],
                           capture_output=True)

    def post_mortem(self):
        """After a break: 32 MB memory dump (MEMDUMP.BIN = linear 0..32 MB); returns the break EIP (int) or None."""
        self.shot('final')
        dump = os.path.join(self.run, 'MEMDUMP.BIN')
        self.cmd('MEMDUMPBIN 0168:00000000 2000000', 1)
        end = time.time() + 30
        while time.time() < end and not (os.path.exists(dump) and os.path.getsize(dump) >= 0x2000000):
            self.pump(0.5)
        return self.eip

    def kill(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


# ----------------------------------------------------------------------------------------------------------- scenarios

class Result:
    """What a run left: outcome ('exit', 'dump', 'trap', 'timeout'), EIP, the game dir and the memory dump
    (obj1/obj2 linear bases found in the dump: they move with the exe's size)."""

    def __init__(self, run, outcome, eip, info):
        self.run, self.game, self.outcome, self.eip = run, os.path.join(run, 'SWOS'), outcome, eip
        path = os.path.join(run, 'MEMDUMP.BIN')
        self.mem = open(path, 'rb').read() if os.path.exists(path) else None
        self.base1 = self.base2 = self.calls = None
        if self.mem:
            off, chunk = info['code']
            self.base1 = self.mem.find(chunk) - off
            off, chunk = info['anchor']
            self.base2 = self.mem.find(chunk) - off
            self.calls = struct.unpack_from('<I', self.mem, self.base1 + info['calls'])[0]
        if eip is not None and self.base1 is not None:
            rel = eip - self.base1
            if info['page'] <= rel < info['page'] + 0x1000:
                self.outcome = 'dump'

    def obj1(self, off, n):
        return self.mem[self.base1 + off:self.base1 + off + n]

    def obj2(self, off, n):
        return self.mem[self.base2 + off:self.base2 + off + n]

    def where(self, lin):
        if self.base1 is None:
            return f'0x{lin:X}'
        if lin >= self.base2:
            return f'obj2+0x{lin - self.base2:X}'
        return f'obj1+0x{lin - self.base1:X}'

    def __str__(self):
        s = self.outcome
        if self.eip is not None:
            s += f' at {self.where(self.eip)} (linear 0x{self.eip:X}; obj1 0x{self.base1:X}, obj2 0x{self.base2:X})'
        if self.calls is not None:
            s += f', {self.calls} GetKey calls'
        return s


def run_case(name, exe_dir, cars, keys, timeout, shots=0):
    """Run one key script on a copy of the game; returns a Result."""
    run, info = prepare(name, exe_dir, cars, steps_of(keys))
    box = Dosbox(run, timeout, shots)
    eip = None
    try:
        outcome = box.go()
        if outcome == 'break':
            eip = box.post_mortem()
            outcome = 'trap'                           # Result turns it into 'dump' when EIP is in the stub
        elif outcome == 'timeout':
            box.shot('final')
    finally:
        box.kill()
        open(os.path.join(run, 'debugger.raw'), 'wb').write(box.screen)
    return Result(run, outcome, eip, info)


CAR_FIXED = 95151                     # .CAR: fixed part (careerFileBuffer ..), then N cached teams + trailer
SLT = 59612                           # someLeaguesTable in the save (world byte [1845], balance [1846])
CUPS = {'CC': 71464, 'CWC': 71543, 'UEFA': 71635}   # euroCupCopy (79 B) / cupWinnersCupCopy / uefaCupCopy (92 B)


def car_info(path):
    """A few .CAR facts for the oracles."""
    d = open(path, 'rb').read()
    n = struct.unpack_from('<H', d, CAR_FIXED)[0]
    t = CAR_FIXED + 2 + n * 684
    tab = d[SLT:SLT + 2000]
    out = {'size': len(d), 'teams': n, 'trailer': d[t:t + 2], 'world': tab[1845], 'sum': sum(tab) % 256}
    for name, off in CUPS.items():
        c = d[off:off + (79 if name == 'CC' else 92)]
        n = 16 if name == 'CC' else c[10]
        lst = c[c[7] + 7:c[7] + 7 + 2 * n]
        out[name] = [(lst[i], lst[i + 1]) for i in range(0, len(lst), 2)]
    return out


# Key scripts. Waits: ':s' before the key, in menu frames (RATE per s). After a screen change wait >= 1 s: the new
# menu drops a key typed while it initialises. After a career load the first fire is always ignored (deterministic).
LOAD1 = 'down:3 down down down down fire fire:2'          # main menu -> CARICA VECCHIA COMP. -> first save -> career
FINISH = 'fire:2'                                 # career menu: FINISCI STAGIONE -> season-end menu


def name_entry(name):
    """Save screen (cursor on SALVA): NOME FILE field, clear it, type name, Enter (= save)."""
    return 'up:2 fire:1 ' + 'bspace ' * 8 + ' '.join(name.lower()) + ' enter:1'


def save_as(name):
    """Season-end menu (cursor on OFFERTE LAVORO) -> SALVA CARRIERA -> name."""
    return 'down:3 down fire:1 ' + name_entry(name)


def quit_and_save(name):
    """Career menu (cursor on FINISCI STAGIONE) -> ESCI -> main menu SALVA CARRIERA -> name."""
    return 'down:2 down fire:2 down:2 down down down up fire:2 ' + name_entry(name)


def check(cond, msg, errs):
    if not cond:
        errs.append(msg)


def season_case(name, build, car, out, timeout=120, extra=None):
    """Load `car`, FINISCI STAGIONE, save as `out`, 'dump'; common oracles + extra(info, errs)."""
    r = run_case(name, build, {os.path.basename(car).upper(): car}, f'{LOAD1} {FINISH} {save_as(out)} dump:3',
                 timeout)
    errs = []
    path = os.path.join(r.game, out + '.CAR')
    check(r.outcome == 'dump', f'run ended with {r}', errs)
    if os.path.exists(path):
        info = car_info(path)
        check(info['sum'] == 0, f"someLeaguesTable sum {info['sum']} != 0", errs)
        if extra:
            extra(info, errs, path)
    else:
        errs.append(f'{out}.CAR not written')
    return not errs, f"{r}; {'; '.join(errs) or 'ok'}"


SCENARIOS = {}


def scenario(fn):
    SCENARIOS[fn.__name__] = fn
    return fn


def builds():
    """Exe under test: SWOSTEST_BUILD (a ready dir with ITALIAN.EXE + DATA), else built from SWOSTEST_BRANCH (a git
    branch/commit), else from this checkout."""
    if not hasattr(builds, 'cache'):
        br = os.environ.get('SWOSTEST_BRANCH')
        builds.cache = {'it': os.environ.get('SWOSTEST_BUILD') or build(re.sub(r'\W', '_', br) if br else 'it', branch=br)}
    return builds.cache


SAVES = os.path.join(MAIN, 'c', 'SWOS')               # read-only source of the reference saves (copied per run)


def juve2(fixed):
    """c/SWOS/JUVE2.CAR (Juventus 1997/98 at FINISCI STAGIONE, CC holder: Intercontinental + CWC), copied; fixed =
    byte 0x173A3 (E092F, the slot-3 cup id saved wrong by the pre-2b96905 euro_found) set to 0 like JUVEFIX."""
    d = bytearray(open(os.path.join(SAVES, 'JUVE2.CAR'), 'rb').read())
    if fixed:
        d[0x173A3] = 0
    path = os.path.join(WORK, 'saves', 'JUVE2F.CAR' if fixed else 'JUVE2.CAR')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(d)
    return path


@scenario
def italy_season():
    """Juventus 1997/98 season end (JUVE2 with E092F fixed): no trap, save; next CC: 16 distinct, Italian clubs in"""
    def cc(info, errs, path):
        lst = info['CC']
        check(len(set(lst)) == 16, f'CC: {len(set(lst))} distinct clubs {lst}', errs)
        check(sum(f == 20 for f, o in lst) >= 1, 'CC: no Italian club', errs)
        check(info['trailer'] == b'C7', f"trailer {info['trailer']!r}", errs)
    return season_case('italy_season', builds()['it'], juve2(True), 'T1', extra=cc)


def two_saves(name, exe_dir, src, timeout=120):
    """Load src, save it from the main menu (X1), reload X1, save again (X2); returns (error or None, X1, X2)."""
    files = []
    for k in (1, 2):
        cur = src if k == 1 else files[-1]
        out = re.sub(r'[^A-Z0-9]', '', name.upper())[:6] + str(k)
        r = run_case(f'{name}_{k}', exe_dir, {os.path.basename(cur).upper(): cur},
                     f'{LOAD1} {quit_and_save(out)} dump:3', timeout)
        path = os.path.join(r.game, out + '.CAR')
        if r.outcome != 'dump' or not os.path.exists(path):
            return f'save {k}: {r}; written: {os.path.exists(path)}', None, None
        files.append(path)
    return None, files[0], files[1]


def ndiff(a, b):
    a, b = open(a, 'rb').read(), open(b, 'rb').read()
    return sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))


@scenario
def roundtrip():
    """Load/save round trip: JUVE2F loaded + saved from the main menu (ROUNDT1), reloaded + saved (ROUNDT2) = ROUNDT1"""
    err, x1, x2 = two_saves('roundtrip', builds()['it'], juve2(True))
    if err:
        return False, err
    n, info = ndiff(x1, x2), car_info(x2)
    return n == 0 and info['sum'] == 0, f'save 1 vs 2: {n} bytes differ, table sum {info["sum"]}'


@scenario
def world_roundtrip():
    """World 3 (31 countries, euro 128): W128B load/save twice; saves equal, W1 block, 128 records, cups 32/32/64"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import careerworld
    src = os.path.join(SAVES, 'W128B.CAR')
    err, x1, x2 = two_saves('world_roundtrip', world_build(), src, 150)
    if err:
        return False, err
    d = open(x2, 'rb').read()
    errs = []
    info = car_info(x2)
    check(info['world'] == 3 and info['sum'] == 0, f"world byte {info['world']}, table sum {info['sum']}", errs)
    check(d[2:4] == struct.pack('<H', careerworld.WMARK), 'no W1 block', errs)
    check(struct.unpack_from('<H', d, 0)[0] == 128, f'{struct.unpack_from("<H", d, 0)[0]} euro records', errs)
    for cup, off, n in (('CC', 0, 32), ('CWC', 92, 32), ('UEFA', 184, 64)):
        c = d[4 + off:4 + off + (160 if cup == 'UEFA' else 92)]
        lst = c[c[7] + 7:c[7] + 7 + 2 * c[10]]
        pairs = {(lst[i], lst[i + 1]) for i in range(0, len(lst), 2)}
        check(c[10] == n and len(pairs) == n, f'{cup}: {c[10]} clubs, {len(pairs)} distinct', errs)
    check(ndiff(x1, x2) == 0, f'save 1 vs 2: {ndiff(x1, x2)} bytes differ', errs)
    return not errs, f"{'; '.join(errs) or 'ok'} (vs W128B as written by its own build: {ndiff(src, x1)} bytes differ)"


def world_build():
    """World 3 (internal/career-test/mkworld3.py, not the DERBY variant), generated into internal/swostest/worlds."""
    d = os.path.join(WORK, 'worlds')
    if not os.path.isdir(os.path.join(d, 'world3')):
        src = open(os.path.join(MAIN, 'internal', 'career-test', 'mkworld3.py')).read()
        src = re.sub(r"(?m)^OUT = .*$", f"OUT = {os.path.join(d, 'world3')!r}", src)
        src = re.sub(r"(?m)^SRC = .*$", f"SRC = {os.path.join(MAIN, 'internal', 'career-test', 'test-world')!r}", src)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'mkworld3.py'), 'w').write(src)
        subprocess.run([sys.executable, os.path.join(d, 'mkworld3.py')], check=True, capture_output=True,
                       env={k: v for k, v in os.environ.items() if k != 'DERBY'})
    packs = ','.join(['ddr-1988-89'] + sorted(os.path.join(d, 'world3', x) for x in os.listdir(os.path.join(d, 'world3'))))
    br = os.environ.get('SWOSTEST_BRANCH')
    return build('world3', env={'SEASON_PACKS': packs}, branch=br)


@scenario
def juve2_trap():
    """Known bug, negative control: JUVE2 as saved (E092F = 1) must not trap at FINISCI STAGIONE + results"""
    r = run_case('juve2_trap', builds()['it'], {'JUVE2.CAR': juve2(False)}, f'{LOAD1} {FINISH} dump:3', 90)
    return r.outcome == 'dump', str(r)


def main(argv):
    if not argv or argv[0] == 'list':
        for k, f in SCENARIOS.items():
            print(f'{k:20} {(f.__doc__ or "").strip().splitlines()[0]}')
        return 0
    if argv[0] == 'keys':                              # keys EXE_DIR CAR|- 'k1:t1 k2:t2 ...' [-shots N] [-t T]
        exe_dir, car, keys = argv[1], argv[2], argv[3]
        shots = float(argv[argv.index('-shots') + 1]) if '-shots' in argv else 3
        timeout = float(argv[argv.index('-t') + 1]) if '-t' in argv else 60
        cars = {} if car == '-' else {os.path.basename(car).upper(): car}
        name = argv[argv.index('-name') + 1] if '-name' in argv else 'keys'
        r = run_case(name, exe_dir, cars, keys, timeout, shots)
        print(r, '->', r.run)
        return 0
    if argv[0] == 'run':
        names = argv[1:] or list(SCENARIOS)
        bad = 0
        for n in names:
            t = time.time()
            ok, msg = SCENARIOS[n]()
            bad += not ok
            print(f'{"PASS" if ok else "FAIL"} {n} ({time.time() - t:.0f} s) {msg}', flush=True)
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
