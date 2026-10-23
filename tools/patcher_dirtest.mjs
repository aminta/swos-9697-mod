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
    atob: s => Buffer.from(s, 'base64').toString('latin1'), Blob, Response, DecompressionStream, TextEncoder, URL, setTimeout, console };
  ctx.document.querySelectorAll = () => [];
  vm.createContext(ctx);
  vm.runInContext(js + '\n;globalThis.__t = { handle, results, PATCHES, ' +
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
