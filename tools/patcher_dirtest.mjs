// Release check of the patcher's one-click folder mode (4.0): the page's own code in Node with mocked
// FileSystemDirectoryHandles over real folders built from orig/ (CD) and orig/gog/ (GOG).
//   node tools/patcher_dirtest.mjs PAGE.html c/RELxx SCRATCH_DIR [3.3.6,...]
// Per UI language (it, en, fr, de): a CD install, a GOG install (game in a subfolder, DOSBOX beside it), the copy
// from a CD folder, a SWOS++ install (LOADER.BIN present: ENGLISH.EXE = RELxx/swospp), a re-run (nothing written),
// a wrong folder, an install stopped half way (red INCOMPLETE, then a re-run completes it), and an update over each earlier release given (its outputs made by its own published page,
// orig/old-patchers/patcher-v<ver>.html, from the originals). Every written file must equal RELxx's (SWOS/ or gog/
// for the GOG exes, swospp/ for SWOS++), the world's pool / guest files included; MOD_BACKUP\<version> must hold the
// files replaced. Exit code 1 on any failure. (Node 18+: DecompressionStream.)
import fs from 'fs'; import path from 'path'; import vm from 'vm'; import crypto from 'crypto';
const [page, rel, root, ups = ''] = process.argv.slice(2);
const M = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const md5 = p => crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex');
const stub = () => new Proxy(function () {}, { get: (t, k) => k === Symbol.iterator ? [][Symbol.iterator] : k in t ? t[k] : (t[k] = stub()),
  set: (t, k, v) => (t[k] = v, true), apply: () => stub() });
function load(file, lang) {                                   // a patcher page's script in its own context
  const html = fs.readFileSync(file, 'utf8');
  const js = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
  const ctx = { document: stub(), localStorage: { getItem: () => null, setItem() {} }, navigator: { language: lang }, window: {},
    atob: s => Buffer.from(s, 'base64').toString('latin1'), Blob, Response, DecompressionStream, TextEncoder, TextDecoder, URL, setTimeout, console };
  ctx.document.querySelectorAll = () => [];
  vm.createContext(ctx);
  vm.runInContext(js + '\n;globalThis.__t = { handle, results, PATCHES, setJoy: typeof setJoy === "function" ? setJoy : null, ' +
    (js.includes('function installDir') ? 'installDir, copyTree, findGame, setLang, DT' : 'x: 0') + ' };', ctx);
  if (ctx.__t.setLang) ctx.__t.setLang(lang);
  return ctx.__t;
}
class FH { constructor(p) { this.p = p; this.kind = 'file'; this.name = path.basename(p); }
  async getFile() { const b = fs.readFileSync(this.p); return { name: this.name, arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.length) }; }
  async createWritable() { const p = this.p, ch = []; return { write: async d => ch.push(Buffer.from(d)), close: async () => { if (cut-- > 0) fs.writeFileSync(p, Buffer.concat(ch)); } }; } }
let cut = Infinity;                                          // writes after the first `cut` are lost (an install stopped half way)
class DH { constructor(p) { this.p = p; this.kind = 'directory'; this.name = path.basename(p); }
  async *entries() { for (const n of fs.readdirSync(this.p)) { const q = path.join(this.p, n); yield [n, fs.statSync(q).isDirectory() ? new DH(q) : new FH(q)]; } }
  async removeEntry(n) { fs.rmSync(path.join(this.p, n), { recursive: true, force: true }); }
  async getDirectoryHandle(n, o = {}) { const q = path.join(this.p, n); if (!fs.existsSync(q)) { if (!o.create) throw Object.assign(new Error('nf'), { name: 'NotFoundError' }); fs.mkdirSync(q); } return new DH(q); }
  async getFileHandle(n, o = {}) { const q = path.join(this.p, n); if (!fs.existsSync(q)) { if (!o.create) throw Object.assign(new Error('nf'), { name: 'NotFoundError' }); fs.writeFileSync(q, ''); } return new FH(q); } }
function game(dir, gog) {                                    // a game folder from the originals
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(path.join(dir, 'DATA'), { recursive: true });
  for (const x of ['ITALIAN.EXE', 'ENGLISH.EXE', 'FRENCH.EXE', 'GERMAN.EXE']) fs.copyFileSync(path.join(M, gog ? 'orig/gog' : 'orig', x), path.join(dir, x));
  for (const x of fs.readdirSync(path.join(M, 'orig/DATA'))) fs.copyFileSync(path.join(M, 'orig/DATA', x), path.join(dir, 'DATA', x));
  if (gog) { fs.mkdirSync(path.join(dir, 'DOSBOX'));                 // GOG's DOSBox confs (contents not read by the page)
    for (const c of ['dosbox_SWOS.conf', 'dosbox_SWOS_single.conf', 'dosbox_SWOS_single_italian.conf', 'dosbox_SWOS_single_french.conf',
                     'dosbox_SWOS_single_german.conf']) fs.writeFileSync(path.join(dir, c), '[autoexec]\r\n'); }
}
let fail = 0;
const ok = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); if (!c) fail++; };
function check(T, dir, gog, pp, tag) {                       // every target file = the release build's
  let n = 0, bad = [], pool = 0;
  const done = new Set();
  for (const p of T.PATCHES.filter(p => !p.from && !p.via)) {
    if (p.target === 'SETUP.DAT') continue;                   // (4.0.1: the controls file, its own cases below)
    if (done.has(p.target) || p.id.includes('SWOS++') !== (pp && p.target === 'ENGLISH.EXE')) continue;
    if (p.target.endsWith('.EXE') && p.id.includes('(GOG)') !== gog) continue;
    const want = path.join(rel, pp && p.target === 'ENGLISH.EXE' ? 'swospp' + (gog ? '/gog' : '') :
                                p.target.endsWith('.EXE') && gog ? 'gog' : 'SWOS', p.target);
    if (!fs.existsSync(want)) continue;
    done.add(p.target); n++;
    if (/^DATA\/(RS\d|TMW5\.19[1-4])/.test(p.target)) pool++;
    const got = path.join(dir, p.target);
    if (!fs.existsSync(got) || md5(got) !== md5(want)) bad.push(p.target);
  }
  ok(!bad.length, `${tag}: ${n} files = ${rel} (pool / guest files ${pool})${bad.length ? ' DIFFER: ' + bad.slice(0, 5).join(', ') : ''}`);
}
const backup = dir => path.join(dir, 'MOD_BACKUP', fs.readdirSync(path.join(dir, 'MOD_BACKUP'))[0]);
for (const lang of ['it', 'en', 'fr', 'de']) {
  const T = load(page, lang), log = [], say = (s, bad) => log.push((bad ? '! ' : '') + s), R = path.join(root, lang);
  for (const [name, gog, sub] of [['cd', false, 'SWOS'], ['gog', true, 'Sensible World of Soccer 96-97']]) {
    const top = path.join(R, name), dir = path.join(top, sub); game(dir, gog);
    const n = await T.installDir(new DH(top), say); ok(n > 0 && !log.at(-1).startsWith('!'), `${lang} ${name}: ${n} written: ${log.at(-1)}`);
    check(T, dir, gog, false, `${lang} ${name}`);
    ok(md5(path.join(backup(dir), 'ITALIAN.EXE')) === md5(path.join(M, gog ? 'orig/gog' : 'orig', 'ITALIAN.EXE')) &&
       md5(path.join(backup(dir), 'DATA/TEAM.020')) === md5(path.join(M, 'orig/DATA/TEAM.020')), `${lang} ${name}: MOD_BACKUP = the originals`);
    if (gog) { const want = { Italiano: 'italian', English: '', Francais: 'french', Deutsch: 'german' }, bad = [];
      for (const [l, c] of Object.entries(want)) {
        const f = path.join(dir, `SWOS Mod - ${l}.bat`), conf = c ? `dosbox_SWOS_single_${c}.conf` : 'dosbox_SWOS_single.conf';
        if (!fs.existsSync(f) || fs.readFileSync(f, 'latin1') !== `@echo off\r\ncd /d "%~dp0DOSBOX"\r\nstart "" DOSBox.exe -conf "..\\dosbox_SWOS.conf" -conf "..\\${conf}" -noconsole -c "exit"\r\n`) bad.push(l); }
      ok(!bad.length && /SWOS Mod - /.test(log.at(-1)), `${lang} gog: 4 language launchers${bad.length ? ' WRONG: ' + bad : ''}: ${log.at(-1).slice(-160)}`);
      fs.unlinkSync(path.join(dir, 'SWOS Mod - Deutsch.bat')); }
    const n2 = await T.installDir(new DH(top), say); ok(n2 === 0, `${lang} ${name} again: ${log.at(-1)}`);
    if (gog) ok(fs.existsSync(path.join(dir, 'SWOS Mod - Deutsch.bat')), `${lang} gog again: a missing launcher is written back`);
    if (!gog) ok(!fs.readdirSync(dir).some(x => x.endsWith('.bat')), `${lang} cd: no launchers`);
  }
  { const top = path.join(R, 'cut'), dir = path.join(top, 'SWOS'); game(dir, false); cut = 40;
    const n = await T.installDir(new DH(top), say); cut = Infinity;
    ok(log.at(-1).startsWith('!'), `${lang} stopped half way: ${n} written: ${log.at(-1).slice(0, 160)}`);
    const n2 = await T.installDir(new DH(top), say); ok(n2 > 0 && !log.at(-1).startsWith('!'), `${lang} stopped half way, run again: ${n2} written: ${log.at(-1).slice(0, 80)}`);
    check(T, dir, false, false, `${lang} stopped half way, run again`);
    ok(md5(path.join(backup(dir), 'ITALIAN.EXE')) === md5(path.join(M, 'orig/ITALIAN.EXE')) &&
       fs.readdirSync(path.join(backup(dir), 'DATA')).every(x => fs.existsSync(path.join(M, 'orig/DATA', x)) &&
                                                              md5(path.join(backup(dir), 'DATA', x)) === md5(path.join(M, 'orig/DATA', x))),
       `${lang} stopped half way, run again: MOD_BACKUP = the originals`); }
  { const src = path.join(R, 'cdsrc'), dst = path.join(R, 'cddst'); game(src, false); fs.rmSync(dst, { recursive: true, force: true }); fs.mkdirSync(dst);
    const g = await T.findGame(new DH(src)); await T.copyTree(g.root, new DH(dst)); const n = await T.installDir(new DH(dst), say);
    ok(n > 0, `${lang} from the CD: ${n} written`); check(T, dst, false, false, `${lang} from the CD`);
    ok(md5(path.join(src, 'ITALIAN.EXE')) === md5(path.join(M, 'orig/ITALIAN.EXE')), `${lang} from the CD: the CD folder untouched`); }
  { const top = path.join(R, 'pp'), dir = path.join(top, 'SWOS'); game(dir, false); fs.writeFileSync(path.join(dir, 'LOADER.BIN'), 'x');
    const n = await T.installDir(new DH(top), say); ok(n > 0, `${lang} SWOS++: ${n} written`); check(T, dir, false, true, `${lang} SWOS++`); }
  { // 4.0.1 joypad. GOG layout (DOSBOX folder + dosbox_SWOS.conf), box 1 (default on): the factory SETUP.DAT -> the calibrated one,
    // dosbox_SWOS.conf: joysticktype=fcs + timed=false (only those two lines), mapper-SVN.map (the d-pad) when absent or GOG's default,
    // a .bak of each file that existed; unticked on a re-run = undone. Own DOSBox (CD folder): box 2 (default off) = SETUP.DAT only.
    const cal = md5(path.join(M, 'tools/setup_calibrated.dat')), fac = k => path.join(M, 'orig/setup-factory', k + '.DAT');
    const dpad = path.join(M, 'tools/mapper-SVN.dpad.map'), dflt = path.join(M, 'orig/setup-factory/mapper-SVN.default.map');
    const conf0 = fs.readFileSync(path.join(M, 'orig/setup-factory/dosbox_SWOS.conf'), 'latin1');
    const same = (a, b) => fs.existsSync(a) && fs.existsSync(b) && md5(a) === md5(b);
    const joyGame = (name, gog, kind, map) => { const top = path.join(R, name), dir = path.join(top, 'SWOS'); game(dir, gog);
      if (kind) fs.copyFileSync(fac(kind), path.join(dir, 'SETUP.DAT'));
      if (gog) fs.writeFileSync(path.join(dir, 'dosbox_SWOS.conf'), conf0, 'latin1');
      if (map) fs.copyFileSync(map, path.join(dir, 'mapper-SVN.map')); return [top, dir]; };
    const J = T.DT[lang].joy, conf1ok = t => t.includes('joysticktype=fcs') && t.includes('timed=false') &&
      t.replace('joysticktype=fcs', 'joysticktype=auto').replace('timed=false', 'timed=true') === conf0;
    for (const [kind, gog] of [['CD', false], ['GOG', true]]) {
      const [top, dir] = joyGame('joy' + kind, gog, kind, null);
      const tickOwn = gog ? [true, false] : [false, true], off = [false, false];
      T.setJoy(...off); const n0 = await T.installDir(new DH(top), say), l0 = log.at(-1);
      ok(n0 > 0 && same(path.join(dir, 'SETUP.DAT'), fac(kind)) && !fs.existsSync(path.join(dir, 'SETUP.DAT.bak')) && !fs.existsSync(path.join(dir, 'mapper-SVN.map')) &&
         !l0.includes('SETUP.DAT') && (!gog || fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf'), 'latin1') === conf0), `${lang} joypad ${kind} unticked, fresh: nothing touched, no joypad line`);
      T.setJoy(...tickOwn); const n = await T.installDir(new DH(top), say), l1 = log.at(-1);
      const conf1 = gog ? fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf'), 'latin1') : '';
      ok(md5(path.join(dir, 'SETUP.DAT')) === cal && same(path.join(dir, 'SETUP.DAT.bak'), fac(kind)) && l1.includes(J.done) && !l1.startsWith('!') &&
         (gog ? conf1ok(conf1) && fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf.bak'), 'latin1') === conf0 && l1.includes(J.conf) &&
                same(path.join(dir, 'mapper-SVN.map'), dpad) && !fs.existsSync(path.join(dir, 'mapper-SVN.map.bak')) && l1.includes(J.map)
              : !fs.existsSync(path.join(dir, 'dosbox_SWOS.conf.bak')) && !fs.existsSync(path.join(dir, 'mapper-SVN.map')) && l1.includes(J.own)),
         `${lang} joypad ${kind} ticked: calibrated + SETUP.DAT.bak = factory, logged${gog ? '; conf fcs + timed=false (only those lines) + .bak; d-pad mapper written (absent before)' : '; nothing else (own DOSBox note)'}`);
      await T.installDir(new DH(top), say);
      ok(md5(path.join(dir, 'SETUP.DAT')) === cal && same(path.join(dir, 'SETUP.DAT.bak'), fac(kind)) && log.at(-1).includes(J.already) &&
         (!gog || same(path.join(dir, 'mapper-SVN.map'), dpad)), `${lang} joypad ${kind} ticked again: kept, .bak kept, "already" logged`);
      T.setJoy(...off); await T.installDir(new DH(top), say); const l3 = log.at(-1);
      ok(same(path.join(dir, 'SETUP.DAT'), fac(kind)) && l3.includes(J.undone) && (!gog || (fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf'), 'latin1') === conf0 && !fs.existsSync(path.join(dir, 'mapper-SVN.map')))),
         `${lang} joypad ${kind} unticked: undone from the .bak files${gog ? ' (the mapper we created is removed)' : ''}, logged`);
      await T.installDir(new DH(top), say);
      ok(same(path.join(dir, 'SETUP.DAT'), fac(kind)) && !log.at(-1).includes(J.undone), `${lang} joypad ${kind} unticked again: untouched`);
    }
    { const [top, dir] = joyGame('joymapdef', true, 'GOG', dflt);       // GOG's own default mapper: the d-pad version replaces it, .bak
      T.setJoy(true, false); await T.installDir(new DH(top), say);
      ok(same(path.join(dir, 'mapper-SVN.map'), dpad) && same(path.join(dir, 'mapper-SVN.map.bak'), dflt), `${lang} joypad GOG default mapper: replaced by the d-pad one, .bak = the default`);
      T.setJoy(false, false); await T.installDir(new DH(top), say);
      ok(same(path.join(dir, 'mapper-SVN.map'), dflt), `${lang} joypad GOG default mapper unticked: the default back`); }
    { const mine = path.join(R, 'mymap.map'); fs.mkdirSync(R, { recursive: true }); fs.writeFileSync(mine, fs.readFileSync(dflt, 'latin1').replace('mod_', 'mod_') + '\r\n# mine\r\n');
      const [top, dir] = joyGame('joymapmine', true, 'GOG', mine);        // the user's own mapper: untouched, logged
      T.setJoy(true, false); await T.installDir(new DH(top), say);
      ok(same(path.join(dir, 'mapper-SVN.map'), mine) && !fs.existsSync(path.join(dir, 'mapper-SVN.map.bak')) && log.at(-1).includes(J.mapkeep) && md5(path.join(dir, 'SETUP.DAT')) === cal,
         `${lang} joypad GOG own mapper: untouched, logged (SETUP.DAT + conf still done)`); }
    { const [top, dir] = joyGame('joycdown', false, 'CD', null);          // a CD folder, box 1 on (GOG's) and box 2 off: nothing (it is not a GOG layout)
      T.setJoy(true, false); await T.installDir(new DH(top), say);
      ok(same(path.join(dir, 'SETUP.DAT'), fac('CD')) && !fs.existsSync(path.join(dir, 'SETUP.DAT.bak')), `${lang} joypad not GOG, only the GOG box ticked: SETUP.DAT untouched`); }
    { // GOG's cloud_saves overlay: its SETUP.DAT shadows the game folder's; same rule there
      for (const [tag, mk] of [['factory', null], ['custom', b => { b[6] = 2; b[100] = 0x39; return b; }]]) {
        const [top, dir] = joyGame('joycloud' + tag, true, 'GOG', null); fs.mkdirSync(path.join(dir, 'cloud_saves'));
        const cs = path.join(dir, 'cloud_saves', 'SETUP.DAT'), b = Buffer.from(fs.readFileSync(fac('GOG'))); fs.writeFileSync(cs, mk ? mk(b) : b);
        const before = fs.readFileSync(cs);
        T.setJoy(true, false); await T.installDir(new DH(top), say); const l1 = log.at(-1);
        if (!mk) ok(md5(cs) === cal && same(path.join(dir, 'cloud_saves', 'SETUP.DAT.bak'), fac('GOG')) && md5(path.join(dir, 'SETUP.DAT')) === cal &&
                    l1.includes(J.cloud), `${lang} joypad cloud_saves ${tag} ticked: both SETUP.DAT calibrated, .bak beside each, logged`);
        else ok(Buffer.compare(fs.readFileSync(cs), before) === 0 && !fs.existsSync(path.join(dir, 'cloud_saves', 'SETUP.DAT.bak')) && md5(path.join(dir, 'SETUP.DAT')) === cal &&
                l1.includes(J.cloud + ' ' + J.custom), `${lang} joypad cloud_saves ${tag} ticked: its SETUP.DAT untouched, logged (the game's own one calibrated)`);
        T.setJoy(false, false); await T.installDir(new DH(top), say);
        ok(Buffer.compare(fs.readFileSync(cs), before) === 0 && same(path.join(dir, 'SETUP.DAT'), fac('GOG')), `${lang} joypad cloud_saves ${tag} unticked: everything back`);
      }
      { const [top, dir] = joyGame('joycloudnone', true, 'GOG', null); fs.mkdirSync(path.join(dir, 'cloud_saves')); T.setJoy(true, false);   // (an empty overlay dir)
        await T.installDir(new DH(top), say); ok(md5(path.join(dir, 'SETUP.DAT')) === cal && !fs.existsSync(path.join(dir, 'cloud_saves', 'SETUP.DAT')), `${lang} joypad cloud_saves empty: nothing created there`); }
    }
    { const [top, dir] = joyGame('joycustom', true, null, null);
      const mine = Buffer.from(fs.readFileSync(fac('GOG'))); mine[6] = 2; mine[100] = 0x39; fs.writeFileSync(path.join(dir, 'SETUP.DAT'), mine);
      T.setJoy(true, false); const n = await T.installDir(new DH(top), say), l1 = log.at(-1);
      ok(n > 0 && Buffer.compare(fs.readFileSync(path.join(dir, 'SETUP.DAT')), mine) === 0 && !fs.existsSync(path.join(dir, 'SETUP.DAT.bak')) &&
         fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf'), 'latin1') === conf0 && !fs.existsSync(path.join(dir, 'mapper-SVN.map')) && l1.includes(J.custom) && !l1.startsWith('!'),
         `${lang} joypad custom SETUP.DAT ticked: untouched (conf and mapper too), no .bak, logged`);
      T.setJoy(false, false); await T.installDir(new DH(top), say);
      ok(Buffer.compare(fs.readFileSync(path.join(dir, 'SETUP.DAT')), mine) === 0, `${lang} joypad custom SETUP.DAT unticked: untouched`); }
    { const [top, dir] = joyGame('joynone', false, null, null); T.setJoy(false, true);
      const n = await T.installDir(new DH(top), say), l1 = log.at(-1);
      ok(n > 0 && !fs.existsSync(path.join(dir, 'SETUP.DAT')) && !fs.existsSync(path.join(dir, 'SETUP.DAT.bak')) && l1.includes(J.none),
         `${lang} joypad missing SETUP.DAT ticked: nothing created, logged`); }
    { const [top, dir] = joyGame('joyconfonly', true, 'GOG', null); const c = conf0.replace(/\[joystick\][^[]*/, '[joystick]\r\n');   // no joysticktype / timed lines at all
      fs.writeFileSync(path.join(dir, 'dosbox_SWOS.conf'), c, 'latin1'); T.setJoy(true, false); await T.installDir(new DH(top), say);
      const t = fs.readFileSync(path.join(dir, 'dosbox_SWOS.conf'), 'latin1');
      ok(/\[joystick\]\r\njoysticktype=fcs\r\ntimed=false\r\n/.test(t), `${lang} joypad conf without the two lines: inserted in [joystick]`); }
    { // 4.0.2 keyboard mode (box 3, GOG only): SETUP.DAT keyboard only (factory), conf fcs + timed=false, the keyboard-mode mapper;
      // switching modes swaps mapper + SETUP.DAT both ways; unticking undoes it all
      const keys = path.join(M, 'tools/mapper-SVN.keys.map'), calf = path.join(M, 'tools/setup_calibrated.dat');
      const conf = d => fs.readFileSync(path.join(d, 'dosbox_SWOS.conf'), 'latin1'), mapf = d => path.join(d, 'mapper-SVN.map');
      { const [top, dir] = joyGame('joykey', true, 'GOG', null);
        T.setJoy(true, false, true); await T.installDir(new DH(top), say); const l1 = log.at(-1);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && !fs.existsSync(path.join(dir, 'SETUP.DAT.bak')) && conf1ok(conf(dir)) &&
           same(mapf(dir), keys) && !fs.existsSync(mapf(dir) + '.bak') && l1.includes(J.kalready) && l1.includes(J.kmap) && !l1.startsWith('!'),
           `${lang} joypad keyboard mode, fresh GOG: factory SETUP.DAT kept, conf fcs + timed=false, keyboard-mode mapper written, logged`);
        T.setJoy(true, false, false); await T.installDir(new DH(top), say); const l2 = log.at(-1);
        ok(md5(path.join(dir, 'SETUP.DAT')) === cal && same(path.join(dir, 'SETUP.DAT.bak'), fac('GOG')) && same(mapf(dir), dpad) &&
           !fs.existsSync(mapf(dir) + '.bak') && l2.includes(J.done) && l2.includes(J.map), `${lang} joypad keyboard mode -> calibrated mode: SETUP.DAT calibrated, d-pad mapper`);
        T.setJoy(true, false, true); await T.installDir(new DH(top), say); const l3 = log.at(-1);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && same(mapf(dir), keys) && l3.includes(J.kdone) && l3.includes(J.kmap),
           `${lang} joypad calibrated -> keyboard mode: factory SETUP.DAT back from the .bak, keyboard-mode mapper`);
        T.setJoy(true, false, true); await T.installDir(new DH(top), say); const l4 = log.at(-1);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && same(mapf(dir), keys) && l4.includes(J.kalready) && !l4.includes(J.kmap),
           `${lang} joypad keyboard mode again: nothing changed`);
        T.setJoy(false, false, false); await T.installDir(new DH(top), say); const l5 = log.at(-1);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && conf(dir) === conf0 && !fs.existsSync(mapf(dir)) && l5.includes(J.undone),
           `${lang} joypad keyboard mode unticked: conf back, our mapper removed, logged`); }
      { const [top, dir] = joyGame('joykeycal', true, null, dflt); fs.copyFileSync(calf, path.join(dir, 'SETUP.DAT'));   // calibrated, no .bak
        T.setJoy(true, false, true); await T.installDir(new DH(top), say);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && same(mapf(dir), keys) && same(mapf(dir) + '.bak', dflt),
           `${lang} joypad keyboard mode over a calibrated SETUP.DAT without .bak: GOG's factory file, GOG's default mapper -> .bak`);
        T.setJoy(false, false, false); await T.installDir(new DH(top), say);
        ok(same(mapf(dir), dflt) && conf(dir) === conf0, `${lang} joypad keyboard mode unticked: GOG's default mapper back`); }
      { const [top, dir] = joyGame('joykeycloud', true, 'GOG', null); fs.mkdirSync(path.join(dir, 'cloud_saves'));
        const cs = path.join(dir, 'cloud_saves', 'SETUP.DAT'); fs.copyFileSync(calf, cs);
        T.setJoy(true, false, true); await T.installDir(new DH(top), say); const l1 = log.at(-1);
        ok(same(cs, fac('GOG')) && same(path.join(dir, 'SETUP.DAT'), fac('GOG')) && l1.includes(J.cloud + ' ' + J.kdone),
           `${lang} joypad keyboard mode, cloud_saves calibrated: both SETUP.DAT keyboard only, logged`); }
      { const mine = path.join(R, 'mine-k.map'); fs.writeFileSync(mine, 'key_up "key 273"\r\n');
        const [top, dir] = joyGame('joykeymine', true, 'GOG', mine);
        T.setJoy(true, false, true); await T.installDir(new DH(top), say);
        ok(same(mapf(dir), mine) && !fs.existsSync(mapf(dir) + '.bak') && log.at(-1).includes(J.mapkeep), `${lang} joypad keyboard mode, own mapper: untouched, logged`); }
      { const [top, dir] = joyGame('joykeycd', false, 'CD', null);          // a CD folder: keyboard mode is for GOG's DOSBox only
        T.setJoy(true, false, true); await T.installDir(new DH(top), say);
        ok(same(path.join(dir, 'SETUP.DAT'), fac('CD')) && !fs.existsSync(mapf(dir)), `${lang} joypad keyboard mode, CD folder: nothing`); }
      T.setJoy(true, false, false);
    }
    T.setJoy(true, false);
  }
  { const w = path.join(R, 'wrong'); fs.rmSync(w, { recursive: true, force: true }); fs.mkdirSync(w); fs.writeFileSync(path.join(w, 'x.txt'), 'x');
    const n = await T.installDir(new DH(w), say); ok(n === 0 && log.at(-1).startsWith('!'), `${lang} wrong folder: ${log.at(-1)}`); }
  for (const v of ups.split(',').filter(Boolean)) {          // an install patched by release v (its own page)
    const top = path.join(R, 'up' + v), dir = path.join(top, 'SWOS'); game(dir, false);
    const O = load(path.join(M, 'orig/old-patchers', `patcher-v${v}.html`), 'en');
    const files = [...['ITALIAN.EXE', 'ENGLISH.EXE', 'FRENCH.EXE', 'GERMAN.EXE'].map(x => path.join(dir, x)),
                   ...fs.readdirSync(path.join(dir, 'DATA')).map(x => path.join(dir, 'DATA', x))];
    await O.handle(files.map(f => ({ name: path.basename(f), arrayBuffer: async () => { const b = fs.readFileSync(f); return b.buffer.slice(b.byteOffset, b.byteOffset + b.length); } })));
    let w = 0;
    for (const r of O.results) if (r.state === 'ok' && !r.patch.id.includes('SWOS++') && !r.patch.id.includes('(GOG)')) { fs.writeFileSync(path.join(dir, r.patch.target), Buffer.from(r.out)); w++; }
    const old = md5(path.join(dir, 'ITALIAN.EXE'));
    const n = await T.installDir(new DH(top), say); ok(n > 0, `${lang} update over ${v} (${w} files of ${v}): ${n} written`);
    check(T, dir, false, false, `${lang} update over ${v}`);
    ok(md5(path.join(backup(dir), 'ITALIAN.EXE')) === old, `${lang} update over ${v}: MOD_BACKUP = the ${v} exe`);
  }
}
console.log(fail ? `${fail} FAILED` : 'ALL OK');
process.exit(fail ? 1 : 0);
