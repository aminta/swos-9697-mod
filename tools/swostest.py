"""SWOS regression harness: runs the game in a private DOSBox-X, feeds it a key script, checks the outcome.

  python3 tools/swostest.py list                     scenarios
  python3 tools/swostest.py run [NAME...]            run scenarios (all when none given); exit code 1 on a failure
  python3 tools/swostest.py keys EXE CAR|- 'KEYS' [-shots S] [-t T] [-name NAME] [-match] [-timer]
        ad-hoc run: EXE = a build dir (ITALIAN.EXE + DATA) or an .EXE file (DATA from c/SWOS); CAR = a save to copy
        in (or -); KEYS = the script below; window screenshots every S s into runs/NAME/shots; T = timeout (s);
        -timer = feed from the timer (70 Hz) instead of GetKey: for SWOS++, which re-patches the menu input code;
        waits are then game time, not menu frames (allow for loading);
        -name NAME = run dir (default keys); -match = the feeder also types during matches, replays and
        highlights (all 12 GetKey calls; waits then count in match frames too)
  Env: SWOSTEST_BUILD = build dir under test, else SWOSTEST_BRANCH = git branch/commit to build, else this checkout.

Key script: space-separated keys fire up down left right esc enter space bspace a-z 0-9, and 'dump'; 'fire+right'
= both held (fire typed), for the entries with input-function control masks (kit colours). 'key:s' waits
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


def prepare(name, exe_dir, cars, steps, match=False, timer=False):
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
    if not os.path.exists(os.path.join(game, 'ITALIAN.EXE')):      # e.g. an English SWOS++ bundle
        shutil.copy(os.path.join(game, 'ENGLISH.EXE'), os.path.join(game, 'ITALIAN.EXE'))
    return run, test_exe(os.path.join(game, 'ITALIAN.EXE'), steps, match, timer)


SCAN = {'fire': 0x1D, 'up': 0x48, 'down': 0x50, 'left': 0x4B, 'right': 0x4D, 'esc': 0x01, 'enter': 0x1C,
        'space': 0x39, 'bspace': 0x0E, 'dump': 0xFF}
SCAN.update({ch: sc for row, base in (('1234567890', 0x02), ('qwertyuiop', 0x10), ('asdfghjkl', 0x1E),
                                      ('zxcvbnm', 0x2C)) for sc, ch in enumerate(row, base)})
SCRIPT_MAX = 200                                       # steps a pause can write
TICKS = 70                                             # timer ticks per s (-timer mode)
HOLD = 1                                               # GetKey calls a typed key stays held (more = menu auto-repeat)
RATE = 30                                              # GetKey calls per second in the menus (calibrated)


def steps_of(text, rate=None):
    """'fire down:2 down fire:10' -> [(scan code, GetKey calls to wait before it)]; ':s' = seconds before the key
    (default 0.5), counted only while the game polls the keyboard (not while it loads or simulates)."""
    out = []
    for tok in text.split():
        k, _, t = tok.partition(':')
        codes = [SCAN[x] for x in k.lower().split('+')]          # 'fire+right': both held, fire typed
        assert len(codes) <= 2, tok
        out.append((codes[0] | (codes[1] << 8 if len(codes) > 1 else 0), max(1, round(float(t or 0.5) * (rate or RATE)))))
    return out


def test_exe(exe, steps, match=False, timer=False):
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
    if not match:
        calls = calls[-2:]      # MenuCheckControls, InputTextKeyLoop (the others: match, replays, highlights)
    if timer:                   # SWOS++ re-patches the menu input code: feed from TimerProc (70 Hz) instead
        t = one(rb'\x66\xff\x05....\x66\xff\x05....\x66\xa1....\x66\x0b\xc0\x75.\x66\xff\x05....\x66\x83\x05....'
                rb'\x01\x66\x83\x25....\x01\x75.\x66\xc7\x05....\xff\xff\xe8') + 59   # call BumpIntroTimers
        assert c[t] == 0xE8
        calls, gk = [t], t + 5 + struct.unpack_from('<i', c, t + 1)[0]
    mcc = one(rb'\x66\x83\x3d....\x05\x0f\x85....\x66\x83\x3d....\xff\x0f\x84')
    intro = one(rb'\x66\x83\x3d....\x00\x75.\xe8....\x75')
    mp = one(rb'\x66\x83\x3d....\x01\x74.\x66\x83\x3d....\xff\x75.\xe8....\x66\xa9\x00\x02\x75.'
             rb'\xe8....\xe8....\xe8....\xc7\x05')              # MenuProc: mov A6, offset g_currentMenu
    curmenu = fx[c.index(b'\xc7\x05', mp + 20) + 6]

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
        movzx eax, byte [cur+1]         ; second key of a combination (fire+right)
        or eax, eax
        jz .go
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
        int 3                           ; 'dump' step: the runner's BPINT 3 stops here (EIP in this page); to go
        jmp .go                         ; on, the runner sets EIP past it (and may write new steps + ptr)
.key:   mov [KEYBUF], al                ; latched (menus' last key, text input) ...
        mov word [KEYCOUNT], 1
        mov [cur], ax                   ; al = key, ah = second key held with it (0 = none)
        push eax
        movzx eax, al
        call emu                        ; ... and held, like Int9KeyboardHandler
        pop eax
        movzx eax, ah
        or eax, eax
        jz .held
        call emu
.held:
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
""" + ''.join(f'        dw {k:#x}, {w}\n' for k, w in steps) + '        dw 0, 0\n' + f'        times {4 * SCRIPT_MAX} db 0\n'
    sym = {'KEYCOUNT': keycount, 'KEYBUF': keybuf, 'GETKEY': (1, gk), 'SCANCODE': scancode, 'PREVSCAN': prevscan,
           'SETKBD': (1, setkbd), 'HOLD': (0, HOLD)}
    code, fix = nasmcave.assemble(src, page, sym)
    assert len(code) <= le.page_size, 'script too long'
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
    lab = nasmcave.labels(src, 0, sym)
    return {'page': page, 'calls': page + lab['calls'], 'code': (fixed, c[fixed:fixed + 48]), 'menu': curmenu[1],
            'brk': page + code.index(b'\xcd\x03'), 'ptr': page + lab['ptr'], 'script': page + lab['script'],
            'anchor': (anchor, d2[anchor:anchor + 64])}


class Dosbox:
    """DOSBox-X under a pty: debugger reachable, int 3 traps caught."""

    def __init__(self, run, timeout, shots=0, exe='ITALIAN.EXE'):
        self.run, self.timeout, self.shots = run, timeout, shots
        conf = CONF.format(cycles=os.environ.get('CYCLES', 'max'), core=os.environ.get('CORE', 'dynamic'), iso=ISO, exe=exe)
        open(os.path.join(run, 'test.conf'), 'w').write(conf)
        self.screen, self.eip, self.t0, self.watch = b'', None, time.time(), set()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(run)
            os.environ['TERM'] = 'xterm'
            os.execv(DOSBOX, [DOSBOX, '-conf', 'test.conf', '-fastlaunch', '-break-start',
                              '-time-limit', '14400'])  # the runner kills it; sessions run long

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
        for _ in range(20):                            # under load the debugger may not take input yet
            pre = len(self.screen)
            self.cmd('BPINT 3', 1)
            if b'breakpoint at INT 03' in re.sub(rb'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\(B', b'', self.screen[pre:]):
                break
        else:
            return 'timeout'
        return self.go_on()

    def go_on(self):
        """F5 (resume) and watch, as go()."""
        self.cmd('C 0160:00000000', 0.3)              # move the code view away: the next break must redraw it
        pre = len(self.screen)
        os.write(self.fd, b'\x1b[15~')                 # F5 = run
        end = time.time() + 2                          # watch from the debugger's '(Running)' on: a break can come
        while b'Running' not in self.screen[pre:] and time.time() < end:   # within the first second
            self.pump(0.05)
        i = self.screen.find(b'Running', pre)
        mark = i + 7 if i >= 0 else len(self.screen)
        start, nshot = time.time(), 0
        while True:
            n = self.pump(0.5)
            if n < 0 or not self.alive():
                return 'exit'
            m = BREAK.search(self.screen, mark)    # the debugger's code view redrawn on an int 3 (CD03)
            if not m and self.watch:                # or on one of our breakpoints (Session.bp)
                seg = re.sub(rb'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\(B', b' ', self.screen[mark:])
                for w in re.finditer(rb'0160:([0-9A-F]{8})\s', seg):
                    if int(w.group(1), 16) in self.watch:
                        m = w
                        break
            if m:
                self.eip = int(m.group(1), 16)
                return 'break'
            el = time.time() - start
            if self.shots and el >= nshot * self.shots:
                self.shot('t%04d' % int(time.time() - self.t0))
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


def run_case(name, exe_dir, cars, keys, timeout, shots=0, match=False, timer=False):
    """Run one key script on a copy of the game; returns a Result."""
    run, info = prepare(name, exe_dir, cars, steps_of(keys, TICKS if timer else RATE), match, timer)
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


class Screen:
    """The current menu read from a dump: entries [(index, text, invisible, disabled)], selected index."""

    def __init__(self, r, menu_off):
        m = r.base2 + menu_off
        mem = r.mem
        self.n = struct.unpack_from('<H', mem, m + 0x10)[0]
        sel = struct.unpack_from('<I', mem, m + 0x0C)[0]
        self.selected = (sel - m - 0x16) // 0x38 if sel else None
        self.entries, self.nav, self.geom = [], [], []
        for i in range(min(self.n, 120)):
            e = m + 0x16 + i * 0x38
            inv, dis = struct.unpack_from('<HH', mem, e + 4)
            self.nav.append((tuple(mem[e + 8:e + 12]), tuple(mem[e + 16:e + 20])))   # l/r/u/d, skip l/r/u/d
            self.geom.append(struct.unpack_from('<4h', mem, e + 0x14))                # x, y, width, height
            ptr = struct.unpack_from('<I', mem, e + 0x26)[0]
            text = ''
            if 0x1000 < ptr < len(mem) - 64:
                raw = mem[ptr:ptr + 40].split(b'\0')[0]
                if raw and all(32 <= b < 127 for b in raw):
                    text = raw.decode()
            self.entries.append((i, text, inv, dis))

    def find(self, text, visible=True, exact=False):
        """Index of the first entry whose text starts with (exact: is) `text`, visible ones only by default."""
        for i, t, inv, dis in self.entries:
            if (t == text if exact else t.startswith(text)) and (not visible or not inv):
                return i
        return None

    def path(self, target):
        """Keys from the selected entry to entry `target` (BFS on the entries' left/right/up/down links)."""
        if self.selected is None:
            return None
        prev, todo = {self.selected: None}, [self.selected]
        while todo:
            cur = todo.pop(0)
            if cur == target:
                keys = []
                while prev[cur]:
                    cur, k = prev[cur]
                    keys.append(k)
                return keys[::-1]
            links, skips = self.nav[cur] if cur < len(self.nav) else ((), ())
            for d, (k, nxt, alt) in enumerate(zip(('left', 'right', 'up', 'down'), links, skips)):
                if nxt < len(self.entries) and self.entries[nxt][2] and alt < len(self.entries):
                    nxt = alt                            # invisible neighbour: the game takes the skip entry
                hops = 0
                while nxt < len(self.entries) and self.entries[nxt][2] and hops < 8:
                    nxt = self.nav[nxt][0][d]            # ... or goes on in the same direction
                    hops += 1
                if nxt < len(self.entries) and nxt not in prev and not self.entries[nxt][2]:
                    prev[nxt] = (cur, k)
                    todo.append(nxt)
        return None

    def texts(self):
        return [t for _, t, inv, _ in self.entries if t and not inv]

    def __str__(self):
        return ' | '.join(('>' if i == self.selected else '') + t + ('(inv)' if inv else '')
                          for i, t, inv, _ in self.entries if t)


class Session:
    """Interactive run: the script pauses at each 'dump', the caller reads the screen and sends the next keys.

        with Session('name', build, cars, 'first keys dump:2') as s:
            while ...: scr = s.screen(); s.send('keys ... dump:1')
    """

    def __init__(self, name, exe_dir, cars, keys, timeout=60, shots=0):
        self.run, self.info = prepare(name, exe_dir, cars, steps_of(keys))
        self.timeout = timeout
        self.box = Dosbox(self.run, timeout, shots)
        self.result = None
        self.log = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.box.kill()
        open(os.path.join(self.run, 'debugger.raw'), 'wb').write(self.box.screen)
        open(os.path.join(self.run, 'session.log'), 'w').write('\n'.join(self.log) + '\n')

    def bp(self, lin, callback):
        """Debugger breakpoint at a linear address; callback(result) runs at each hit, then the game goes on."""
        self.box.cmd(f'BP 0160:{lin:08X}', 0.3)
        self.box.watch.add(lin)
        self.bps = getattr(self, 'bps', {})
        self.bps[lin] = callback

    def wait(self):
        """Run to the next break; returns the Result (outcome 'dump' = our pause, 'trap', 'timeout', 'exit')."""
        b = self.box
        if not hasattr(self, 'started'):
            self.started = True
            outcome = b.go()
        else:
            outcome = b.go_on()
        if os.environ.get('SWOSTEST_BP') and not getattr(self, 'bps', None) and outcome == 'break':
            base1 = Result(self.run, 'x', None, self.info).base1 if b.post_mortem() is not None else None
            self.bp_hits = {}
            for off in os.environ['SWOSTEST_BP'].split(','):     # counting breakpoints (use CORE=normal)
                o = int(off, 16)
                self.bp(base1 + o, lambda r, o=o: self.bp_hits.__setitem__(o, self.bp_hits.get(o, 0) + 1))
        while outcome == 'break' and b.eip in getattr(self, 'bps', {}):
            dump = os.path.join(self.run, 'MEMDUMP.BIN')
            if os.path.exists(dump):
                os.remove(dump)
            b.post_mortem()
            self.bps[b.eip](Result(self.run, 'bp', b.eip, self.info))
            pre = len(b.screen)
            b.cmd('BPLIST', 0.5)
            self.log.append('BPLIST: ' + re.sub(rb'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\(B', b' ', b.screen[pre:])
                            .decode('latin-1')[-300:])
            b.cmd('BPDEL *', 0.3)                     # re-arm: a DOSBox-X breakpoint may not survive its hit
            b.cmd('BPINT 3', 0.2)                      # (BPDEL * also removed the int 3 one)
            for lin in self.bps:
                b.cmd(f'BP 0160:{lin:08X}', 0.2)
            outcome = b.go_on()
        eip = None
        dump = os.path.join(self.run, 'MEMDUMP.BIN')
        if os.path.exists(dump):
            os.remove(dump)
        if outcome == 'break':
            eip = b.post_mortem()
            outcome = 'trap'
        elif outcome == 'timeout':
            b.shot('final')
        self.result = Result(self.run, outcome, eip, self.info)
        return self.result

    def screen(self):
        assert self.result.outcome == 'dump', str(self.result)
        return Screen(self.result, self.info['menu'])

    def send(self, keys):
        """Write the next steps into the stub's script area, point ptr at them, step over the int 3, resume."""
        r, b = self.result, self.box
        steps = steps_of(keys)
        assert len(steps) < SCRIPT_MAX
        data = b''.join(struct.pack('<HH', k, w) for k, w in steps) + b'\0' * 4
        base = r.base1 + self.info['script']
        for i in range(0, len(data), 16):
            b.cmd(f'SM 0168:{base + i:08X} ' + ' '.join(f'{x:02X}' for x in data[i:i + 16]), 0.2)
        b.cmd(f'SM 0168:{r.base1 + self.info["ptr"]:08X} ' + ' '.join(f'{x:02X}' for x in struct.pack('<I', base)), 0.2)
        b.cmd(f'SR EIP {r.base1 + self.info["brk"] + 2:X}', 0.3)   # int 3 = 2 bytes (CD 03)
        self.log.append(keys)
        return self.wait()


def press(s, scr, text, wait=2, exact=True):
    """Select the visible entry `text` (or entry number), check on the next pause that it is the selected one (a
    move can be taken twice), then fire; returns the new Result (None if not reachable)."""
    i = text if isinstance(text, int) else scr.find(text, exact=exact)
    if i is None:
        return None
    for _ in range(4):
        if scr.selected == i:
            return s.send(f'fire dump:{wait}')
        keys = scr.path(i)
        if not keys:
            return None
        if s.send(' '.join(keys) + ' dump:0.5').outcome != 'dump':
            return s.result
        scr = s.screen()
    return None


# Career "results only", the fast loop (Davide): career menu PARTITA -> VIS. RISULTATI -> ESCI -> PARTITA ...
# (PROSS. PARTITA only shows each match). The squad screen hides VIS. RISULTATI while an injured/suspended player is
# in the first 16: he must be swapped with one beyond the 16th (face of the player -> left, then fire on the name).


RED = lambda c: c[0] > 180 and c[1] < 90 and c[2] < 90   # red rows (237,76,61), red cards; not skin (255,109,0)


def squad_rows(s, scr, tag):
    """Screenshot of the paused game -> [(entry, unavailable)] for the squad rows (entries 25,y,82,8 sorted by y).
    Unavailable = red row background (x=100) or red pixels in the face/icon column (x 2-11): red card / injury."""
    from PIL import Image
    rows = sorted((g[1], i) for i, g in enumerate(scr.geom)
                  if (g[0], g[2], g[3]) == (25, 82, 8) and not scr.entries[i][1])   # drawn rows, not text copies
    path = os.path.join(s.run, 'shots', tag + '.png')
    for _ in range(10):                                # the window can be briefly uncapturable (display, Space)
        s.box.shot(tag)
        if os.path.exists(path):
            break
        time.sleep(3)
    im = Image.open(path).convert('RGB')
    w, h = im.size
    top = h - w * 400 // 640                           # window title bar
    px = lambda x, y: im.getpixel((min(w - 1, int(x * w / 320)), min(h - 1, int(top + y * (h - top) / 200))))
    out = []
    for y, i in rows:
        icon = sum(RED(px(x, y + dy)) for x in range(2, 12) for dy in range(1, 8))
        out.append((i, RED(px(100, y + 4)) or icon >= 16))     # faces have ~6 reddish points, red icons 20+
    return out


def substitute(s, scr, tries=16):
    """Squad screen without VIS. RISULTATI (Davide): an unavailable player (red row or red icon) among the first 16
    is swapped with a fit player beyond the 16th: fire on his row, fire on the 17th row's face until its player is
    fit (and a goalkeeper, P, for row 1), fire on the 17th row's name. Returns an error string or None."""
    rows = squad_rows(s, scr, f'sq{len(s.log):03d}')
    if len(rows) != 17:
        return f'squad screen: {len(rows)} rows'
    reserve = rows[-1][0]
    ry = scr.geom[reserve][1]
    face = next((i for i, (l, r) in enumerate(scr.nav) if l[1] == reserve and scr.geom[i][0] < 25), None)
    bad = [(k, i) for k, (i, un) in enumerate(rows[:16]) if un]
    if not bad or face is None:
        return f'squad screen without VIS. RISULTATI, unavailable rows {bad}, face {face}'
    for k, i in bad:
        press(s, s.screen(), i, wait=1)
        for _ in range(tries):
            press(s, s.screen(), face, wait=1)
            cur = s.screen()
            pos = next((t for j, t, inv, _ in cur.entries if t and not inv and cur.geom[j][:2] == (108, ry)), '')
            if not squad_rows(s, cur, f'sq{len(s.log):03d}')[-1][1] and (pos == 'P') == (k == 0):
                break
        else:
            return f'no fit reserve for row {k + 1}'
        press(s, s.screen(), reserve, wait=1)
    return None


def advance(s, stop, max_steps=400):
    """Press through the career until stop(screen) is true; returns (ok, message)."""
    for step in range(max_steps):
        r = s.result
        if r.outcome != 'dump':
            return False, f'step {step}: {r}'
        scr = s.screen()
        s.log.append(f'[{step}] {scr}')
        seen = s.log[-12::2] if len(s.log) > 12 else []
        if seen and len(set(seen)) == 1 and seen[0].startswith('['):
            return False, f'step {step}: stuck on {str(scr)[:200]}'
        if stop(scr):
            return True, f'{step} steps'
        texts = scr.texts()
        if 'VIS. RISULTATI' in texts:
            press(s, scr, 'VIS. RISULTATI') or s.send('fire dump:2')
        elif 'AMICHEVOLE' in texts and 'CONTINUA CARRIERA' in texts:     # main menu (after a save)
            press(s, scr, 'CONTINUA CARRIERA') or s.send('fire dump:2')
        elif 'MOD. TATTICA' in texts and 'AVVERSARI' in texts:          # squad screen without VIS. RISULTATI
            err = substitute(s, scr)
            if err:
                return False, f'step {step}: {err}'
        elif 'TRASFERIMENTI' in texts and 'PARTITA' in texts:
            press(s, scr, 'PARTITA') or s.send('fire dump:2')
        elif '- RISULTATO -' in texts:                   # cup round screen: -> squad screen
            press(s, scr, '- RISULTATO -') or s.send('fire dump:2')
        elif 'ESCI' in texts:
            press(s, scr, 'ESCI') or s.send('fire dump:2')
        else:
            s.send('fire dump:2')                        # message screens
    return False, f'no stop after {max_steps} steps'


CAR_FIXED = 95151                   # .CAR: fixed part (careerFileBuffer ..), then N cached teams + trailer
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


def next_season_save(s, name):
    """Season-end menu -> CONTINUA CARRIERA -> (messages) -> new season's career menu -> ESCI -> SALVA CARRIERA -> name.
    Returns the save path or an error string."""
    for _ in range(8):                                 # sacked: CONTINUA CARRIERA is disabled -> take a job offer
        scr = s.screen()
        i = scr.find('CONTINUA CARRIERA', exact=True)
        if i is not None and not scr.entries[i][3]:
            break
        s.log.append(f'[job] {scr}')
        if scr.find('ACCETTA', exact=True) is not None:      # the offer letter: accept it
            press(s, scr, 'ACCETTA', wait=3)
            continue
        rows = [j for j, g in enumerate(scr.geom) if g[0] == 8 and g[2] == 304 and not scr.entries[j][2]
                and not scr.entries[j][3]]             # the offers screen: one selectable row per offer
        if scr.find('OFF. LAVORO DA') is not None and rows:
            for _ in range(12):
                if s.screen().selected in rows:
                    break
                s.send('up dump:0.5')
            s.send('fire dump:2')                      # take the selected offer
        elif scr.find('OFFERTE LAVORO', exact=True) is not None and i is not None:
            press(s, scr, 'OFFERTE LAVORO')
        else:
            press(s, scr, 'ESCI') or s.send('fire dump:2')
        if s.result.outcome != 'dump':
            return f'job offer: {s.result}'
    if press(s, s.screen(), 'CONTINUA CARRIERA', wait=3) is None:
        return f'no CONTINUA CARRIERA on {s.screen()}'
    for _ in range(20):                                # chairman's note, job offers ...: CONTINUA / fire
        if s.result.outcome != 'dump':
            return f'new season: {s.result}'
        scr = s.screen()
        s.log.append(f'[ns] {scr}')
        if 'TRASFERIMENTI' in scr.texts():
            break
        press(s, scr, 'CONTINUA') or s.send('fire dump:2')
    else:
        return 'career menu of the new season not reached'
    press(s, s.screen(), 'ESCI', wait=3)
    if press(s, s.screen(), 'SALVA CARRIERA') is None:
        return f'no SALVA CARRIERA on {s.screen()}'
    s.send(name_entry(name) + ' dump:3')
    path = os.path.join(s.run, 'SWOS', name + '.CAR')
    return path if os.path.exists(path) else f'{name}.CAR not written ({s.result})'


@scenario
def italy_advance():
    """JUVEFIX3 (Juventus 1998/99 mid-season): results-only loop with substitutions to FINISCI STAGIONE, new season,
    save; next CC list: 16 distinct clubs incl. the Italian champion"""
    car = os.path.join(SAVES, 'JUVEFIX3.CAR')
    with Session('italy_advance', builds()['it'], {'JUVEFIX3.CAR': car}, 'dump:2', 180) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: no first pause ({s.result})'
        s.send('down down down down down fire dump:2')
        s.send('fire dump:2')
        ok, msg = advance(s, lambda scr: scr.find('FINISCI STAGIONE', exact=True) is not None)
        if not ok:
            return False, 'advance: ' + msg
        press(s, s.screen(), 'FINISCI STAGIONE', wait=3)
        if s.result.outcome != 'dump':
            return False, f'FINISCI STAGIONE: {s.result}'
        path = next_season_save(s, 'ADV1')
        if not path.endswith('.CAR'):
            return False, f'{msg}; {path}'
    info, errs = car_info(path), []
    lst = info['CC']
    check(info['sum'] == 0 and info['trailer'] == b'C7', f"sum {info['sum']}, trailer {info['trailer']!r}", errs)
    check(len(set(lst)) == 16, f'CC: {len(set(lst))} distinct {lst}', errs)
    check(any(f == 20 for f, o in lst), 'CC: no Italian club', errs)
    return not errs, f"{msg}; {'; '.join(errs) or 'ok'}; next CC {sorted(lst)} (Juventus 20,32 {'in' if (20, 32) in lst else 'out'})"


SLOT = 0x1A22C            # player's European slot buffer dseg_DA0E2 (DIY layout), IT obj2 offset in a0f38ad5 builds
HOLDERS = 0xC058B         # CC / CWC / UEFA holder team numbers (words, FFFF none), set at the season end, not saved


def slot_ties(r, n):
    """(round index, contest id, [(country a, country b)] of the first n ties) from the player's European slot."""
    d = r.obj2(SLOT, 0x443)
    team = lambda i: struct.unpack_from('<H', d, 0x24D + 2 * i)[0]
    ties = [(team(d[0x2CD + 2 * k]) & 0xFF, team(d[0x2CD + 2 * k + 1]) & 0xFF) for k in range(n)]
    return struct.unpack_from('<H', d, 0x57)[0], d[0x2D], ties


@scenario
def euro_draws():
    """JUVE2F 1997/98 end -> 1998/99: CC holder rule (next CC list) and no same-country ties in rounds 1-2 of the
    player's CWC/UEFA (euro9697-nodorby; obj2 offsets of build a0f38ad5)"""
    with Session('euro_draws', builds()['it'], {'JUVE2F.CAR': juve2(True)}, 'dump:2', 180) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: no first pause ({s.result})'
        s.send('down down down down down fire dump:2')
        s.send('fire dump:2')
        press(s, s.screen(), 'FINISCI STAGIONE', wait=3)
        if s.result.outcome != 'dump':
            return False, f'FINISCI STAGIONE: {s.result}'
        holders = struct.unpack_from('<3H', s.result.obj2(HOLDERS, 6))
        path = next_season_save(s, 'EUR1')
        if not path.endswith('.CAR'):
            return False, path
        if holders[0] in (0, 0xFFFF):                  # not set at the season-end menu: read again in the new season
            holders = struct.unpack_from('<3H', s.result.obj2(HOLDERS, 6))
        errs, notes = [], [f'holders CC/CWC/UEFA {[hex(h) for h in holders]}']
        lst = car_info(path)['CC']
        cc = holders[0]
        check(len(set(lst)) == 16, f'CC: {len(set(lst))} distinct', errs)
        if cc != 0xFFFF:
            check((cc & 0xFF, cc >> 8) in lst, f'CC holder {cc & 0xFF},{cc >> 8} not in the new CC list', errs)
            notes.append(f'holder country {cc & 0xFF} x{sum(f == cc & 0xFF for f, o in lst)} in the CC list')
        seen = {}

        def stop(scr):
            rnd, cid, ties = slot_ties(s.result, 16)
            title = scr.entries[0][1] if scr.entries else ''
            r2 = 'SECONDO TURNO' in title and ('EUFA' if cid == 2 else 'COPPE') in title   # that cup's round-2 screen
            if cid in (1, 2) and ((rnd == 0 and 0 not in seen and any(a or b for a, b in ties)) or (r2 and 1 not in seen)):
                k = 0 if rnd == 0 and not r2 else 1
                n = 16 if k == 0 else 8
                seen[k] = ties[:n]
                same = [j for j, (a, b) in enumerate(ties[:n]) if a == b]
                check(not same, f'round {k + 1} ({"CWC" if cid == 1 else "UEFA"}): same-country ties {same} '
                      f'{[ties[j] for j in same]} (screen: {title.strip()})', errs)
            return 1 in seen
        ok, msg = advance(s, stop)
        if not ok:
            return False, f"advance: {msg}; {'; '.join(errs + notes)}"
        hits = {f'obj1+{o:X}': n for o, n in getattr(s, 'bp_hits', {}).items()}
    return not errs, f"{msg}; {'; '.join(errs) or 'ok'}; {'; '.join(notes)}; rounds checked {sorted(seen)}; bp hits {hits}"


def checkw1(path):
    """internal/career-test/checkw1.py on a world save (DATA next to it); returns (ok, its output)."""
    r = subprocess.run([sys.executable, os.path.join(MAIN, 'internal', 'career-test', 'checkw1.py'), path],
                       capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    ok = r.returncode == 0 and 'W1 block: True' in out and 'bad pairs 0' in out
    for line in out.splitlines():
        if line.startswith(('CC ', 'CWC ', 'UEFA ')):
            ok = ok and line.endswith('dups 0')
    m = re.search(r'table sum mod 256 (\d+)', out)
    ok = ok and 'euro records k=128' in out and re.search(r'world byte 4\b', out) is not None
    return ok and m is not None and m.group(1) == '0', out


def season_over(scr):
    """FINISCI STAGIONE offered, or already the season-end menu (every match played: no FINISCI STAGIONE)."""
    return scr.find('FINISCI STAGIONE', exact=True) is not None or any('FINE CAMP' in t for t in scr.texts())


@scenario
def world8485():
    """Europe 1984-85 world (world 4): new career at Liverpool, two seasons (save, reload, save), checkw1 on both"""
    exe = os.environ.get('W8485_BUILD', os.path.join(WORK, 'builds', 'w8485'))
    out, msgs = [], []
    first = os.environ.get('W8485_FROM')                   # resume from a season-1 save (W84A.CAR)
    if first:
        out, msgs = [first], [f'season 1: from {first}']
    for season in ((2,) if first else (1, 2)):
        cars = {} if season == 1 else {'W84A.CAR': out[0]}
        with Session(f'world8485_{season}', exe, cars, 'dump:2', 240) as s:
            if s.wait().outcome != 'dump':
                return False, f'START: no first pause ({s.result})'
            if season == 1:
                for t in ('CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'ENGLAND', 'FIRST DIVISION', 'LIVERPOOL'):
                    if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                        return False, f'new career: {t} not reached ({s.result})'
            else:
                s.send('down down down down down fire dump:2')
                s.send('fire dump:3')
            ok, msg = advance(s, season_over, 900)
            if not ok:
                return False, f'season {season}: {msg}'
            if s.screen().find('FINISCI STAGIONE', exact=True) is not None:
                press(s, s.screen(), 'FINISCI STAGIONE', wait=3)
            if s.result.outcome != 'dump':
                return False, f'season {season} FINISCI STAGIONE: {s.result}'
            path = next_season_save(s, 'W84' + 'AB'[season - 1])
            if not path.endswith('.CAR'):
                return False, f'season {season}: {path}'
        good, report = checkw1(path)
        out.append(path)
        msgs.append(f'season {season}: {msg}, ' + ('checkw1 ok' if good else 'checkw1 FAIL'))
        open(os.path.join(WORK, 'runs', f'world8485_{season}', 'checkw1.txt'), 'w').write(report + '\n')
        if not good:
            return False, '; '.join(msgs) + '\n' + report
    return True, '; '.join(msgs)


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
        r = run_case(name, exe_dir, cars, keys, timeout, shots, '-match' in argv, '-timer' in argv)
        print(r, '->', r.run)
        return 0
    if argv[0] == 'run':
        names = argv[1:] or list(SCENARIOS)
        bad = 0
        for n in names:
            t = time.time()
            ok, msg = SCENARIOS[n]()
            if not ok and msg.startswith('START'):          # rare stall at the main menu (cause unknown): retry once
                print(f'RETRY {n}: {msg}', flush=True)
                ok, msg = SCENARIOS[n]()
            bad += not ok
            print(f'{"PASS" if ok else "FAIL"} {n} ({time.time() - t:.0f} s) {msg}', flush=True)
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
