"""SWOS regression harness: runs the game in a private DOSBox-X, feeds it a key script, checks the outcome.

  python3 tools/swostest.py list                     scenarios
  python3 tools/swostest.py run [-jN] [NAME...]      run scenarios (all when none given); exit code 1 on a failure;
        -jN = N scenarios at a time (own processes and run dirs; -j = 4)
  python3 tools/swostest.py keys EXE CAR|- 'KEYS' [-shots S] [-t T] [-name NAME] [-match] [-timer]
        ad-hoc run: EXE = a build dir (ITALIAN.EXE + DATA) or an .EXE file (DATA from c/SWOS); CAR = a save to copy
        in (or -); KEYS = the script below; window screenshots every S s into runs/NAME/shots; T = timeout (s);
        -timer = feed from the timer (70 Hz) instead of GetKey: for SWOS++, which re-patches the menu input code;
        waits are then game time, not menu frames (allow for loading);
        -name NAME = run dir (default keys); -match = the feeder also types during matches, replays and
        highlights (all 12 GetKey calls; waits then count in match frames too)
  Env: SWOSTEST_NOEXIT=1 = DOSBox-X stays at the DOS prompt when the game exits (see its last message: shots/final);
       SWOSTEST_BUILD = build dir under test, else SWOSTEST_BRANCH = git branch/commit to build, else this checkout;
       SWOSTEST_RUNS = run dirs (default internal/swostest/runs; another one = a second suite at the same time);
       TURBO=0 = real-time speed (default: DOSBox-X turbo, the emulated machine runs as fast as the host allows).

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
- DOSBox-X runs under a pty with -break-start and BPINT 3, core=dynamic, cycles=max, turbo: the mod's `int 3; jmp $`
  traps and the 'dump' step break into the debugger; the runner sees the code view (CD03), writes MEMDUMP.BIN and
  reads EIP; obj1/obj2 linear bases are found in the dump (they move with the exe size). No break before the timeout =
  hang or a script that went astray (runs/<name>/shots/final.png shows where).
- Speed (2026-10-11): all waits are game time (menu frames), and turbo runs it ~10x real time; a Session dumps the
  whole 32 MB only at its first pause (bases), then one ~1 MB dump per pause (stub page + obj2: menu, slots) and small
  ones on demand; debugger commands are typed in one go, short forms (~1 ms per char), no fixed sleeps.
- Oracles: saves written by the game, checked in Python (car_info, W1 block, cup lists), the outcome, the dump.
"""
import hashlib, os, pty, re, select, shutil, signal, struct, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN = os.path.expanduser('~/swos-mod')               # main checkout: c/, orig/, internal/ live there
WORK = os.path.join(MAIN, 'internal', 'swostest')
RUNS = os.environ.get('SWOSTEST_RUNS') or os.path.join(WORK, 'runs')   # run dirs (another one = a parallel suite)
DOSBOX = '/Applications/dosbox-x.app/Contents/MacOS/dosbox-x'
ISO = os.path.join(MAIN, 'orig', 'swos9697ita.iso')
BREAK = re.compile(rb'[0-9A-F]{4}:([0-9A-F]{8}) +' + (rb'[0-9A-F]{2}' if os.environ.get('SWOSTEST_BP4C') else
                                                     rb'(?:CD03|CC\s)'))   # mod traps CD 03, the game's own CC

CONF = """[sdl]
output=surface
[dosbox]
machine=svga_s3
memsize=32
[cpu]
core={core}
cputype=pentium
cycles={cycles}
turbo={turbo}
stop turbo on key=false
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
    run = os.path.join(RUNS, name)
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
        mov dword [ptr], script         ; the runner writes the next steps from the start of the script area
        int 3                           ; 'dump' step: the runner's BPINT 3 stops here (EIP in this page); to go
        jmp .go                         ; on, the runner sets EIP past it (and may write new steps)
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
    return {'page': page, 'size2': le.obj(2).vsize, 'calls': page + lab['calls'], 'code': (fixed, c[fixed:fixed + 48]), 'menu': curmenu[1],
            'brk': page + code.index(b'\xcd\x03'), 'ptr': page + lab['ptr'], 'script': page + lab['script'],
            'anchor': (anchor, d2[anchor:anchor + 64])}


ANSI = re.compile(rb'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\(B')
MEMSIZE = 0x2000000                                   # memsize=32: linear 0..32 MB


class Dosbox:
    """DOSBox-X under a pty: debugger reachable, int 3 traps caught."""

    def __init__(self, run, timeout, shots=0, exe='ITALIAN.EXE'):
        self.run, self.timeout, self.shots = run, timeout, shots
        conf = CONF if not os.environ.get('SWOSTEST_NOEXIT') else CONF.replace('{exe}\nexit\n', '{exe}\n')
        conf = conf.format(cycles=os.environ.get('CYCLES', 'max'), core=os.environ.get('CORE', 'dynamic'), iso=ISO,
                           exe=exe, turbo='false' if os.environ.get('TURBO') == '0' else 'true')
        open(os.path.join(run, 'test.conf'), 'w').write(conf)
        self.screen, self.eip, self.t0, self.watch = b'', None, time.time(), set()
        self.stats = {}                                # wall time per phase (s), shown in the session log
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(run)
            os.environ['TERM'] = 'xterm'
            os.execv(DOSBOX, [DOSBOX, '-conf', 'test.conf', '-fastlaunch', '-break-start',
                              '-time-limit', '100000000'])  # the runner kills it; the limit counts EMULATED
                                                        # seconds: 14400 ended turbo runs after ~4.5 real minutes

    def pump(self, t, until=None, start=None):
        """Read the debugger's output for up to t s; returns early once `until` (bytes regex, b'' = any output) shows
        up in the output after `start` (default: what is read from now on). Returns the bytes read, -1 if the process
        is gone."""
        end = time.time() + t
        got = 0
        start = len(self.screen) if start is None else start
        while True:
            left = end - time.time()
            if left <= 0:
                return got
            r, _, _ = select.select([self.fd], [], [], min(left, 0.05))
            if r:
                try:
                    b = os.read(self.fd, 65536)
                except OSError:
                    return -1                          # process gone
                if not b:
                    return -1
                self.screen += b
                got += len(b)
                if until is not None and re.search(until, ANSI.sub(b' ', self.screen[start:])):
                    return got

    def cmd(self, text, wait=1.0, until=None):
        pre = len(self.screen)
        os.write(self.fd, text.encode() + b'\r')
        return self.pump(wait, until, pre)

    def alive(self):
        pid, st = os.waitpid(self.pid, os.WNOHANG)
        if pid:                                        # gone: keep how (signal / exit code) for the session log
            self.status = (f'signal {os.WTERMSIG(st)}' if os.WIFSIGNALED(st) else f'exit code {os.WEXITSTATUS(st)}')
        return pid == 0

    def go(self):
        """Run until DOSBox-X exits ('exit'), an int 3 breaks into the debugger ('break': a trap or a 'dump' step) or
        the timeout ('timeout' = hang without a trap, or the script did not get where expected)."""
        self.pump(1)
        for _ in range(30):                            # under load the debugger may not take input yet
            pre = len(self.screen)
            self.cmd('BPINT 3', 1, rb'breakpoint at INT 03')
            if b'breakpoint at INT 03' in ANSI.sub(b'', self.screen[pre:]):
                break
        else:
            return 'timeout'
        return self.go_on()

    def go_on(self):
        """F5 (resume) and watch, as go()."""
        t = time.time()
        if os.environ.get('SWOSTEST_BP4C') and self.eip is not None and not getattr(self, 'bp4c', False):
            self.cmd('BPINT 21 4C', 1, rb'breakpoint at INT 21')    # debug: after the first pause, also stop on
            for x in ('00', '06', '0D', '0E'):                 # the DOS exit (int 21h, AH 4Ch) and on CPU
                self.cmd('BPINT ' + x, 0.5)                        # exceptions (any break: SWOSTEST_BP4C only)
            self.bp4c = True
        os.write(self.fd, b'C 160:0\r')        # move the code view away: the next break must redraw it
        pre = len(self.screen)
        os.write(self.fd, b'\x1b[15~')                 # F5 = run
        self.pump(2, rb'Running', pre)                 # watch from the debugger's '(Running)' on
        i = self.screen.find(b'Running', pre)
        mark = i + 7 if i >= 0 else len(self.screen)
        start, nshot = time.time(), 0
        while True:
            n = self.pump(0.25, b'')
            if n < 0 or not self.alive():
                for _ in range(20):                    # keep how DOSBox-X ended (exit code / signal) for the log
                    if not self.alive() or getattr(self, 'status', None):
                        break
                    time.sleep(0.1)
                return self.stat('run', t, 'exit')
            if n:
                m = BREAK.search(self.screen, mark)    # the debugger's code view redrawn on an int 3 (CD03)
                if not m and self.watch:               # or on one of our breakpoints (Session.bp)
                    seg = ANSI.sub(b' ', self.screen[mark:])
                    for w in re.finditer(rb'0160:([0-9A-F]{8})\s', seg):
                        if int(w.group(1), 16) in self.watch:
                            m = w
                            break
                if m:
                    self.pump(0.02)                    # the rest of the redraw
                    self.eip = int(m.group(1), 16)
                    return self.stat('run', t, 'break')
            el = time.time() - start
            if self.shots and el >= nshot * self.shots:
                self.shot('t%04d' % int(time.time() - self.t0))
                nshot += 1
            if el > self.timeout:
                return self.stat('run', t, 'timeout')

    def stat(self, k, t, ret=None):
        self.stats[k] = self.stats.get(k, 0) + time.time() - t
        return ret

    def dump(self, lin, n):
        """n bytes of linear memory from lin (debugger MEMDUMPBIN into the run dir, read back)."""
        t = time.time()
        path = os.path.join(self.run, 'MEMDUMP.BIN')
        if os.path.exists(path):
            os.remove(path)
        for attempt in range(3):                       # a command typed while the debugger redraws can be lost
            os.write(self.fd, f'MEMDUMPBIN 168:{lin:X} {n:X}\r'.encode())
            end = time.time() + 10 + n / 0x200000
            while not (os.path.exists(path) and os.path.getsize(path) >= n) and time.time() < end:
                self.pump(0.01)
            if os.path.exists(path) and os.path.getsize(path) >= n:
                break
        else:
            raise RuntimeError(f'MEMDUMPBIN {lin:X} {n:X}: no file')
        data = open(path, 'rb').read()
        self.stat('dump', t)
        return data

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

    def post_mortem(self, shot=True):
        """After a break: full memory dump (MEMDUMP.BIN = linear 0..32 MB, read by Result); returns the break EIP."""
        if shot:
            self.shot('final')
        self.dump(0, MEMSIZE)
        return self.eip

    def kill(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


# ----------------------------------------------------------------------------------------------------------- scenarios

class Result:
    """What a run left: outcome ('exit', 'dump', 'trap', 'timeout'), EIP, the game dir and the game's memory.
    Memory: the full dump MEMDUMP.BIN when there is one (obj1/obj2 linear bases found in it: they move with the exe's
    size), else read on demand from the paused game (box) at the bases a Session already knows; read() caches."""

    def __init__(self, run, outcome, eip, info, box=None, bases=None):
        self.run, self.game, self.outcome, self.eip = run, os.path.join(run, 'SWOS'), outcome, eip
        self.box, self.chunks, self._mem = box, [], None
        self.base1 = self.base2 = self.calls = None
        if bases:
            self.base1, self.base2 = bases
        else:
            path = os.path.join(run, 'MEMDUMP.BIN')
            if os.path.exists(path) and os.path.getsize(path) == MEMSIZE:
                self._mem = open(path, 'rb').read()
                off, chunk = info['code']
                self.base1 = self._mem.find(chunk) - off
                off, chunk = info['anchor']
                self.base2 = self._mem.find(chunk) - off
        if bases and box:                              # one dump: the stub's page + obj2 (adjacent; menus, slots)
            lo, hi = self.base1 + info['page'], self.base2 + info['size2']
            if 0 < hi - lo <= 0x200000:
                self.read(lo, hi - lo)
        if self.base1 is not None and (self._mem is not None or box):
            self.calls = struct.unpack('<I', self.obj1(info['calls'], 4))[0]
        if eip is not None and self.base1 is not None:
            rel = eip - self.base1
            if info['page'] <= rel < info['page'] + 0x1000:
                self.outcome = 'dump'

    @property
    def mem(self):
        """The whole 32 MB (dumped now if this result only reads ranges)."""
        if self._mem is None and self.box:
            self._mem = self.box.dump(0, MEMSIZE)
        return self._mem

    def read(self, lin, n):
        if self._mem is not None:
            return self._mem[lin:lin + n]
        for a, d in self.chunks:
            if a <= lin and lin + n <= a + len(d):
                return d[lin - a:lin - a + n]
        assert self.box, 'memory of a finished pause'
        d = self.box.dump(lin, n)
        self.chunks.append((lin, d))
        return d

    def cached(self, lin, n):
        return self._mem is not None or any(a <= lin and lin + n <= a + len(d) for a, d in self.chunks)

    def obj1(self, off, n):
        return self.read(self.base1 + off, n)

    def obj2(self, off, n):
        return self.read(self.base2 + off, n)

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
        self.n = struct.unpack('<H', r.read(m + 0x10, 2))[0]
        sel = struct.unpack('<I', r.read(m + 0x0C, 4))[0]
        self.selected = (sel - m - 0x16) // 0x38 if sel else None
        n = min(self.n, 120)
        mem = r.read(m, 0x16 + n * 0x38)
        ptrs = [struct.unpack_from('<I', mem, 0x16 + i * 0x38 + 0x26)[0] for i in range(n)]
        ptrs = [p if 0x1000 < p < MEMSIZE - 64 else 0 for p in ptrs]
        out = [p for p in ptrs if p and not r.cached(p, 40)]
        if out and max(out) - min(out) < 0x100000:     # texts outside the cached ranges: one dump for all
            r.read(min(out), max(out) + 40 - min(out))
        self.entries, self.nav, self.geom = [], [], []
        for i in range(n):
            e = 0x16 + i * 0x38
            inv, dis = struct.unpack_from('<HH', mem, e + 4)
            self.nav.append((tuple(mem[e + 8:e + 12]), tuple(mem[e + 16:e + 20])))   # l/r/u/d, skip l/r/u/d
            self.geom.append(struct.unpack_from('<4h', mem, e + 0x14))                # x, y, width, height
            text = ''
            if ptrs[i]:
                raw = r.read(ptrs[i], 40).split(b'\0')[0]
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
        el = time.time() - self.box.t0
        if getattr(self.box, 'status', None):
            self.log.append(f'DOSBox-X ended: {self.box.status}')
        self.log.append(f'{getattr(self, "steps", 0)} pauses in {el:.0f} s: ' +
                        ', '.join(f'{k} {v:.0f} s' for k, v in sorted(self.box.stats.items())))
        open(os.path.join(self.run, 'debugger.raw'), 'wb').write(self.box.screen)
        open(os.path.join(self.run, 'session.log'), 'w').write('\n'.join(self.log) + '\n')

    def bp(self, lin, callback):
        """Debugger breakpoint at a linear address; callback(result) runs at each hit, then the game goes on."""
        self.box.cmd(f'BP 0160:{lin:08X}', 0.3)
        self.box.watch.add(lin)
        self.bps = getattr(self, 'bps', {})
        self.bps[lin] = callback

    def wait(self):
        """Run to the next break; returns the Result (outcome 'dump' = our pause, 'trap', 'timeout', 'exit').
        The first pause dumps all memory (finds the obj1/obj2 bases); later pauses read only what is asked
        (Result.read: one dump of the stub page + obj2 up front, the rest on demand)."""
        b = self.box
        if self.result:
            self.result.box = None                     # its memory is gone once the game runs on
        if not hasattr(self, 'started'):
            self.started = True
            outcome = b.go()
        else:
            outcome = b.go_on()
        if os.environ.get('SWOSTEST_BP') and not getattr(self, 'bps', None) and outcome == 'break':
            base1 = self.paused('x', b.eip).base1
            self.bp_hits = {}
            for off in os.environ['SWOSTEST_BP'].split(','):     # counting breakpoints (use CORE=normal)
                o = int(off, 16)
                self.bp(base1 + o, lambda r, o=o: self.bp_hits.__setitem__(o, self.bp_hits.get(o, 0) + 1))
        while outcome == 'break' and b.eip in getattr(self, 'bps', {}):
            r = self.paused('bp', b.eip)
            self.bps[b.eip](r)
            r.box = None
            pre = len(b.screen)
            b.cmd('BPLIST', 0.5)
            self.log.append('BPLIST: ' + ANSI.sub(b' ', b.screen[pre:]).decode('latin-1')[-300:])
            b.cmd('BPDEL *', 0.3)                     # re-arm: a DOSBox-X breakpoint may not survive its hit
            b.cmd('BPINT 3', 0.2)                      # (BPDEL * also removed the int 3 one)
            for lin in self.bps:
                b.cmd(f'BP 0160:{lin:08X}', 0.2)
            outcome = b.go_on()
        self.steps = getattr(self, 'steps', 0) + 1
        if outcome == 'break':
            self.result = self.paused('trap', b.eip)   # Result turns it into 'dump' when EIP is in the stub
            if self.result.outcome != 'dump' and self.result._mem is None:
                b.post_mortem()                        # a real trap: full dump + screenshot for the post-mortem
                self.result = Result(self.run, 'trap', b.eip, self.info)
        else:
            if outcome == 'timeout':
                b.shot('final')
            dump = os.path.join(self.run, 'MEMDUMP.BIN')
            if os.path.exists(dump):
                os.remove(dump)                        # an older pause's dump
            self.result = Result(self.run, outcome, None, self.info)
        return self.result

    def paused(self, outcome, eip):
        """Result of the paused game: the first time a full dump (bases), then reads on demand."""
        if not getattr(self, 'bases', None):
            self.box.post_mortem(shot=False)
            r = Result(self.run, outcome, eip, self.info, self.box)
            self.bases = (r.base1, r.base2)
            return r
        return Result(self.run, outcome, eip, self.info, self.box, self.bases)

    def screen(self):
        assert self.result.outcome == 'dump', str(self.result)
        return Screen(self.result, self.info['menu'])

    def poke(self, lin, data):
        """Write bytes into the paused game's memory (debugger SM; the next read sees them)."""
        os.write(self.box.fd, f"SM 168:{lin:X} {' '.join(f'{x:X}' for x in data)}\r".encode())
        if self.result:
            self.result.chunks = []

    def send(self, keys):
        """Write the next steps into the stub's script area (ptr was reset to it by the pause), step over the int 3, resume
        (debugger commands typed in one go: DOSBox-X runs them in order before the F5)."""
        r, b = self.result, self.box
        t = time.time()
        steps = steps_of(keys)
        assert len(steps) < SCRIPT_MAX
        data = b''.join(struct.pack('<HH', k, w) for k, w in steps) + b'\0' * 4
        base = r.base1 + self.info['script']
        hexs = lambda d: ' '.join(f'{x:X}' for x in d)       # short forms: the debugger takes ~1 ms per typed char
        cmds = [f'SM 168:{base + i:X} {hexs(data[i:i + 16])}' for i in range(0, len(data), 16)]
        cmds.append(f'SR EIP {r.base1 + self.info["brk"] + 2:X}')   # int 3 = 2 bytes (CD 03)
        os.write(b.fd, ''.join(c + '\r' for c in cmds).encode())
        if os.environ.get('SWOSTEST_VERIFY'):          # read the script back (the SMs must have landed)
            got = b.dump(base, len(data))
            assert got == data, f'SM: wrote {data.hex()}, read {got.hex()}'
        b.stat('send', t)
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
    fit (and a goalkeeper, P, for row 1), fire on the 17th row's name. Row 1 first tries a fit goalkeeper of the bench
    (rows 12-16: a national squad may have only one goalkeeper beyond the 16th). Returns an error string or None."""
    pos_of = lambda cur, y: next((t for j, t, inv, _ in cur.entries if t and not inv and cur.geom[j][1] == y
                                  and 95 <= cur.geom[j][0] <= 125), '')     # the position text of the row at y
    for _ in range(8):                          # one swap per round, then look again
        cur = s.screen()
        rows = squad_rows(s, cur, f'sq{len(s.log):03d}')
        if len(rows) != 17:
            return f'squad screen: {len(rows)} rows'
        reserve = rows[-1][0]
        ry = cur.geom[reserve][1]
        face = next((i for i, (l, r) in enumerate(cur.nav) if l[1] == reserve and cur.geom[i][0] < 25), None)
        bad = [(k, i) for k, (i, un) in enumerate(rows[:16]) if un]
        if not bad:
            return None if 'VIS. RISULTATI' in cur.texts() else f'squad screen without VIS. RISULTATI, no unavailable row'
        if face is None:
            return f'squad screen: no face entry for the 17th row'
        k, i = bad[0]
        if k == 0:                              # the goalkeeper: a fit one from the bench?
            gk = rows[11][0] if not rows[11][1] else None   # row 12 = the reserve goalkeeper (SWOS squads; the rows'
                                                            # positions are drawn, not menu entries)
            if gk is not None:
                press(s, cur, i, wait=1)
                press(s, s.screen(), gk, wait=1)
                continue
        press(s, cur, i, wait=1)
        for _ in range(tries):
            press(s, s.screen(), face, wait=1)
            c2 = s.screen()
            if not squad_rows(s, c2, f'sq{len(s.log):03d}')[-1][1] and (pos_of(c2, ry) == 'P') == (k == 0):
                break
        else:
            return f'no fit reserve for row {k + 1}'
        press(s, s.screen(), reserve, wait=1)
    return 'squad screen: still unavailable players after 8 swaps'


def nat_callups(s, limit=120):
    """National team squad screen ('SQUADRA DEL ...', 'SCEGLI ALTRI N GIOCATORI ...'): add players from the home
    leagues' clubs (enabled player rows = eligible) until N is 0, then ESCI. Returns an error or None."""
    taken, clubs_done = set(), set()
    for _ in range(limit):
        scr = s.screen()
        texts = scr.texts()
        s.log.append(f'[callups] {scr}')
        need = next((int(m.group(1)) for t in texts for m in [re.match(r'SCEGLI ALTRI (\d+)', t)] if m), 0)
        if any(t.startswith('SQUADRA DEL ') for t in texts):
            if need == 0:
                press(s, scr, 'ESCI') or s.send('fire dump:2')
                return None
            s.squad_title = next(t for t in texts if t.startswith('SQUADRA DEL '))
            press(s, scr, 'AGGIUNGI GIOCATORE') or s.send('fire dump:2')
        elif 'AGGIUNGI GIOCA. INTERNAZIONALE (CASA)' in texts and len(texts) <= 4:
            if not hasattr(s, 'abroad'):        # once: the abroad chooser -> the world (CARR. STORICHE) -> its
                press(s, scr, next(t for t in texts if 'FUORI CASA' in t))   # countries, then back
                if press(s, s.screen(), 'CARR. STORICHE') is not None:
                    s.abroad = s.screen().texts()
                    s.log.append(f'[abroad] {s.screen()}')
                else:
                    s.abroad = []
                for _ in range(4):              # back to the squad screen
                    t2 = s.screen().texts()
                    if any(t.startswith('SQUADRA DEL ') for t in t2) or 'AGGIUNGI GIOCATORE' in t2:
                        break
                    sc2 = s.screen()
                    i = sc2.find('ABBANDONA', exact=True)
                    if i is None:
                        i = sc2.find('ESCI', exact=True)
                    if i is None:
                        s.send('esc dump:2')
                        continue
                    for _ in range(40):         # the country list: its links do not reach ESCI, walk down
                        if s.screen().selected == i:
                            break
                        s.send('down dump:0.3')
                    s.send('fire dump:2')
                continue
            press(s, scr, 'AGGIUNGI GIOCA. INTERNAZIONALE (CASA)')
        elif 'AGGIUNGI GIOCA. INTERNAZIONALE (CASA)' in texts and any('DIVISION' in t or 'LEAGUE' in t for t in texts) \
                and 'ABBANDONA' in texts:
            s.home_leagues = texts
            first = next(i for i, t, inv, dis in scr.entries if t and not inv and t != texts[0])
            press(s, scr, first)                # the top league
        elif 'AGGIUNGI GIOCA. INTERNAZIONALE (CASA)' in texts and 'ESCI' in texts and 'CONTINUA' in [
                t for _, t, _, _ in scr.entries]:   # a club's players
            club = scr.entries[1][1]
            rows = [i for i, t, inv, dis in scr.entries if scr.geom[i][0] == 8 and scr.geom[i][2] >= 304
                    and not inv and not dis and (club, scr.geom[i][1]) not in taken]
            if not rows:
                clubs_done.add(club)
                press(s, scr, 'ESCI') or s.send('fire dump:2')
                continue
            taken.add((club, scr.geom[rows[0]][1]))
            press(s, scr, rows[0], wait=1)
        elif any(t.startswith('AGGIUNGI GIOCA.') for t in texts):   # the clubs of the league
            if not hasattr(s, 'home_clubs'):
                s.home_clubs = texts
            club = next((t for i, t, inv, dis in scr.entries if t and not inv and not dis and i > 3
                         and t not in clubs_done and t not in ('ABBANDONA', 'ESCI') and scr.geom[i][2] > 60), None)
            if club is None:
                return f'call-ups: no club left ({need} players missing)'
            press(s, scr, club)
        else:
            press(s, scr, 'ESCI') or s.send('fire dump:2')
    return 'call-ups: too many steps'


def advance(s, stop, max_steps=400):
    """Press through the career until stop(screen) is true; returns (ok, message)."""
    recent = []
    for step in range(max_steps):
        r = s.result
        if r.outcome != 'dump':
            return False, f'step {step}: {r}'
        scr = s.screen()
        s.log.append(f'[{step}] {scr}')
        recent.append(str(scr))                          # stuck: the last 16 screens are 1 or 2 alternating ones
        if len(recent) >= 16 and len(set(recent[-16:])) <= 2:
            return False, f'step {step}: stuck on {" / ".join(sorted(set(recent[-16:])))[:300]}'
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
        elif any(t.startswith('SQUADRA DEL ') for t in texts) and 'ESCI' in texts:   # national call-ups
            err = nat_callups(s)
            if err:
                return False, f'step {step}: {err}'
        elif 'SCEGLI SQUADRA' in texts and 'VISUALIZZA MONDO' in texts and \
                scr.entries[scr.find('PARTITA', exact=True)][3]:   # national team menu: squad first
            press(s, scr, 'SCEGLI SQUADRA') or s.send('fire dump:2')
        elif ('TRASFERIMENTI' in texts or 'VISUALIZZA MONDO' in texts) and 'PARTITA' in texts:
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
    tmp = f'{path}.{os.getpid()}'
    open(tmp, 'wb').write(d)
    os.replace(tmp, path)                              # parallel runs: never a half-written save
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
        if 'TRASFERIMENTI' in scr.texts() or 'VISUALIZZA MONDO' in scr.texts():    # club / national team menu
            break
        if any(t.startswith('SQUADRA DEL ') for t in scr.texts()):    # national squad call-ups
            err = nat_callups(s)
            if err:
                return err
            continue
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
                       capture_output=True, text=True, env=dict(os.environ, CHECKW1_TOOLS=os.path.join(ROOT, 'tools')))
    out = (r.stdout + r.stderr).strip()
    if os.environ.get('W8485_SMALL'):              # a world with small cups (<= 80 European clubs): no W1 block
        return 'trailer end ok: True' in out and 'table sum mod 256 0' in out, out
    ok = r.returncode == 0 and 'W1 block: True' in out and 'bad pairs 0' in out
    for line in out.splitlines():
        if line.startswith(('CC ', 'CWC ', 'UEFA ')):
            ok = ok and line.endswith('dups 0')
    m = re.search(r'table sum mod 256 (\d+)', out)
    ok = ok and f"euro records k={os.environ.get('W8485_K', '128')}" in out and re.search(rf"world byte {os.environ.get('W8485_WNUM', '4')}\b", out) is not None
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
        with Session(f'world8485_{season}', exe, cars, 'dump:2', 240, int(os.environ.get('W8485_SHOTS', 0))) as s:
            if s.wait().outcome != 'dump':
                return False, f'START: no first pause ({s.result})'
            if season == 1:
                team = os.environ.get('W8485_TEAM', 'INGHILTERRA,FIRST DIVISION,LIVERPOOL').split(',')
                for t in ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', os.environ.get('W8485_WORLD', 'EUROPA 1984-85')] + team:
                    if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                        return False, f'new career: {t} not reached ({s.result})'
                if os.environ.get('W8485_START') == '1':          # menu check only: the career has started
                    return True, f'career started: {s.screen()}'[:400]
            else:
                s.send('down down down down down fire dump:2')
                s.send('fire dump:3')
            seen, errs = {}, []

            def stop(scr):                             # the player's European cup: no same-country tie in rounds 1-2
                rnd, cid, ties = slot_ties(s.result, 32)
                if struct.unpack_from('<H', s.result.obj2(SLOT, 2))[0] == 2:   # a league phase (type 2): no ties
                    return season_over(scr)
                title = scr.entries[0][1] if scr.entries else ''
                k = {0: 'PRIMO TURNO', 1: 'SECONDO TURNO'}.get(rnd)
                if cid <= 2 and k and k in title and (season, rnd) not in seen and any(a or b for a, b in ties):
                    n = struct.unpack_from('<H', s.result.obj2(SLOT + 0x31, 2))[0] >> (rnd + 1)
                    seen[season, rnd] = ties[:n]
                    same = [ties[j] for j in range(n) if ties[j][0] == ties[j][1]]
                    check(not same, f'season {season} cup {cid} round {rnd + 1}: same-country ties {same}', errs)
                return season_over(scr) or (r2only and (season, 1) in seen)
            r2only = os.environ.get('W8485_R2') == '1'         # stop once the player's round 2 is checked
            ok, msg = advance(s, stop, 900)
            if r2only:
                return (season, 1) in seen and not errs, f"season {season}: {msg}; {'; '.join(errs) or 'ok'}"

            msg += f', euro rounds checked {sorted(seen)}'
            if not ok or errs:
                return False, f"season {season}: {msg}; {'; '.join(errs)}"
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
        open(os.path.join(RUNS, f'world8485_{season}', 'checkw1.txt'), 'w').write(report + '\n')
        if not good:
            return False, '; '.join(msgs) + '\n' + report
    return True, '; '.join(msgs)


def nat_offsets(exe):
    """obj2 offsets in the exe under test: national competition copies (careerContests: EC 6, ECQ 7-14, WC 20,
    WCQ 21-28) and dseg_17A3CE (2 = the national team of the manager's nationality offers a job at once: debug)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    le = LE(open(exe, 'rb').read())
    d1, d2 = le.obj_bytes(1), le.obj_bytes(2)
    t2 = {f[1]: f[4] for f in le.fixups() if f[0] == 2 and f[3] == 2 and f[4] is not None}
    cc = next(o for o in sorted(t2) if struct.unpack_from('<H', d2, o + 8)[0] == 79
              and struct.unpack_from('<H', d2, o + 18)[0] == 92 and struct.unpack_from('<H', d2, o + 28)[0] == 92)
    copy = [t2[cc + 10 * k + 4] for k in range(34)]
    t1 = {f[1]: f[4] for f in le.fixups() if f[0] == 1 and f[3] == 2}
    m = re.search(rb'\x66\x83\x3d(.{4})\x13\x0f\x84.{4}\x66\x83\x3d(.{4})\x01\x0f\x84', d1, re.S)
    k = re.search(rb'\xa1(.{4})\xa3.{4}\x80\x3d.{4}\x50\x74.\xa1(.{4})\xa3', d1, re.S)   # cseg_5C304: dseg_C8B14 =
    return {'ec': copy[6], 'ecq': copy[7:15], 'wc': copy[20], 'wcq': copy[21:29], 'force': t1[m.start(2)],  # seasons
            'mask': t1[k.start(1)],
            'isnat': t1[re.search(rb'\x66\xa1(.{4})\x66\x0b\xc0\x74.\x80\x3d.{4}\x50\x75.\xe8', d1, re.S).start(1)],
            'flags': t1[re.search(rb'\xf6\x05(.{4})\x80\x74.\x66\xa1.{4}\x66\xa3(.{4})\xf6\x05\1\x40\x0f\x84', d1, re.S).start(1)],
            'd6cd0': t1[re.search(rb'\xf6\x05(.{4})\x80\x74.\x66\xa1.{4}\x66\xa3(.{4})\xf6\x05\1\x40\x0f\x84', d1, re.S).start(2)],
            'csd': t1[re.search(rb'\x66\xa1.{4}\x66\x0b\xc0\x75.\x66\x83\x3d(.{4})\x03\x72', d1, re.S).start(1)]}                       # (bits) a European national team may offer a job


def team_list(r, off):
    """Team words of a competition copy (list at +7 + [+7]; groups: count at +0Dh; cups: the first stage)."""
    hdr = r.obj2(off, 0x30)
    lst = off + 7 + hdr[7]
    n = hdr[13] if hdr[1] == 0 else hdr[15]       # groups: teams at +0Dh; cups: the first stage's teams (+0Fh)
    words = struct.unpack(f'<{n}H', r.obj2(lst, 2 * n))
    return [w for w in words if w] if hdr[1] else list(words)


def nat_names(build):
    """Team word -> name from the national files of the build (TEAM.180-185 stand for 080-085)."""
    out = {}
    for f in range(180, 186):
        d = open(os.path.join(build, 'DATA', 'TEAM.%03d' % f), 'rb').read()
        for i in range(struct.unpack('>H', d[:2])[0]):
            r = d[2 + i * 684:]
            out[r[0] | r[1] << 8] = r[5:22].split(b'\0')[0].decode('latin-1')
    return out


def nat_offer_save(exe, off, name='W84NAT', season=None, lefts=0):
    """Slow part, once per build (kept in internal/swostest/saves/W84NAT.CAR; W84NAT_REDO=1 makes it again): new
    career at St. Andrews (Malta: 10 clubs, a short season; low expectations), debug switches poked so that England offers its job at once, the
    offer kept (CONSIDERA: a national job is accepted at the season end), season played, saved at the season-end menu.
    lefts: the coach's nationality moved that many times left from ENG first (5 = GDR). Returns the save path or an
    error."""
    dst = os.path.join(WORK, 'saves', name + '.CAR')
    stamp = dst + '.exe'
    if os.path.exists(dst) and open(stamp).read() == md5(os.path.join(exe, 'ITALIAN.EXE')) \
            and not os.environ.get('W84NAT_REDO'):
        return dst
    with Session('world8485_natA', exe, {}, 'dump:2', 240) as s:   # season: currentSeasonShowing poked (cycles)
        if s.wait().outcome != 'dump':
            return f'START: no first pause ({s.result})'
        if press(s, s.screen(), 'CARRIERA') is None:
            return f'no CARRIERA ({s.result})'
        if lefts:
            i = s.screen().find('ENG', exact=True)
            if i is None or press(s, s.screen(), i, wait=0.5) is None:
                return f'no nationality field on {s.screen()}'
            s.send(' '.join(['fire+left:0.5'] * lefts) + ' dump:0.5')
            s.log.append(f'[nationality] {s.screen().entries[i][1]}')
        for t in ['SCEGLI SQUADRA', 'CARR. STORICHE', 'EUROPA 1984-85', 'MALTA',
                  'ST. ANDREWS']:              # Davide: a small league (18 matches) and a weak club (no sacking)
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return f'new career: {t} not reached ({s.result})'
        s.poke(s.result.base2 + off['force'], b'\x02')         # debug: the national team calls at once
        s.poke(s.result.base2 + off['mask'], b'\xff\xff\xff\x0f')   # in any season
        if season is not None:
            s.poke(s.result.base2 + off['csd'], struct.pack('<H', season))
        offer = lambda scr: 'TRASFERIMENTI' in scr.texts() and 'OFFERTE LAVORO' in scr.texts()
        ok, msg = advance(s, lambda scr: offer(scr) or season_over(scr), 600)
        if not ok or not offer(s.screen()):
            return f'no job offer ({msg})'
        err = nat_letter(s, 'CONSIDERA')
        if err:
            return err
        ok, msg = advance(s, season_over, 600)
        if not ok:
            return 'season 1: ' + msg
        if s.screen().find('FINISCI STAGIONE', exact=True) is not None:
            press(s, s.screen(), 'FINISCI STAGIONE', wait=3)
        if press(s, s.screen(), 'SALVA CARRIERA') is None:
            return f'no SALVA CARRIERA on {s.screen()}'
        s.send(name_entry(name) + ' dump:3')
        path = os.path.join(s.run, 'SWOS', name + '.CAR')
        if not os.path.exists(path):
            return f'{name}.CAR not written ({s.result})'
    shutil.copy(path, dst)
    open(stamp, 'w').write(md5(os.path.join(exe, 'ITALIAN.EXE')))
    return dst


def nat_letter(s, button):
    """Career menu with a job offer -> OFFERTE LAVORO -> the national offer's row -> the letter -> button (CONSIDERA
    during the season, ACCETTA at its end) -> back to the menu. Returns an error or None."""
    if press(s, s.screen(), 'OFFERTE LAVORO') is None:
        return f'no OFFERTE LAVORO on {s.screen()}'
    scr = s.screen()
    rows = [j for j, g in enumerate(scr.geom) if g[0] == 8 and g[2] == 304 and not scr.entries[j][2]
            and not scr.entries[j][3]]               # one selectable row per offer (as next_season_save)
    if scr.find('OFFERTA DI LAVORO INTERNAZIONALE', exact=False) is None or not rows:
        return f'no national offer on {scr}'
    s.offer = next(t for t in scr.texts() if t.startswith('OFFERTA DI LAVORO INTERNAZIONALE'))
    for _ in range(12):
        if s.screen().selected in rows:
            break
        s.send('up dump:0.5')
    s.send('fire dump:2')
    scr = s.screen()
    s.log.append(f'[letter] {scr}')
    i = scr.find(button, exact=True)
    if i is None or scr.entries[i][3]:
        return f'{button} not available on {scr}'
    press(s, scr, button, wait=3)
    for _ in range(6):
        if 'TRASFERIMENTI' in s.screen().texts() or 'CONTINUA CARRIERA' in s.screen().texts():
            return None
        press(s, s.screen(), 'ESCI') or s.send('fire dump:2')
    return f'after {button}: {s.screen()}'


@scenario
def world8485_nat():
    """Europe 1984-85 world, national teams (England's job by the debug switch; saves W84NAT / W84NAT3 made once per
    build): the real Euro 88 qualifying groups and Euro 88's 8 (host + 7 group winners); with the season index poked
    to the next cycle, the Italia 90 qualifying draw (host out) and its 24 (holder, host, 13 European, direct)"""
    exe = os.environ.get('W8485_BUILD', os.path.join(WORK, 'builds', 'w8485'))
    off, names = nat_offsets(os.path.join(exe, 'ITALIAN.EXE')), nat_names(exe)
    nm = lambda ws: [names.get(w, hex(w)) for w in ws]
    errs, notes = [], []
    real = [{'SPAIN', 'ROMANIA', 'AUSTRIA', 'ALBANIA'}, {'ITALY', 'SWEDEN', 'PORTUGAL', 'SWITZERLAND', 'MALTA'},
            {'SOVIET UNION', 'EAST GERMANY', 'FRANCE', 'ICELAND', 'NORWAY'},
            {'ENGLAND', 'YUGOSLAVIA', 'NORTHERN IRELAND', 'TURKEY'}, {'HOLLAND', 'GREECE', 'HUNGARY', 'POLAND', 'CYPRUS'},
            {'DENMARK', 'CZECHOSLOVAKIA', 'WALES', 'FINLAND'},
            {'REPUBLIC IRELAND', 'BULGARIA', 'BELGIUM', 'SCOTLAND', 'LUXEMBOURG'}, set()]

    def england(name, season, seasons, lefts=0):
        """Load the save, accept the national offer; returns the Session (open)."""
        car = nat_offer_save(exe, off, name, season, lefts)
        if not car.endswith('.CAR'):
            raise RuntimeError(f'{name}: {car}')
        s = Session(f'world8485_nat_{name}', exe, {name + '.CAR': car}, 'dump:2', 240)
        if s.wait().outcome != 'dump':
            raise RuntimeError(f'START: no first pause ({s.result})')
        s.send('down down down down down fire dump:2')
        s.send('fire dump:3')
        err = nat_letter(s, 'ACCETTA')
        if err:
            raise RuntimeError(err)
        return s

    def season_end(s, label):
        ok, msg = advance(s, season_over, 600)
        if not ok:
            raise RuntimeError(f'{label}: {msg}')
        if s.screen().find('FINISCI STAGIONE', exact=True) is not None:
            press(s, s.screen(), 'FINISCI STAGIONE', wait=3)

    def after_end(s):
        """Season-end menu -> CONTINUA CARRIERA (enabled by a poke when the manager was sacked: only the season-end
        processing matters) -> the first screen after it (the national finalists are chosen there)."""
        for _ in range(6):                        # chairman's notes first
            scr = s.screen()
            i = scr.find('CONTINUA CARRIERA', exact=True)
            if i is not None:
                break
            press(s, scr, 'CONTINUA') or s.send('fire dump:2')
        else:
            raise RuntimeError(f'no CONTINUA CARRIERA on {scr}')
        if scr.entries[i][3]:
            s.poke(s.result.base2 + s.info['menu'] + 0x16 + i * 0x38 + 6, b'\0\0')
            s.send('dump:0.5')
        press(s, s.screen(), 'CONTINUA CARRIERA', wait=3)
        for _ in range(10):                       # chairman's opinion, then the season end runs
            scr = s.screen()
            if 'VISUALIZZA MONDO' in scr.texts() or any(t.startswith('SQUADRA DEL ') for t in scr.texts()):
                break
            press(s, scr, 'CONTINUA') or s.send('fire dump:2')

    def callups(s):
        """National team menu -> SCEGLI SQUADRA -> call-ups (records home leagues, the abroad chooser, the title)."""
        for _ in range(8):                        # from the main menu (after the save): back into the career
            texts = s.screen().texts()
            if 'SCEGLI SQUADRA' in texts:
                break
            press(s, s.screen(), 'CONTINUA CARRIERA' if 'CONTINUA CARRIERA' in texts else 'CONTINUA') \
                or s.send('fire dump:2')
        if press(s, s.screen(), 'SCEGLI SQUADRA') is None:
            raise RuntimeError(f'no SCEGLI SQUADRA on {s.screen()}')
        err = nat_callups(s)
        if err:
            raise RuntimeError(err)

    def new_season(s, label):
        path = next_season_save(s, 'W84NN')
        if not path.endswith('.CAR'):
            raise RuntimeError(f'{label}: {path}')

    with Session('world8485_nat_menu', exe, {}, 'dump:2', 120) as s:   # the coach's nationalities: + YUG, URS, GDR
        if s.wait().outcome != 'dump' or press(s, s.screen(), 'CARRIERA') is None:
            return False, f'START: {s.result}'
        i = s.screen().find('ENG', exact=True)
        seen = []
        if i is not None and press(s, s.screen(), i, wait=0.5) is not None:   # (fire on the field = right)
            for _ in range(5):
                s.send('fire+left dump:0.5')
                seen.append(s.screen().entries[i][1])
        notes.append(f'coach nationalities before ENG: {seen}')
        check(seen[-4:] == ['YUG', 'RFT', 'URS', 'RDT'], f'coach nationalities: {seen}', errs)   # Italian exe
    try:
        with england('W84NAT', None, 2) as s:             # Euro 88
            check(s.offer.endswith('ENG'), f'offer: {s.offer}', errs)
            new_season(s, '1985-86')
            callups(s)
            notes.append(f"call-ups: {getattr(s, 'squad_title', '?')}, home {getattr(s, 'home_leagues', '?')}, "
                         f"abroad {getattr(s, 'abroad', '?')}")
            check('FIRST DIVISION' in getattr(s, 'home_leagues', []), 'England: home call-ups not from the world', errs)
            ab = getattr(s, 'abroad', [])
            check('GERMANIA EST' in ab and 'URSS' in ab and not {'CROAZIA', 'UCRAINA'} & set(ab),
                  f'call-ups abroad: not the world 1984-85 ({ab})', errs)
            season_end(s, '1985-86')
            new_season(s, '1986-87')
            groups = [nm(team_list(s.result, o)) for o in off['ecq']]
            notes.append(f'Euro 88 qualifying {groups}')
            check([set(g) for g in groups] == real, 'Euro 88 qualifying groups are not the real ones', errs)
            season_end(s, '1986-87')
            after_end(s)
            ec = nm(team_list(s.result, off['ec']))
            notes.append(f'Euro 88 {ec}')
            check(len(ec) == 8 and ec[0] == 'WEST GERMANY' and all(sum(t in g for t in ec) == 1 for g in real[:7]),
                  f'Euro 88: {ec}', errs)
            season_end(s, '1987-88 (Euro 88 played)')     # the 8-team format: groups, semi-finals, final
            after_end(s)
            notes.append(f'after Euro 88: {str(s.screen())[:60]}')
            mid = os.path.join(s.run, 'SWOS', 'W84NN.CAR')   # saved at the start of 1986-87 (Euro 88 qualifying)
        with Session('world8485_nat_reload', exe, {'W84NN.CAR': mid}, 'dump:2', 240) as s:   # national career reload
            if s.wait().outcome != 'dump':
                raise RuntimeError(f'reload: no first pause ({s.result})')
            s.send('down down down down down fire dump:2')
            s.send('fire dump:3')
            for _ in range(6):
                if 'VISUALIZZA MONDO' in s.screen().texts():
                    break
                press(s, s.screen(), 'CONTINUA') or s.send('fire dump:2')
            groups = [nm(team_list(s.result, o)) for o in off['ecq']]
            check('ENGLAND' in s.screen().texts() and [set(g) for g in groups] == real,
                  f'reloaded national career: {str(s.screen())[:80]} groups {groups}', errs)
            notes.append(f'reloaded mid-qualifying: {str(s.screen())[:40]}')
        with england('W84GDR', None, 1, lefts=5) as s:   # an East German coach: the GDR job, DDR-Oberliga call-ups
            check(s.offer.endswith('EAS'), f'GDR coach: offer {s.offer}', errs)   # the game: 3 letters of the name
            new_season(s, 'GDR 1985-86')
            callups(s)
            notes.append(f"GDR: {s.offer}, {getattr(s, 'squad_title', '?')}, home clubs {getattr(s, 'home_clubs', '?')}")
            check(getattr(s, 'squad_title', '') == 'SQUADRA DEL EAST GERMANY'      # one league: straight to its clubs
                  and 'DYNAMO DRESDEN' in getattr(s, 'home_clubs', []), 'GDR job / call-ups', errs)
        with england('W84NAT3', 3, 1) as s:               # next cycle: Italia 90
            new_season(s, 'WC 1990 qualifying')
            groups = [nm(team_list(s.result, o)) for o in off['wcq']]
            notes.append(f'WC 1990 qualifying {groups}')
            flat = [t for g in groups for t in g]
            check(len(flat) == len(set(flat)) and 'ITALY' not in flat and len(flat) == 32 and 'ENGLAND' in flat,
                  f'WC 1990 qualifying: {len(flat)} teams', errs)
            season_end(s, 'WC 1990 qualifying')
            after_end(s)
            wc = nm(team_list(s.result, off['wc']))
            notes.append(f'WC 1990 {wc}')
            check(len(wc) == 24 and len(set(wc)) == 24 and wc[0] == 'ITALY' and 'ARGENTINA' in wc,
                  f'WC 1990: {len(wc)} teams', errs)
            season_end(s, '1989-90 (WC 1990 played)')     # 24 teams, 6 groups, best thirds, knockout
            after_end(s)
            holder = nm([struct.unpack('<H', s.result.obj2(off['d6cd0'], 2))[0]])[0]
            notes.append(f'WC 1990 winner (new holder): {holder}')
            check(holder in wc, f'WC 1990 winner {holder} is not one of the 24', errs)
    except RuntimeError as e:
        return False, f'{e}; ' + '; '.join(errs + notes)
    return not errs, '; '.join(errs + notes)


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


def play_preset(s, button, max_steps=400, start='TORNEO'):
    """PRESET COMPETITION > CLASSIC TOURNEYS > button, all teams by the computer, every match by results only, to the
    end (start: TORNEO, or LEGA for a league). Returns (ok, message, rounds [(title, [(home, away)])], coin texts);
    s.matches = the matches played (PROSS. PARTITA / REPLAY presses)."""
    s.matches = 0
    for t in ('COMP. PREDEFINITA', 'TORNEI STORICI', button, start):
        if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
            return False, f'{t} not reached ({s.result})', [], []
    rounds, coins, title = [], [], None
    for k in range(max_steps):
        if s.result.outcome != 'dump':
            return False, f'{s.result} after {len(rounds)} rounds', rounds, coins
        scr = s.screen()
        vis = [t for _, t, inv, _ in scr.entries if t and not inv]
        coins += [t.strip() for t in vis if 'SORTEGGIO' in t and t.strip() not in coins]
        if scr.entries[0][1] != title:
            title = scr.entries[0][1]
            names = vis[vis.index('ESCI') + 1:]
            pairs = [(names[j + 1], names[j + 2]) for j in range(len(names) - 2) if names[j] in ('C', '-')]
            rounds.append((title.strip(), pairs))
        for want in ('VIS. RISULTATI', 'REPLAY', 'PROSS. PARTITA', 'PROSSIMO TURNO', 'TURNO RITORNO', 'CONTINUA', 'OK'):
            i = scr.find(want, exact=True)
            if i is not None:
                s.matches += want in ('PROSS. PARTITA', 'REPLAY')
                break
        else:
            end = 'FINALE' in title or (start == 'LEGA' and vis[1:3] == ['STAT', 'ESCI'])
            return end, f"{len(rounds)} rounds, last {title.strip()!r}" + ('' if end else f" ({' | '.join(vis)})"), rounds, coins
        press(s, scr, i, wait=3)
    return False, f'no end in {max_steps} steps', rounds, coins


@scenario
def classic_wc34():
    """3.2 tourney pack: World Cup 1934 in CLASSIC TOURNEYS, the real bracket (R1 ties of ties.csv, each later tie =
    winners of two adjacent ties, also after replays), replays + coin toss, third place, final"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import mkseason
    pk = mkseason.Pack(os.path.join(ROOT, 'packs', 'world-cup-1934'))
    name = {k: c['name'] for k, c in pk.clubs.items()}
    r1 = [(name[x['home']], name[x['away']]) for x in pk.ties['wc34'] if x['round'] == '1']
    with Session('classic_wc34', builds()['it'], {}, 'dump:2', 900) as s:
        s.wait()
        ok, msg, rounds, coins = play_preset(s, 'COPPA MONDIALE 1934')
    errs = []
    main = [(t, p) for t, p in rounds if not re.search(r' (I )?R(E|$)', t) and 'SPAREGGIO' not in t]   # replays: 'I REPLA'...
    check([t for t, _ in main] == ['COPPA MONDIALE 1934 ' + x for x in
                                   ('PRIMO TURNO', 'QUARTI FINALE', 'SEMIFINALE', 'FINALE')], f'rounds {[t for t, _ in main]}', errs)
    check(main and main[0][1] == r1[:len(main[0][1])], f'round 1 {main[0][1] if main else None} != ties.csv', errs)
    if main:
        main[0] = (main[0][0], r1)                   # (the screen lists 6 ties; the rest is ties.csv, checked above)
    for (_, before), (t, after) in zip(main, main[1:]):
        for k, (h, a) in enumerate(after):          # tie k of a round: one winner of tie 2k and one of tie 2k+1 before
            sides = [set(before[2 * k]), set(before[2 * k + 1])] if 2 * k + 1 < len(before) else []
            check(sides and len({h, a} & sides[0]) == 1 and len({h, a} & sides[1]) == 1,
                  f'{t} tie {k + 1} {h}-{a}: not winners of ties {2 * k + 1}, {2 * k + 2}', errs)
    third = [p for t, p in rounds if 'SPAREGGIO 3' in t]
    check(bool(third), 'no third-place match', errs)
    return ok and not errs, f"{msg}; {' > '.join(f'{t[20:]}: {p}' for t, p in main)}; third {third[:1]}; coin {coins}; " + '; '.join(errs)


@scenario
def classic_groups():
    """3.2 tourney pack with groups (packs/_template_tourney, test build only): 2 groups of 4, semi-finals from
    1A-2B / 1B-2A (each semi-final: one team of each group), third place, final; its round robin (5 clubs, home and
    away: 20 matches) in CLASSIC TOURNEYS"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import mkseason
    pk = mkseason.Pack(os.path.join(ROOT, 'packs', '_template_tourney'))
    names = [c['name'] for c in pk.clubs.values()]
    names = [c['name'] for c in pk.clubs.values() if c['file'] == 'teams']
    ga, gb = set(names[:4]), set(names[4:])
    exe = build('tourney_groups', env={'SEASON_PACKS': 'ddr-1988-89,world-cup-1934,' + os.path.join(ROOT, 'packs', '_template_tourney')})
    with Session('classic_groups', exe, {}, 'dump:2', 900) as s:
        s.wait()
        ok, msg, rounds, coins = play_preset(s, 'TORNEO ESEMPIO 1960')
    errs = []
    semi = [p for t, p in rounds if 'SEMIFINALE' in t]
    check(bool(semi) and len(semi[0]) == 2, f'semi-finals {semi}', errs)
    for h, a in (semi[0] if semi else []):
        check(len({h, a} & ga) == 1 and len({h, a} & gb) == 1, f'semi-final {h}-{a}: not one team of each group', errs)
    check(any('SPAREGGIO 3' in t for t, _ in rounds), 'no third-place match', errs)
    with Session('classic_league', exe, {}, 'dump:2', 900) as s:     # the template's round robin, home and away
        s.wait()
        ok2, msg2, _, _ = play_preset(s, 'GIRONE ESEMPIO 1960', start='LEGA')
        n = len([k for k, c in pk.clubs.items() if c['file'] == 'league'])
        check(ok2 and s.matches == n * (n - 1), f'round robin: {msg2}, {s.matches} matches (want {n * (n - 1)})', errs)
    return ok and not errs, (f"{msg}; rounds {[t[19:] for t, _ in rounds]}; semi {semi[:1]}; round robin {n} clubs, "
                             f"{s.matches} matches; " + '; '.join(errs))


@scenario
def classic_tourneys():
    """CLASSIC TOURNEYS of 2.0 still play to the final (hist_draw changed in 3.2): World Cup 1982, Mitropa 1934, FA Cup 1871-72"""
    out, good = [], True
    for button in ('COPPA MONDIALE 1982', 'COPPA MITROPA 1934', 'FA CUP 1871-72'):
        with Session('classic_' + button.split()[-1].replace('-', ''), builds()['it'], {}, 'dump:2', 900) as s:
            s.wait()
            ok, msg, rounds, coins = play_preset(s, button, 600)
        if button == 'COPPA MITROPA 1934':          # the real bracket also after play-offs (3.2 sort flag)
            sys.path.insert(0, os.path.join(ROOT, 'tools'))
            import historic
            first = [t for t, p in rounds if 'ANDAT' in t and 'REPLAY' not in t]
            legs = {t: p for t, p in rounds}
            main = [legs[t] for t in first]
            r1 = [(historic.M34[2 * k][2], historic.M34[2 * k + 1][2]) for k in range(8)]
            if main and main[0] == r1[:len(main[0])]:
                main[0] = r1
            for before, after in zip(main, main[1:]):
                for k, (h, a) in enumerate(after):
                    sides = [set(before[2 * k]), set(before[2 * k + 1])] if 2 * k + 1 < len(before) else []
                    if not (sides and len({h, a} & sides[0]) == 1 and len({h, a} & sides[1]) == 1):
                        ok, msg = False, msg + f'; Mitropa {h}-{a}: not the winners of ties {2 * k + 1}, {2 * k + 2}'
            msg += f'; Mitropa rounds {[t[19:] for t, _ in rounds]}, first legs {main}'
        good &= ok
        out.append(f"{button}: {'ok' if ok else 'FAIL'} {msg}, {len(coins)} coin tosses")
    return good, '; '.join(out)


@scenario
def lp36_tourney():
    """UEFA league phase (tools/lp36.py; private test pack internal/world2526/lp36, PROTO36 build): the 36 clubs of the
    2025-26 Champions League in CLASSIC TOURNEYS. The game's own draw (calendar read in memory: every UEFA rule),
    8 matchdays = the draw, the 1-36 table pages, the final ranking recomputed from memory with the UEFA criteria,
    play-offs 9-24 (seeded pairs), round of 16 (seeded clubs v the play-off winners of their pair), bracket to the final"""
    import csv
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lib97
    import lp36
    from le import LE
    pack = os.path.join(MAIN, 'internal', 'world2526', 'lp36')
    if not os.path.isdir(pack):
        return True, 'SKIP: private pack internal/world2526/lp36 missing'
    clubs = list(csv.DictReader(open(os.path.join(pack, 'clubs.csv'))))
    names, cc = [c['name'] for c in clubs], [c['country'] for c in clubs]
    exe = build('lp36', env={'PROTO36': '1', 'SEASON_PACKS': 'ddr-1988-89,world-cup-1934,' + pack})

    class _P:
        pass
    op = _P()
    op.le = LE(open(os.path.join(ROOT, 'orig', 'ITALIAN.EXE'), 'rb').read())
    diy = lib97._sites(op)[3] + 0x41F
    errs, cal, rows, aw, rounds, heads = [], None, None, None, {}, set()
    with Session('lp36_tourney', exe, {}, 'dump:2', 1800) as s:
        s.wait()
        for t in ('COMP. PREDEFINITA', 'TORNEI STORICI', 'CHAMPIONS LEAGUE 2025-26', 'TORNEO'):
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'{t} not reached ({s.result})'
        for k in range(900):
            if s.result.outcome != 'dump':
                return False, f'{s.result} at step {k}'
            scr = s.screen()
            vis = [t for _, t, inv, _ in scr.entries if t and not inv]
            title = vis[0].replace('CHAMPIONS LEAGUE 2025-26', '').strip()
            if title.startswith('PRIMO'):
                heads |= {t for t in vis if t.startswith('CLASSIFICA')}
                b = s.result.obj2(diy, 0x733)
                if cal is None:
                    cal = [(b[lp36.CAL_OFF + 2 * i], b[lp36.CAL_OFF + 2 * i + 1]) for i in range(144)]
                rows = [struct.unpack_from('<7H', b, lp36.ROW + 4 + 18 * r) for r in range(36)]
                aw = (b[lp36.AWAY_GF:lp36.AWAY_GF + 36], b[lp36.AWAY_GF + 36:lp36.AWAY_GF + 72])
            key = title.split()[0] + (' ' + title.split()[1] if title.split()[0] in ('SECONDO', 'TERZO') else '')
            for j in range(len(vis) - 2):
                if vis[j] in ('C', '-') and vis[j + 1] in names and vis[j + 2] in names:
                    r = rounds.setdefault(key, [])
                    p = (vis[j + 1], vis[j + 2])
                    if p not in r and p[::-1] not in r:
                        r.append(p)
            for want in ('VIS. RISULTATI', 'PROSS. PARTITA', 'PROSSIMO TURNO', 'TURNO RITORNO', 'CONTINUA', 'OK'):
                i = scr.find(want, exact=True)
                if i is not None:
                    break
            else:
                break
            press(s, scr, i, wait=3)
    try:
        lp36.check(cal, cc)
    except AssertionError as e:
        errs.append(f'draw breaks a rule: {e}')
    played = [(names.index(h), names.index(a)) for h, a in rounds.get('PRIMO', [])]
    check(played and all(m in cal for m in played), f'league-phase fixtures not in the draw: {[m for m in played if m not in cal][:4]}', errs)
    check(all(r[0] == 8 for r in rows), f'played {[r[0] for r in rows]}', errs)
    check(heads == {'CLASSIFICA 1-18', 'CLASSIFICA 19-36'}, f'table headers {heads}', errs)
    pts = [r[6] for r in rows]
    gd = [r[4] - r[5] for r in rows]
    opp = {x: [] for x in range(36)}
    for h, a in cal:
        opp[h].append(a)
        opp[a].append(h)
    key = lambda r: (pts[r], gd[r], rows[r][4], aw[0][r], rows[r][1], aw[1][r], sum(pts[o] for o in opp[r]),
                     sum(gd[o] for o in opp[r]), sum(rows[o][4] for o in opp[r]), -r)
    rank = sorted(range(36), key=key, reverse=True)
    place = {names[r]: k + 1 for k, r in enumerate(rank)}
    po = rounds.get('SECONDO TURNO', [])
    check(sorted(place[x] for t in po for x in t) == list(range(9, 25)), f'play-off clubs {po}', errs)
    for h, a in po:                          # unseeded (23/24 ..) at home first v seeded (9/10 ..) of the same pair
        j = (place[a] - 9) // 2
        check(place[h] in (23 - 2 * j, 24 - 2 * j), f'play-off {h} ({place[h]}) - {a} ({place[a]})', errs)
    r16 = rounds.get('TERZO TURNO', [])
    check(len(r16) == 8 and sorted(place[a] for _, a in r16) == list(range(1, 9)), f'round of 16 {r16}', errs)
    for h, a in r16:                         # play-off winner v seeded club of its pair (15/16 v 17/18 -> 1/2 ...)
        j = (min(place[h], 33 - place[h]) - 9) // 2
        check((place[a] + 1) // 2 == 4 - j, f'R16 {h} ({place[h]}) - {a} ({place[a]})', errs)
    order = [('TERZO TURNO', 'QUARTI'), ('QUARTI', 'SEMIFINALE'), ('SEMIFINALE', 'FINALE')]
    for a, b in order:
        prev, nxt = rounds.get(a, []), rounds.get(b, [])
        for k, (h, x) in enumerate(nxt):     # tie k = one club of tie 2k and one of tie 2k+1 before
            sides = [set(prev[2 * k]), set(prev[2 * k + 1])] if 2 * k + 1 < len(prev) else []
            check(sides and len({h, x} & sides[0]) == 1 and len({h, x} & sides[1]) == 1, f'{b} {h}-{x} not from {a}', errs)
    check(len(rounds.get('FINALE', [])) == 1, 'no final', errs)
    top = ', '.join(f'{k + 1} {names[r]} {pts[r]}' for k, r in enumerate(rank[:3]))
    return not errs, (f'draw ok, {len(played)} fixtures seen, 144 x 8; top {top}; play-offs {po[:2]}...; R16 {r16[:2]}...; '
                      f'final {rounds.get("FINALE")}; ' + '; '.join(errs))


@scenario
def world2526():
    """World 2025-26 with the UEFA league phases (private converter internal/world2526, LP=1: CL / EL / UECL of 36, the
    real 2025-26 clubs in season 1, the 2025-26 qualifier cascade): career at Arsenal, two seasons as world8485"""
    run = os.path.join(MAIN, 'internal', 'world2526', 'run.sh')
    if not os.path.exists(run):
        return True, 'SKIP: private converter internal/world2526 missing'
    out = os.path.join(WORK, 'builds', 'world2526')
    r = subprocess.run(['sh', run], env=dict(os.environ, LP='1', OUT=out, TOOLS=os.path.join(ROOT, 'tools')),
                       capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(out, 'ITALIAN.EXE')):
        return False, f'build: {(r.stdout + r.stderr)[-300:]}'
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K')}
    os.environ.update(W8485_BUILD=out, W8485_WORLD='WORLD 2025-26', W8485_TEAM='EUROPA,ENGLAND,ENGLAND DIV 1,ARSENAL',
                      W8485_WNUM='5', W8485_K='108')
    try:
        return world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_parallel(names, jobs):
    """run -jN: each scenario in its own process (own run dirs and DOSBox-X, one host core each in turbo); the
    builds are made once here first. Output in the order of the names; exit code 1 on a failure."""
    env = dict(os.environ, SWOSTEST_BUILD=builds()['it'])
    if 'world_roundtrip' in names:
        world_build()
    t0, todo, running, out = time.time(), list(names), {}, {}
    while todo or running:
        while todo and len(running) < jobs:
            n = todo.pop(0)
            running[n] = subprocess.Popen([sys.executable, os.path.abspath(__file__), 'run', n], env=env,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(0.5)
        for n, p in list(running.items()):
            if p.poll() is not None:
                out[n] = (p.returncode, p.stdout.read().strip())
                print(out[n][1], flush=True)
                del running[n]
    print(f'{len(names)} scenarios, {jobs} at a time: {time.time() - t0:.0f} s', flush=True)
    return 1 if any(rc for rc, _ in out.values()) else 0


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
        names = [a for a in argv[1:] if not a.startswith('-j')] or list(SCENARIOS)
        jobs = int(next((a[2:] for a in argv[1:] if a.startswith('-j')), 1) or 4)
        if jobs > 1 and len(names) > 1:
            return run_parallel(names, jobs)
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
