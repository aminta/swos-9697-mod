"""SWOS regression harness: runs the game in a private DOSBox-X, feeds it a key script, checks the outcome.

  python3 tools/swostest.py list                     scenarios
  python3 tools/swostest.py run [-jN] [NAME...]      run scenarios (all when none given); exit code 1 on a failure;
        -jN = N scenarios at a time (own processes and run dirs; -j = 4)
  python3 tools/swostest.py keys EXE CAR|- 'KEYS' [-shots S] [-t T] [-name NAME] [-match] [-timer]
        ad-hoc run: EXE = a build dir (ITALIAN.EXE + DATA) or an .EXE file (DATA from c/SWOS); CAR = a save to copy
        in (or -); KEYS = the script below; window screenshots every S s into runs/NAME/shots (with SWOSTEST_SCREENCAPTURE=1); T = timeout (s);
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
                                                     rb'(?:CD03|CC(?:\s|\x1b))'))   # mod traps CD 03, the game's own CC
                                                     # (the code view puts an ANSI erase right after 'CC')

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
    # g_workingPalette (obj2): ShowStadiumInit's `add esi, 64000 / mov edi, g_workingPalette / mov ecx, 768 / rep movsb`;
    # the menus' palette as the DAC has it once faded in (frames are rebuilt from memory, no screencapture)
    st = re.search(rb'\x81\xC6\x00\xFA\x00\x00\xBF....\xB9\x00\x03\x00\x00\xF3\xA4', c, re.S).start()
    assert fx[st + 7][0] == 2, 'g_workingPalette'
    return {'pal': fx[st + 7][1], 'page': page, 'size2': min(le.obj(2).vsize, le.obj(2).npages * le.page_size), 'calls': page + lab['calls'], 'code': (fixed, c[fixed:fixed + 48]), 'menu': curmenu[1],
            'brk': page + code.index(b'\xcd\x03'), 'ptr': page + lab['ptr'], 'script': page + lab['script'],
            'anchor': (anchor, d2[anchor:anchor + 64])}


def bp_str(r):
    """SWOSTEST_BP_STR = obj2 offset of a pointer (e.g. the A0 pseudo register): the string it points to;
    SWOSTEST_BP_HEX = obj2 offset:bytes,...: those bytes."""
    out = ''
    for a in filter(None, os.environ.get('SWOSTEST_BP_HEX', '').split(',')):   # obj2 offset:bytes, logged in hex
        o, n = a.split(':')
        out += f' {o}:{r.obj2(int(o, 16), int(n)).hex()}'
    off = os.environ.get('SWOSTEST_BP_STR')
    if not off:
        return out
    p = struct.unpack('<I', r.obj2(int(off, 16), 4))[0]
    return out + ' ' + r.read(p, 24).split(b'\0')[0].decode('latin-1')


ANSI = re.compile(rb'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\(B')
MEMSIZE = 0x2000000                                   # memsize=32: linear 0..32 MB


class Dosbox:
    """DOSBox-X under a pty: debugger reachable, int 3 traps caught."""

    def __init__(self, run, timeout, shots=0, exe='ITALIAN.EXE'):
        self.run, self.timeout, self.shots = run, timeout, shots
        conf = CONF if not os.environ.get('SWOSTEST_NOEXIT') else CONF.replace('{exe}\nexit\n', '{exe}\n')
        if os.environ.get('SWOSTEST_MEMSIZE'):         # (experiments: DOSBox-X memory in MB; dumps still read 32 MB)
            conf = conf.replace('memsize=32', 'memsize=' + os.environ['SWOSTEST_MEMSIZE'])
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
                if not m and getattr(self, 'memwatch', False):   # SWOSTEST_BPLM: a memory breakpoint's hit, then
                    seg = ANSI.sub(b' ', self.screen[mark:])     # the code view (EIP after the writing instruction)
                    k = re.search(rb'Memory breakpoint[^\n]*->', seg)
                    if k:
                        m = re.compile(rb'0160:([0-9A-F]{8})\s').search(seg, k.end())
                        self.memhit = m is not None
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

    def shot(self, tag, pal=None, vga=None):
        """A frame of the game: runs/<name>/shots/<tag>.png. Paused game (pal = the palette, 768 bytes of VGA 6-bit
        values): 320x200, one pixel per game pixel, from the video memory at A0000 (vga = those 64000 bytes when
        already read). Running game (periodic shots, a timeout): a screencapture of the window, only with
        SWOSTEST_SCREENCAPTURE=1 (Davide, 2026-10-18: it made macOS ask for screen recording over and over)."""
        path = os.path.join(self.run, 'shots', tag + '.png')
        if pal is not None:
            from PIL import Image
            if vga is None:
                vga = self.dump(0xA0000, 64000)
            im = Image.frombytes('P', (320, 200), bytes(vga[:64000]))
            im.putpalette(bytes((v & 63) * 255 // 63 for v in pal[:768]))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            im.save(path)
            return
        if not os.environ.get('SWOSTEST_SCREENCAPTURE'):
            return
        exe = os.path.join(WORK, 'bin', 'winid')            # window id of a pid (screencapture -l needs it)
        if not os.path.exists(exe):
            os.makedirs(os.path.dirname(exe), exist_ok=True)
            subprocess.run(['swiftc', '-O', os.path.join(ROOT, 'tools', 'swostest_winid.swift'), '-o', exe], check=True)
        win = subprocess.run([exe, str(self.pid)], capture_output=True, text=True)
        wid = win.stdout.strip()
        if wid and wid != '0':
            os.makedirs(os.path.join(self.run, 'shots'), exist_ok=True)
            subprocess.run(['screencapture', '-x', '-o', '-l', wid, path], capture_output=True)

    def post_mortem(self, shot=True, info=None):
        """After a break: full memory dump (MEMDUMP.BIN = linear 0..32 MB, read by Result) and, with the run's info
        (obj2 found in the dump), the frame 'final' from it; returns the break EIP."""
        mem = self.dump(0, MEMSIZE)
        if shot and info:
            off, chunk = info['anchor']
            base2 = mem.find(chunk) - off
            if base2 >= 0:
                self.shot('final', mem[base2 + info['pal']:base2 + info['pal'] + 768], mem[0xA0000:0xA0000 + 64000])
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
        if bases and box:                              # one dump: the stub's page + obj2's pages (adjacent; menus,
                                                       # slots; a big world's zero-filled tail is read on demand)
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
            eip = box.post_mortem(info=info)
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
        self.entries, self.nav, self.geom, self.colors = [], [], [], []
        for i in range(n):
            e = 0x16 + i * 0x38
            inv, dis = struct.unpack_from('<HH', mem, e + 4)
            self.nav.append((tuple(mem[e + 8:e + 12]), tuple(mem[e + 16:e + 20])))   # l/r/u/d, skip l/r/u/d
            self.geom.append(struct.unpack_from('<4h', mem, e + 0x14))                # x, y, width, height
            self.colors.append(struct.unpack_from('<H', mem, e + 0x1E)[0])            # bg.backAndFrameColor
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

    def path(self, target, bad=frozenset(), steps=False):
        """Keys from the selected entry to entry `target` (BFS on the entries' left/right/up/down links); bad = moves
        (entry, key) seen to go elsewhere in the game; steps: [(key, expected entry)] instead of the keys."""
        if self.selected is None:
            return None
        prev, todo = {self.selected: None}, [self.selected]
        while todo:
            cur = todo.pop(0)
            if cur == target:
                out = []
                while prev[cur]:
                    p, k = prev[cur]
                    out.append((k, cur))
                    cur = p
                out = out[::-1]
                return out if steps else [k for k, _ in out]
            links, skips = self.nav[cur] if cur < len(self.nav) else ((), ())
            for d, (k, nxt, alt) in enumerate(zip(('left', 'right', 'up', 'down'), links, skips)):
                if (cur, k) in bad:
                    continue
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

    def __init__(self, name, exe_dir, cars, keys, timeout=60, shots=0, match=False):
        self.run, self.info = prepare(name, exe_dir, cars, steps_of(keys), match)
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

    def bp_stack(self, r):
        """SWOSTEST_BP_STACK=1: the obj1 return addresses in the 0x200 bytes above ESP at a breakpoint hit."""
        if not os.environ.get('SWOSTEST_BP_STACK'):
            return ''
        path = os.path.join(self.run, 'MEMDUMP.BIN')
        if os.path.exists(path):
            os.remove(path)
        self.box.cmd('MEMDUMPBIN 168:ESP 200', 2)
        if not os.path.exists(path):
            return ' stack ?'
        v = struct.unpack('<128I', open(path, 'rb').read()[:512])
        return ' stack ' + ' '.join(f'{x - r.base1:X}' for x in v if r.base1 <= x < r.base1 + 0xB3000)

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
            for off in filter(None, os.environ.get('SWOSTEST_BPLM', '').split(',')):   # memory watches (obj2 offsets,
                b.cmd(f'BPLM {self.paused("x", b.eip).base2 + int(off, 16):08X}', 0.3)   # CORE=normal): a change
                b.memwatch = True                                                    # stops as a trap at its EIP
            for off in os.environ['SWOSTEST_BP'].split(','):     # counting breakpoints (use CORE=normal)
                o = int(off, 16)
                self.bp(base1 + o, lambda r, o=o: (self.bp_hits.__setitem__(o, self.bp_hits.get(o, 0) + 1),
                                                   self.log.append(f'BP obj1+{o:X} hit {self.bp_hits[o]}' + bp_str(r)
                                                                   + self.bp_stack(r))))
        while outcome == 'break' and getattr(b, 'memhit', False) and os.environ.get('SWOSTEST_BPLM_GO'):
            b.memhit = False                           # SWOSTEST_BPLM_GO: log the writer's EIP (+ stack), re-arm, go on
            r = self.paused('bplm', b.eip)
            self.log.append(f'BPLM obj1+{b.eip - r.base1:X}' + bp_str(r) + self.bp_stack(r))
            r.box = None
            b.cmd('BPDEL *', 0.3)
            b.cmd('BPINT 3', 0.2)
            for lin in getattr(self, 'bps', {}):
                b.cmd(f'BP 0160:{lin:08X}', 0.2)
            for off in filter(None, os.environ.get('SWOSTEST_BPLM', '').split(',')):
                b.cmd(f'BPLM {r.base2 + int(off, 16):08X}', 0.3)
            outcome = b.go_on()
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
                b.post_mortem(info=self.info)          # a real trap: full dump + frame for the post-mortem
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

    def shot(self, tag):
        """Frame of the paused game (Dosbox.shot from memory: video memory + g_workingPalette)."""
        assert self.result.outcome == 'dump', str(self.result)
        self.box.shot(tag, self.result.obj2(self.info['pal'], 768))

    def screen(self):
        assert self.result.outcome == 'dump', str(self.result)
        return Screen(self.result, self.info['menu'])

    def poke(self, lin, data):
        """Write bytes into the paused game's memory (debugger SM; the next read sees them)."""
        os.write(self.box.fd, f"SM 168:{lin:X} {' '.join(f'{x:X}' for x in data)}\r".encode())
        self.box.pump(0.05)                            # (read the echo: ~90 pokes in one pause filled the pty and
        if self.result:                                # os.write blocked for good)
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
    bad = set()
    for attempt in range(40):
        if scr.selected == i:
            return s.send(f'fire dump:{wait}')
        steps = scr.path(i, bad, steps=True)
        if not steps:
            return None
        if attempt < 2 and not bad:                    # the whole path at once (the usual case)
            if s.send(' '.join(k for k, _ in steps) + ' dump:0.5').outcome != 'dump':
                return s.result
            scr = s.screen()
            continue
        cur, (k, want) = scr.selected, steps[0]        # it went astray: one key at a time, and a move that lands
        if s.send(k + ' dump:0.5').outcome != 'dump':  # elsewhere (a link the model reads wrong) is not tried again
            return s.result
        scr = s.screen()
        if scr.selected != want:
            bad.add((cur, k))
    return None


# Career "results only", the fast loop (Davide): career menu PARTITA -> VIS. RISULTATI -> ESCI -> PARTITA ...
# (PROSS. PARTITA only shows each match). The squad screen hides VIS. RISULTATI while an injured/suspended player is
# in the first 16: he must be swapped with one beyond the 16th (face of the player -> left, then fire on the name).


# red on the frames built from memory (the game's palette, no colour management): the red row gradient (255,36,36)..
# (255,101,101) and the injury / red card red (255,0,0); not skin (182,72,0), (255,109,0) nor the shirts' maroon
RED = lambda c: c[0] >= 240 and c[1] <= 101 and abs(c[1] - c[2]) <= 8


def squad_rows(s, scr, tag):
    """Screenshot of the paused game -> [(entry, unavailable)] for the squad rows (entries 25,y,82,8 sorted by y).
    Unavailable = red row background (x=100) or red pixels in the face/icon column (x 2-11): red card / injury."""
    from PIL import Image
    rows = sorted((g[1], i) for i, g in enumerate(scr.geom)
                  if (g[0], g[2], g[3]) == (25, 82, 8) and not scr.entries[i][1])   # drawn rows, not text copies
    s.shot(tag)
    im = Image.open(os.path.join(s.run, 'shots', tag + '.png')).convert('RGB')
    w, h = im.size
    top = h - w * 400 // 640                           # window title bar (0: frames built from memory)
    px = lambda x, y: im.getpixel((min(w - 1, int(x * w / 320)), min(h - 1, int(top + y * (h - top) / 200))))
    out = []
    for y, i in rows:
        icon = sum(RED(px(x, y + dy)) for x in range(2, 12) for dy in range(1, 8))
        out.append((i, RED(px(100, y + 4)) or icon >= 16))     # faces have ~6 reddish points, red icons 20+
    return out


SLOT_ROLE = 'GDDDDMMMMAAGDMA'                     # record order of a SWOS squad: G RB LB D D RW LW M M A A, bench G D M A
POS_ROLE = {'P': 'G', 'TD': 'D', 'TS': 'D', 'D': 'D', 'MD': 'M', 'MS': 'M', 'M': 'M', 'A': 'A'}


def reserve_info(cur, y):
    """The 17th squad row (the reserve shown, the only row with texts): (name, role G/D/M/A or '', value)."""
    t = sorted((cur.geom[j][0], tx) for j, tx, inv, _ in cur.entries if tx and not inv and cur.geom[j][1] == y
               and cur.geom[j][0] < 180)
    name = next((tx for x, tx in t if x == 25), '')
    role = next((POS_ROLE.get(tx, '') for x, tx in t if 95 <= x <= 125), '')
    price = next((tx for x, tx in t if x >= 138), '')
    m = re.fullmatch(r'L([0-9.]+)(K|MN|MD)', price)
    value = (float(m.group(1)) * {'K': 0.001, 'MN': 1, 'MD': 1000}[m.group(2)] if m else
             -1 if price == 'PROVA' else 0)          # RIS (the game's invented reserves) 0, trial players -1
    return name, role, value


def substitute(s, scr, tries=40):
    """Squad screen (Davide, 2026-10-16: the harness used to put any fit reserve - a defender up front, a trial player -
    in place of a starter and leave him there). Two passes on the 17th row (the reserve shown; its face cycles through
    the reserves beyond the 16th):
    1. restore: a starter swapped out earlier (s.subs: slot -> (starter, stand-in)) who is fit again goes back to his
       slot;
    2. an unavailable player (red row / red icon) among the first 16: the best fit reserve of the slot's role (record
       order G D D D D M M M M A A, bench G D M A), by value; another role, the game's invented reserves (RIS) and
       trial players (PROVA) only when nothing better is there. Row 1 must be a goalkeeper (P): a fit one of the
       bench (row 12) first. Returns an error string or None."""
    subs = s.__dict__.setdefault('subs', {})

    def cycle(face, ry):                                # every reserve once: [(name, role, value, fit)]
        seen = []
        for _ in range(tries):
            c2 = s.screen()
            name, role, value = reserve_info(c2, ry)
            if seen and name == seen[0][0]:
                break
            rows2 = squad_rows(s, c2, f'sq{len(s.log):03d}')
            if len(rows2) != 17:                        # not the squad screen any more (a message, a shot
                break                                   # that failed): stop cycling, the caller looks again
            seen.append((name, role, value, not rows2[-1][1]))
            press(s, c2, face, wait=1)
        return seen

    def bring(face, ry, want):                          # cycle the 17th row to the reserve named want
        for _ in range(tries):
            if reserve_info(s.screen(), ry)[0] == want:
                return True
            press(s, s.screen(), face, wait=1)
            if s.result.outcome != 'dump':
                return False
        s.send('dump:1')                                # one more look after a pause (redraw)
        return reserve_info(s.screen(), ry)[0] == want

    def swap(slot_entry, reserve):                      # select the row, then the reserve's name: they change places
        press(s, s.screen(), slot_entry, wait=1)
        press(s, s.screen(), reserve, wait=1)

    for _ in range(10):                                 # one swap per round, then look again
        cur = s.screen()
        rows = squad_rows(s, cur, f'sq{len(s.log):03d}')
        if len(rows) != 17:
            return f'squad screen: {len(rows)} rows'
        reserve = rows[-1][0]
        ry = cur.geom[reserve][1]
        face = next((i for i, (l, r) in enumerate(cur.nav) if l[1] == reserve and cur.geom[i][0] < 25), None)
        if face is None:
            return 'squad screen: no face entry for the 17th row'
        # the first keeper fit again; row 12 must still be him (11 in subs: he left the 16, a stand-in is there)
        if s.__dict__.get('gk_swap') and 11 not in subs and not rows[11][1] and not rows[0][1]:
            swap(rows[0][0], rows[11][0])
            s.gk_swap = False
            s.log.append('[subs] slot 1: the first keeper back')
            continue
        pool = cycle(face, ry) if subs or any(un for _, un in rows[:16]) else []
        back = next(((k, st) for k, (st, _) in sorted(subs.items())
                     if any(n == st and fit for n, _, _, fit in pool) and not rows[k][1]), None)
        if back is None:                                # restore also over an unavailable stand-in
            back = next(((k, st) for k, (st, _) in sorted(subs.items())
                         if any(n == st and fit for n, _, _, fit in pool)), None)
        if back is not None:                            # 1. a starter fit again: back to his slot
            k, st = back
            if bring(face, ry, st):
                swap(rows[k][0], reserve)
                s.log.append(f'[subs] slot {k + 1}: {st} back')
            del subs[k]
            continue
        for k in [k for k, st in list(subs.items()) if not any(n == st[0] for n, _, _, _ in pool)]:
            del subs[k]                                 # the starter left the squad (sold, the game's changes)
        bad = [k for k, (i, un) in enumerate(rows[:16]) if un]
        if not bad and 'VIS. RISULTATI' not in cur.texts():
            bad = [0]                                   # no goalkeeper in goal (the game's own squad changes)
        if not bad:
            return None if 'VIS. RISULTATI' in cur.texts() else 'squad screen without VIS. RISULTATI, no unavailable row'
        k = bad[0]
        need = SLOT_ROLE[k] if k < len(SLOT_ROLE) else ''
        if k == 0 and not rows[11][1] and not s.__dict__.get('gk_swap') and 11 not in subs:   # the keeper: row 12
            swap(rows[0][0], rows[11][0])               # is the bench keeper in SWOS squads (drawn rows have no
                                                        # texts) unless a stand-in took his place
            s.gk_swap = True
            s.log.append('[subs] slot 1: the bench keeper (row 12) in')
            continue
        pool = pool or cycle(face, ry)
        fit = [(n, r, v) for n, r, v, f in pool if f and n]
        rank = lambda c: ((c[1] == need) if need else 1,           # the slot's role first (G: keepers only)
                          c[2] > 0, c[2] >= 0, c[2])               # real players, then RIS, trial players last
        cand = ([c for c in fit if c[1] == 'G'] or fit) if k in (0, 11) else \
            ([c for c in fit if c[1] != 'G'] or fit)          # out of role only as a last resort (the game itself
        if not cand:                                          # puts an outfield player in goal when it must)
            return f'no fit reserve for row {k + 1}'
        best = None
        for c in sorted(cand, key=rank, reverse=True):        # the best one that the cycle shows again (a read
            if bring(face, ry, c[0]):                         # before the row's redraw can miss a name)
                best = c
                break
        if best is None:
            return f'row {k + 1}: no candidate found again in the reserves ({[c[0] for c in cand][:6]})'
        stand_in = best[0]
        swap(rows[k][0], reserve)
        out = reserve_info(s.screen(), ry)[0]           # the one who left the 16 is now the 17th row
        if k not in subs:
            subs[k] = (out, stand_in)
        s.log.append(f'[subs] slot {k + 1} ({need or "any"}): {out} out, {stand_in} ({best[1] or "?"}, {best[2]}) in')
    return 'squad screen: still unavailable players after 10 swaps'


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
        if os.environ.get('SWOSTEST_FILL') and fill_check(s, f'step {step}') is False and not getattr(s, 'fill_bad', 0):
            s.fill_bad = 1                               # (investigation: the menu texture at every step; the first
            s.log.append(f'[fill] FIRST CHANGE at step {step}, after: {recent[-1] if recent else "-"}')   # change)
        recent.append(str(scr))                          # stuck: the last 16 screens are 1 or 2 alternating ones
        if len(recent) >= 16 and len(set(recent[-16:])) <= 2:
            return False, f'step {step}: stuck on {" / ".join(sorted(set(recent[-16:])))[:300]}'
        if stop(scr):
            return True, f'{step} steps'
        texts = scr.texts()
        if 'VIS. RISULTATI' in texts and 'MOD. TATTICA' in texts and (getattr(s, 'subs', None) or
                                                                     getattr(s, 'gk_swap', False)):
            err = substitute(s, scr)                     # stand-ins in the 16: bring fit starters back first
            if err:
                return False, f'step {step}: {err}'
            press(s, s.screen(), 'VIS. RISULTATI') or s.send('fire dump:2')
        elif 'VIS. RISULTATI' in texts:
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


def fill_check(s, tag):
    """The menu buttons' texture: FILL.256 lives at linAdr384k + 65536 (64000 pixels) while the menus run; a match draws
    its virtual pitch over the whole 384k buffer, and GameLoop / highlights / animations reload it (LoadFillAndSwtitle)
    before the menus come back. Compares that memory with the game folder's FILL.256 and logs '[fill] <tag>: intact' or
    'CHANGED' (differing bytes, the first offset). The address of linAdr384k: LoadFillAndSwtitle's `mov eax,
    [linAdr384k]; add eax, 65536; mov [A1], eax`. Returns True when intact (None if it could not be read)."""
    try:
        if not hasattr(fill_check, 'off'):
            sys.path.insert(0, os.path.join(ROOT, 'tools'))
            from le import LE
            import sacups
            d1 = LE(open(os.path.join(ROOT, 'orig', 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
            a1 = struct.pack('<I', sacups.regs(d1)['A0'] + 4)
            offs = {struct.unpack('<I', m.group(1))[0] for m in
                    re.finditer(rb'\xa1(.{4})\x05\x00\x00\x01\x00\xa3' + re.escape(a1), d1, re.S)}
            assert len(offs) == 1, offs
            fill_check.off = offs.pop()
            fill_check.ref = open(os.path.join(s.run, 'SWOS', 'FILL.256'), 'rb').read()[:64000]
        lin = struct.unpack('<I', s.result.obj2(fill_check.off, 4))[0] + 65536
        mem = s.result.read(lin, 64000)
        diff = [i for i in range(0, 64000, 16) if mem[i:i + 16] != fill_check.ref[i:i + 16]]
        s.log.append(f'[fill] {tag}: ' + ('intact' if not diff else
                                          f'CHANGED ({len(diff)} of 4000 blocks, first +{diff[0] * 16:#x})'))
        return not diff
    except Exception as e:                           # never let the check break a run
        s.log.append(f'[fill] {tag}: check failed {e}')
        return None


def menu_check(s, tag):
    """Main menu after a career (Davide, 2026-10-16: once its buttons showed an in-match frame instead of their
    FILL.256 texture): screenshot it and compare the MOD. TATTICA button with the game's gradient (a smooth dark
    blue left to right). A corrupted texture is noted in the session log as '[menu] CORRUPTED' (no failure)."""
    try:
        from PIL import Image
        s.shot('menu_' + tag)
        path = os.path.join(s.run, 'shots', 'menu_' + tag + '.png')
        im = Image.open(path).convert('RGB')
        w, h = im.size
        top = h - w * 400 // 640
        y = int(top + 92 * (h - top) / 200)              # the button's middle row (game y 92), x 22..150
        row = [im.getpixel((int(x * w / 320), y)) for x in range(22, 150, 2)]
        jumps = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) > 60 for a, b in zip(row, row[1:]))
        s.log.append(f'[menu] {tag}: ' + ('CORRUPTED' if jumps > 20 else 'clean') + f' ({jumps} jumps)')
        fill_check(s, tag)
    except Exception as e:                           # never let the check break a run
        s.log.append(f'[menu] {tag}: check failed {e}')


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
    menu_check(s, 'season_end')                  # the main menu after a career: corrupted buttons? (Davide)
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


def nosack_off(exe):
    """obj2 offset of dseg_D6B62 (non-zero: the chairman never sacks the manager; cleared by every season start):
    the second word of the `mov ax,[D6B64]; or ax,ax; jnz; mov ax,[D6B62]; or ax,ax; jnz` pair of both sacking
    checks (cseg_3CCF0)."""
    import collections
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    le = LE(open(exe, 'rb').read())
    pat = re.compile(rb'\x66\xa1(.{4})\x66\x0b\xc0\x0f\x85.{4}\x66\xa1(.{4})\x66\x0b\xc0\x0f\x85', re.S)
    pairs = collections.Counter(struct.unpack('<II', m.group(1) + m.group(2)) for m in pat.finditer(le.obj_bytes(1)))
    hits = [b for (a, b), n in pairs.items() if a == b + 2 and n == 2]
    assert len(hits) == 1, hits
    return hits[0]


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
    want = os.environ.get('W8485_K', '128')            # 'N+': at least N (uefaq: the qualifying opponents' records)
    k = re.search(r'euro records k=(\d+)', out)
    ok = ok and k is not None and (int(k.group(1)) >= int(want[:-1]) if want.endswith('+') else k.group(1) == want)
    ok = ok and re.search(rf"world byte {os.environ.get('W8485_WNUM', '4')}\b", out) is not None
    return ok and m is not None and m.group(1) == '0', out


def season_over(scr):
    """FINISCI STAGIONE offered, or already the season-end menu (every match played: no FINISCI STAGIONE)."""
    return scr.find('FINISCI STAGIONE', exact=True) is not None or any('FINE CAMP' in t for t in scr.texts())


@scenario
def season4748():
    """3.3.5: CLASSIC SEASONS Italy 1947-48 (21 clubs, all computer): the first 6 match days, 10 matches each with 20
    different clubs and one at rest (oddtables.py; before, a club played twice on some match days)"""
    b = builds()['it']
    days = 6                                    # the 3.3.4 table: days 5, 6, 8, 9, 11..21 irregular
    with Session('season4748', b, {}, 'dump:2', 400) as s:
        s.wait()
        for t in ('STAGIONE', 'STAG. STORICHE', 'ITALIA 1947-48'):
            if press(s, s.screen(), t, 2) is None:
                return False, f'{t} not reached ({s.result})'
        for _ in range(12):                     # the STAGIONE button (76), right of ABBANDONA (75)
            scr = s.screen()
            if scr.entries[scr.selected][1] == 'STAGIONE':
                break
            s.send(('right' if scr.entries[scr.selected][1] == 'ABBANDONA' else 'down') + ' dump:0.5')
        s.send('fire dump:3')
        matches = []
        for _ in range(days * 10 * 3):
            scr = s.screen()
            if s.result.outcome != 'dump':
                return False, f'after {len(matches)} matches: {s.result}'
            pair = (scr.entries[12][1], scr.entries[13][1]) if len(scr.entries) > 13 else None
            if pair and scr.entries[11][1] == 'C' and pair[0] and pair[1]:    # a match before its result
                matches.append(pair)
                if len(matches) == days * 10:
                    break
            s.send('fire dump:2')
    errs = []
    for d in range(days):
        day = matches[d * 10:d * 10 + 10]
        clubs = [c for m in day for c in m]
        check(len(day) == 10 and len(set(clubs)) == 20, f'day {d + 1}: {len(day)} matches, {len(set(clubs))} clubs '
              f'{sorted(c for c in set(clubs) if clubs.count(c) > 1)} twice', errs)
    return not errs, '; '.join(errs) or f'{days} match days of 10 matches, 20 clubs each (first: {matches[:2]})'


@scenario
def w84_lowprice():
    """3.3.4 (Daniele): a 1984-85 career at Volsungur (Iceland), whose 16 players are all worth the minimum: the team
    screen divided by the average player price (0) and the game stopped (DOS/4GW divide error); avgprice.py"""
    exe = os.environ.get('W8485_BUILD') or builds()['it']       # (as world8485: builds/w8485 is a stale build)
    with Session('w84_lowprice', exe, {}, 'dump:2', 240) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: no first pause ({s.result})'
        for t in ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'EUROPA 1984-85', 'ISLANDA', 'VOLSUNGUR']:
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'new career: {t} not reached ({s.result})'
        seen = []
        for _ in range(6):                      # the team screen and on (VIS. RISULTATI, back...)
            r = s.send('fire dump:2')
            if r.outcome != 'dump':
                return False, f'after {seen}: {r}'
            seen.append(s.screen().entries[0][1] if s.screen().entries else '?')
        return True, 'Volsungur career: ' + ' > '.join(seen)


def w84_tag():
    """Run dir prefix of world8485()'s two seasons: 'world8485', or '<scenario>_w84' when another scenario runs it, so
    world8485 and world2526 (... which call world8485()) never share run dirs in one suite (-j2: one overwrote the
    other's session.log and screenshots)."""
    n = os.environ.get('SWOSTEST_SCENARIO')
    return 'world8485' if n in (None, '', 'world8485') else f'{n}_w84'


def fmt_lines(build, title, lang='it', world=0):
    """The FORMAT page's first page for title, as written in the build's DATA\\FMTxx[world].DAT (fmtpage.py)."""
    path = os.path.join(build, 'DATA', f'FMT{lang.upper()}{world or ""}.DAT')
    d = open(path, 'rb').read()
    for i in range(struct.unpack_from('<H', d, 4)[0]):
        e = d[8 + 48 * i:56 + 48 * i]
        if e[1:42].split(b'\0')[0].decode('latin-1') == title:
            off, ln = struct.unpack_from("<IH", e, 42)
            return d[off:off + ln].decode('latin-1').split('\x0c')[0].split('\n')
    return None


@scenario
def format_page():
    """5.0 / 4.0: the FORMAT page (fmtpage.py), in the exe language FMT_LANG (it, en, fr, de; SWOSTEST_BUILD = a build
    of that language). Season > classic seasons > DDR 1988-89 (by entry number, the same menus in every language):
    FORMAT of the Oberliga and of the FDGB-Pokal (DATA\\FMTxx.DAT); Italian: also a new 1984-85 career at Liverpool,
    the First Division (world 4: FMTIT4.DAT). Each page shows the competition's title and the file's lines"""
    b = builds()['it']
    lang = os.environ.get('FMT_LANG', 'it')
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import fmtgame
    ddr = fmtgame.from_pack(os.path.join(ROOT, 'packs', 'ddr-1988-89'))
    errs, info = [], []
    def check_page(scr, title, world):
        want = fmt_lines(b, title, lang, world)
        got = [e[1] for e in scr.entries[1:1 + len(want or [])]] if want else None
        check(scr.entries[0][1] == title and want and got == want, f'{title}: shown {scr.entries[0][1]!r} {got} '
              f'want {want}', errs)
        info.append(f'{title}: {len(want or [])} lines')
    with Session('format_season_' + lang, b, {}, 'dump:2', 300) as s:
        s.wait()
        walk(s, 8, 2)                                   # SEASON
        import mkseason
        press(s, s.screen(), mkseason.SEASONS_NAMES[lang].decode('latin-1'), 2)   # classic seasons
        press(s, s.screen(), 'DDR 1988-89', 2)
        for _ in range(12):                             # the start button (76), right of the abandon one (75)
            if s.screen().selected == 76:
                break
            s.send(('right' if s.screen().selected == 75 else 'down') + ' dump:0.5')
        s.send('fire dump:3')
        walk(s, 18, 3)                                  # VIEW COMPETITIONS (the season menu's entry 18)
        for k, item in ((1, ddr[0]), (2, ddr[1])):
            walk(s, k, 3)
            walk(s, 9, 3)                               # STAT
            walk(s, 5, 3)                               # FORMAT
            scr = s.screen()
            check_page(scr, item[2][lang], 0)
            s.shot(f'format_{lang}_{k}')
            walk(s, 16, 3)                              # EXIT -> statistics
            walk(s, 4, 3)                               # EXIT -> the competition
            walk(s, 10, 3)                              # EXIT -> the list
    if lang != 'it':
        return not errs, '; '.join(errs + info) if errs else 'FORMAT pages drawn: ' + '; '.join(info)
    with Session('format_w84', b, {}, 'dump:2', 300) as s:
        s.wait()
        for t in ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'EUROPA 1984-85', 'INGHILTERRA', 'FIRST DIVISION',
                  'LIVERPOOL']:
            if press(s, s.screen(), t) is None:
                return False, f'new career: {t} not reached'
        s.send('fire dump:3')
        walk(s, 11, 3)                                  # VISUAL. COMPETIZ.
        walk(s, 1, 3)
        walk(s, s.screen().find('STAT', exact=True), 3)
        walk(s, s.screen().find('FORMULA', exact=True), 3)
        check_page(s.screen(), 'INGHILTERRA FIRST DIVISION', 4)
        s.shot('format_w84')
    return not errs, '; '.join(errs + info) if errs else 'FORMAT pages drawn: ' + '; '.join(info)


@scenario
def w84_record():
    """3.3.6: REGISTRO GESTIONE in a 1984-85 career shows the world's seasons (FillManagementRecordInfo added 1996 to
    the season number: '1998/99' in the career's third season). W84B_MREC.CAR (world8485's W84B: Darlington, season
    1986/87) loaded: the record's season line is 1986/87 (careerworld w_mrec)"""
    car = os.path.join(WORK, 'saves', 'W84B_MREC.CAR')
    if not os.path.exists(car):
        return True, 'SKIP: no saves/W84B_MREC.CAR (a world8485 run\'s W84B.CAR)'
    exe = os.environ.get('W8485_BUILD', os.path.join(WORK, 'builds', 'w8485'))
    with Session('w84_record', exe, {'W84B.CAR': car}, 'dump:2', 300) as s:
        s.wait()
        s.send(LOAD1 + ' dump:3')
        scr = s.screen()
        season = scr.entries[2][1]                    # CAMP. 1986/87
        walk(s, scr.find('VISUAL. COMPETIZ.', exact=True), 3)
        walk(s, s.screen().find('REGISTRO GESTIONE', exact=True), 3)
        t = s.screen().texts()
        line = next((x for x in t if 'STAGIONE' in x), None)
    ok = line is not None and season.endswith('1986/87') and line.startswith('1986/87')
    return ok, f'{season}: record line {line!r}'


@scenario
def world8485():
    """Europe 1984-85 world (world 4): new career at Liverpool, two seasons (save, reload, save), checkw1 on both"""
    exe = os.environ.get('W8485_BUILD') or builds()['it']       # (builds/w8485 was a stale 3.0-era build)
    out, msgs = [], []
    first = os.environ.get('W8485_FROM')                   # resume from a season-1 save (W84A.CAR)
    if first:
        out, msgs = [first], [f'season 1: from {first}']
    for season in ((2,) if first else (1,) if os.environ.get('W8485_ONE') == '1' else (1, 2)):   # (W8485_ONE: season 1 only)
        cars = {} if season == 1 else {'W84A.CAR': out[0]}
        with Session(f'{w84_tag()}_{season}', exe, cars, 'dump:2', int(os.environ.get('W8485_TMO', 240)), int(os.environ.get('W8485_SHOTS', 0))) as s:
            if s.wait().outcome != 'dump':
                return False, f'START: no first pause ({s.result})'
            if season == 1:
                team = os.environ.get('W8485_TEAM', 'INGHILTERRA,FIRST DIVISION,LIVERPOOL').split(',')
                path = ['CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', os.environ.get('W8485_WORLD', 'EUROPA 1984-85')] + team
                if os.environ.get('W8485_PATH'):              # the whole selector path; '<back>' = ESCI until the
                    path = ['CARRIERA', 'SCEGLI SQUADRA'] + os.environ['W8485_PATH'].split(',')   # next step shows
                for k, t in enumerate(path):
                    if t == '<back>':
                        for _ in range(6):
                            if s.screen().find(path[k + 1], exact=True) is not None:
                                break
                            for _ in range(40):              # (ESCI has no menu links the BFS knows: walk down)
                                scr = s.screen()
                                if any(e[0] == scr.selected and e[1] == 'ESCI' for e in scr.entries):
                                    break
                                s.send('down dump:0.5')
                            if s.send('fire dump:2').outcome != 'dump':
                                return False, f'new career: ESCI ({s.result})'
                        continue
                    scr = s.screen()                      # a group of a level (menulevels): its level first
                    lvl = None if scr.find(t, exact=True) is not None else \
                        next((x for i, x, inv, _ in scr.entries if 11 <= i <= 20 and x and not inv and
                              t.startswith(x + ' ')), None)
                    if lvl and press(s, scr, lvl) is None:
                        return False, f'new career: level {lvl} of {t} not reached ({s.result})'
                    if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                        return False, f'new career: {t} not reached ({s.result})'
                if os.environ.get('W8485_START') == '1':          # menu check only: the career has started
                    return True, f'career started: {s.screen()}'[:400]
            else:
                s.send('down down down down down fire dump:2')
                s.send('fire dump:3')
            seen, errs = {}, []
            nosack, poked = (nosack_off(os.path.join(exe, 'ITALIAN.EXE')) if os.environ.get('W8485_NOSACK') == '1'
                             else None), set()

            def hexlog():                              # W8485_HEX: obj2 offset:bytes (o1/ prefix: obj1),
                for a in filter(None, os.environ.get('W8485_HEX', '').split(',')):   # logged when they change
                    o, n = a.split(':')
                    if o.startswith('o1/'):
                        v = s.result.read(s.result.base1 + int(o[3:], 16), int(n)).hex()
                    else:
                        v = s.result.obj2(int(o, 16), int(n)).hex()
                    if hexseen.get(o) != v:
                        hexseen[o] = v
                        s.log.append(f'HEX {o} {v}')

            mid = os.environ.get('W8485_MIDSAVE', '').split(':') if season == 1 else ['']   # obj2 off:byte:dumps:
            midc = [0]                                 # a career save mid-season once the byte held that long

            def stop(scr):                             # the player's European cup: no same-country tie in rounds 1-2
                if nosack is not None and season not in poked:   # W8485_NOSACK: the game's 'no sacking' word
                    s.poke(s.result.base2 + nosack, b'\x01\x00')   # (dseg_D6B62, cleared at every season start)
                    poked.add(season)
                if peek is not None:                   # W8485_PEEK: the largest word seen at an obj2 offset
                    peek[1] = max(peek[1], struct.unpack_from('<H', s.result.obj2(peek[0], 2))[0])
                hexlog()
                if mid[0] and s.result.obj2(int(mid[0], 16), 1)[0] == int(mid[1], 0):
                    midc[0] += 1
                    if midc[0] >= int(mid[2]):
                        return True
                if diy is not None:                    # W8485_DIY (world_split): the split league's DIY when its
                    b = s.result.obj2(diy[0], 0x733)    # day / freeze changes, the calendar once frozen
                    if diy_league(b) and diyseen.get('k') != (b[0x1C1:0x1C3], b[diy[1] + 4]):
                        diyseen['k'] = (b[0x1C1:0x1C3], b[diy[1] + 4])
                        s.log.append(f'DIY {b.hex()}')
                        open(os.path.join(s.run, 'diy.log'), 'a').write(f'DIY {b.hex()}\n')   # (live, for long runs)
                        if b[diy[1] + 4] and 'cal' not in diyseen:
                            diyseen['cal'] = 1
                            s.log.append(f'CAL {s.result.obj2(diy[2], 1870).hex()}')
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
            hexseen, diyseen = {}, {}
            diy = [int(x, 16) for x in os.environ['W8485_DIY'].split(',')] if os.environ.get('W8485_DIY') else None
            diy_league = lambda b: b[0:2] == b'\0\0' and (b[diy[1]:diy[1] + 2] == b'\xfeP' if len(diy) < 4 else
                                                            struct.unpack_from('<H', b, 0x31)[0] == diy[3])   # (a split
            # league by its mark; W8485_DIY's 4th field: any league of that many clubs, the odd-league scenario)
            r2only = os.environ.get('W8485_R2') == '1'         # stop once the player's round 2 is checked
            peek = [int(os.environ['W8485_PEEK'], 0), 0] if os.environ.get('W8485_PEEK') else None
            ok, msg = advance(s, stop, 900)
            if mid[0] and midc[0] >= int(mid[2]):          # W8485_MIDSAVE: ESCI -> SALVA CARRIERA -> W84A, mid-season
                press(s, s.screen(), 'ESCI', wait=3)
                if press(s, s.screen(), 'SALVA CARRIERA') is None:
                    return False, f'mid-season save: no SALVA CARRIERA on {s.screen()}'
                s.send(name_entry('W84A') + ' dump:3')
                path = os.path.join(s.run, 'SWOS', 'W84A.CAR')
                return os.path.exists(path), f'saved mid-season: {path}'
            if r2only:
                return (season, 1) in seen and not errs, f"season {season}: {msg}; {'; '.join(errs) or 'ok'}"

            msg += f', euro rounds checked {sorted(seen)}' + (f', peek max {peek[1]}' if peek else '')
            if not ok or errs:
                return False, f"season {season}: {msg}; {'; '.join(errs)}"
            for _ in range(8):                         # FINISCI STAGIONE with the career club's matches still in
                if s.screen().find('FINISCI STAGIONE', exact=True) is not None:   # the calendar (a play-off of
                    press(s, s.screen(), 'FINISCI STAGIONE', wait=3)               # dplay: no 'manager' flag on
                if s.result.outcome != 'dump':                                     # its entries) plays them first
                    return False, f'season {season} FINISCI STAGIONE: {s.result}'
                texts = s.screen().texts()
                if not ('MOD. TATTICA' in texts and 'AVVERSARI' in texts):
                    break
                ok, m2 = advance(s, lambda scr: season_over(scr) and 'MOD. TATTICA' not in scr.texts(), 200)
                msg += f', after FINISCI STAGIONE: {m2}'
                if not ok:
                    return False, f"season {season}: {msg}" 
            if diy is not None and os.environ.get('W8485_SLOTS'):   # (the split league once the season is over,
                lin = struct.unpack('<I', s.result.obj2(int(os.environ['W8485_SLOTS'], 16), 4))[0]   # from its slot:
                b = s.result.read(lin, 0x733)          # its last days may come after the career club's last match)
                if diy_league(b):
                    s.log.append(f'DIY {b.hex()}')
            if os.environ.get('W8485_SAVE_END'):      # (debug) a save at the season-end menu, before CONTINUA
                nm = os.environ['W8485_SAVE_END']
                if press(s, s.screen(), 'SALVA CARRIERA') is None:
                    return False, f'season {season}: no SALVA CARRIERA on {s.screen()}'
                s.send(name_entry(nm) + ' dump:3')
                return True, f'season {season}: saved {os.path.join(s.run, "SWOS", nm + ".CAR")}'
            path = next_season_save(s, 'W84' + 'AB'[season - 1])
            if s.result.outcome == 'dump':             # (after the season end: its logs)
                hexlog()
            if not path.endswith('.CAR'):
                return False, f'season {season}: {path}'
        good, report = checkw1(path)
        out.append(path)
        msgs.append(f'season {season}: {msg}, ' + ('checkw1 ok' if good else 'checkw1 FAIL'))
        open(os.path.join(RUNS, f'{w84_tag()}_{season}', 'checkw1.txt'), 'w').write(report + '\n')
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
    exe = os.environ.get('W8485_BUILD') or builds()['it']       # (builds/w8485 was a stale 3.0-era build)
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


@scenario
def w84_cache():
    """3.3.3: the 1984-85 world's team cache. W84E_TEAM254.CAR (Liverpool 1984-85, season end: league 22 + FA Cup 64
    + UEFA Cup 64 = 124 cached teams; 3.3.2 exits to DOS with data/team.254) -> CONTINUA CARRIERA -> the next season
    saved in the big cache (more than 100 records, BIGC); that save reloaded and saved twice: equal, BIGC kept; an old
    save (W84A.CAR, 3.0) reloaded and saved twice: equal, no BIGC (the game's cache)"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import careerworld
    b = builds()['it']
    errs, info = [], []
    car = os.path.join(WORK, 'saves', 'W84E_TEAM254.CAR')     # (repro by the world 2025-26 sessions)
    with Session('w84_cache', b, {'W84E.CAR': car}, 'dump:2', 300) as s:
        s.wait()
        s.send(LOAD1 + ' dump:3')
        path = next_season_save(s, 'W84F')
    if not path.endswith('.CAR'):
        return False, f'next season: {path}'
    d = open(path, 'rb').read()
    n = struct.unpack_from('<H', d, CAR_FIXED)[0]
    mark = struct.pack('<I', careerworld.BIGC) in d[:CAR_FIXED]
    check(n > 100 and mark, f'next season: {n} records, BIGC {mark}', errs)
    info.append(f'next season {n} records')
    for tag, src, big in (('new', path, True), ('old', os.path.join(WORK, 'saves', 'W84A.CAR'), False)):
        err, x1, x2 = two_saves('w84_cache_' + tag, b, src, 150)
        if err:
            errs.append(f'{tag}: {err}')
            continue
        d1, d2 = open(x1, 'rb').read(), open(x2, 'rb').read()
        m = struct.pack('<I', careerworld.BIGC) in d2[:CAR_FIXED]
        n2 = struct.unpack_from('<H', d2, CAR_FIXED)[0]
        check(ndiff(x1, x2) == 0 and m == big, f'{tag}: save 1 vs 2 {ndiff(x1, x2)} bytes, BIGC {m}, {n2} records', errs)
        info.append(f'{tag}: {n2} records, BIGC {m}, vs source {ndiff(src, x1)} bytes')
    return not errs, '; '.join(errs + info) if errs else '; '.join(info)


@scenario
def w84_cupdraw():
    """3.3.3 (lib97 nc_bye / nc_adv from world-2025-26): a new 1984-85 career at LIVERPOOL: the FA Cup (id CC, 64 clubs)
    keeps the real first-round bracket of ties.csv in its first season (round-1 list at slot +2CDh = 0..63, the
    contest order); 3.3.2 shuffled it (the cup header's byte 8 was 0)"""
    errs = []
    with Session('w84_cupdraw', builds()['it'], {}, 'dump:2', 240) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: {s.result}'
        for t in ('CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'EUROPA 1984-85', 'INGHILTERRA', 'FIRST DIVISION',
                  'LIVERPOOL'):
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'new career: {t} not reached ({s.result})'
        r = s.result
        d = r.read(r.base2, 0x100000)
        hits = [i - 0x2D for i in range(0x2D, len(d) - 0x443) if d[i] == 0xCC and d[i + 4:i + 6] == b'\x40\x00']
        if not hits:
            return False, 'FA Cup slot (id CC, 64 clubs) not found'
        start = list(d[hits[0] + 0x2CD:hits[0] + 0x2CD + 64])
    check(start == list(range(64)), f'round 1 list {start[:16]}... (ties.csv order: 0..63)', errs)
    return not errs, '; '.join(errs) or f'FA Cup round 1 = ties.csv (slot obj2+{hits[0]:#x})'


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
    errs, cal, rows, aw, rounds, heads, disc = [], None, None, None, {}, set(), None
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
                disc = b[lp36.DISC:lp36.DISC + 36]
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
                     sum(gd[o] for o in opp[r]), sum(rows[o][4] for o in opp[r]), -disc[r], -r)
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


def world_lock():
    """An exclusive lock around internal/world2526/run.sh: it rewrites its converter output (world5/) every time, so
    two builds at once (world2526 and world2526q in a parallel suite) would break each other."""
    import contextlib
    import fcntl

    @contextlib.contextmanager
    def lock():
        with open(os.path.join(WORK, 'world2526.lock'), 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    return lock()


@scenario
def world2526():
    """World 2025-26 with the UEFA league phases (private converter internal/world2526, LP=1: CL / EL / UECL of 36, the
    real 2025-26 clubs in season 1, the 2025-26 qualifier cascade): career at Arsenal, two seasons as world8485"""
    run = os.path.join(MAIN, 'internal', 'world2526', 'run.sh')
    if not os.path.exists(run):
        return True, 'SKIP: private converter internal/world2526 missing'
    out = os.path.join(WORK, 'builds', 'world2526')
    with world_lock():                         # (world2526q builds from the same converter output dir)
        r = subprocess.run(['sh', run], env=dict(os.environ, LP='1', OUT=out, TOOLS=os.path.join(ROOT, 'tools')),
                           capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(out, 'ITALIAN.EXE')):
        return False, f'build: {(r.stdout + r.stderr)[-300:]}'
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K')}
    os.environ.update(W8485_BUILD=out, W8485_WORLD='WORLD 2025-26', W8485_TEAM='EUROPA,ENGLAND,ENGLAND DIV 1,ARSENAL',
                      W8485_WNUM='5', W8485_K='108+' if os.environ.get('UEFAQ_FORCE') else '108')
    try:
        return world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@scenario
def world2526q():
    """World 2025-26 test world (LP=1) built with UEFAQ_FORCE='CL Q1' (the career club enters the CL qualifying):
    Ajax two seasons, no sacking (a small country: an English club's 64-club cup + a league phase can fill the
    game's 100-team cache); season 2 must open with at least two qualifying ties played by the manager
    ('PRELIM.' contests, rounds named by their qualifying round, not FINALE)"""
    run = os.path.join(MAIN, 'internal', 'world2526', 'run.sh')
    if not os.path.exists(run):
        return True, 'SKIP: private converter internal/world2526 missing'
    out = os.path.join(WORK, 'builds', 'world2526q')
    with world_lock():
        r = subprocess.run(['sh', run], env=dict(os.environ, LP='1', OUT=out, TOOLS=os.path.join(ROOT, 'tools'),
                                                 UEFAQ_FORCE='CL Q1'), capture_output=True, text=True)
    if r.returncode or not os.path.exists(os.path.join(out, 'ITALIAN.EXE')):
        return False, f'build: {(r.stdout + r.stderr)[-300:]}'
    keys = ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K', 'W8485_NOSACK')
    keep = {k: os.environ.get(k) for k in keys}
    os.environ.update(W8485_BUILD=out, W8485_WORLD='WORLD 2025-26', W8485_TEAM='EUROPA,HOLLAND,HOLLAND DIV 1,AJAX',
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    log = os.path.join(RUNS, w84_tag() + '_2', 'session.log')
    ties, bad = [], []
    if os.path.exists(log):
        for line in open(log, errors='replace'):
            if not line.startswith('[') or 'PRELIM.' not in line.split('|')[0]:
                continue
            f = [x.strip() for x in line.split('|')]
            title = f[0].split(']', 1)[1].strip()
            if 'FINALE' in title:
                bad.append(title)
            if '- PARTITA -' in f:                     # a leg the manager could play: one tie per round name
                key = title.split(' TURNO')[0] + ' TURNO' if ' TURNO' in title else title
                if key not in ties:
                    ties.append(key)
    ok = ok and len(ties) >= 2 and not bad
    return ok, f'{msg}; ties played {ties}; FINALE titles {bad[:2]}'


def walk(s, target, w=3, tries=20):
    """Select entry `target` (text or number) one key at a time, re-planning after each move (menus where a planned
    path drifts: two-column lists, moves taken twice), then fire; returns the new screen."""
    for _ in range(tries):
        scr = s.screen()
        i = scr.find(target) if isinstance(target, str) else target
        if i is None:
            raise AssertionError(f'{target} not on screen')
        if scr.selected == i:
            s.send(f'fire dump:{w}')
            return s.screen()
        p = scr.path(i)
        if not p:
            raise AssertionError(f'no path to {target} from {scr.selected}')
        s.send(p[0] + ' dump:0.5')
    raise AssertionError(f'{target} not reached')


def friendly_prematch(s, home, away):
    """Main menu -> AMICHEVOLE with two Bundesliga clubs (player-controlled) -> pre-match screen."""
    for t in ('AMICHEVOLE', 'OK', 'SCEGLI SQUADRE', 'SQUADRE CLUB', 'EUROPA', 'GERMANIA', '1. LIGA', home, away):
        walk(s, t, 2)
    for _ in range(12):                         # AMICHEVOLE (55) is reached from the list by down, then right (56, 57)
        scr = s.screen()
        if scr.selected == 55:
            s.send('fire dump:4')
            return s.screen()
        s.send(('right' if scr.selected in (56, 57) else 'down') + ' dump:0.5')
    raise AssertionError('AMICHEVOLE not reached')


@scenario
def kits_reset():
    """3.2.4 (Marco): kits set in a friendly's pre-match screen left without playing must not carry over to the next
    friendly with other teams (button back to AUTO, SELECT KITS shows the new teams)"""
    errs = []
    with Session('kits_reset', builds()['it'], {}, 'dump:3', 400) as s:
        s.wait()
        scr = friendly_prematch(s, 'HAMBURG', 'SCHALKE')
        scr = walk(s, 68)                       # KITS AUTO -> SELECT KITS
        scr = walk(s, 2, 2)                     # the shown team wears its second kit
        scr = walk(s, 'OK')
        check(scr.entries[68][1] == 'MAGLIE FISSE', f'after OK: {scr.entries[68][1]!r}', errs)
        for _ in range(22):                     # pre-match ESCI: down the rows to VIS. PARTITA, then right
            s.send('down dump:0.5')
            if s.screen().selected == 9:
                break
        s.send('right dump:0.5')
        scr = walk(s, 8)
        check(scr.find('AMICHEVOLE') is not None, 'main menu not reached', errs)
        scr = friendly_prematch(s, 'BAYERN MUNICH', 'BOR. DORTMUND')
        check(scr.entries[68][1] == 'MAGLIE AUTO', f'second friendly: button {scr.entries[68][1]!r}', errs)
        scr = walk(s, 68)
        names = {scr.entries[1][1], scr.entries[3][1].split(':')[0]}
        check(names == {'BAYERN MUNICH', 'BOR. DORTMUND'}, f'SELECT KITS teams {names}', errs)
    return not errs, '; '.join(errs) or 'button AUTO and the new teams after a pre-match left without playing'


SHIRT_EXPECT = {17: '#.###|#...#|#...#|#...#|#...#', 20: '###.###|..#.#.#|###.#.#|#...#.#|###.###',
                41: '#...#|#...#|#.#.#|###.#|..#.#', 99: '###.###|#.#.#.#|###.###|..#...#|###.###'}


@scenario
def shirt_numbers():
    """3.2.5 (Marco): shirt numbers 17..99 over the controlled player, built from the game's digits (friendly, human
    HAMBURG numbered 17..32, goal kicks): sprites 1335..1417 in spritesIndex, 17 / 20 / 41 / 99 pixel-exact"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import shirtnum
    b = builds()['it']
    src = os.path.join(b, 'DATA', 'TEAM.014')
    d = bytearray(open(src if os.path.exists(src) else os.path.join(MAIN, 'orig', 'DATA', 'TEAM.014'), 'rb').read())
    for t in range(struct.unpack('>H', d[:2])[0]):
        o = 2 + t * 684
        if d[o + 5:o + 22].split(b'\0')[0] == b'HAMBURG':
            for k in range(16):
                d[o + 76 + k * 38 + 2] = 17 + k
    team = os.path.join(WORK, 'saves', 'TEAM014_HAMBURG17.BIN')
    os.makedirs(os.path.dirname(team), exist_ok=True)
    open(team, 'wb').write(d)
    spr = shirtnum.spr_index(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE')))
    errs = []
    with Session('shirt_numbers', b, {'DATA/TEAM.014': team}, 'dump:3', 300, match=True) as s:
        s.wait()
        for t in ('AMICHEVOLE', 'OK', 'SCEGLI SQUADRE', 'SQUADRE CLUB', 'EUROPA', 'GERMANIA', '1. LIGA', 'HAMBURG'):
            walk(s, t, 2)
        s.send('fire dump:2')                   # HAMBURG: COMPUTER -> GIOCA-ALLENA (human)
        walk(s, 'SCHALKE', 2)
        for _ in range(12):
            scr = s.screen()
            if scr.selected == 55:
                s.send('fire dump:4')
                break
            s.send(('right' if scr.selected in (56, 57) else 'down') + ' dump:0.5')
        for _ in range(22):                     # pre-match: down the rows to VIS. PARTITA
            s.send('down dump:0.5')
            if s.screen().selected == 9:
                break
        r = s.send('fire ' + 'fire:3 ' * 30 + 'dump:2')     # into the match: fire for the kicks
        check(r.outcome == 'dump', f'match: {r}', errs)
        if r.outcome == 'dump':
            ptrs = struct.unpack('<83I', r.read(r.base2 + spr + shirtnum.NEWBASE * 4, 83 * 4))
            check(all(ptrs) and ptrs[1] - ptrs[0] == 96, f'spritesIndex[1335..] {ptrs[:3]}', errs)
            if all(ptrs):
                m = r.read(ptrs[0] - 256, 256 + 83 * 96)
                check(m[0] == 1, f'build flag {m[0]}', errs)
                for n, want in SHIRT_EXPECT.items():
                    h = m[256 + (n - 17) * 96:]
                    w, nl = struct.unpack_from('<hh', h, 10)
                    rows = '|'.join(''.join('#' if h[24 + y * 8 + x // 2] >> (0 if x & 1 else 4) & 15 else '.'
                                            for x in range(w)) for y in range(nl))
                    ordn = struct.unpack_from('<h', h, 22)[0]
                    check(rows == want and ordn == shirtnum.NEWBASE + n - 17, f'{n}: {rows} #{ordn}', errs)
    return not errs, '; '.join(errs) or 'numbers 17..99 built (17, 20, 41, 99 pixel-exact) in a match'


@scenario
def india_season():
    """3.2.7 (Pietro): new career at EAST BENGAL (India, in the mod's Asian cups: season events up to week 128), whole
    season by results, FINISCI STAGIONE -> season-end menu -> next season saved (3.2.6: divide overflow, exit to DOS)"""
    with Session('india_season', builds()['it'], {}, 'dump:3', 500) as s:
        s.wait()
        for t in ('CARRIERA', 'SCEGLI SQUADRA', 'ASIA', 'INDIA', 'EAST BENGAL'):
            walk(s, t, 3)
        ok, msg = advance(s, season_over, 900)
        if not ok:
            return False, 'advance: ' + msg
        scr = s.screen()
        if scr.find('FINISCI STAGIONE', exact=True) is not None:
            press(s, scr, 'FINISCI STAGIONE', wait=3)
        for _ in range(30):
            if s.result.outcome != 'dump':
                return False, f'season end: {s.result}'
            scr = s.screen()
            if scr.find('CONTINUA CARRIERA', exact=True) is not None:
                break
            s.send('fire dump:2')
        path = next_season_save(s, 'IND2')
    return path.endswith('.CAR'), f'{msg}; next season {os.path.basename(path)}'


XTRA_CLUB, XTRA_FILE, XTRA_ORD = 'HAMBURG', 14, 17


def xtra_build():
    """The build under test when it has the XTRA hook (a world with "extra" squads), else a test build with XTRA_HOOK."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import xtra
    b = builds()['it']
    if xtra.hooked(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE'))):
        return b
    if not hasattr(xtra_build, 'cache'):
        xtra_build.cache = build('xtra_hook', env={'XTRA_HOOK': '1'})
    return xtra_build.cache


def xtra_test_file(path, extra=9):
    """Test DATA/XTRA.014: HAMBURG (ordinal 17) gets 9 players = copies of its own first 9 renamed XTRA TEST 1..9
    (same skills and price: an extra's wage = the reserve rate of his twin's)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import xtra
    d = open(os.path.join(ROOT, 'orig', 'DATA', 'TEAM.%03d' % XTRA_FILE), 'rb').read()
    k = struct.unpack('>H', d[:2])[0]
    ham = 2 + XTRA_ORD * 684
    assert d[ham + 5:ham + 22].split(b'\0')[0] == XTRA_CLUB.encode()
    pl = []
    for j in range(extra):
        q = bytearray(d[ham + 76 + j * 38:ham + 76 + (j + 1) * 38])
        q[3:26] = f'XTRA TEST {j + 1}'.encode().ljust(23, b'\0')
        q[2] = 30 + j
        pl.append(bytes(q))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(xtra.build({XTRA_ORD: pl}, k, extra))
    return pl


@scenario
def xtra_squad():
    """Extended career squads (xtra.py): a new career at HAMBURG with a test DATA/XTRA.014 starts with 16 + 9 real
    players (careerNumPlayers 25, slots 16..24 = the file's players, squad order 16..24) instead of the game's 10
    invented reserves, also after save + load; control: HANSA ROSTOCK (no block) gets 16 + 10 reserves = 26"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import xtra
    b = xtra_build()
    _, cnp, ct, cmp, sel = xtra.sites(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE')))
    path = os.path.join(WORK, 'saves', 'XTRA014_TEST.BIN')
    pl = xtra_test_file(path)
    errs, info = [], []
    with Session('xtra_squad', b, {'DATA/XTRA.%03d' % XTRA_FILE: path}, 'dump:3', 300) as s:
        s.wait()
        for t in ('CARRIERA', 'SCEGLI SQUADRA', 'EUROPA', 'GERMANIA'):
            walk(s, t, 3)
        if s.screen().find('1. LIGA') is not None:
            walk(s, '1. LIGA', 3)
        scr = walk(s, XTRA_CLUB, 4)
        r = s.result
        team = struct.unpack('<H', r.obj2(sel, 2))[0]
        n = struct.unpack('<H', r.obj2(cnp, 2))[0]
        order = list(r.obj2(cmp, 32))
        names = [r.obj2(ct + 76 + j * 38 + 3, 23).split(b'\0')[0].decode('latin1') for j in range(32)]
        info.append(f'team {team:#x}, {n} players, order {order[:n]}, slot 16 {names[16]!r}, slot 24 {names[24]!r}')
        check(team == XTRA_ORD << 8 | XTRA_FILE, f'managed team {team:#x}', errs)
        check(n == 25, f'careerNumPlayers {n}', errs)
        check(order[16:25] == list(range(16, 25)), f'squad order {order[16:25]}', errs)
        check(names[16:25] == [f'XTRA TEST {j + 1}' for j in range(9)], f'slots 16..24 {names[16:25]}', errs)
        check(r.obj2(ct + 684, 9 * 38) == b''.join(pl), 'slots 16..24 differ from the file', errs)
        for _ in range(10):                         # chairman's letter -> career menu
            scr = s.screen()
            if 'TRASFERIMENTI' in scr.texts():
                break
            press(s, scr, 'CONTINUA') or s.send('fire dump:2')
        r = s.result
        n = struct.unpack('<H', r.obj2(cnp, 2))[0]
        check(n == 25 and list(r.obj2(cmp, 25))[16:] == list(range(16, 25)),
              f'career menu: {n} players (the 10 invented reserves must not be added)', errs)
        form = [r.obj2(ct + 76 + j * 38 + 37, 1)[0] for j in range(16, 25)]
        check(form == [q[37] for q in pl], f'extras byte 37 (form) {form} changed', errs)
        wages = struct.unpack('<32I', r.obj2(xtra.wage_table(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE'))), 128))
        prices = [r.obj2(ct + 76 + j * 38 + 32, 1)[0] for j in range(32)]
        ratio = [round(wages[16 + j] / wages[j], 2) for j in range(9) if wages[j]]
        check(len(ratio) == 9 and all(0.6 <= x <= 0.7 for x in ratio), f'extra / twin wage {ratio} (66% expected)', errs)
        info.append(f'extra / twin wage {ratio}')
        press(s, s.screen(), 'ESCI', wait=3)
        if press(s, s.screen(), 'SALVA CARRIERA') is None:
            return False, f'no SALVA CARRIERA on {s.screen()}'
        s.send(name_entry('XTRA1') + ' dump:3')
        car = os.path.join(s.run, 'SWOS', 'XTRA1.CAR')
        if not os.path.exists(car):
            return False, f'XTRA1.CAR not written ({s.result}); ' + '; '.join(info)
        keep = os.path.join(WORK, 'saves', 'XTRA1.CAR')
        shutil.copy(car, keep)
    with Session('xtra_squad_load', b, {'XTRA1.CAR': keep}, 'dump:2', 120) as s:
        s.wait()
        s.send('down down down down down fire dump:2')      # CARICA VECCHIA COMPETIZIONE -> the only save
        r = s.send('fire dump:3')
        n2 = struct.unpack('<H', r.obj2(cnp, 2))[0]
        names2 = [r.obj2(ct + 76 + j * 38 + 3, 23).split(b'\0')[0].decode('latin1') for j in range(32)]
        check(n2 == 25 and names2[16:25] == names[16:25], f'after load: {n2} players, slot 16 {names2[16]!r}', errs)
        info.append(f'reloaded XTRA1.CAR: {n2} players; menu: ' + ', '.join(s.screen().texts())[:160])
    with Session('xtra_squad_ctl', b, {'DATA/XTRA.%03d' % XTRA_FILE: path}, 'dump:3', 300) as s:
        s.wait()                                # control: a club without an XTRA block keeps the game's reserves
        for t in ('CARRIERA', 'SCEGLI SQUADRA', 'EUROPA', 'GERMANIA'):
            walk(s, t, 3)
        if s.screen().find('1. LIGA') is not None:
            walk(s, '1. LIGA', 3)
        walk(s, 'HANSA ROSTOCK', 4)
        for _ in range(10):
            scr = s.screen()
            if 'TRASFERIMENTI' in scr.texts():
                break
            press(s, scr, 'CONTINUA') or s.send('fire dump:2')
        n3 = struct.unpack('<H', s.result.obj2(cnp, 2))[0]
        check(n3 == 26, f'HANSA ROSTOCK: {n3} players (16 + 10 reserves expected)', errs)
        info.append(f'HANSA ROSTOCK {n3} players')
    return not errs, '; '.join(errs + info)


@scenario
def xtra_season():
    """Extended career squads: XTRA1.CAR (HAMBURG with 25 players, made by xtra_squad) played to the season end by
    results, season-end menu, next season saved: no trap, at most 32 players, the real extras still in the squad"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import xtra
    b = xtra_build()
    _, cnp, ct, cmp, sel = xtra.sites(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE')))
    keep = os.path.join(WORK, 'saves', 'XTRA1.CAR')
    if not os.path.exists(keep):
        ok, msg = xtra_squad()
        if not ok:
            return False, 'xtra_squad: ' + msg
    errs, info = [], []
    xpath = os.path.join(WORK, 'saves', 'XTRA014_TEST.BIN')
    xtra_test_file(xpath)                       # the career's data file: the game reads it again for the wages
    with Session('xtra_season', b, {'XTRA1.CAR': keep, 'DATA/XTRA.%03d' % XTRA_FILE: xpath}, 'dump:2', 900) as s:
        s.wait()
        s.send('down down down down down fire dump:2')
        s.send('fire dump:3')
        ns = globals().get('nosack_off')         # the chairman never sacks (when this harness knows the switch)
        if ns:
            s.poke(s.result.base2 + ns(os.path.join(b, 'ITALIAN.EXE')), b'\x01\x00')
        ok, msg = advance(s, season_over, 900)
        if not ok:
            return False, 'advance: ' + msg
        r = s.result
        n = struct.unpack('<H', r.obj2(cnp, 2))[0]
        names = [r.obj2(ct + 76 + j * 38 + 3, 23).split(b'\0')[0].decode('latin1') for j in range(32)]
        order = list(r.obj2(cmp, 32))[:n]
        real = sum(1 for j in order if names[j].startswith('XTRA TEST'))
        check(16 <= n <= 32, f'season end: {n} players', errs)
        check(real >= 5, f'only {real} of the 9 real extras still in the squad', errs)
        info.append(f'season end: {n} players, {real} XTRA TEST in the squad; {msg}')
        scr = s.screen()
        if scr.find('FINISCI STAGIONE', exact=True) is not None:
            press(s, scr, 'FINISCI STAGIONE', wait=3)
        for _ in range(30):
            if s.result.outcome != 'dump':
                return False, f'season end: {s.result}; ' + '; '.join(info)
            scr = s.screen()
            if scr.find('CONTINUA CARRIERA', exact=True) is not None:
                break
            s.send('fire dump:2')
        r = s.result                            # twins again before the season start recomputes the wages: each extra
        twin = [r.obj2(ct + 76 + j * 38, 38) for j in range(9)]          # gets bytes 25..37 (form, skills, price) of
        for j in range(9):                                               # the record player he was copied from
            q = r.obj2(ct + 76 + (16 + j) * 38, 38)
            if q[3:26].split(b'\0')[0] == f'XTRA TEST {j + 1}'.encode():
                s.poke(r.base2 + ct + 76 + (16 + j) * 38 + 25, twin[j][25:38])
        path = next_season_save(s, 'XTRA2')
        check(path.endswith('.CAR'), f'next season: {path}', errs)
        if path.endswith('.CAR'):
            r = s.result
            n2 = struct.unpack('<H', r.obj2(cnp, 2))[0]
            info.append(f'next season saved, {n2} players')
            check(n2 <= 32, f'next season: {n2} players', errs)
            team = struct.unpack('<H', r.obj2(sel, 2))[0]
            if team != XTRA_ORD << 8 | XTRA_FILE:      # sacked: another club, no extras to check
                info.append(f'next season at another club ({team:#x}): wage check skipped')
                return not errs, '; '.join(errs + info)
            wages = struct.unpack('<32I', r.obj2(xtra.wage_table(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE'))), 128))
            names = [r.obj2(ct + 76 + j * 38 + 3, 23).split(b'\0')[0].decode('latin1') for j in range(32)]
            d = open(os.path.join(ROOT, 'orig', 'DATA', 'TEAM.%03d' % XTRA_FILE), 'rb').read()
            twin = [d[2 + XTRA_ORD * 684 + 76 + j * 38 + 3:][:23].split(b'\0')[0].decode('latin1') for j in range(9)]
            ratio = [round(wages[16 + j] / wages[j], 2) for j in range(9)
                     if names[16 + j] == f'XTRA TEST {j + 1}' and names[j] == twin[j] and wages[j]]
            check(ratio and all(0.6 <= x <= 0.7 for x in ratio), f'next season: extra / twin wage {ratio}', errs)
            info.append(f'next season extra / twin wage {ratio}')
    return not errs, '; '.join(errs + info)


BENCH_PATH = 'CARRIERA,SCEGLI SQUADRA,CARR. STORICHE,MONDO 2026-27,EUROPA,DANIMARCA,RANDERS'


@scenario
def bench_numbers():
    """World 2026-27 ('squad_numbers' world, benchnum.py): RANDERS keeps every real shirt number. New career (16 + 9
    XTRA players): the squad screen and the pre-match screen (both run SetBenchPlayersNumbers) leave the bench players'
    numbers as they were (not 12..16); then a season by results (the harness substitutions swap starters with bench /
    reserve players, XTRA ones included): every player still at the club has his first number, new players (trial
    players, reserves) got free ones, no number twice in the squad (at the start and at the end).
    Build: BENCH_BUILD (a world 2026-27 build with the hooks), default internal/swostest/builds/w2627-latest;
    BENCH_CONTROL=1 runs it on a build without them (negative control: it must fail)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import xtra
    import benchnum
    b = os.environ.get('BENCH_BUILD') or os.path.join(WORK, 'builds', 'w2627-latest')
    exe = os.path.join(b, 'ITALIAN.EXE')
    bench = benchnum.sites(lepatch.LEPatch(os.path.join(MAIN, 'orig', 'ITALIAN.EXE')))[0]
    if lepatch.LEPatch(exe).get(1, bench, 1) != b'\xe8' and not os.environ.get('BENCH_CONTROL'):
        return False, f'{b}: no benchnum hook (a world 2026-27 build with squad_numbers is needed)'
    _, cnp, ct, cmp, sel = xtra.sites(lepatch.LEPatch(exe))
    errs, info = [], []

    def squad(r):
        n = struct.unpack('<H', r.obj2(cnp, 2))[0]
        order = list(r.obj2(cmp, 32))[:n]
        rec = [r.obj2(ct + 76 + j * 38, 38) for j in order]
        return [(q[3:26].split(b'\0')[0].decode('latin1'), q[2]) for q in rec]

    with Session('bench_numbers', b, {}, 'dump:3', 900) as s:
        s.wait()
        for t in BENCH_PATH.split(','):
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'new career: {t} not reached ({s.result})'
        for _ in range(10):
            scr = s.screen()
            if 'TRASFERIMENTI' in scr.texts():
                break
            press(s, scr, 'CONTINUA') or s.send('fire dump:2')
        first = squad(s.result)
        num = dict(first)
        bench = [x for x in first[11:16]]
        info.append(f'{len(first)} players; bench {bench}')
        check(len(first) == 25, f'{len(first)} players (16 + 9 XTRA expected)', errs)
        dup = lambda sq: sorted({k for _, k in sq if [x for _, x in sq].count(k) > 1})
        check(not dup(first), f'start: duplicate numbers {dup(first)}', errs)
        check([x[1] for x in bench] != list(range(12, 17)), f'bench already 12..16: {bench}', errs)
        ns = globals().get('nosack_off')
        if ns:
            s.poke(s.result.base2 + ns(exe), b'\x01\x00')
        for entry in ('SQUADRA', 'PARTITA'):     # squad screen / pre-match screen: SetBenchPlayersNumbers
            press(s, s.screen(), entry, wait=3)
            now = squad(s.result)
            check(now == first, f'after {entry}: {[x for x in now if num.get(x[0]) != x[1]]}', errs)
            for _ in range(4):
                if 'TRASFERIMENTI' in s.screen().texts():
                    break
                press(s, s.screen(), 'ESCI', wait=2) or s.send('escape dump:2')
        ok, msg = advance(s, season_over, 900)
        if not ok:
            return False, 'advance: ' + msg + '; ' + '; '.join(errs + info)
        end = squad(s.result)
        moved = [(n, num[n], k) for n, k in end if n in num and num[n] != k]
        check(not moved, f'season end: numbers changed {moved}', errs)
        check(not dup(end), f'season end: duplicate numbers {dup(end)} in {end}', errs)
        new = [(n, k) for n, k in end if n not in num]
        info.append(f'new players {new}')
        info.append(f'season end: {len(end)} players, {sum(1 for n, _ in end if n in num)} of the first squad, '
                    f'{len(moved)} numbers changed; {msg}')
    return not errs, '; '.join(errs + info)


def menu_glyphs(r, spr):
    """The menu's small digits as menunum / shirtnum build them: {digit: [columns of pixels]} from sprites 162..171."""
    def sprite(i):
        ptr = struct.unpack('<I', r.read(r.base2 + spr + i * 4, 4))[0]
        h = r.read(ptr, 24)
        nl = struct.unpack_from('<h', h, 12)[0]
        px = r.read(struct.unpack('<I', h[:4])[0], nl * 8)
        return [[(px[y * 8 + x // 2] >> (0 if x & 1 else 4)) & 15 for x in range(16)] for y in range(nl)]
    cols = lambda g: [x for x in range(16) if any(row[x] for row in g)]
    out = {}
    for dgt in range(2, 10):
        g = sprite(161 + dgt)
        c = cols(g)
        out[dgt] = [[row[x] for row in g] for x in range(c[0], c[-1] + 1)]
    one = sprite(162)                   # the menu's "10" has no gap: 1 = its own sprite, 0 = "10" after that width
    c = cols(one)
    out[1] = [[row[x] for row in one] for x in range(c[0], c[-1] + 1)]
    ten = sprite(171)
    c = cols(ten)
    z = [x for x in c if x >= c[0] + len(out[1])]
    out[0] = [[row[x] for row in ten] for x in range(z[0], z[-1] + 1)]
    return out


@scenario
def menu_numbers():
    """3.3.4: shirt numbers 17..99 in the menus. MOD. TATTICA > UTN A (LEICESTER CITY's squad): its players poked to
    17..32, the pitch redrawn: the little numbers 12..99 are the new sprites 1620.. (menunum; the game's small numbers
    are 1..11 only), each one = tens digit, 1 pixel, units digit of the menu's own small digits (rebuilt here from
    sprites 162..171). MENU_PATH: the menu entries in another language (English: 'EDIT TACTICS,USER_A')"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import shirtnum
    import menunum
    b = builds()['it']
    exe = next(os.path.join(b, x) for x in ('ITALIAN.EXE', 'ENGLISH.EXE') if os.path.exists(os.path.join(b, x)))
    spr = shirtnum.spr_index(lepatch.LEPatch(exe))
    d = open(os.path.join(MAIN, 'orig', 'DATA', 'TEAM.008'), 'rb').read()
    lei = next(2 + i * 684 for i in range(struct.unpack('>H', d[:2])[0])
               if d[2 + i * 684 + 5:2 + i * 684 + 22].split(b'\0')[0] == b'LEICESTER CITY')
    first = d[lei + 76 + 3:lei + 76 + 26]
    errs, info = [], []
    with Session('menu_numbers', b, {}, 'dump:3', 300) as s:
        s.wait()
        for t in os.environ.get('MENU_PATH', 'MOD. TATTICA,UTN A').split(','):    # English: EDIT TACTICS,USER_A
            press(s, s.screen(), t, wait=3)
        r = s.result
        mem = r.mem
        recs = [m.start() - 3 - 76 for m in re.finditer(re.escape(first), mem)]
        recs = [x for x in recs if mem[x + 5:x + 19] == b'LEICESTER CITY']
        check(recs, 'LEICESTER CITY record not found in memory', errs)
        for x in recs:
            for k in range(16):
                s.poke(x + 76 + k * 38 + 2, bytes((17 + k,)))
        s.send('down dump:1')
        s.send('up dump:2')
        s.shot('menu_numbers')
        r = s.result
        ptrs = struct.unpack('<88I', r.read(r.base2 + spr + menunum.NEWBASE * 4, 88 * 4))
        check(all(ptrs), f'spritesIndex[{menunum.NEWBASE}..] not filled ({sum(1 for x in ptrs if x)} of 88)', errs)
        if all(ptrs):
            g = menu_glyphs(r, spr)
            for n in (12, 17, 20, 23, 32, 41, 99):
                h = r.read(ptrs[n - 12], 24)
                w, nl = struct.unpack_from('<hh', h, 10)
                px = r.read(struct.unpack('<I', h[:4])[0], nl * 8)
                got = [[(px[y * 8 + x // 2] >> (0 if x & 1 else 4)) & 15 for y in range(nl)] for x in range(w)]
                want = g[n // 10] + [[0] * nl] + g[n % 10]
                check(got == want and struct.unpack_from('<h', h, 22)[0] == menunum.NEWBASE + n - 12,
                      f'{n}: sprite differs from tens + gap + units', errs)
            info.append(f'{len(recs)} copies of LEICESTER poked to 17..32; sprites 12..99 built, checked 12 17 20 23 32 '
                        f'41 99')
    return not errs, '; '.join(errs + info) + f' (screenshot runs/menu_numbers/shots/menu_numbers.png)'


PURPLE_RGB, MAROON_MENU = (24, 8, 34), (27, 0, 9)


def italy_friendly(s, home, away):
    """Main menu -> AMICHEVOLE, ITALIA SERIE A: home (human) and away (computer) -> pre-match screen of home."""
    for t in ('AMICHEVOLE', 'OK', 'SCEGLI SQUADRE', 'SQUADRE CLUB', 'EUROPA'):
        walk(s, t, 2)
    for _ in range(30):                         # ITALIA (49): one key at a time down the middle column
        sel = s.screen().selected
        if sel == 49:
            break
        s.send(('down' if sel < 49 else 'up') + ' dump:0.5')
    s.send('fire dump:3')
    walk(s, 'SERIE A', 2)
    walk(s, home, 2)
    s.send('fire dump:2')                       # home: COMPUTER -> GIOCA-ALLENA
    walk(s, away, 2)
    for _ in range(12):
        scr = s.screen()
        i = scr.find('AMICHEVOLE', exact=True)
        if scr.selected == i:
            s.send('fire dump:4')
            return s.screen()
        s.send(('right' if scr.selected in (i + 1, i + 2) else 'down') + ' dump:0.5')
    raise AssertionError('AMICHEVOLE not reached')


@scenario
def purple_kits():
    """3.3.0: kit colour 10 = purple (Fiorentina): palette entry 12 purple in the SELECT KITS editor for Fiorentina and
    maroon for Inter, purple in the match Fiorentina-Inter and Fiorentina-Roma (Roma's maroon kit clashes: green away);
    3.3.1: Inter in Barcelona's kits (blue and maroon stripes): the automatic choice avoids purple vs maroon; SELECT KITS
    opens on the automatic choice (Fiorentina-Roma: Roma second kit) and OK plays it; 3.3.3: the team name box in the
    colour of who controls the team (purple player, red computer); 3.3.4 (Marco): purple has palette entry 4 of its
    own in the editor and entry 12 stays maroon, so a maroon part of Fiorentina's second kit leaves the first purple"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    b = builds()['it']
    p = lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE'))
    import re as _re
    fp = _re.search(rb'\xbf....\xbe....\xb9\x0f\x00\x00\x00', p.le.obj_bytes(1), _re.S)
    working = p.target(1, fp.start() + 6)[1]
    errs, info = [], []
    d = bytearray(open(os.path.join(b, 'DATA', 'TEAM.020'), 'rb').read())
    for t in range(struct.unpack('>H', d[:2])[0]):          # 3.3.1: INTER MILAN in Barcelona's kits (blue and
        o = 2 + t * 684                                      # maroon stripes / light blue): purple vs maroon stripes
        if d[o + 5:o + 22].split(b'\0')[0] == b'INTER':
            d[o + 26:o + 36] = bytes([2, 5, 6, 5, 5, 0, 7, 7, 7, 7])
    fio = bytearray(open(os.path.join(b, 'DATA', 'TEAM.020'), 'rb').read())
    for t in range(struct.unpack('>H', fio[:2])[0]):        # 3.3.4 (Marco): Fiorentina's second kit with maroon
        o = 2 + t * 684                                      # shorts: the purple first kit stays purple in SELECT KITS
        if fio[o + 5:o + 22].split(b'\0')[0] == b'FIORENTINA':
            fio[o + 34] = 6
    fiom = os.path.join(WORK, 'saves', 'TEAM020_FIOMAROON.BIN')
    barca = os.path.join(WORK, 'saves', 'TEAM020_BARCA.BIN')
    os.makedirs(os.path.dirname(barca), exist_ok=True)
    open(barca, 'wb').write(d)
    open(fiom, 'wb').write(fio)
    for away, kits, cars in (('INTER', True, {'DATA/TEAM.020': fiom}), ('ROMA', False, {}),
                             ('INTER', False, {'DATA/TEAM.020': barca})):
        with Session('purple_kits_' + away[:5] + ('_barca' if cars and not kits else ''), b, cars, 'dump:3', 300, match=True) as s:
            s.wait()
            italy_friendly(s, 'FIORENTINA', away)
            if kits:
                scr = walk(s, 68, 3)
                pal = s.result.read(s.result.base2 + working + 36, 3)      # 3.3.4: purple has entry 120 of its
                own = s.result.read(s.result.base2 + working + 12, 3)      # own, entry 12 stays the menus' maroon
                check(scr.entries[1][1] == 'FIORENTINA' and tuple(own) == PURPLE_RGB and tuple(pal) == MAROON_MENU,
                      f'editor {scr.entries[1][1]} entry 4 {tuple(own)} entry 12 {tuple(pal)}', errs)
                s.shot('purple_kits_editor')        # Fiorentina: purple first kit, maroon second shorts
                check(scr.colors[1] == 11, f'team name box {scr.colors[1]} for the human player (want 11, purple)', errs)
                scr = walk(s, 1, 3)             # the other team
                check(scr.colors[1] == 10, f'team name box {scr.colors[1]} for the computer (want 10, red)', errs)
                pal = s.result.read(s.result.base2 + working + 36, 3)
                check(tuple(pal) == MAROON_MENU, f'editor {s.screen().entries[1][1]} {tuple(pal)}', errs)
                walk(s, 20, 3)                  # ESCI
                s.screen()                      # entry 4 back to the menus' skin brown outside the editor
                after = tuple(s.result.read(s.result.base2 + working + 12, 3))
                check(after == (27, 9, 0), f'entry 4 after SELECT KITS {after} (want 27, 9, 0)', errs)
            elif away == 'ROMA':                # 3.3.1 (Marco): SELECT KITS opens on the automatic choice (Roma's
                scr = walk(s, 68, 3)            # maroon vs purple: Roma in its second kit), and OK keeps it
                t = scr.texts()
                check('IN CAMPO: PRIMA TENUTA' in t and 'ROMA: SECONDA TENUTA' in t, f'SELECT KITS opens on {t[:5]}', errs)
                walk(s, 21, 3)                  # OK: the match is played in these kits
            for _ in range(22):
                s.send('down dump:0.5')
                if s.screen().selected == 9:
                    break
            r = s.send('fire ' + 'fire:3 ' * 8 + 'dump:2')
            check(r.outcome == 'dump', f'{away}: match {r}', errs)
            if r.outcome == 'dump':
                pal = tuple(r.read(r.base2 + working + 36, 3))
                o2 = r.read(r.base2, 0x100000)
                m = o2.find(b'PKMK')
                marks = tuple(o2[m + 4:m + 6]) if m >= 0 else None
                worn = (marks[0] | marks[1]) if marks else None     # bit 0 purple, bit 1 maroon worn
                want = PURPLE_RGB if worn == 1 else (25, 0, 8)
                check(marks is not None and pal == want and worn != 3, f'match vs {away}: marks {marks}, entry 12 {pal}', errs)
                info.append(f"{away}{' (Barcelona kits)' if cars and not kits else ''}: marks {marks}")
                if away == 'INTER' and kits:
                    check(worn == 1, f'Fiorentina-Inter: purple not worn ({marks})', errs)
    return not errs, '; '.join(errs + info) if errs else 'purple in the editor (maroon for Inter) and vs Inter; ' + '; '.join(info)


@scenario
def purple_manual():
    """3.3.2 (Marco): kits set by hand never put purple against maroon. Fiorentina-Roma with Roma forced into its maroon
    first kit: Roma plays its green second kit; against Zenit's kits (maroon / white with maroon shorts) forced into the
    first kit: the second kit with white shorts. Fiorentina stays purple in both"""
    errs, info = [], []
    b = builds()['it']
    d = bytearray(open(os.path.join(b, 'DATA', 'TEAM.020'), 'rb').read())
    for t in range(struct.unpack('>H', d[:2])[0]):
        o = 2 + t * 684
        if d[o + 5:o + 22].split(b'\0')[0] == b'ROMA':
            d[o + 26:o + 36] = bytes([0, 6, 6, 1, 6, 0, 1, 1, 6, 1])     # ZENIT's kits
    zenit = os.path.join(WORK, 'saves', 'TEAM020_ZENIT.BIN')
    os.makedirs(os.path.dirname(zenit), exist_ok=True)
    open(zenit, 'wb').write(d)
    for tag, cars in (('roma', {}), ('zenit', {'DATA/TEAM.020': zenit})):
        with Session('purple_manual_' + tag, b, cars, 'dump:3', 300, match=True) as s:
            s.wait()
            italy_friendly(s, 'FIORENTINA', 'ROMA')
            scr = walk(s, 68, 3)                # SELECT KITS: both teams in their first kits, by hand
            for _ in range(2):
                if 'IN CAMPO: SECONDA TENUTA' in scr.texts():
                    scr = walk(s, 2, 3)
                scr = walk(s, 1, 3)             # the other team
            t = scr.texts()
            check('IN CAMPO: PRIMA TENUTA' in t and 'ROMA: PRIMA TENUTA' in t + ['FIORENTINA: PRIMA TENUTA']
                  and not any(x.endswith('SECONDA TENUTA') for x in t), f'{tag}: not both first kits: {t[:5]}', errs)
            walk(s, 21, 3)                      # OK
            for _ in range(22):
                s.send('down dump:0.5')
                if s.screen().selected == 9:
                    break
            r = s.send('fire ' + 'fire:3 ' * 8 + 'dump:2')
            check(r.outcome == 'dump', f'{tag}: match {r}', errs)
            if r.outcome == 'dump':
                o2 = r.read(r.base2, 0x100000)
                m = o2.find(b'PKMK')
                marks = tuple(o2[m + 4:m + 6]) if m >= 0 else None
                check(marks is not None and (marks[0] | marks[1]) == 1, f'{tag}: marks {marks} (want purple only)', errs)
                info.append(f'{tag}: marks {marks}')
    return not errs, '; '.join(errs + info) if errs else 'manual kits: purple kept, no maroon (' + '; '.join(info) + ')'


@scenario
def purple_stadium():
    """3.3.1: the line-ups screen before the match (ShowStadiumInit) keeps Fiorentina purple: palette entry 12 purple
    after the screen's second copy of the stad.256 palette (breakpoints: normal core)"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import re as _re
    os.environ['CORE'] = 'normal'               # one process per scenario: only this one runs the slower core
    b = builds()['it']
    p = lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE'))
    d1 = p.le.obj_bytes(1)
    m = _re.search(rb'\x81\xC6\x00\xFA\x00\x00\xBF....(?:\xB9\x00\x03\x00\x00\xF3\xA4|\xE8....\x90\x90)\xFF\x35', d1, _re.S)
    after = m.end() - 2                         # the `push D0` after the copy the screen keeps (hooked or not)
    fp = _re.search(rb'\xbf....\xbe....\xb9\x0f\x00\x00\x00', d1, _re.S)
    working = p.target(1, fp.start() + 6)[1]
    got = []
    with Session('purple_stadium', b, {}, 'dump:3', 300, match=True) as s:
        s.wait()
        italy_friendly(s, 'INTER', 'FIORENTINA')
        base1, base2 = s.result.base1, s.result.base2
        s.bp(base1 + after, lambda r: got.append(tuple(r.read(base2 + working + 36, 3))))
        for _ in range(22):
            s.send('down dump:0.5')
            if s.screen().selected == 9:
                break
        r = s.send('fire ' + 'fire:3 ' * 4 + 'dump:2')
    ok = r.outcome == 'dump' and got and got[0] == PURPLE_RGB
    return ok, f'line-ups screen entry 12 {got} ({r.outcome})'


@scenario
def blond_faces():
    """3.3.0: face 3 = black skin + blond hair: FIORENTINA's outfield players set to face 3 (test copy of TEAM.020);
    pre-match face icon 189 built (yellow hair), in the match the new sprite set 1418.. is registered and has hair in
    entry 15 (yellow) and dark skin (no entry 5)"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lepatch
    import shirtnum
    import blond
    b = builds()['it']
    d = bytearray(open(os.path.join(b, 'DATA', 'TEAM.020'), 'rb').read())
    for t in range(struct.unpack('>H', d[:2])[0]):
        o = 2 + t * 684
        if d[o + 5:o + 22].split(b'\0')[0] == b'FIORENTINA':
            for j in range(16):
                if d[o + 76 + j * 38 + 26] >> 5:
                    d[o + 76 + j * 38 + 26] |= 0x18
    team = os.path.join(WORK, 'saves', 'TEAM020_BLOND.BIN')
    os.makedirs(os.path.dirname(team), exist_ok=True)
    open(team, 'wb').write(d)
    spr = shirtnum.spr_index(lepatch.LEPatch(os.path.join(b, 'ITALIAN.EXE')))
    errs = []
    nib = lambda data: [x >> 4 for x in data] + [x & 15 for x in data]
    with Session('blond_faces', b, {'DATA/TEAM.020': team}, 'dump:3', 300, match=True) as s:
        s.wait()
        italy_friendly(s, 'FIORENTINA', 'INTER')
        r = s.result
        p189 = struct.unpack('<I', r.read(r.base2 + spr + 189 * 4, 4))[0]
        icon = r.read(struct.unpack('<I', r.read(p189, 4))[0], 64) if p189 else b''
        check(15 in nib(icon[:24]), f'face icon 189 without yellow hair ({icon[:24].hex()})', errs)
        for _ in range(22):
            s.send('down dump:0.5')
            if s.screen().selected == 9:
                break
        r = s.send('fire ' + 'fire:3 ' * 8 + 'dump:2')
        check(r.outcome == 'dump', f'match {r}', errs)
        if r.outcome == 'dump':
            ptrs = struct.unpack('<202I', r.read(r.base2 + spr + blond.NEW1 * 4, 202 * 4))
            check(all(ptrs), 'sprite set not registered', errs)
            if all(ptrs):
                h = r.read(ptrs[0], 24)
                w, nl, wq = struct.unpack_from('<hhh', h, 10)
                px = nib(r.read(struct.unpack('<I', h[:4])[0], wq * 8 * nl))
                check(15 in px and 5 not in px, f'set 1418 frame 0: yellow {15 in px}, light skin 5 {5 in px}', errs)
    return not errs, '; '.join(errs) or 'blond face icon in the pre-match screen; sprite set 1418.. yellow hair, dark skin'



@scenario
def world_byes():
    """National-cup first-round byes in a career (lib97 nc_bye / nc_adv): the template world (packs/_template_world)
    with the ALPHA cup cut to 6 clubs, 2 of them with a bye (ALPHA ROVERS, ALPHA ATHLETIC); career at ALPHA ROVERS:
    it plays no round 1, round 1 is ties.csv's (fixed draw, first season), round 2 the fixed draw (ALPHA ROVERS v
    ALPHA ATHLETIC = its a3 v a4), it plays its semi-final, the season ends"""
    import csv
    import shutil
    pk = os.path.join(WORK, 'packs', 'world-byes')
    shutil.rmtree(pk, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, 'packs', '_template_world'), pk)
    f = os.path.join(pk, 'alpha', 'ties.csv')
    rows = list(csv.DictReader(open(f)))
    r1 = [r for r in rows if r['round'] == '1']
    byes = [{'competition': r['competition'], 'round': '1', 'home': r['winner'], 'away': '', 'winner': ''} for r in r1[2:]]
    with open(f, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['competition', 'round', 'home', 'away', 'winner'])
        w.writeheader()
        w.writerows(r1[:2] + byes + [r for r in rows if r['round'] != '1'])
    exe = build('world_byes', env={'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(pk, x) for x in ('alpha', 'beta')])})
    errs, titles, slot, seen = [], [], [None], []
    with Session('world_byes', exe, {}, 'dump:2', 900) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: {s.result}'
        for t in ('CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', '1984-85', 'ALPHA', 'ALPHA LEAGUE', 'ALPHA ROVERS'):
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'new career: {t} not reached ({s.result})'
        d = s.result.obj2(0, 0x100000)                  # the ALPHA cup's slot (id D3, 6 clubs)
        hits = [i - 0x2D for i in range(0x2D, len(d) - 0x443) if d[i] == 0xD3 and d[i + 4:i + 6] == b'\x06\x00'
                and d[i - 0x2D + 0x59] == 3]
        if not hits:
            return False, 'ALPHA cup slot not found'
        slot[0] = hits[0]
        start = list(s.result.obj2(slot[0] + 0x2CD, 6))   # round 1 in ties.csv order (fixed draw, first season)

        def stop(scr):
            t = scr.entries[0][1] if scr.entries else ''
            if 'ALPHA CUP' in t and t not in titles:
                titles.append(t)
            c = s.result.obj2(slot[0], 0x443)
            if c[0x57] == 1 and not seen:
                seen.append(list(c[0x2CD:0x2CD + 4]))
            return season_over(scr)
        ok, msg = advance(s, stop, 300)
    semi = bool(titles) and 'SEMIFINALE' in titles[0]
    if not ok and semi and 'squad screen' in msg:       # (the template's 16-man squads: no fit stand-in left after
        msg += ' (after the semi-final: accepted)'      # injuries; the cup checks below are already decided)
        ok = True
    check(ok, msg, errs)
    check(semi, f'ALPHA ROVERS cup matches {titles} (first must be the semi-final)', errs)
    check(start[:4] == [0, 1, 2, 3], f'round 1 list {start} (ties.csv order: 0 1 2 3, byes 4 5 left out)', errs)
    check(seen and seen[0][0] in (2, 3) and seen[0][1] in (0, 1) and seen[0][2:4] == [4, 5],
          f'round 2 list {seen} (fixed draw: winner of tie 2 v winner of tie 1, then 4 v 5 = ties.csv a2-a1, a3-a4)', errs)
    return not errs, '; '.join(errs) or f'{msg}; cup matches {titles}; round 1 {start[:4]}, round 2 list {seen[0]}'



@scenario
def world_groups():
    """Parallel groups of one level (pgroups.py): the world 2026-27 (private data internal/world2526/world5tm) with
    Italy's Serie C as 3 groups of 20 below Serie B ('parallel', groups promote their winner only, B's 3 relegated
    clubs spread over the groups by area); a season at RENATE (Serie C): after it every Italian division holds 20,
    the 3 group winners are in B, B's 3 relegated clubs are in the groups, no club moved between groups"""
    import collections
    import json
    import shutil
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    if not os.path.isdir(src):
        return True, 'SKIP: private data internal/world2526/world5tm missing'
    w = os.path.join(WORK, 'world_groups')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    f = os.path.join(w, 'world5tm', 'ita', 'pack.json')
    d = json.load(open(f))
    lg = next(c for c in d['competitions'] if c['type'] == 'league')
    dv = lg['divisions']
    dv[1]['promoted'], dv[1]['relegated'] = 3, 3
    for g in (2, 3, 4):
        dv[g]['promoted'], dv[g]['relegated'] = 1, 0
    lg['parallel'] = {'upper': 1, 'first': 2, 'count': 3}
    lg.pop('playoffs', None)                    # (pgroups alone: no dplay moves; world_playoffs has them)
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]   # (the converter's file order)
    packs = [os.path.join(w, 'world5tm', x) for x in order]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + packs)}
    exe = build('world_groups', env=env)
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = env['SEASON_PACKS']
    import mkseason
    pk = [p for p in mkseason.packs() if p.parallel()][0]
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    _, levels, clubs = pk.parallel()
    first, sizes = next((d, sz) for d, sz in levels if len(sz) > 1)
    u = first - 1
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_SEASONS')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM='EUROPA,ITALIA,SERIE C GIRONE A,RENATE',
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if not os.path.exists(car):
        return False, f'no season-1 save: {msg}'
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]           # someLeaguesTable (ITA save offset)
    cnt, ups, downs, side = collections.Counter(), 0, 0, 0
    for g, base, _ in clubs:
        new = base + struct.unpack('b', slt[g:g + 1])[0]
        cnt[new] += 1
        if base >= first and new == u:
            ups += 1
        elif base == u and new >= first:
            downs += 1
        elif base >= first and new >= first and new != base:
            side += 1
    errs = []
    check(ok, msg, errs)
    check(all(cnt[first + i] == n for i, n in enumerate(sizes)) and cnt[u] == 20, f'divisions {sorted(cnt.items())}', errs)
    check(ups == len(sizes) and downs == 3 and side == 0, f'group winners up {ups}, B down {downs}, group to group {side}', errs)
    return not errs, '; '.join(errs) or f'{msg}; divisions {sorted(cnt.items())}; up {ups}, down {downs}'



@scenario
def world_playoffs():
    """Italian play-offs at the season end (dplay.py): the world 2026-27 (private data internal/world2526/world5tm)
    with Serie B promoted 2 / relegated 3, the Serie C groups promoted 1 / relegated 0 and league 'playoffs': 'ita';
    a season at RENATE (Serie C, Serie B simulated): after it every Italian division holds 20, Serie B sent 3 up and
    4 down, the groups sent 4 up (3 winners + the play-off winner), no club moved between groups"""
    import collections
    import json
    import shutil
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    if not os.path.isdir(src):
        return True, 'SKIP: private data internal/world2526/world5tm missing'
    w = os.path.join(WORK, 'world_playoffs')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    f = os.path.join(w, 'world5tm', 'ita', 'pack.json')
    d = json.load(open(f))
    lg = next(c for c in d['competitions'] if c['type'] == 'league')
    dv = lg['divisions']
    dv[1]['promoted'], dv[1]['relegated'] = 2, 3
    for g in (2, 3, 4):
        dv[g]['promoted'], dv[g]['relegated'] = 1, 0
    lg['parallel'] = {'upper': 1, 'first': 2, 'count': 3}
    lg['playoffs'] = 'ita'
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]   # (the converter's file order)
    packs = [os.path.join(w, 'world5tm', x) for x in order]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + packs)}
    exe = build('world_playoffs', env=env)
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = env['SEASON_PACKS']
    import mkseason
    pk = [p for p in mkseason.packs() if p.parallel()][0]
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    _, levels, clubs = pk.parallel()
    first, sizes = next((d, sz) for d, sz in levels if len(sz) > 1)
    u = first - 1
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_SEASONS')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM='EUROPA,ITALIA,SERIE C GIRONE A,RENATE',
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if not os.path.exists(car):
        return False, f'no season-1 save: {msg}'
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]           # someLeaguesTable (ITA save offset)
    cnt, mv = collections.Counter(), collections.Counter()
    for g, base, _ in clubs:
        new = base + struct.unpack('b', slt[g:g + 1])[0]
        cnt[new] += 1
        if new != base:
            mv['A' if base == 0 else 'B' if base == u else 'C', 'A' if new == 0 else 'B' if new == u else
               'C' if new >= first else '?'] += 1
            if base >= first and new >= first:
                mv['C-C'] += 1
    errs = []
    check(ok, msg, errs)
    check(all(cnt[first + i] == n for i, n in enumerate(sizes)) and cnt[u] == 20 and cnt[0] == 20,
          f'divisions {sorted(cnt.items())}', errs)
    check(mv['B', 'A'] == 3 and mv['A', 'B'] == 3 and mv['B', 'C'] == 4 and mv['C', 'B'] == 4 and not mv['C-C'],
          f'moves {dict(mv)}', errs)
    return not errs, '; '.join(errs) or f'{msg}; divisions {sorted(cnt.items())}; moves {dict(mv)}'


@scenario
def world_dplay_b(force='5', team='EUROPA,ITALIA,SERIE B,MODENA'):
    """The career club's Serie B play-off, played (dplay step 2): the world 2026-27 (private data internal/world2526/
    world5tm, 'playoffs': 'ita') built with DPLAY_FORCE=5 (at the league end the career club takes 5th place); a
    season at MODENA: the PLAY-OFF SERIE B contest is built in slot 4 after the last league day and played to its
    end (the season log in W84A.CAR: kind 1, the 6 clubs with MODENA 5th in the order 5th 8th 6th 7th 3rd 4th, a
    winner among them), and that winner is the club Serie B sends up besides the first two"""
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    if not os.path.isdir(src):
        return True, 'SKIP: private data internal/world2526/world5tm missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order]), 'DPLAY_FORCE': force}
    exe = build('world_dplay_' + force, env=env)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team,
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    os.environ.setdefault('W8485_HEX', '156d8:16,18e04:4,1b528:6')   # (the session log: the state's head, slot 4)
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if not os.path.exists(car):
        return False, f'no season-1 save: {msg}'
    d = open(car, 'rb').read()
    k = d.find(b'DPLG')
    errs = []
    check(ok, msg, errs)
    if k < 0:
        return False, f'{msg}; no dplay log in W84A.CAR'
    magic, res, kind, n = struct.unpack_from('<HHBB', d, k + 4)      # dplay.c dp_save (912 B)
    teams = struct.unpack_from('<28H', d, k + 4 + 8)
    places = d[k + 4 + 120:k + 4 + 148]
    groups = d[k + 4 + 148:k + 4 + 176]
    nmv = d[k + 4 + 912]                                     # (then dp_out's head: nmv, ntie, ..)
    mv = [struct.unpack_from('<HHb', d, k + 4 + 912 + 4 + 8 * i) for i in range(min(nmv, 4))]
    out, cpo = force in ('16', '17'), int(force) > 100
    want = (3, 28) if cpo else (2, 2) if out else (1, 6)
    check(magic == 0x5044 and (kind, n) == want, f'state magic {magic:#x} kind {kind} n {n}', errs)
    if cpo:                                                  # 5th v 10th, 6th v 9th, 7th v 8th per group, 4ths, 3rds,
        check(list(places[:18]) == [4, 9, 5, 8, 6, 7] * 3 and list(places[18:24]) == [3] * 3 + [2] * 3 and places[24] == 10
              and list(places[25:]) == [1] * 3 and list(groups[:18]) == [g for g in (1, 2, 3) for _ in range(6)],
              f'places {list(places)} groups {list(groups)}', errs)   # the best 11th, 2nds
    else:
        check(list(places[:n]) == ([16, 15] if out else [4, 7, 5, 6, 2, 3]), f'places {list(places[:n])}', errs)
    check(res in teams[:n], f'winner {res:#x} not among {[hex(t) for t in teams[:n]]}', errs)
    if cpo:
        check(any(t == res and dl == -1 for _, t, dl in mv), f'C winner {res:#x} not moved up: moves {mv}', errs)
        sys.path.insert(0, os.path.join(ROOT, 'tools'))      # the two groups simulated at the league end: their
        old = os.environ.get('SEASON_PACKS')                   # winners then (the state's tables) = the clubs the
        os.environ['SEASON_PACKS'] = env['SEASON_PACKS']       # season end promoted from them
        import mkseason
        pk = [p for p in mkseason.packs() if p.parallel()][0]
        if old is None:
            os.environ.pop('SEASON_PACKS')
        else:
            os.environ['SEASON_PACKS'] = old
        glob = {}
        for key in pk.league_clubs:
            fl, i = pk.where[key]
            base = next(b for fk, (ff, b) in pk.files.items() if ff == fl)
            glob[fl | (i << 8)] = base + i
        slt = d[0xE8DC:0xE8DC + 2000]
        sg = d[k + 4 + 270:k + 4 + 272]
        for j in range(2):
            win = struct.unpack_from('<H', d, k + 4 + 272 + 320 * j)[0]
            g = glob.get(win)
            check(sg[j] and g is not None and sg[j] + struct.unpack('b', slt[g:g + 1])[0] == 1,   # (-> Serie B, pgroups)
                  f'group division {sg[j]}: early winner {win:#x} (global {g}) not promoted', errs)
    elif out:                                                # the play-out's loser goes down
        lose = teams[1] if res == teams[0] else teams[0]
        check(any(t == lose and dl == 1 for _, t, dl in mv), f'loser {lose:#x} not moved down: moves {mv}', errs)
    else:
        check(any(t == res and dl == -1 for _, t, dl in mv), f'winner {res:#x} not moved up: moves {mv}', errs)
    return not errs, '; '.join(errs) or (f'{msg}; clubs {[hex(t) for t in teams[:n]]}, winner {res:#x} '
                                         f'(place {places[teams.index(res)] + 1}), moves {mv}')



SPLITS = {   # world_split kinds: country, career path (ITA), the 'split' of its first division (formats2627.md)
    'single': ('sco', 'EUROPA,SCOZIA,SCOTTISH PREMIERSHIP,ST. MIRREN',
               {'after': 33, 'home': 'balance', 'groups': [{'places': [1, 6], 'rounds': 'single'},
                                                            {'places': [7, 12], 'rounds': 'single'}]}),
    'double': ('aut', 'EUROPA,AUSTRIA,HARTBERG',
               {'after': 22, 'groups': [{'places': [1, 6], 'rounds': 'double'}, {'places': [7, 12], 'rounds': 'double'}]}),
    'h2h': ('mda', 'EUROPA,MOLDAVIA,PETROCUB',
            {'after': 21, 'groups': [{'places': [1, 6], 'rounds': 'double', 'points': 'h2h_half'},
                                     {'places': [7, 8], 'rounds': 'none'}]}),
    'reverse3': ('nir', 'EUROPA,ALTRE NAZIONI,IRLANDA DEL NORD,BANGOR',
                 {'after': 33, 'home': 'reverse3', 'groups': [{'places': [1, 6], 'rounds': 'single'},
                                                              {'places': [7, 12], 'rounds': 'single'}]}),
    'odd': ('bul', 'EUROPA,BULGARIA,LOKOMOTIV SOFIA',
            {'after': 26, 'groups': [{'places': [1, 4], 'rounds': 'double'}, {'places': [5, 9], 'rounds': 'double'},
                                     {'places': [10, 14], 'rounds': 'single'}]}),
    'three': ('gre', 'EUROPA,GRECIA,VOLOS',
              {'after': 26, 'groups': [{'places': [1, 4], 'rounds': 'double'},
                                       {'places': [5, 8], 'rounds': 'double', 'points': 'half_up'},
                                       {'places': [9, 14], 'rounds': 'double'}]}),
    'none': ('cze', 'EUROPA,REP. CECA,PARDUBICE',
             {'after': 30, 'groups': [{'places': [1, 6], 'rounds': 'single'}, {'places': [7, 10], 'rounds': 'none'},
                                      {'places': [11, 16], 'rounds': 'single'}]}),
    'stages': ('mlt', 'EUROPA,MALTA,HIBERNIANS',
               {'stages': [{'after': 11, 'groups': [{'places': [1, 6], 'rounds': 'single'},
                                                    {'places': [7, 12], 'rounds': 'single'}]},
                           {'after': 16, 'reset': True, 'keep': 'opening', 'home': 'reverse1',
                            'groups': [{'places': [1, 12], 'rounds': 'single'}]},
                           {'after': 27, 'groups': [{'places': [1, 6], 'rounds': 'single'},
                                                    {'places': [7, 12], 'rounds': 'single'}]}]}),
    'halved': ('rou', 'EUROPA,ROMANIA,BOTOSANI',
               {'after': 30, 'groups': [{'places': [1, 6], 'rounds': 'double', 'points': 'half_up'},
                                        {'places': [7, 16], 'rounds': 'single', 'points': 'half_up'}]}),
}


def split_build():
    """The world 2026-27 (private data internal/world2526/world5tm) with the three SPLITS; SPLIT_BUILD reuses one."""
    import json
    if os.environ.get('SPLIT_BUILD'):
        return os.environ['SPLIT_BUILD']
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    w = os.path.join(WORK, 'world_split')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    for c, _, sp in SPLITS.values():
        f = os.path.join(w, 'world5tm', c, 'pack.json')
        d = json.load(open(f))
        lg = next(x for x in d['competitions'] if x['type'] == 'league')
        (lg['divisions'][0] if 'divisions' in lg else lg)['split'] = sp
        json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    return build('world_split', env={'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(w, 'world5tm', x)
                                                                                for x in order])})


def split_check_stages(log, key):
    """A chain of stages (Malta): days, every stage frozen, the figures since the last reset, the last stage's
    groups in place order, the 'keep' table (rows by place, points by place)."""
    import split
    diys = [b for b in (bytes.fromhex(ln[4:]) for ln in log if ln.startswith('DIY ')) if b[0:2] == b'\0\0']
    if not diys:
        return False, 'no snapshot of the split league'
    clubs = lambda b: sorted(b[0x12D:0x12D + 2 * struct.unpack_from('<H', b, 0x31)[0]])
    diys = [b for b in diys if clubs(b) == clubs(diys[0])]
    last, st, o = diys[-1], split.ST, split.OFF
    w = lambda b, k: struct.unpack_from('<H', b, k)[0]
    n = w(last, 0x31)
    stg = key['stages']
    rnd = {'none': 0, 'single': 1, 'double': 2, 'triple': 3, 'quadruple': 4}
    sizes = [[g['places'][1] - g['places'][0] + 1 for g in x['groups']] for x in stg]
    rounds = [[rnd[g.get('rounds', 'single')] for g in x['groups']] for x in stg]
    total = stg[0]['after'] + sum(len(split.schedule(z, r)) for z, r in zip(sizes, rounds))
    errs = []
    check(w(last, 0x1C3) == total and w(last, 0x1C1) == total and w(last, 0x5F) == 0,
          f'days {w(last, 0x1C3)} / day {w(last, 0x1C1)} / cycles {w(last, 0x5F)}, {total} wanted', errs)
    check(last[st + o['frozen']] == len(stg), f'frozen stage {last[st + o["frozen"]]}, {len(stg)} wanted', errs)
    first = max([i for i, x in enumerate(stg) if x.get('reset')] or [0])
    per = []
    for z, r in zip(sizes[first:], rounds[first:]):
        m = {(a - 1) * b for a, b in zip(z, r)}
        per.append(m.pop() if len(m) == 1 else None)
    want = None if None in per else sum(per) + (0 if any(x.get('reset') for x in stg) else stg[0]['after'])
    rec = lambda r: struct.unpack_from('<I7H', last, 0x2B3 + 18 * r)
    for r in range(n):
        t = rec(r)
        check(want is None or t[1] == want, f'row {r}: played {t[1]}, {want} wanted', errs)
        check(t[7] == 3 * t[2] + t[3] and t[2] + t[3] + t[4] == t[1], f'row {r}: {t}', errs)
    order = [w(last, 0x6D + 2 * i) // 18 for i in range(n)]
    p2r = list(last[st + o['p2r']:st + o['p2r'] + n])
    start = 0
    for g, m in enumerate(sizes[-1]):
        check(sorted(order[start:start + m]) == sorted(p2r[start:start + m]),
              f'last stage group {g + 1}: {order[start:start + m]} / {p2r[start:start + m]}', errs)
        pts = [rec(r)[7] for r in order[start:start + m]]
        check(pts == sorted(pts, reverse=True), f'last stage group {g + 1} not in order: {pts}', errs)
        start += m
    if any(x.get('keep') for x in stg):
        k = st + o['h2h']
        rows = list(last[k:k + n])
        kp = [w(last, k + 22 + 2 * i) for i in range(n)]
        ki = next(i for i, x in enumerate(stg) if x.get('keep'))   # in order within the groups of the stage before
        start, okk = 0, sorted(rows) == list(range(n))
        for m in (sizes[ki - 1] if ki else [n]):
            okk = okk and kp[start:start + m] == sorted(kp[start:start + m], reverse=True)
            start += m
        check(okk, f'kept table {rows} {kp}', errs)
    return not errs, '; '.join(errs[:6]) or f'{len(stg)} stages, {total} days, final order {order}'


def split_check(log, key, slots_table):
    """The split league's snapshots (session log 'DIY' / 'CAL' lines of world8485 with W8485_DIY) against the pack
    key (converted as mkseason.splits does)."""
    import split
    rnd = {'none': 0, 'single': 1, 'double': 2, 'triple': 3, 'quadruple': 4}
    gs = key['groups']
    spec = {'groups': [g['places'][1] - g['places'][0] + 1 for g in gs], 'rounds': [rnd[g.get('rounds', 'single')] for g in gs],
            'points': [g.get('points', 'full') for g in gs], 'home': key.get('home', 'seeded'), 'after': key['after']}
    diys = [b for b in (bytes.fromhex(ln[4:]) for ln in log if ln.startswith('DIY ')) if b[0:2] == b'\0\0']   # leagues
    cal = [bytes.fromhex(ln[4:]) for ln in log if ln.startswith('CAL ')]
    if not diys:
        return False, 'no snapshot of the split league'
    clubs = lambda b: sorted(b[0x12D:0x12D + 2 * struct.unpack_from('<H', b, 0x31)[0]])
    diys = [b for b in diys if clubs(b) == clubs(diys[0])]      # (not another country's split league)
    st = split.ST
    n = struct.unpack_from('<H', diys[-1], 0x31)[0]
    d1 = spec['after']
    spec['games'] = d1 // split.days_before(n, 1)
    days = split.schedule(spec['groups'], spec['rounds'])
    d2 = len(days)
    last = diys[-1]
    errs = []
    w = lambda b, o: struct.unpack_from('<H', b, o)[0]
    day = w(last, 0x1C1)
    check(w(last, 0x1C3) == d1 + d2, f'days {w(last, 0x1C3)} != {d1} + {d2}', errs)
    check(day == d1 + d2 and w(last, 0x5F) == 0, f'last snapshot: day {day}, cycles left {w(last, 0x5F)}', errs)
    fz = split.OFF['frozen']
    check(any(not b[st + fz] and w(b, 0x1C1) < d1 for b in diys), 'no snapshot before the split', errs)
    fr = [b for b in diys if b[st + fz]]
    check(fr and all(w(b, 0x1C1) >= d1 for b in fr), f'frozen before day {d1}', errs)
    row = lambda o: o // 18
    order = [row(w(last, 0x6D + 2 * i)) for i in range(n)]
    p2r = list(last[st + split.OFF['p2r']:st + split.OFF['p2r'] + n])
    grp = last[st + split.OFF['grp']:st + split.OFF['grp'] + n]
    pre = [w(last, st + split.OFF['pre'] + 2 * r) for r in range(n)]
    rec = lambda r: struct.unpack_from('<I7H', last, 0x2B3 + 18 * r)   # team, played, won, drawn, lost, gf, ga, pts
    full = (n - 1) * spec['games']
    before = next((b for b in diys if not b[st + split.OFF['frozen']] and all(struct.unpack_from('<H', b, 0x2B3 + 18 * r + 4)[0] == full
                                                             for r in range(n))), None)   # (all pre-split played)
    rounds = spec['rounds']
    sizes, start = spec['groups'], 0
    pts_rule = spec.get('points', ['full'] * len(sizes))
    for g, m in enumerate(sizes):
        rows = order[start:start + m]
        check(sorted(rows) == sorted(p2r[start:start + m]) and all(grp[r] == g for r in rows),
              f'group {g + 1}: final places {start + 1}-{start + m} rows {rows}, frozen {p2r[start:start + m]}', errs)
        games = (n - 1) * spec['games'] + (m - 1) * rounds[g]
        for r in rows:
            t = rec(r)
            want = 3 * t[2] + t[3]
            if pts_rule[g] in ('half_up', 'half_down'):
                half = (pre[r] + 1) // 2 if pts_rule[g] == 'half_up' else pre[r] // 2
                want = want - pre[r] + half
            elif pts_rule[g] in ('reset', 'h2h_half'):          # the points after the split, from the snapshot
                if before is None:                               # with every pre-split match played
                    continue
                b = struct.unpack_from('<I7H', before, 0x2B3 + 18 * r)
                want = 3 * (t[2] - b[2]) + (t[3] - b[3]) + (pre[r] // 2 if pts_rule[g] == 'h2h_half' else 0)
            check(t[1] == games and t[2] + t[3] + t[4] == games, f'row {r}: played {t[1]} (W{t[2]} D{t[3]} L{t[4]}), '
                  f'{games} wanted', errs)
            check(t[7] == want, f'row {r}: points {t[7]}, {want} wanted (points before the split {pre[r]})', errs)
        key = [(rec(r)[7], pre[r] if pts_rule[g] not in ('full', 'reset') else 0) for r in rows]
        check(all(key[i][:2] >= key[i + 1][:2] for i in range(m - 1)), f'group {g + 1} not in order: {key}', errs)
        start += m
    if cal and spec.get('home') in ('balance', 'reverse3'):    # the career club's post-split fixtures: home side by
        c = cal[0]                                             # the matrix of the slots (the engine's own fixtures)
        mat = split.matrix(slots_table(n), n, spec['games'], spec['games'] + 1, spec['home'])
        slot = {last[0xED + i]: i for i in range(n)}
        words = {}
        o, k, seen = 0, 0, 0
        while o + 0x10 <= len(c) and seen < 400:
            seen += 1
            size = w(c, o + 2)
            if not size:
                break
            if c[o] == last[0x2B]:
                if d1 <= k < d1 + d2 and c[o + 5]:
                    words.setdefault('fx', []).append((w(c, o + 0xC), w(c, o + 0xE)))
                k += 1
            o += size
        fx = words.get('fx', [])
        me = set.intersection(*[{a, b} for a, b in fx]) if fx else set()
        check(len(me) == 1 and any(len(fx) == (m - 1) * r for m, r in zip(sizes, rounds)),
              f'career club post-split fixtures {fx}', errs)
        row = {w(last, 0x12D + 2 * r): r for r in range(n)}           # team number -> row -> slot
        bad = [(hex(a), hex(b)) for a, b in fx if a in row and b in row
               and mat[slot[row[a]] * n + slot[row[b]]] == 0]
        check(not bad, f'home side against the {spec["home"]} rule: {bad}', errs)
        log.append(f'post-split fixtures {[(hex(a), hex(b)) for a, b in words.get("fx", [])]}')
    return not errs, '; '.join(errs[:6]) or f'days {d1} + {d2}, final order {order}, groups {sizes}'


def world_split(kind):
    c, team, spec = SPLITS[kind]
    exe = split_build()
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import split
    import lepatch
    po = lepatch.LEPatch(os.path.join(MAIN, 'orig', 'ITALIAN.EXE'))
    sa = split.sites(po)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_DIY', 'W8485_FROM', 'W8485_TMO', 'W8485_SLOTS')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_DIY=f"{sa['DIY']:x},{split.ST:x},{sa['CAL']:x}", W8485_TMO='600',
                      W8485_SLOTS=f"{sa['SLOTS']:x}")
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    log = open(os.path.join(RUNS, f'{w84_tag()}_1', 'session.log')).read().splitlines()
    good, rep = (split_check_stages(log, spec) if 'stages' in spec else
                 split_check(log, spec, lambda n: split.pair_table(po, sa, n)))
    open(os.path.join(RUNS, f'{w84_tag()}_1', 'split.txt'), 'w').write(rep + '\n' + '\n'.join(
        x for x in log if x.startswith('post-split')) + '\n')
    return ok and good, f'{rep}; {msg}'


@scenario
def world_split_single():
    """Mid-season split, single round robin (split.py): Scotland (Premiership 33 + 5, top 6 / bottom 6, the
    pair-balance home rule) in the world 2026-27 with SPLITS; a season at ST. MIRREN played to its end: 38 days,
    everyone 38 matches, the final table = the frozen groups in order (points in full), the career club's 5 fixtures
    after the split at home by the balance of the engine's first 33 days"""
    return world_split('single')


@scenario
def world_split_double():
    """Mid-season split, double round robin: Austria (22 + 10, Meistergruppe / Qualifikationsgruppe, points in full)
    at HARTBERG: 32 days, 32 matches each, the groups in order"""
    return world_split('double')


@scenario
def world_split_h2h():
    """Mid-season split, head-to-head points: Moldova (21 + the top 6 double round robin (10) from half the points
    won against each other, rounded down; 7th-8th done) at PETROCUB: 31 days, the top 6's points = half their
    head-to-head points + the later ones"""
    return world_split('h2h')


@scenario
def world_split_reverse3():
    """Mid-season split, 'reverse3' home rule: Northern Ireland (33 + 5, Section A / B; home = the club away in their
    3rd meeting) at BANGOR"""
    return world_split('reverse3')


@scenario
def world_split_odd():
    """Mid-season split, odd groups: Bulgaria 26 + groups 1-4 / 5-9 (double, byes) / 10-14 (single, byes) at
    LOKOMOTIV SOFIA: 6 / 4 / 2 matches a day"""
    return world_split('odd')


@scenario
def world_split_three():
    """Mid-season split, three groups: Greece 26 + 1-4 / 5-8 (points halved, rounded up) / 9-14, all double, at
    VOLOS"""
    return world_split('three')


@scenario
def world_split_none():
    """Mid-season split with a group that stops: Czech Republic 30 + 1-6 / 7-10 (no more league matches: their
    placement knockout is a play-off item) / 11-16 at PARDUBICE"""
    return world_split('none')


@scenario
def world_split_stages():
    """A chain of stages: Malta (Opening Round 11 + top / bottom 6 once more; Closing Round from 0 points, return
    legs of the Opening's 11, then top / bottom 6 again; the Opening table kept for the Final Four) at HIBERNIANS:
    32 days, every stage frozen, the Closing figures only, the kept table"""
    return world_split('stages')


@scenario
def world_odd_league():
    """A league with an odd number of clubs (mkseason.odd_leagues: the engine's own rest day, no phantom club): the
    full world with the real odd sizes (ODD_BUILD, default the newest internal/swostest/builds/w2627odd-*), a
    season at AUCKLAND CITY (New Zealand, 11 clubs): 22 days of 5 matches, every club 20 matches and 2 rests, the
    season ended and the next one started"""
    import glob
    b = os.environ.get('ODD_BUILD') or (sorted(glob.glob(os.path.join(WORK, 'builds', 'w2627odd-*'))) or [None])[-1]
    if not b:
        return True, 'SKIP: no w2627odd build'
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import split
    import lepatch
    sa = split.sites(lepatch.LEPatch(os.path.join(MAIN, 'orig', 'ITALIAN.EXE')))
    n = int(os.environ.get('ODD_CLUBS', 11))
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_DIY', 'W8485_TMO', 'W8485_SLOTS')}
    os.environ.update(W8485_BUILD=b, W8485_WORLD='MONDO 2026-27', W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1',
                      W8485_TEAM=os.environ.get('ODD_TEAM', 'OCEANIA,NUOVA ZELANDA,NEW ZEALAND NATIONAL LEAGUE,AUCKLAND CITY'),
                      W8485_DIY=f"{sa['DIY']:x},{split.ST:x},{sa['CAL']:x},{n:x}", W8485_TMO='600',
                      W8485_SLOTS=f"{sa['SLOTS']:x}")
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    log = open(os.path.join(RUNS, f'{w84_tag()}_1', 'session.log')).read().splitlines()
    diys = [bytes.fromhex(ln[4:]) for ln in log if ln.startswith('DIY ')]
    if not diys:
        return False, f'no snapshot of a {n}-club league; {msg}'
    clubs = lambda x: sorted(x[0x12D:0x12D + 2 * n])
    diys = [x for x in diys if clubs(x) == clubs(diys[0])]
    last = diys[-1]
    w = lambda k: struct.unpack_from('<H', last, k)[0]
    rows = [struct.unpack_from('<I7H', last, 0x2B3 + 18 * r) for r in range(n)]
    errs = []
    check(w(0x1C1) == w(0x1C3) == 2 * n and w(0x5F) == 0, f'days {w(0x1C1)} / {w(0x1C3)}, {2 * n} wanted', errs)
    check(all(t[1] == 2 * (n - 1) and t[2] + t[3] + t[4] == t[1] for t in rows),
          f'played {[t[1] for t in rows]}, {2 * (n - 1)} wanted', errs)
    check(ok, msg, errs)
    return not errs, '; '.join(errs) or f'{n} clubs, {2 * n} days, every club {2 * (n - 1)} matches; {msg}'


@scenario
def world_split_halved():
    """Mid-season split, halved points: Romania (30 + play-off 6 double (10) / play-out 10 single (9), points halved
    rounded up, 'points before rounding' first tie-break) at BOTOSANI: 40 days, 40 / 39 matches, points = the halved
    split points + the later ones, groups in order"""
    return world_split('halved')

@scenario
def world_dplay_out():
    """The career club's Serie B play-out, played (dplay step 2): as world_dplay_b with DPLAY_FORCE=17 (MODENA 17th
    at the league end, the play-out held whatever the points): PLAY-OUT SERIE B 17th v 16th in slot 4, two legs, the
    loser down"""
    return world_dplay_b('17')


@scenario
def world_dplay_c():
    """The career club's Serie C play-off, played (dplay step 3): as world_dplay_b with DPLAY_FORCE=105 at RENATE
    (Serie C group A, 5th at its league end): the other two groups simulated at once, PLAY-OFF SERIE C (28 clubs) in
    slot 4 - group rounds, national rounds with seeds, Final Four - played to its end; its winner promoted (the
    season log: kind 3, the 28 clubs in place order, the winner moved up)"""
    return world_dplay_b('105', 'EUROPA,ITALIA,SERIE C GIRONE A,RENATE')



@scenario
def world_leaguecup():
    """League cups in a career world (the country table's slot 2, the game's own league-cup slot): the world 2026-27
    (private data internal/world2526/world5tm) with England's staged EFL Cup (world5tm-lc/eng, id F0 for the test,
    season.league_cup) merged in; a season at BRADFORD CITY (League One, in the round of 16): the EFL CUP rounds are played (their titles seen) and
    the season ends and saves (checkw1)"""
    import json
    import shutil
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    lc = os.path.join(MAIN, 'internal', 'world2526', 'world5tm-lc', 'eng')
    if not (os.path.isdir(src) and os.path.isdir(lc)):
        return True, 'SKIP: private data internal/world2526/world5tm(-lc) missing'
    w = os.path.join(WORK, 'world_leaguecup')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    eng = os.path.join(w, 'world5tm', 'eng')
    d = json.load(open(os.path.join(eng, 'pack.json')))
    if not any(c['key'] == 'league_cup' for c in d['competitions']):
        c = json.load(open(os.path.join(lc, 'competition.json')))
        c.setdefault('id', 'F0')
        d['competitions'].append(c)
        d['season']['league_cup'] = c['key']
        d['season']['league_cup_europe'] = True        # (its winner: England's last UECL place, uefaq)
        json.dump(d, open(os.path.join(eng, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
        rows = open(os.path.join(lc, 'ties.csv')).read().splitlines()[1:]
        with open(os.path.join(eng, 'ties.csv'), 'a') as t:
            t.write('\n'.join(rows) + '\n')
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(w, 'world5tm', x) for x in order])}
    exe = build('world_leaguecup', env=env)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM='EUROPA,INGHILTERRA,EFL LEAGUE ONE,BRADFORD CITY',
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    log = open(os.path.join(RUNS, w84_tag() + '_1', 'session.log'), errors='replace').read()
    titles = sorted(set(re.findall(r'EFL CUP[A-Z0-9 ./-]*', log)))
    errs = []
    check(ok, msg, errs)
    check(titles, 'no EFL CUP screen in season 1', errs)
    return not errs, '; '.join(errs) or f'{msg}; {titles[:8]}'



GPLAY_SCO = [   # Scotland 2026-27 (internal/world2526/formats2627.md 1): the three promotion / relegation play-offs
    {'key': 'prem_po', 'kind': 'promotion', 'entrants': [[1, 3], [1, 4], [1, 2], [0, 11]],
     'rounds': [{'ties': [[1, 0]], 'legs': 2, 'host': 'listed', 'level': 'et_pens'},
                {'ties': [['W0', 2]], 'legs': 2, 'host': 'better', 'level': 'et_pens'},
                {'ties': [['W1', 3]], 'legs': 2, 'host': 'listed', 'level': 'et_pens'}],
     'winner_div': 0, 'loser_div': 1},
    {'key': 'champ_po', 'kind': 'promotion', 'entrants': [[1, 9], [2, 4], [2, 2], [2, 3]],
     'rounds': [{'ties': [[1, 0], [3, 2]], 'legs': 2, 'host': 'better', 'level': 'et_pens'},
                {'ties': [['W0', 'W1']], 'legs': 2, 'host': 'better', 'level': 'et_pens'}],
     'winner_div': 1, 'loser_div': 2},
    {'key': 'l1_po', 'kind': 'promotion', 'entrants': [[2, 9], [3, 4], [3, 2], [3, 3]],
     'rounds': [{'ties': [[1, 0], [3, 2]], 'legs': 2, 'host': 'better', 'level': 'et_pens'},
                {'ties': [['W0', 'W1']], 'legs': 2, 'host': 'better', 'level': 'et_pens'}],
     'winner_div': 2, 'loser_div': 3}]


@scenario
def world_gplay():
    """Knockout promotion / relegation play-offs at the season end (gplay.py): the world 2026-27 with Scotland's three
    play-offs (GPLAY_SCO) added to a copy of its pack; a season at CLYDE (League Two): after it every Scottish
    division keeps its size (12, 10, 10, 10) and the moves between two divisions are the direct ones plus 0 or 1
    play-off swap each"""
    import collections
    import json
    import shutil
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    if not os.path.isdir(src):
        return True, 'SKIP: private data internal/world2526/world5tm missing'
    w = os.path.join(WORK, 'world_gplay')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    f = os.path.join(w, 'world5tm', 'sco', 'pack.json')
    d = json.load(open(f))
    lg = next(c for c in d['competitions'] if c['type'] == 'league')
    lg['ko_playoffs'] = GPLAY_SCO
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(w, 'world5tm', x) for x in order])}
    exe = build('world_gplay', env=env)
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = env['SEASON_PACKS']
    import mkseason
    pk = next(p for p in mkseason.packs() if p.meta.get('id', '').endswith('-sco'))
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    clubs = []
    for key in pk.league_clubs:
        fl, i = pk.where[key]
        base = next(b for fk, (ff, b) in pk.files.items() if ff == fl)
        clubs.append((base + i, pk.division[key]))
    sizes = collections.Counter(dv for _, dv in clubs)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM='EUROPA,SCOZIA,SCOTTISH LEAGUE TWO,CLYDE',
                      W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if not os.path.exists(car):
        return False, f'no season-1 save: {msg}'
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]
    cnt, mv = collections.Counter(), collections.Counter()
    for g, base in clubs:
        new = base + struct.unpack('b', slt[g:g + 1])[0]
        cnt[new] += 1
        if new != base:
            mv[base, new] += 1
    errs = []
    check(ok, msg, errs)
    check(cnt == sizes, f'divisions {sorted(cnt.items())} (were {sorted(sizes.items())})', errs)
    for a in range(3):                                       # direct 1 each way (+ 0 or 1 play-off swap)
        check(mv[a, a + 1] in (1, 2) and mv[a + 1, a] == mv[a, a + 1], f'moves {a}<->{a + 1}: {dict(mv)}', errs)
    return not errs, '; '.join(errs) or f'{msg}; divisions {sorted(cnt.items())}; moves {dict(mv)}'


GP_KO = dict(magic=0, season=2, slot=3, cid=4, pi=5, kind=6, n=7, nrs=8, ngr=9, gcur=10, ntie=11, d1=13, d2=14,
             rs=16, rb=121, gp0=157, pa=170, pb=210, pw=250, ptie=290, tw=330, tl=354, code=378, team=474,
             size=674)                  # gplay.c struct gp_ko (gp_log: tag, seasons, pl_pi, ko at 8, gp_out at 682)
GP_GT, GP_STKO = 32, 648      # gplay.c GT (a club code = division * GT + place), struct gp_state's ko


def gp_ptrs(exe):
    """obj2 offsets and sizes of gplay's GP_LOG and GP_ST (the 'GPLOGPTR' block of its glue)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    d1 = LE(open(os.path.join(exe, 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
    k = d1.find(b'GPLOGPTR')
    return struct.unpack_from('<4I', d1, k + 8) if k >= 0 else None


def gp_eu(exe):
    """obj2 offsets of D8CB6 (the slot-3 contest), the euro cup won flags D6C64 / D6C66 / D6C68 and the season
    records (106 B each; GPLOGPTR)."""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    d1 = LE(open(os.path.join(exe, 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
    k = d1.find(b'GPLOGPTR')
    return struct.unpack_from('<5I', d1, k + 24)


def gp_ko(b):
    """A gp_ko's fields (gp_log / GP_ST bytes from its offset)."""
    f = {k: b[v] for k, v in GP_KO.items() if k not in ('rs', 'rb', 'gp0', 'pa', 'pb', 'pw', 'ptie', 'tw', 'tl', 'code',
                                                         'team', 'size', 'magic')}
    f['magic'] = struct.unpack_from('<H', b, 0)[0]
    n, nt = f['n'], f['ntie']
    f['team'] = list(struct.unpack_from(f'<{n}H', b, GP_KO['team']))
    f['code'] = list(struct.unpack_from(f'<{n}H', b, GP_KO['code']))
    f['tw'], f['tl'] = list(b[GP_KO['tw']:GP_KO['tw'] + nt]), list(b[GP_KO['tl']:GP_KO['tl'] + nt])
    np = b[GP_KO['gp0'] + f['gcur'] + 1]
    f['pairs'] = [(b[GP_KO['pa'] + i], b[GP_KO['pb'] + i], b[GP_KO['pw'] + i], b[GP_KO['ptie'] + i]) for i in range(np)]
    return f


@scenario
def world_gplay_play(force='2', team='EUROPA,SCOZIA,SCOTTISH LEAGUE TWO,CLYDE', div=3):
    """The career club's knockout play-off, played (gplay, the playable step): the world 2026-27 with Scotland's
    play-offs (GPLAY_SCO) built with GPLAY_FORCE=2 (at the league end the career club takes 2nd place of League
    Two); a season at CLYDE: the League One play-off (League Two 2nd-4th + League One 9th, League One simulated at
    the league end) is built in slot 4 and played to its end (the session log's GP_ST / GP_LOG: 4 clubs, the club's
    place among them, two rounds of two legs, every tie decided, the winner among the clubs), and the season end
    moves its real winner up (or keeps the League One 9th, the loser of the final down)"""
    import json
    import shutil
    src = os.environ.get('W2627P_DATA') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-poule')   # (a stable
    if not os.path.isdir(src):                                                    # snapshot: world5tm is regenerated)
        return True, f'SKIP: private data {src} missing'
    w = os.path.join(WORK, 'world_gplay_play')
    shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(src, os.path.join(w, 'world5tm'))
    f = os.path.join(w, 'world5tm', 'sco', 'pack.json')
    d = json.load(open(f))
    lg = next(c for c in d['competitions'] if c['type'] == 'league')
    lg['ko_playoffs'] = [dict(po, names={'*': [po['key'].upper().replace('_', ' '), po['key'].upper()]}) for po in GPLAY_SCO]
    json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(w, 'world5tm', x) for x in order]),
           'GPLAY_FORCE': force}
    exe = os.environ.get('GPLAY_BUILD') or build('world_gplay_play_' + force, env=env)
    ptrs = gp_ptrs(exe)
    if not ptrs:
        return False, 'no GPLOGPTR block in the exe'
    log_at, st_at, log_n, st_n = ptrs
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_HEX=f'{log_at:x}:{log_n},{st_at:x}:{st_n}')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    hexes = {}
    for ln in open(os.path.join(RUNS, w84_tag() + '_1', 'session.log'), errors='replace'):
        p = ln.split()
        if len(p) == 3 and p[0] == 'HEX':
            hexes.setdefault(int(p[1], 16), []).append(bytes.fromhex(p[2]))
    errs = []
    check(ok, msg, errs)
    sts = [b for b in hexes.get(st_at, []) if b[:2] == b'GK']
    if not sts:
        return False, f'{msg}; the play-off never ran (no GP_ST seen)'
    run = [gp_ko(b[GP_STKO:]) for b in sts]
    logs = [b for b in hexes.get(log_at, []) if b[:4] == b'GPLG']
    if not logs:
        return False, f'{msg}; no season-end log (GP_LOG); last state {run[-1]}'
    lg = logs[-1]
    ko = gp_ko(lg[8:])
    nmv = lg[682]
    mv = [struct.unpack_from('<HHb', lg, 686 + 8 * i) for i in range(min(nmv, 32))]
    check(lg[6] == ko['pi'] + 1, f'season end: seasons {lg[4]} / {lg[5]}, played play-off {lg[6]}', errs)
    me = div * GP_GT + int(force) - 1
    check(ko['magic'] == 0x4B47 and ko['cid'] == 0xFE and ko['n'] == 4 and me in ko['code'],
          f"contest {ko['cid']:#x} n {ko['n']} codes {ko['code']}", errs)
    check(ko['ntie'] == 3 and all(x != 255 for x in ko['tw']), f"ties {ko['ntie']} winners {ko['tw']}", errs)
    win = ko['team'][ko['tw'][-1]] if ko['tw'] and ko['tw'][-1] < ko['n'] else None
    wcode = ko['code'][ko['tw'][-1]] if win is not None else None
    if wcode is not None and wcode // GP_GT == div:                 # a League Two club won: up one
        check(any(t == win and dl == -1 for _, t, dl in mv), f'winner {win:#x} not moved up: {mv}', errs)
    elif wcode is not None:                                      # the League One 9th won: it stays
        check(not any(t == win for _, t, dl in mv), f'League One winner {win:#x} moved: {mv}', errs)
    gw = sorted({r['gcur'] for r in run})
    return not errs, '; '.join(errs) or (f"{msg}; contest clubs {[hex(t) for t in ko['team']]} codes {ko['code']}, "
                                         f"game rounds seen {gw}, winner {win:#x} (code {wcode}), moves {mv}")


def sr_blocks(b):
    """'SR' bytes -> [(key, [team words])] up to the dw 0."""
    out, k = [], 0
    while k + 4 <= len(b):
        key, n = struct.unpack_from('<HB', b, k)
        if not key:
            break
        out.append((key, list(struct.unpack_from(f'<{n}H', b, k + 4))))
        k += 4 + 2 * n
    return out


@scenario
def world_statesim(team='SUDAMERICA,BRASILE,CAMPEONATO BRASILEIRO SERIE A,ATHLETICO-PR'):
    """State championships at the season end (statespec statesim.c + ripool, World 2026-27 private data world5tm):
    two seasons at ATHLETICO-PR (Paranaense): season 1's SS_LAST (statesim's SR) has one block per state, the
    Paranaense's = the real stage-1 order seen at its first knockout (ST_RANK block 0, st_rec) with its relegation
    play-outs applied; season 2's Paranaense list (block 0 again) still holds 12 clubs and no season-1 relegated
    LEAGUE club (those leave through RI_OVR; a state-only club keeps its word, ripool swaps its identity)"""
    src = os.path.join(MAIN, 'internal', 'world2526', 'world5tm')
    if not os.path.isdir(src):
        return True, 'SKIP: private data internal/world2526/world5tm missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order])}
    exe = os.environ.get('STATESIM_BUILD') or build('world_statesim' + ('_' + os.environ['SWOSTEST_TAG']
                                                                         if os.environ.get('SWOSTEST_TAG') else ''),
                                                      env=env)   # (a tag of its own: parallel sessions)
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    from le import LE
    d1 = LE(open(os.path.join(exe, 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
    k = d1.find(b'SSLASTPT')
    if k < 0:
        return False, 'no SSLASTPT block in the exe (statesim not built)'
    rank_at, last_at, ord_at, champ_at = struct.unpack_from('<4I', d1, k + 8)
    keep = {x: os.environ.get(x) for x in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_HEX=f'o1/{rank_at:x}:470,o1/{last_at:x}:470,o1/{ord_at:x}:208,o1/{champ_at:x}:26')   # (+ ss_ord: each state's
                                                                              # stage-1 order, club indices)
    try:
        ok, msg = world8485()
    finally:
        for x, v in keep.items():
            if v is None:
                os.environ.pop(x, None)
            else:
                os.environ[x] = v
    hexes = {}
    for sn in (1, 2):                            # (each season's own run)
        f = os.path.join(RUNS, w84_tag() + f'_{sn}', 'session.log')
        for ln in open(f, errors='replace') if os.path.exists(f) else []:
            q = ln.split()
            if len(q) == 3 and q[0] == 'HEX':
                hexes.setdefault(q[1], []).append(bytes.fromhex(q[2]))
    errs = []
    check(ok, msg, errs)
    ranks = [sr_blocks(b) for b in hexes.get(f'o1/{rank_at:x}', [])]
    lasts = [sr_blocks(b) for b in hexes.get(f'o1/{last_at:x}', [])]
    played = [r[0] for r in ranks if r]                      # block 0 as st_rec wrote it, each season
    lasts = [x for x in lasts if x]
    check(len(lasts) >= 1, f'statesim never ran (SS_LAST {len(lasts)} values)', errs)
    if lasts:                                    # (the first one may be the career's start: pg_fix runs there)
        L = next((x for x in lasts if played and x[0][0] == played[0][0]), lasts[-1])
        keys = [kk for kk, _ in L]
        check(len(L) >= 10 and len(set(keys)) == len(keys), f'season 1: {len(L)} blocks, keys {[hex(x) for x in keys]}',
              errs)
        if played:
            pk, pw = played[0]
            blk = dict(L).get(pk)
            check(blk is not None and sorted(blk) == sorted(pw), f'played state {pk:#x}: SR {blk} vs order {pw}', errs)
            if len(played) >= 2 and blk:
                p2k, p2w = played[1]                 # (a relegated state-only club keeps its word: ripool swaps
                gone = [w for w in blk[-2:] if w in p2w and (w & 255) != 0xA1]   # the identity in file 161)
                check(p2k == pk and len(p2w) == len(pw) and not gone,
                      f'season 2 list {[hex(x) for x in p2w]}: season-1 relegated {[hex(x) for x in blk[-2:]]} '
                      f'still in: {[hex(x) for x in gone]}', errs)
            else:
                check(False, f'season 2: no block 0 seen ({len(played)} seasons with one)', errs)
        else:
            check(False, 'no block 0 (st_rec) seen', errs)
        champs = [struct.unpack('<13H', b) for b in hexes.get(f'o1/{champ_at:x}', []) if any(b)]
        if champs:                               # (statesim's champions: one of each simulated state's clubs)
            byk = [ws for _, ws in L]
            order = sorted(byk, key=lambda ws: 0)
            check(all(c == 0 or any(c in ws for ws in byk) for c in champs[-1]) and sum(1 for c in champs[-1] if c)
                  >= len(L) - 1, f'champions {[hex(c) for c in champs[-1]]}', errs)
        else:
            check(False, 'no statesim champions seen', errs)
    return not errs, '; '.join(errs + [f"{msg}; SR seasons {len(played)}, statesim runs {len(lasts)}; "
                                        f"played {[(hex(kk), [hex(x) for x in w]) for kk, w in played]}; "
                                        f"last {[(hex(kk), [hex(x) for x in w[-2:]]) for kk, w in (lasts[0] if lasts else [])]}"])


@scenario
def world_gplay_reserve(force='20', team='EUROPA,ITALIA,SERIE C GIRONE A,RENATE', src=None, div=2, direct=20):
    """The career club relegated into the reserve is sacked (gplay gp_sack, SeasonFinished's contract check): the
    world 2026-27 with Italy's reserve (private data internal/world2526/world5tm-reserve: Serie C groups, 20th down
    directly, play-outs 16th-19th into the reserve) built with GPLAY_FORCE (the career club's place in its group at
    the league end); a season at RENATE: forced 20th -> sacked (CONTINUA CARRIERA disabled, job offers); forced into
    the play-out (16-19) -> it is played, and the club is sacked if and only if it lost (GPLAY_FORCE=16: world_gplay_
    reserve_out); sacked with no job offer left, the career ends (the game's own way) instead of a next season in the
    reserve (which trapped in cseg_3283C)"""
    src = src or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-reserve')
    src = src.rstrip('/')
    if not os.path.isdir(src):
        return True, f'SKIP: private data {src} missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order]), 'GPLAY_FORCE': force}
    exe = os.environ.get('GPLAY_BUILD') or build(f'world_gplay_reserve_{os.path.basename(src)}_{force}', env=env)
    log_at, st_at, log_n, st_n = gp_ptrs(exe)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX', 'W8485_ONE')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_HEX=f'{log_at:x}:{log_n},{st_at:x}:{st_n}', W8485_ONE='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lines = open(os.path.join(RUNS, w84_tag() + '_1', 'session.log'), errors='replace').read().splitlines()
    sacked = any(ln.startswith('[job]') and 'RINNOVARVI IL CONTRATTO' in ln for ln in lines)   # (the chairman's note)
    over = not ok and 'no CONTINUA CARRIERA on CARRIERA' in msg     # (sacked, no offer left: the career is over)
    errs = []
    check(ok or over, msg, errs)
    how = 'no offer left: career over' if over else 'a job taken, the next season saved'
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if int(force) == direct:
        check(sacked, f'forced {force}th: not sacked', errs)
        if 'res1' in src and os.path.exists(car):            # (an off-file pool: the sacked manager's old club swapped)
            left, cnt = reserve_left(car, src)
            check(not left, f'clubs left in the reserve division: {left}', errs)
        return not errs, '; '.join(errs) or f'{msg}; {force}th: sacked ({how})'
    sts = [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(f'HEX {st_at:x} ')]
    sts = [b for b in sts if b[:2] == b'GK']
    if not sts:
        return False, f'{msg}; the play-out never ran (no GP_ST seen)'
    ko = gp_ko(sts[-1][GP_STKO:])
    me = div * GP_GT + int(force) - 1
    check(ko['kind'] == 4 and ko['n'] == 4 and me in ko['code'], f"play-out kind {ko['kind']} codes {ko['code']}", errs)
    i = ko['code'].index(me) if me in ko['code'] else None
    lost = i is not None and i in ko['tl']
    mine = [t for t in range(ko['ntie']) if i in (ko['tw'][t], ko['tl'][t])]
    check(mine, f"the club's tie not decided: winners {ko['tw']} losers {ko['tl']}", errs)
    if ko['slot']:                                           # (played: every tie decided; else the gap decided the
        check(all(x != 255 for x in ko['tw']), f"play-out not over: winners {ko['tw']}", errs)   # club's tie)
    how = how + ('' if ko['slot'] else '; the club\'s tie decided by the gap, no contest')
    check(sacked == lost, f'play-out {"lost" if lost else "won"}, sacked {sacked}', errs)
    if 'res1' in src and os.path.exists(car):                # (an off-file pool: no club left in the reserve)
        left, cnt = reserve_left(car, src)
        check(not left, f'clubs left in the reserve division: {left}', errs)
    return not errs, '; '.join(errs) or f'{msg}; play-out {"lost: sacked (" + how + ")" if lost else "won: kept the job"}'


@scenario
def world_gplay_reserve_out():
    """world_gplay_reserve with the career club forced 17th: its play-out (17th v 18th) played, sacked if lost"""
    return world_gplay_reserve('17')


def club_divisions(car, src, country, words):
    """After a season (W84A.CAR): team word (file | ordinal << 8) -> its division (base + someLeaguesTable)."""
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = ','.join([os.path.join(src, x) for x in order])
    import mkseason
    pk = next(p for p in mkseason.packs() if p.meta.get('id', '').endswith('-' + country))
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]
    out = {}
    for key in pk.league_clubs:
        fl, i = pk.where[key]
        if (fl | i << 8) in words:
            g = next(b for fk, (ff, b) in pk.files.items() if ff == fl) + i
            out[fl | i << 8] = pk.division[key] + struct.unpack('b', slt[g:g + 1])[0]
    return out


def reserve_left(car, src, country='ita'):
    """After a season (W84A.CAR): the country's clubs whose division (base + someLeaguesTable) is past its last one,
    i.e. left in the reserve division (an off-file pool swaps every relegated club out but the manager's), and the
    clubs per division."""
    import collections
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = ','.join([os.path.join(src, x) for x in order])
    import mkseason
    pk = next(p for p in mkseason.packs() if p.meta.get('id', '').endswith('-' + country))
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    nd = len(pk.divisions())
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]
    left, cnt = [], collections.Counter()
    for key in pk.league_clubs:
        fl, i = pk.where[key]
        base = next(b for fk, (ff, b) in pk.files.items() if ff == fl)
        g = base + i
        dv = pk.division[key] + struct.unpack('b', slt[g:g + 1])[0]
        cnt[dv] += 1
        if dv >= nd:
            left.append((key, dv))
    return left, cnt


@scenario
def world_gplay_seried_res():
    """world_gplay_reserve in Serie D (the data session's TM_RESERVE=1 snapshot internal/world2526/world5tm-res1: the
    Eccellenza reserve below Serie D): LIGORNA (girone A, 17 clubs, 2 down directly) forced 17th -> sacked"""
    return world_gplay_reserve('17', 'EUROPA,ITALIA,SERIE D GIRONE A,LIGORNA',
                               os.path.join(MAIN, 'internal', 'world2526', 'world5tm-res1'), 5, 17)


@scenario
def world_gplay_seried_out():
    """As world_gplay_seried_res with LIGORNA forced 13th: its Serie D play-out (13th v 14th, a single match at the
    better placed's, extra time, then the better placed stays) played, sacked if lost"""
    return world_gplay_reserve('13', 'EUROPA,ITALIA,SERIE D GIRONE A,LIGORNA',
                               os.path.join(MAIN, 'internal', 'world2526', 'world5tm-res1'), 5, 17)


@scenario
def world_gplay_reserve_gap():
    """world_gplay_reserve with the career club forced 16th: the 19th 8+ points behind, its play-out tie is not played
    (the gap rule) and no contest is built (the season went on; a slot-4 contest without the club stopped it)"""
    return world_gplay_reserve('16')


@scenario
def world_gplay_seried(force='3', team='EUROPA,ITALIA,SERIE D GIRONE A,LIGORNA', div=5):
    """A Serie D group play-off played (gplay 'placement', World 2026-27 with Serie D: the data session's snapshot
    internal/world2526/world5tm-e0b89822, W2627D_DATA): LIGORNA (girone A) forced 3rd at the league end -> the group
    play-off (2nd v 5th, 3rd v 4th, then the final; single matches at the better placed, extra time, then the better
    placed) built in slot 4 and played to its end; it moves nobody"""
    src = os.environ.get('W2627D_DATA') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-e0b89822')
    if not os.path.isdir(src):
        return True, f'SKIP: private data {src} missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order]), 'GPLAY_FORCE': force}
    exe = os.environ.get('GPLAY_BUILD') or build('world_gplay_seried_' + force, env=env)
    log_at, st_at, log_n, st_n = gp_ptrs(exe)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX', 'W8485_ONE')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_HEX=f'{log_at:x}:{log_n},{st_at:x}:{st_n}', W8485_ONE='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lines = open(os.path.join(RUNS, w84_tag() + '_1', 'session.log'), errors='replace').read().splitlines()
    errs = []
    check(ok, msg, errs)
    sts = [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(f'HEX {st_at:x} ')]
    sts = [b for b in sts if b[:2] == b'GK']
    if not sts:
        return False, f'{msg}; the play-off never ran (no GP_ST seen)'
    ko = gp_ko(sts[-1][GP_STKO:])
    me = div * GP_GT + int(force) - 1
    check(ko['kind'] == 3 and ko['n'] == 4 and ko['slot'] == 4 and me in ko['code'],
          f"play-off kind {ko['kind']} slot {ko['slot']} codes {ko['code']}", errs)
    check(ko['ntie'] == 3 and all(x != 255 for x in ko['tw']), f"play-off not over: winners {ko['tw']}", errs)
    win = ko['code'][ko['tw'][-1]] if ko['tw'] and ko['tw'][-1] < ko['n'] else None
    return not errs, '; '.join(errs) or f"{msg}; play-off codes {ko['code']}, winner code {win}"


@scenario
def world_gplay_poule(force='1', team='EUROPA,ITALIA,SERIE D GIRONE A,LIGORNA'):
    """The Poule Scudetto played (gplay: a group contest as the game's type 2 in slot 3): the data session's snapshot
    world5tm-poule (TM_RESERVE=1 TM_POULE=1: POULE_D in Italy's play-offs); LIGORNA forced 1st of Serie D girone A at
    the league end -> the other 8 groups simulated now, the 9 winners in 3 triangulars, the 3 winners + the best
    runner-up, two-legged semis, the final; the season end's title result = the contest's real champion, and the 9
    clubs are in Serie C after the season (the early-simulated groups restored at the season end)"""
    import json
    import shutil
    src = os.environ.get('W2627P_DATA') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-poule')
    if not os.path.isdir(src):
        return True, f'SKIP: private data {src} missing (the data session\'s TM_POULE=1 snapshot)'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order]), 'GPLAY_FORCE': force}
    exe = os.environ.get('GPLAY_BUILD') or build('world_gplay_poule', env=env)
    log_at, st_at, log_n, st_n = gp_ptrs(exe)
    eu = gp_eu(exe)
    keep = {k: os.environ.get(k) for k in ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K',
                                            'W8485_NOSACK', 'W8485_HEX', 'W8485_ONE')}
    os.environ.update(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM=team, W8485_WNUM='5', W8485_K='108+',
                      W8485_NOSACK='1', W8485_HEX=f'{log_at:x}:{log_n},{st_at:x}:{st_n},' + ','.join(
                          f'{a:x}:{4 if i == 0 else 106 if i == 4 else 2}' for i, a in enumerate(eu)), W8485_ONE='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lines = open(os.path.join(RUNS, w84_tag() + '_1', 'session.log'), errors='replace').read().splitlines()
    errs = []
    check(ok, msg, errs)
    sts = [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(f'HEX {st_at:x} ')]
    sts = [b for b in sts if b[:2] == b'GK']
    if not sts:
        return False, f'{msg}; the Poule never ran (no GP_ST seen)'
    ko = gp_ko(sts[-1][GP_STKO:])
    t2 = sts[-1][GP_STKO + 570 + 7]
    check(ko['kind'] == 5 and ko['n'] == 9 and ko['slot'] == 3 and t2 == 1 and 5 * GP_GT in ko['code'],
          f"Poule kind {ko['kind']} n {ko['n']} slot {ko['slot']} t2 {t2} codes {ko['code']}", errs)
    logs = [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(f'HEX {log_at:x} ')]
    logs = [b for b in logs if b[:4] == b'GPLG']
    if not logs:
        return False, f"{msg}; no season-end log; last state {ko}"
    lg_ = logs[-1]
    kl = gp_ko(lg_[8:])
    champ = kl['team'][kl['tw'][0]] if kl['tw'] and kl['tw'][0] < kl['n'] else None
    nres = lg_[683]
    res = [struct.unpack_from('<BBHHHH', lg_, 942 + 10 * i) for i in range(min(nres, 4))]
    check(lg_[6] == kl['pi'] + 1 and champ is not None, f'season end: played {lg_[6]}, champion {champ}', errs)
    check(any(r[0] == 5 and r[2] == champ for r in res), f'title result {res} not the champion {champ}', errs)
    last = {}                                                             # (no European cup credited: the season
    for ln in lines:                                                      # review's D8CB6 cleared by gp_sack, the
        p_ = ln.split()                                                   # won flags 0)
        if len(p_) == 3 and p_[0] == 'HEX':
            last[int(p_[1], 16)] = bytes.fromhex(p_[2])
    flags = [struct.unpack('<H', last.get(a, bytes(2))[:2])[0] for a in eu[1:4]]
    check(not any(flags), f'a European cup credited: flags {flags}', errs)
    rec = last.get(eu[4], bytes(106))                                     # (the season record: a Poule won by the
    won = champ is not None and champ == kl['team'][kl['code'].index(5 * GP_GT)] if 5 * GP_GT in kl['code'] else False
    if won:                                                               # club -> its 4th line, WINNERS)
        check(struct.unpack_from('<I', rec, 34)[0] and rec[89] == 1, f'record line: {rec[34:38].hex()} {rec[89]}', errs)
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')    # (the 9 group winners: up into Serie C, the
    if os.path.exists(car):                                               # early tables restored at the season end)
        dv = club_divisions(car, src, 'ita', set(kl['team']))
        check(len(dv) == 9 and all(2 <= x <= 4 for x in dv.values()), f'Poule clubs after the season: {dv}', errs)
    return not errs, '; '.join(errs) or f"{msg}; Poule clubs {[hex(t) for t in kl['team']]}, champion {champ:#x}, res {res}"


@scenario
def world_gplay_poule_save():
    """world_gplay_poule with a career save inside the Poule (W8485_MIDSAVE: once its slot-3 contest is built and a
    few match days on) and a fresh session loading it: the Poule goes on to its end and the title = its champion
    (GP_ST / GP_GS from the engine block, gp_sync's slot pointers)"""
    src = os.environ.get('W2627P_DATA') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-poule')
    if not os.path.isdir(src):
        return True, f'SKIP: private data {src} missing'
    order = [ln.split()[0].lower() for ln in open(src + '.txt') if ' file ' in ln]
    env = {'SEASON_PACKS': ','.join(['ddr-1988-89'] + [os.path.join(src, x) for x in order]), 'GPLAY_FORCE': '1'}
    exe = os.environ.get('GPLAY_BUILD') or build('world_gplay_poule', env=env)
    log_at, st_at, log_n, st_n = gp_ptrs(exe)
    keys = ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K', 'W8485_NOSACK', 'W8485_HEX',
            'W8485_ONE', 'W8485_MIDSAVE', 'W8485_FROM')
    keep = {k: os.environ.get(k) for k in keys}
    base = dict(W8485_BUILD=exe, W8485_WORLD='MONDO 2026-27', W8485_TEAM='EUROPA,ITALIA,SERIE D GIRONE A,LIGORNA',
                W8485_WNUM='5', W8485_K='108+', W8485_NOSACK='1', W8485_HEX=f'{log_at:x}:{log_n},{st_at:x}:{st_n}')
    try:
        os.environ.update(base, W8485_ONE='1', W8485_MIDSAVE=f'{st_at + GP_STKO + 3:x}:3:6')
        ok, msg = world8485()
        if not ok:
            return False, f'first session: {msg}'
        path = msg.split(': ', 1)[1]
        os.environ.pop('W8485_MIDSAVE')
        os.environ.update(base, W8485_FROM=path)
        ok2, msg2 = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lines = open(os.path.join(RUNS, w84_tag() + '_2', 'session.log'), errors='replace').read().splitlines()
    errs = []
    check(ok2, msg2, errs)
    logs = [bytes.fromhex(ln.split()[2]) for ln in lines if ln.startswith(f'HEX {log_at:x} ')]
    logs = [b for b in logs if b[:4] == b'GPLG']
    if not logs:
        return False, f'{msg2}; no season-end log after the reload'
    lg_ = logs[-1]
    kl = gp_ko(lg_[8:])
    champ = kl['team'][kl['tw'][0]] if kl['tw'] and kl['tw'][0] < kl['n'] else None
    res = [struct.unpack_from('<BBHHHH', lg_, 942 + 10 * i) for i in range(min(lg_[683], 4))]
    check(kl['slot'] == 3 and kl['n'] == 9 and champ is not None, f'after the reload: slot {kl["slot"]}, champion {champ}', errs)
    check(any(r[0] == 5 and r[2] == champ for r in res), f'title result {res} not the champion {champ}', errs)
    return not errs, '; '.join(errs) or f"{msg}; reloaded: {msg2}; champion {champ:#x}"


def full_season(country, team):
    country = os.environ.get('W2627FULL_COUNTRY', country)
    """A season of the full 5.0 world (91 countries, TM_FULL; the data session's staged build: W2627FULL = its build
    dir, default the newest internal/swostest/builds/w2627full-*) at team ('CONTINENT,COUNTRY,DIVISION,CLUB'): after
    it every division of the country keeps its size and every club moved exactly one level of its chain (a division,
    or a level of parallel groups)"""
    import collections
    import glob
    bdir = os.environ.get('W2627FULL') or (sorted(glob.glob(os.path.join(WORK, 'builds', 'w2627full-*'))) or [''])[-1]
    data = os.environ.get('W2627FULL_DATA') or os.path.join(MAIN, 'internal', 'world2526', 'world5tm-full-lc')
    if not os.path.isdir(bdir) or not os.path.isdir(data):
        return True, 'SKIP: no full build (W2627FULL) or private data internal/world2526/world5tm-full-lc'
    order = [ln.split()[0].lower() for ln in open(data.replace('-lc', '') + '.txt') if ' file ' in ln]
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    old = os.environ.get('SEASON_PACKS')
    os.environ['SEASON_PACKS'] = ','.join([os.path.join(data, x) for x in order])
    import mkseason
    pk = next(p for p in mkseason.packs() if p.meta.get('id', '').endswith('-' + country))
    if old is None:
        os.environ.pop('SEASON_PACKS')
    else:
        os.environ['SEASON_PACKS'] = old
    par = pk.league.get('parallel')
    pars = {q['first']: q['count'] for q in (par if isinstance(par, list) else [par] if par else [])}
    level, d, n, lv = {}, 0, len(pk.divisions()), 0
    while d < n:
        for x in range(d, d + pars.get(d, 1)):
            level[x] = lv
        d, lv = d + pars.get(d, 1), lv + 1
    level[n] = lv                               # (the reserve, out of every division: one level below the last)
    clubs = []
    for key in pk.league_clubs:
        fl, i = pk.where[key]
        base = next(b for fk, (ff, b) in pk.files.items() if ff == fl)
        clubs.append((base + i, pk.division[key]))
    sizes = collections.Counter(dv for _, dv in clubs)
    keys = ('W8485_BUILD', 'W8485_WORLD', 'W8485_TEAM', 'W8485_WNUM', 'W8485_K', 'W8485_NOSACK')
    keep = {k: os.environ.get(k) for k in keys}
    os.environ.update(W8485_BUILD=bdir, W8485_WORLD='MONDO 2026-27', W8485_TEAM=os.environ.get('W2627FULL_TEAM', team), W8485_WNUM='5',
                      W8485_K='108+', W8485_NOSACK='1')
    try:
        ok, msg = world8485()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    car = os.path.join(RUNS, w84_tag() + '_1', 'SWOS', 'W84A.CAR')
    if not os.path.exists(car):
        return False, f'no season-1 save: {msg}'
    slt = open(car, 'rb').read()[0xE8DC:0xE8DC + 2000]
    cnt, mv = collections.Counter(), collections.Counter()
    for g, base in clubs:
        new = base + struct.unpack('b', slt[g:g + 1])[0]
        cnt[new] += 1
        if new != base:
            mv[base, new] += 1
    errs = []
    check(ok, msg, errs)
    check(cnt == sizes, f'divisions {sorted(cnt.items())} (were {sorted(sizes.items())})', errs)
    bad = {k: v for k, v in mv.items() if k[1] not in level or abs(level[k[0]] - level[k[1]]) != 1}
    check(not bad, f'moves not of one level: {bad}', errs)
    return not errs, '; '.join(errs) or f'{msg}; divisions {sorted(cnt.items())}; moves {dict(mv)}'


@scenario
def world_full_slv():
    """Full 5.0 world (full_season): a season at HACHADURA (El Salvador, Tercera occidente): two levels of parallel
    zones (Segunda, Tercera) keep their sizes, the moves go one level by the clubs' areas (pgroups multi-level)"""
    return full_season('slv', 'NORDAMERICA,EL SALVADOR,TERCERA DIVISION OCCIDENTE,HACHADURA')


@scenario
def world_full_eng():
    """Full 5.0 world (full_season): a season at SALFORD CITY (England, League Two): four divisions with the real
    direct places and the Championship / League One / League Two play-offs (gplay) keep their sizes"""
    return full_season('eng', 'EUROPA,INGHILTERRA,EFL LEAGUE TWO,SALFORD CITY')


@scenario
def world_full_arg():
    """Full 5.0 world (full_season): a season at BOCA JUNIORS (Argentina, LIGA PROFESIONAL ZONA A, 15 clubs: a rest day
    each matchday): the season end runs with no 25+-club division (the 30-club table made the season end ask for
    team 0: VerifyTeamLoaded's int 3); sizes kept"""
    return full_season('arg', 'SUDAMERICA,ARGENTINA,LIGA PROFESIONAL ZONA A,BOCA JUNIORS')


@scenario
def world_full_usa():
    """Full 5.0 world (full_season): a season at PHILADELPHIA (USA, MLS EASTERN CONFERENCE, 15 clubs, rest days)"""
    return full_season('usa', 'NORDAMERICA,USA,MLS EASTERN CONFERENCE,PHILADELPHIA')

@scenario
def lp36_tie():
    """League-phase tie-breakers 9-10 (UEFA 2026-27 art. 18.01; tools/lp36.py, lp36 test pack in CLASSIC TOURNEYS):
    (a) a match the engine played: its statistics poked (home 2 yellows + 1 expulsion = 5 points) and lp_game's
    record poked for matchday 1's first fixture -> that club's disciplinary points are 5, its opponent's 0; (b) after
    the last matchday every row is made equal on criteria 1-8 (all zero) with disciplinary points (35 - row) // 2:
    the play-offs (places 9-24) must follow fewer points first, then the contest order (criterion 10's fallback)"""
    import csv
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import lib97
    import lp36
    import lepatch
    from le import LE
    pack = os.path.join(MAIN, 'internal', 'world2526', 'lp36')
    if not os.path.isdir(pack):
        return True, 'SKIP: private pack internal/world2526/lp36 missing'
    names = [c['name'] for c in csv.DictReader(open(os.path.join(pack, 'clubs.csv')))]
    exe = build('lp36tie', env={'PROTO36': '1', 'SEASON_PACKS': 'ddr-1988-89,world-cup-1934,' + pack})
    op = lepatch.LEPatch(os.path.join(ROOT, 'orig', 'ITALIAN.EXE'))
    diy = lib97._sites(op)[3] + 0x41F
    a0 = __import__('sacups').regs(op.le.obj_bytes(1))['A0']
    game, (t1, t2, _) = lp36._game_sites(op, a0)
    d1 = LE(open(os.path.join(exe, 'ITALIAN.EXE'), 'rb').read()).obj_bytes(1)
    lg = game + 5 + struct.unpack_from('<i', d1, game + 1)[0]          # lp_game: A1 A2 / A3 G2 / A1 A1 / A3 G1 / C6 05 F 01
    assert d1[game] == 0xE8 and d1[lg] == 0xA1 and d1[lg + 15] == 0xA3 and d1[lg + 20:lg + 22] == b'\xc6\x05', d1[lg:lg + 30].hex()
    g2, g1, gplay = (struct.unpack_from('<I', d1, x)[0] for x in (lg + 6, lg + 16, lg + 22))
    m = re.search(rb"\x6b\xc1\x12\x8b\x80.{4}\x03\x05(.{4})", d1, re.S)      # lp_tptr: + [SELTEAMS]
    selt = struct.unpack('<I', m.group(1))[0]
    errs, info, rounds, done = [], [], {}, set()

    def poke(s, lin, data):                    # (short SM commands, the debugger's echo read after each: many
        for k in range(0, len(data), 16):      # pokes in a row filled the pty and both sides waited forever)
            s.poke(lin + k, data[k:k + 16])
            s.box.pump(0.05)

    def mark(s, text):                         # progress, written at once (the session log comes at the end)
        open(os.path.join(s.run, 'progress.txt'), 'a').write(text + '\n')
    with Session('lp36_tie', exe, {}, 'dump:2', 1800) as s:
        s.wait()
        for t in ('COMP. PREDEFINITA', 'TORNEI STORICI', 'CHAMPIONS LEAGUE 2025-26', 'TORNEO'):
            if press(s, s.screen(), t) is None or s.result.outcome != 'dump':
                return False, f'{t} not reached ({s.result})'
        u32 = lambda off: struct.unpack('<I', s.result.obj2(off, 4))[0]
        for k in range(600):
            if s.result.outcome != 'dump':
                return False, f'{s.result} at step {k}; ' + '; '.join(info + errs)
            scr = s.screen()
            vis = [t for _, t, inv, _ in scr.entries if t and not inv]
            title = vis[0].replace('CHAMPIONS LEAGUE 2025-26', '').strip()
            mark(s, f'{k} {title[:40]} done {sorted(done)}')
            if title.startswith('PRIMO'):
                b = s.result.obj2(diy, 0x733)
                played = [struct.unpack_from('<H', b, lp36.ROW + 4 + 18 * r)[0] for r in range(36)]
                mark(s, f'   played {sorted(set(played))}')
                cal = [(b[lp36.CAL_OFF + 2 * i], b[lp36.CAL_OFF + 2 * i + 1]) for i in range(144)]
                if 'a' not in done and set(played) == {0}:             # (a) before matchday 1
                    h, a = cal[0]
                    ptr = lambda r: (struct.unpack_from('<I', b, lp36.ROW + 18 * r)[0] + u32(selt)) & 0xFFFFFFFF
                    poke(s, s.result.base2 + g1, struct.pack('<I', ptr(h)))
                    poke(s, s.result.base2 + g2, struct.pack('<I', ptr(a)))
                    poke(s, s.result.base2 + gplay, b'\x01')
                    poke(s, s.result.base2 + t1[1] + 6, struct.pack('<HH', 2, 1))     # bookings 2, sendings-off 1
                    poke(s, s.result.base2 + t2[1] + 6, struct.pack('<HH', 0, 0))
                    done.add('a')
                    first = (h, a)
                elif 'a' in done and 'a2' not in done and set(played) == {1}:
                    h, a = first
                    disc = b[lp36.DISC:lp36.DISC + 36]
                    info.append(f'matchday 1: {names[h]} {disc[h]} points, {names[a]} {disc[a]}; all {list(disc)}')
                    check(disc[h] == 5 and disc[a] == 0, f'played match: disciplinary points {disc[h]} / {disc[a]}', errs)
                    check(s.result.obj2(gplay, 1) == b'\0', 'lp_game record not taken', errs)
                    check(sum(disc) - 5 > 0, 'simulated matches gave no cards', errs)
                    done.add('a2')
                elif 'b' not in done and set(played) == {8} and struct.unpack_from('<H', b, 0x5F)[0] == 0:
                    for r in range(36):                                 # (b) criteria 1-8 equal, 9 = (35 - r) // 2
                        poke(s, s.result.base2 + diy + lp36.ROW + 4 + 18 * r, struct.pack('<7H', 8, 0, 0, 0, 0, 0, 0))
                    poke(s, s.result.base2 + diy + lp36.AWAY_GF, bytes(72))
                    poke(s, s.result.base2 + diy + lp36.DISC, bytes((35 - r) // 2 for r in range(36)))
                    done.add('b')
            if title.startswith('TERZO') or title.startswith('QUARTI'):
                break
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
    check(done >= {'a', 'a2', 'b'}, f'steps done {sorted(done)}', errs)
    rank = sorted(range(36), key=lambda r: ((35 - r) // 2, r))               # fewer points, then the contest order
    place = {names[r]: k + 1 for k, r in enumerate(rank)}
    po = rounds.get('SECONDO TURNO', [])
    check(len(po) == 8 and sorted(place[x] for t in po for x in t) == list(range(9, 25)),
          f'play-off clubs {[(x, place[x]) for t in po for x in t]}', errs)
    for h, a in po:                          # unseeded (23/24 ..) at home first v seeded (9/10 ..) of the same pair
        j = (place[a] - 9) // 2
        check(place[h] in (23 - 2 * j, 24 - 2 * j), f'play-off {h} ({place[h]}) - {a} ({place[a]})', errs)
    info.append(f'play-offs {[(h, place[h], a, place[a]) for h, a in po]}')
    return not errs, '; '.join(info + errs)


@scenario
def club_renames():
    """4.0 (Davide): INTER MILAN / INTERNAZIONALE -> INTER, AC MILAN -> MILAN in every DATA file of the build
    (patch.rename_clubs: 1996-97, the historic packs and worlds, the European cup tourneys, the transfer pool);
    no game run"""
    b = builds()['it']
    d = os.path.join(b, 'DATA')
    old = [n for n in sorted(os.listdir(d)) if re.search(rb'(?<![A-Z0-9 .])(INTER MILAN|AC MILAN|INTERNAZIONALE)\x00',
                                                          open(os.path.join(d, n), 'rb').read())]
    t20 = open(os.path.join(d, 'TEAM.020'), 'rb').read()
    want = {'INTER', 'MILAN'} <= {t20[2 + i * 684 + 5:2 + i * 684 + 22].split(b'\0')[0].decode('latin1')
                                  for i in range(struct.unpack('>H', t20[:2])[0])}
    hist = [n for n in ('TEAM.105', 'TEAM.145') if b'INTER\0' not in open(os.path.join(d, n), 'rb').read()]
    ok = not old and want and not hist
    return ok, f'old names in {old}; INTER + MILAN in TEAM.020 {want}; INTER missing in {hist}' if not ok else \
        'no old name in DATA; TEAM.020 INTER + MILAN; TEAM.105 / TEAM.145 INTER'


def menu_down_to(s, entry, tries=24):
    """'down' until the entry is selected (the menu skips any number of invisible entries; path() gives up after 8)."""
    for _ in range(tries):
        if s.screen().selected == entry:
            return True
        s.send('down dump:0.5')
    return s.screen().selected == entry


@scenario
def menu_levels():
    """4.0 (menutab + menulevels): team choice of a league with levels of groups, level first then group (Davide):
    world 2026-27 (MENU14_BUILD, default builds/w2627-latest), career -> ITALIA = SERIE A, B, C, D (the game showed
    10 of 14 divisions); SERIE D -> its 9 groups, title '... - ITALIA SERIE D'; ESCI -> the levels; SERIE D GIRONE I -> its clubs -> a career at
    TRAPANI starts, its VIEW WORLD lists ITALIA's levels + cups and SERIE D opens its groups; EL SALVADOR: SEGUNDA /
    TERCERA DIVISION -> OCCIDENTE / ORIENTE"""
    b = os.path.realpath(os.environ.get('MENU14_BUILD') or os.path.join(WORK, 'builds', 'w2627-latest'))
    vis = lambda scr: [t for i, t, inv, _ in scr.entries if 11 <= i <= 86 and t and not inv]
    errs, notes = [], []
    head = ('CARRIERA', 'SCEGLI SQUADRA', 'CARR. STORICHE', 'MONDO 2026-27')
    with Session('menu_levels', b, {}, 'dump:2', 600) as s:
        s.wait()
        try:
            for t in head + ('EUROPA',):
                walk(s, t, 3)
            walk(s, 'ITALIA', 3)
            lv = vis(s.screen())
            check(lv == ['SERIE A', 'SERIE B', 'SERIE C', 'SERIE D'], f'ITALIA levels {lv}', errs)
            s.shot('levels')
            walk(s, 'SERIE D', 3)
            gr = vis(s.screen())
            check(gr == [f'SERIE D GIRONE {g}' for g in 'ABCDEFGHI'], f'SERIE D groups {gr}', errs)
            title = s.screen().texts()[0]
            check(title.endswith('ITALIA SERIE D'), f'title {title!r}', errs)
            s.shot('groups')
            check(menu_down_to(s, 88), 'ESCI not reached from the groups', errs)
            s.send('fire dump:3')
            back = vis(s.screen())
            check(back == lv, f'ESCI -> {back}', errs)
            walk(s, 'SERIE D', 3)
            walk(s, 'SERIE D GIRONE I', 3)
            clubs = vis(s.screen())
            check('TRAPANI' in clubs and 'SIRACUSA CALCIO' in clubs, f'GIRONE I clubs {clubs}', errs)
            s.shot('girone_i')
            walk(s, 'TRAPANI', 3)
            s.send('fire dump:3')
            texts = s.screen().texts()
            check('TRASFERIMENTI' in texts or 'PARTITA' in texts, f'career menu {texts[:8]}', errs)
            walk(s, 'VISUALIZZA MONDO', 3)              # VIEW WORLD: the same list with the cups (the second pick)
            for t in ('CARR. STORICHE', 'MONDO 2026-27', 'EUROPA', 'ITALIA'):   # (a world's view: its entry first)
                if s.screen().find(t, exact=True) is not None:
                    walk(s, t, 3)
            wv = vis(s.screen())
            check(wv[:4] == lv and len(wv) > 4, f'VIEW WORLD ITALIA {wv}', errs)
            walk(s, 'SERIE D', 3)
            gr2 = vis(s.screen())
            check(gr2 == gr, f'VIEW WORLD SERIE D {gr2}', errs)
            notes.append(f'VIEW WORLD {wv}')
        except AssertionError as e:
            return False, f'{e}; {"; ".join(errs)}; screen {s.screen().texts()[:16]}'
    with Session('menu_levels_slv', b, {}, 'dump:2', 600) as s:
        s.wait()
        try:
            for t in head:
                walk(s, t, 3)
            cont = next((c for c in ('NORDAMERICA', 'NORD AMERICA', 'CENTROAMERICA') if s.screen().find(c, exact=True) is not None), None)
            walk(s, cont, 3)
            walk(s, 'EL SALVADOR', 3)
            lv = vis(s.screen())
            check('SEGUNDA DIVISION' in lv and 'TERCERA DIVISION' in lv, f'EL SALVADOR levels {lv}', errs)
            walk(s, 'SEGUNDA DIVISION', 3)
            gr = vis(s.screen())
            check(gr == ['SEGUNDA DIVISION OCCIDENTE', 'SEGUNDA DIVISION ORIENTE'], f'SEGUNDA groups {gr}', errs)
            notes.append(f'EL SALVADOR {lv}')
        except AssertionError as e:
            return False, f'{e}; {"; ".join(errs)}; screen {s.screen().texts()[:16]}'
    return not errs, '; '.join(errs) or 'ITALIA: SERIE A, B, C, D -> SERIE D GIRONE A..I -> ESCI -> GIRONE I -> TRAPANI career; ' + '; '.join(notes)


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


NS_W4 = ('EUROPA 1984-85', 'MALTA', 131)             # world_ns: Malta 1984-85 (TEAM.131) and Cyprus 2025-26 (TMW5.131,
NS_W5 = ('WORLD 2025-26', 'CYPRUS', 131)             # the test world generated from file 112): one team word, two worlds


def world_ns_build():
    """Build 'world_ns': the default packs + Europe 1984-85 (world 4, TEAM.101-145) + a 20-country test world 5 from the
    private SWOS 2020 converter (FIRST_FILE=112: its files 112-131 reuse 1984-85 numbers, TMW5.nnn), XTRA hook on;
    plus test XTRA files for ordinal 0 of file 131 in both worlds. Returns (build, {dos name: path}) or None."""
    conv = os.path.join(MAIN, 'internal', 'world2526', 'mkworld2526.py')
    src = os.path.join(MAIN, 'orig', 'swos2020', '2025_26')
    if not (os.path.exists(conv) and os.path.isdir(src)):
        return None
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import xtra
    wdir = os.path.join(WORK, 'world_ns')
    shutil.rmtree(os.path.join(wdir, 'w5'), ignore_errors=True)
    r = subprocess.run([sys.executable, '-I', conv, src, os.path.join(wdir, 'w5'), 'first20'], capture_output=True,
                       text=True, env=dict(os.environ, FIRST_FILE='112'), check=True)
    w5 = [os.path.join(wdir, 'w5', ln.split()[0].lower()) for ln in r.stdout.splitlines() if ' file ' in ln]
    w4 = os.path.join(ROOT, 'packs', 'europe-1984-85')
    packs = ['ddr-1988-89', 'italia-1947-48', 'world-cup-1934'] + \
        [os.path.join(w4, c) for c in sorted(os.listdir(w4)) if not c.startswith('.')] + w5
    b = build('world_ns', env={'SEASON_PACKS': ','.join(packs), 'XTRA_HOOK': '1'})
    files = {}
    for team, dos, tag in (('TEAM.131', 'XTRA.131', 'W4'), ('TMW5.131', 'XTW5.131', 'W5')):
        d = open(os.path.join(b, 'DATA', team), 'rb').read()
        k = struct.unpack('>H', d[:2])[0]
        pl = []
        for j in range(9):                       # ordinal 0 gets club 1's first 9 players, renamed XTRA <world> j
            q = bytearray(d[2 + 684 + 76 + j * 38:2 + 684 + 76 + (j + 1) * 38])
            q[3:26] = f'XTRA {tag} {j + 1}'.encode().ljust(23, b'\0')
            q[2] = 30 + j
            pl.append(bytes(q))
        path = os.path.join(wdir, dos)
        open(path, 'wb').write(xtra.build({0: pl}, k, 9))
        files['DATA/' + dos] = path
    return b, files


def ns_new_career(s, path, club, tag, save, info, errs):
    """Main menu -> CARRIERA -> SCEGLI SQUADRA -> path ('<back>' = ESCI until the next step shows) -> club (ordinal 0
    of file 131): check the managed team word, the 25 players with XTRA <tag>, save as `save` from the main menu."""
    import xtra
    import lepatch
    _, cnp, ct, _, sel = xtra.sites(lepatch.LEPatch(os.path.join(s.run, 'SWOS', 'ITALIAN.EXE')))
    path = ['CARRIERA', 'SCEGLI SQUADRA'] + path + [club]
    for k, t in enumerate(path):
        if t == '<back>':
            for _ in range(6):
                if s.screen().find(path[k + 1], exact=True) is not None:
                    break
                ns_exit(s)
            continue
        walk(s, t, 3)
        if t == 'CARRIERA' and 'SCEGLI SQUADRA' not in s.screen().texts() and 'CONTINUA' in s.screen().texts():
            walk(s, 'CONTINUA', 3)               # a career is running: start a new one
    r = s.result
    team = struct.unpack('<H', r.obj2(sel, 2))[0]
    n = struct.unpack('<H', r.obj2(cnp, 2))[0]
    names = [r.obj2(ct + 76 + j * 38 + 3, 23).split(b'\0')[0].decode('latin1') for j in range(25)]
    info.append(f'{club}: team {team:#x}, {n} players, {names[0]!r} / {names[16]!r}')
    check(team == 131, f'{club}: team word {team:#x}', errs)
    check(n == 25 and names[16:25] == [f'XTRA {tag} {j + 1}' for j in range(9)], f'{club}: extras {n} {names[16:18]}', errs)
    for _ in range(10):                          # chairman's letter -> career menu
        scr = s.screen()
        if 'TRASFERIMENTI' in scr.texts():
            break
        press(s, scr, 'CONTINUA') or s.send('fire dump:2')
    press(s, s.screen(), 'ESCI', wait=3)
    if press(s, s.screen(), 'SALVA CARRIERA') is None:
        return f'no SALVA CARRIERA on {s.screen()}'
    scr = s.screen()                             # the cursor starts on SALVA or (a new career after a save) on the
    k = [e[0] for e in scr.entries].index(scr.find('NOME FILE:', exact=True))      # name field: edit the field
    walk(s, scr.entries[k + 1][0], 1)
    s.send('bspace ' * 8 + ' '.join(save.lower()) + ' enter:1 dump:3')
    car = os.path.join(s.run, 'SWOS', save + '.CAR')
    return car if os.path.exists(car) else f'{save}.CAR not written ({s.result})'


def ns_load(s, name):
    """Main menu -> CARICA VECCHIA COMPETIZIONE -> name -> the career menu; returns its texts."""
    press(s, s.screen(), 'CARICA VECCHIA COMPETIZIONE')
    for _ in range(8):
        scr = s.screen()
        if 'TRASFERIMENTI' in scr.texts():
            return scr.texts()
        if scr.texts()[:1] == ['CARICA VECCHIA COMPETIZIONE'] and scr.find(name, exact=True) is not None:
            walk(s, name, 3)                     # the save list (the cursor may start on the last one loaded)
            continue
        if press(s, scr, 'CONTINUA') is None:   # no blind fire here (it could start a match): wait for the menu
            s.send('dump:2')
    return s.screen().texts()


def mkseason_careers_name():
    return 'CARR. STORICHE'                     # (the IT exe: careerworld WCONT is named as CLASSIC CAREERS)


def ns_view(s):
    """Career menu -> VISUALIZZA MONDO: the texts of the world's list (the swapped countriesTable), then back."""
    press(s, s.screen(), 'VISUALIZZA MONDO', wait=3)
    if s.screen().find(mkseason_careers_name(), exact=True) is not None:   # [-1, 99]: the world's own continent
        press(s, s.screen(), mkseason_careers_name(), wait=3)
    texts = s.screen().texts()
    for _ in range(6):
        if 'TRASFERIMENTI' in s.screen().texts():
            break
        ns_exit(s)
    return texts


def ns_exit(s):
    """Fire the list's ESCI / ABBANDONA (team-selector lists: no menu links the BFS knows, walk down to it)."""
    for _ in range(60):
        scr = s.screen()
        if any(e[0] == scr.selected and e[1] in ('ESCI', 'ABBANDONA') for e in scr.entries):
            break
        s.send('down dump:0.5')
    s.send('fire dump:2')


@scenario
def world_ns():
    """Two career worlds in one exe, each with its own country namespace (1984-85 + a 20-country 2025-26 test world
    on the same numbers 112-131): new careers at Valletta 1984-85 (after a detour into world 5's club list) and AEK
    Larnaca 2025-26 = the same team word 0x83 with each world's XTRA extras; then each save loaded after the other
    world's in one session (VIEW WORLD lists the right world), its season played to the end and saved, checkw1"""
    bf = world_ns_build()
    if bf is None:
        return True, 'SKIP: private converter internal/world2526 or orig/swos2020 missing'
    b, files = bf
    errs, info = [], []
    with Session('world_ns_new', b, files, 'dump:2', 240) as s:
        if s.wait().outcome != 'dump':
            return False, f'START: no first pause ({s.result})'
        car5 = ns_new_career(s, ['CARR. STORICHE', NS_W5[0], NS_W5[1]], 'AEK LARNACA', 'W5', 'NSW5', info, errs)
        car4 = ns_new_career(s, ['CARR. STORICHE', NS_W5[0], 'ENGLAND', 'ENGLAND DIV 1', '<back>', NS_W4[0], NS_W4[1]],
                             'VALLETTA', 'W4', 'NSW4', info, errs)
    for c in (car5, car4):
        if not c.endswith('.CAR'):
            return False, f'{c}; ' + '; '.join(info + errs)
    for first, then, want, other, cw in ((car5, car4, 'INGHILTERRA', 'ENGLAND', ('4', '128', '')),
                                         (car4, car5, 'ENGLAND', 'INGHILTERRA', ('5', '64', '1'))):
        tag = os.path.basename(then)[:-4]
        cars = dict(files, **{'NSW5.CAR': car5, 'NSW4.CAR': car4})
        with Session(f'world_ns_{tag}', b, cars, 'dump:2', 240) as s:
            if s.wait().outcome != 'dump':
                return False, f'START: no first pause ({s.result})'
            ns_load(s, os.path.basename(first)[:-4])
            press(s, s.screen(), 'ESCI', wait=3)
            texts = ns_load(s, tag)
            check('TRASFERIMENTI' in texts, f'{tag}: career menu not reached after the other world ({texts[:4]})', errs)
            view = ns_view(s)
            check(want in view and other not in view, f'{tag} after the other world: VIEW WORLD {view[:8]}', errs)
            check('TRASFERIMENTI' in s.screen().texts(), f'{tag}: back from VIEW WORLD: {s.screen().texts()[:4]}', errs)
            ok, msg = advance(s, season_over, 900)
            if not ok:
                return False, f'{tag}: {msg}; ' + '; '.join(info + errs)
            if s.screen().find('FINISCI STAGIONE', exact=True) is not None:
                press(s, s.screen(), 'FINISCI STAGIONE', wait=3)
            path = next_season_save(s, tag + 'B')
            if not path.endswith('.CAR'):
                return False, f'{tag}: {path}'
        keep = {k: os.environ.get(k) for k in ('W8485_WNUM', 'W8485_K', 'W8485_SMALL')}
        os.environ.update(W8485_WNUM=cw[0], W8485_K=cw[1])
        if cw[2]:
            os.environ['W8485_SMALL'] = '1'
        else:
            os.environ.pop('W8485_SMALL', None)
        try:
            good, report = checkw1(path)
        finally:
            for k, v in keep.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        info.append(f'{tag}: season played after the other world, {msg}, checkw1 {"ok" if good else "FAIL"}')
        check(good, f'{tag}: checkw1\n{report}', errs)
    return not errs, '; '.join(info + errs)




def new_career(s, country, league, team, continent='EUROPA'):
    """Main menu -> CARRIERA -> SCEGLI SQUADRA -> continent -> country -> league -> team -> the
    chairman's note -> career menu."""
    for t in ('CARRIERA', 'SCEGLI SQUADRA', continent):
        walk(s, t, 3)
    for _ in range(60):                         # the countries (columns): one key at a time by the geometry, fire
        scr = s.screen()                        # only on a selection still there one pause later (a move can be
        i = scr.find(country, exact=True)       # taken twice)
        if scr.selected == i:
            s.send('dump:1')
            if s.screen().selected == i:
                break
            continue
        (x, y, _, _), (tx, ty, _, _) = scr.geom[scr.selected], scr.geom[i]
        key = 'right' if x < tx else 'left' if x > tx else 'down' if y < ty else 'up'
        s.send(key + ' dump:0.5')
    else:
        raise AssertionError(f'{country} not reached')
    s.send('fire dump:3')
    if league:                                  # (None: a one-division country, the clubs come at once)
        walk(s, league, 3)
    if team is None:                            # its first club: the first visible entry that has links
        scr = s.screen()
        team = next(i for i, t, inv, _ in scr.entries if t and not inv and i and scr.path(i) is not None)
    walk(s, team, 3)
    s.send('fire dump:3')


def league_table(r, base, n):
    """Rows (played, won, drawn, lost, for, against, points) of a league slot's table (18-byte rows from +2B3h, in
    the order of the team words)."""
    d = r.read(r.base2 + base + 0x2B3, 18 * n)
    return [struct.unpack_from('<7H', d, 18 * k + 4) for k in range(n)]

def contest_tables(r, cid, groups, size):
    """Every buffer of contest `cid` running a group stage of `groups` x `size` (DIY layout: id +2Dh, groups +4Fh,
    clubs per group +51h): [rows (played, won, drawn, lost, for, against, points) of groups * size rows]."""
    d = r.read(r.base2, 0x100000)
    out = []
    for i in range(len(d) - 0x2B3 - 18 * 24):
        if d[i + 0x2D] == cid and struct.unpack_from('<H', d, i + 0x4F)[0] == groups and \
                struct.unpack_from('<H', d, i + 0x51)[0] == size and d[i] == 0:
            out.append(league_table(r, i, groups * size))
    return out


def state_rounds(r, cid, seen):
    """Knockout snapshots of a type-2 contest cid (statespec): seen['rank'] = the copy's +59h order when its
    first knockout stage starts ([53h] = 1); seen[n] = [the round's list +2CDh (n clubs)], first-seen order."""
    d = r.read(r.base2, 0x100000)
    for i in range(len(d) - 0x41F):
        if d[i + 0x2D] != cid:
            continue
        n = struct.unpack_from('<H', d, i + 0x31)[0]
        if d[i] == 2 and struct.unpack_from('<H', d, i + 0x53)[0] == 1 and 'rank' not in seen:
            seen['rank'] = list(d[i + 0x59:i + 0x59 + n])
        elif d[i] == 1 and n in (2, 4, 6, 8, 16):
            lst = list(d[i + 0x2CD:i + 0x2CD + n])
            ties = struct.unpack_from('<H', d, i + 0x4F)[0]
            if (lst, ties) not in seen.setdefault(n, []):
                seen[n].append((lst, ties))


def tie_sets(lst, ties):
    return [frozenset(lst[2 * k:2 * k + 2]) for k in range(ties)]


@scenario
def statespec_byes():
    """State knockout byes (lib97.st_ko / st_kend, STATESPEC_TEST=2 build: a Pernambucano-shaped world-0 test state
    F1 at ATL PARANAENSE: 8 clubs, single round robin; 3rd-6th play the QF (6v3, 5v4), 1st-2nd wait; SF W(5v4) v 1st,
    W(6v3) v 2nd; final): the QF round has 2 ties of exactly those pairs, the SF one tie per bye with the winner of
    its own QF tie, the final one SF winner of each tie"""
    b = os.environ.get('STATESPEC_BUILD2') or builds()['it']
    errs, seen = [], {}
    with Session('statespec_byes', b, {}, 'dump:2', 1800) as s:
        s.wait()
        new_career(s, 'BRASILE', None, 'ATL PARANAENSE', 'SUDAMERICA')

        def stop(scr):
            state_rounds(s.result, 0xF1, seen)
            return season_over(scr)
        ok, msg = advance(s, stop, 1700)
    check(ok, f'season: {msg}', errs)
    R = seen.get('rank')
    check(R is not None and len(R) == 8, f'group ranking {R}', errs)
    if R and seen.get(6) and seen.get(4) and seen.get(2):
        qf, qt = seen[6][0]
        check(qt == 2 and tie_sets(qf, 2) == [frozenset((R[5], R[2])), frozenset((R[4], R[3]))]
              and qf[4:6] == [R[0], R[1]], f'QF {qf} ties {qt} (ranking {R})', errs)
        sf, st = seen[4][0]
        a, c = tie_sets(sf, 2)
        check(st == 2 and R[0] in a and len(a & {R[4], R[3]}) == 1 and R[1] in c and len(c & {R[5], R[2]}) == 1,
              f'SF {sf}', errs)
        fin = set(seen[2][0][0])
        check(len(fin & a) == 1 and len(fin & c) == 1, f'final {sorted(fin)}', errs)
    else:
        check(False, f'rounds seen {sorted(k for k in seen if k != "rank")}', errs)
    return not errs, '; '.join(errs + [f'{msg}; ranking {R}, rounds ' + ', '.join(
        f'{n}: {v[0]}' for n, v in sorted((k, v) for k, v in seen.items() if k != 'rank'))])


@scenario
def statespec_ce():
    """A state's second group stage by 'from' (statespec.st_grp, STATESPEC_TEST=3 build: a Cearense-shaped world-0
    test state F1 at ATL PARANAENSE: 2 groups of 5, then C = the top 3 of A, D = the top 3 of B, 2 groups of 3):
    the second stage's group rows (DIY+6Dh) are exactly those clubs, group by group"""
    b = os.environ.get('STATESPEC_BUILD3') or builds()['it']
    errs, seen = [], {}
    with Session('statespec_ce', b, {}, 'dump:2', 1800) as s:
        s.wait()
        new_career(s, 'BRASILE', None, 'ATL PARANAENSE', 'SUDAMERICA')

        def stop(scr):
            d = s.result.read(s.result.base2, 0x100000)
            for i in range(0, len(d) - 0x41F):
                if d[i + 0x2D] != 0xF1 or d[i] not in (0, 2):
                    continue
                w = lambda o: struct.unpack_from('<H', d, i + o)[0]
                if d[i] == 2 and w(0x53) == 1 and 'rank' not in seen:
                    seen['rank'] = list(d[i + 0x59:i + 0x59 + 10])
                if d[i] == 0 and w(0x31) == 6 and w(0x4F) == 2 and w(0x51) == 3 and 'rows' not in seen:
                    seen['rows'] = [w(0x6D + 2 * k) // 18 for k in range(6)]
            return season_over(scr)
        ok, msg = advance(s, stop, 1700)
    check(ok, f'season: {msg}', errs)
    R, rows = seen.get('rank'), seen.get('rows')
    if R and rows:
        a = [t for t in R if t < 5][:3]
        bb = [t for t in R if t >= 5][:3]
        check(set(rows[:3]) == set(a) and set(rows[3:]) == set(bb), f'phase 2 groups {rows[:3]} / {rows[3:]}, '
              f'want {a} / {bb} (ranking {R})', errs)
    else:
        check(False, f'ranking {R}, phase-2 rows {rows}', errs)
    return not errs, '; '.join(errs + [f'{msg}; ranking {R}, phase 2 {rows}'])


@scenario
def statespec_merit():
    """State knockout by merit (statespec 'pairing': 'merit', statespec.st_ko positions; STATESPEC_TEST=4 build: a
    Mineiro-shaped world-0 test state F1 at ATL PARANAENSE: 3 cross blocks of 4, the engine's 4 qualifiers (3
    winners + the best 2nd, merit order): SF 1st v 4th, 2nd v 3rd; final)"""
    b = os.environ.get('STATESPEC_BUILD4') or builds()['it']
    errs, seen = [], {}
    with Session('statespec_merit', b, {}, 'dump:2', 1800) as s:
        s.wait()
        new_career(s, 'BRASILE', None, 'ATL PARANAENSE', 'SUDAMERICA')

        def stop(scr):
            state_rounds(s.result, 0xF1, seen)
            return season_over(scr)
        ok, msg = advance(s, stop, 1700)
    check(ok, f'season: {msg}', errs)
    R = seen.get('rank')
    if R and seen.get(4) and seen.get(2):
        sf, st = seen[4][0]
        check(st == 2 and tie_sets(sf, 2) == [frozenset((R[0], R[3])), frozenset((R[1], R[2]))],
              f'SF {sf} (ranking {R})', errs)
        fin = set(seen[2][0][0])
        a, c = tie_sets(sf, 2)
        check(len(fin & a) == 1 and len(fin & c) == 1, f'final {sorted(fin)}', errs)
    else:
        check(False, f'ranking {R}, rounds {sorted(k for k in seen if k != "rank")}', errs)
    return not errs, '; '.join(errs + [f'{msg}; ranking {R}, rounds ' + ', '.join(
        f'{n}: {v[0]}' for n, v in sorted((k, v) for k, v in seen.items() if k != 'rank'))])


@scenario
def statespec_test():
    """State championships (statespec.py, STATESPEC_TEST=1 build: world 0's Brazil gets a Paranaense-shaped test state,
    id F1): a career at ATL PARANAENSE plays it in slot 1: 12 clubs in 2 blocks of 6 playing only the OTHER block
    (lp36 fixture contest, 6 days of 6): at every pause of the group stage every row has played the same number of
    matches and block A's goals for = block B's goals against (and the reverse; a round robin inside the groups
    would give A's for = A's against); points 3W + D; the season to its end (knockout 8, 4, 2; the league)"""
    b = os.environ.get('STATESPEC_BUILD') or builds()['it']
    errs, snaps = [], {}
    with Session('statespec_test', b, {}, 'dump:2', 1800) as s:
        s.wait()
        new_career(s, 'BRASILE', None, 'ATL PARANAENSE', 'SUDAMERICA')

        seen = {}

        def stop(scr):
            for rows in contest_tables(s.result, 0xF1, 2, 6):
                pl = {x[0] for x in rows}
                if len(pl) == 1 and pl != {0}:
                    snaps[pl.pop()] = rows
            state_rounds(s.result, 0xF1, seen)
            return season_over(scr)
        ok, msg = advance(s, stop, 1700)
    check(ok, f'season: {msg}', errs)
    R = seen.get('rank')                         # (knockout: QF 4X v 1X, 3X v 2X inside each group, lib97.st_ko;
    if R and seen.get(8) and seen.get(4):        # SF the winners of the same group's two ties, st_kend)
        grp = lambda t: t // 6
        order = {g: [t for t in R if grp(t) == g] for g in (0, 1)}
        want = [frozenset((order[g][3], order[g][0])) for g in (0, 1)] + \
               [frozenset((order[g][2], order[g][1])) for g in (0, 1)]
        qf = tie_sets(*seen[8][0])
        check(sorted(map(sorted, qf)) == sorted(map(sorted, want)), f'QF {seen[8][0][0]} (ranking {R})', errs)
        for t in tie_sets(*seen[4][0]):
            check(len({grp(x) for x in t}) == 1 and all(any(x in q for q in qf) for x in t)
                  and len({next(k for k, q in enumerate(qf) if x in q) for x in t}) == 2,
                  f'SF tie {sorted(t)} (QF {[sorted(q) for q in qf]})', errs)
    else:
        check(False, f'knockout rounds seen {sorted(k for k in seen if k != "rank")}', errs)
    check(len(snaps) >= 3 and max(snaps) <= 6, f'group-stage snapshots after days {sorted(snaps)}', errs)
    for d, rows in sorted(snaps.items()):
        a, bb = rows[:6], rows[6:]
        gf = lambda rs: sum(x[4] for x in rs)
        ga = lambda rs: sum(x[5] for x in rs)
        check(gf(a) == ga(bb) and ga(a) == gf(bb), f'day {d}: A for/against {gf(a)}/{ga(a)}, B {gf(bb)}/{ga(bb)}', errs)
        check(all(x[6] == 3 * x[1] + x[2] for x in rows), f'day {d}: points 3W + D', errs)
    return not errs, '; '.join(errs + [f'{msg}; snapshots {sorted(snaps)}, last {snaps.get(max(snaps)) if snaps else None}'])

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
            os.environ['SWOSTEST_SCENARIO'] = n
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
