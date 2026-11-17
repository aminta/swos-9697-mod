#!/bin/zsh
# tools/hosttest/mkfixtures.sh [world data]: the host suite's (tools/hosttest/run.py) fixtures, from this checkout.
#   1. c/HTW, c/HTO4, c/HTOMM, c/HTPC2 (and 1b: c/HTn7rf / HTn7rd, test_sreg's, world5tm-h2): one release-recipe build (buildrel.sh's: the packs + the world data, every
#      test switch cleared) of ITALIAN.EXE with HOSTTEST_SYMS=1 (ITALIAN.syms.json next to it; the log build-it.log),
#      copied to the dirs test_registry / test_wmodes, test_swe, test_wtphys and test_swc1 (test_ledger...) read.
#      World data: $1, else world5tm-s1rank-int3.
#   2. the snapshot fixtures' builds (internal/hosttest/fixtures/*/N.json 'build'): kept in internal/hosttest/
#      fixture-builds/<name>, internal/swostest/builds/<name> a symlink to it (swostest's build_cleanup removes
#      <name>-<key> dirs unused for 3 days; a symlink it cannot). One gone comes back from its archive on
#      /Volumes/Backup1/swos-mod-runs (sha1 in ARCHIVED.txt checked) - the snapshots run that build's code, a rebuild
#      would not match them. A build no archive has: an error only if a test reads its fixture dir.
#   42-fixroot (MC 16/11): 1, 1b and the S7 shaped fixtures (S7W-ws4c, S7RI-hs; tools/hosttest/mkshaped.sh) are built into ONE new
#      dir c/FX-<tip sha>/ with a MANIFEST.json (md5s); nothing is rebuilt in place. `export HOSTTEST_FIXROOT=c/FX-<sha>` (printed)
#      makes every test read it (tools/hosttest/fixroot.py checks the manifest; a stale or edited fixture FAILs).
# Never c/SWOS (shared). Run from the checkout root; no DOSBox.
set -eu
cd "$(git rev-parse --show-toplevel)"
export PATH=/opt/homebrew/bin:$PATH
M=$HOME/swos-mod; C=$M/c; W=$M/internal/world2526/${1:-world5tm-s1rank-int3}
test -f $W.txt || { echo "no world data $W.txt"; exit 1; }
EU=$(ls -d packs/europe-1984-85/*/ | sed 's|/$||' | sed "s|^|$PWD/|" | paste -sd, -)
export SEASON_PACKS="ddr-1988-89,italia-1947-48,world-cup-1934,$EU,$(grep ' file ' $W.txt | awk -v w=$W '{print w"/"tolower($1)}' | paste -sd, -)"
CLR=($(python3 -c "import sys; sys.path.insert(0, 'tools'); import modver; print(' '.join(getattr(modver, 'BUILD_SWITCHES', modver.TEST_VARS)))") ${(k)parameters[(I)*_FORCE*]})
for v in $CLR; do unset $v; done
export HOSTTEST_SYMS=1

# 42-fixroot (MC 16/11): every fixture goes into ONE new dir c/FX-<tip sha>/ (never rebuilt in place: another session's
# mkfixtures cannot change what a running suite reads), with a MANIFEST.json of md5s (tools/hosttest/fixroot.py checks it).
# The tests read it through `export HOSTTEST_FIXROOT=c/FX-<sha>` (printed at the end); MKFIX_LEGACY=1 also refreshes the old
# in-place c/HT* dirs for sessions that still read them.
SHA=$(git rev-parse --short HEAD); [ -n "$(git status --porcelain --untracked-files=no)" ] && SHA=$SHA-d$(date +%H%M%S)
FX=$C/FX-$SHA
if [ -e $FX/MANIFEST.json ]; then echo "fixtures for $SHA exist: $FX"; else
  T=$FX.tmp.$$; trap 'rm -rf $T' EXIT; mkdir -p $T
  P=$T/HTW; mkdir -p $P/SWOS/DATA
  rsync -a --exclude DATA --exclude ITALIAN.EXE --exclude ENGLISH.EXE --exclude FRENCH.EXE --exclude GERMAN.EXE $C/REL40rc2/SWOS/ $P/SWOS/
  cp -p orig/DATA/* $P/SWOS/DATA/
  python3 $M/internal/release-tools/bfull.py orig/ITALIAN.EXE $P/SWOS/ITALIAN.EXE it $P/SWOS/DATA > $P/build-it.log 2>&1 \
    || { tail -20 $P/build-it.log; exit 1; }
  test -s $P/SWOS/ITALIAN.syms.json
  echo "$SHA, data ${W:t}, HOSTTEST_SYMS=1 (tools/hosttest/mkfixtures.sh $(date +%F))" >> $P/build-it.log
  for d in HTO4 HTOMM HTPC2 HTMC HTTC1; do cp -a $P $T/$d; done      # (HTMC: test_champ / test_cbonus's plain HOSTTEST_SYMS image; HTTC1: test_tcache / test_tc1b, the release-recipe exe)
  echo "FX/HTW: $(md5 -q $P/SWOS/ITALIAN.EXE)  $(tail -1 $P/build-it.log)"

  # 1b. test_sreg's pair: HTn7rf (SREG_FORCE=1) and HTn7rd (dormant), the release recipe on world5tm-h2 (its own SEASON_PACKS)
  W2=$M/internal/world2526/world5tm-h2
  P2="ddr-1988-89,italia-1947-48,world-cup-1934,$EU,$(grep ' file ' $W2.txt | awk -v w=$W2 '{print w"/"tolower($1)}' | paste -sd, -)"
  for d in HTn7rf HTn7rd; do
    N=$T/$d; mkdir -p $N/SWOS/DATA
    rsync -a --exclude DATA --exclude ITALIAN.EXE --exclude ENGLISH.EXE --exclude FRENCH.EXE --exclude GERMAN.EXE $C/REL40rc2/SWOS/ $N/SWOS/
    cp -p orig/DATA/* $N/SWOS/DATA/
    F=(); [ $d = HTn7rf ] && F=(SREG_FORCE=1)
    env SEASON_PACKS=$P2 $F python3 $M/internal/release-tools/bfull.py orig/ITALIAN.EXE $N/SWOS/ITALIAN.EXE it $N/SWOS/DATA \
      > $N/build-it.log 2>&1 || { tail -20 $N/build-it.log; exit 1; }
    test -s $N/SWOS/ITALIAN.syms.json
    echo "$SHA, data ${W2:t}, HOSTTEST_SYMS=1 ${F[*]} (tools/hosttest/mkfixtures.sh $(date +%F))" >> $N/build-it.log
    echo "FX/$d: $(md5 -q $N/SWOS/ITALIAN.EXE)  $(tail -1 $N/build-it.log)"
  done

  # 1c. the S7 shaped fixtures (Italy = internal/s7pack-real/ita): the default of the S7 / wsites / bteam / rimoves tests
  for d in S7W-ws4c S7RI-hs S7W-p6w; do      # (S7W-p6w: test_s7swap piece 4 / test_bteam_s7, shaped with S7_WSITES_TEST=1)
    ME=; [ $d = S7W-p6w ] && ME=S7_WSITES_TEST=1
    MKSHAPED_ENV=$ME zsh tools/hosttest/mkshaped.sh $T/$d > $T/$d.mk.log 2>&1 || { tail -20 $T/$d.mk.log; echo "FAIL: shaped $d"; exit 1; }
    echo "FX/$d: $(md5 -q $T/$d/SWOS/ITALIAN.EXE)  $(tail -1 $T/$d/build-it.log)"
  done

  python3 - $T <<'E'
import hashlib, json, os, sys
r = sys.argv[1]
man = {}
for d in sorted(os.listdir(r)):
    p = os.path.join(r, d)
    if os.path.isdir(p):
        man[d] = {rel: hashlib.md5(open(os.path.join(p, rel), 'rb').read()).hexdigest()
                  for rel in ('SWOS/ITALIAN.EXE', 'SWOS/ITALIAN.syms.json') if os.path.isfile(os.path.join(p, rel))}
json.dump(man, open(os.path.join(r, 'MANIFEST.json'), 'w'), indent=1, sort_keys=True)
E
  rm -f $T/*.mk.log
  mv $T $FX; trap - EXIT
fi
if [ -n "${MKFIX_LEGACY:-}" ]; then
  for d in HTW HTO4 HTOMM HTPC2 HTMC HTTC1 HTn7rf HTn7rd S7W-ws4c S7RI-hs S7W-p6w; do rm -rf $C/$d.old; [ -e $C/$d ] && mv $C/$d $C/$d.old; cp -a $FX/$d $C/$d && rm -rf $C/$d.old; done
fi
echo "export HOSTTEST_FIXROOT=$FX"

A=/Volumes/Backup1/swos-mod-runs
python3 - $M $A $PWD/tools/hosttest/tests <<'E'
import glob, hashlib, json, os, subprocess, sys
m, a, tests = sys.argv[1:4]
builds = os.path.join(m, 'internal', 'swostest', 'builds')
keep = os.path.join(m, 'internal', 'hosttest', 'fixture-builds')
os.makedirs(keep, exist_ok=True)
src = ''.join(open(os.path.join(tests, f)).read() for f in os.listdir(tests) if f.endswith('.py'))
need = {}
for js in glob.glob(os.path.join(m, 'internal', 'hosttest', 'fixtures', '*', '[0-9]*.json')):
    b = json.load(open(js)).get('build')
    if b and '/internal/swostest/builds/' in b:
        need.setdefault(os.path.basename(b.rstrip('/')), set()).add(os.path.basename(os.path.dirname(js)))
sums = {}
if os.path.exists(os.path.join(a, 'ARCHIVED.txt')):
    for ln in open(os.path.join(a, 'ARCHIVED.txt')):
        p = ln.split()
        if len(p) >= 4:
            sums[p[2]] = p[3]
bad = 0
for n in sorted(need):
    link, kept = os.path.join(builds, n), os.path.join(keep, n)
    if os.path.isdir(link) and not os.path.islink(link) and not os.path.exists(kept):
        os.rename(link, kept)                                # (a live build dir: kept out of build_cleanup's reach)
    if not os.path.exists(os.path.join(kept, 'ITALIAN.EXE')):
        tar = os.path.join(a, f'builds_{n}.tar')
        used = sorted(d for d in need[n] if f"'{d}'" in src)
        if not os.path.exists(tar) or os.path.basename(tar) not in sums:
            print(f'fixture build {n}: missing, no archive (fixtures {sorted(need[n])}; '
                  + (f'read by the tests: {used})' if used else 'no test reads them)'))
            bad += bool(used)
            continue
        if hashlib.sha1(open(tar, 'rb').read()).hexdigest() != sums[os.path.basename(tar)]:
            print(f'fixture build {n}: archive sha1 mismatch'); bad += 1; continue
        subprocess.run(['tar', 'xf', tar, '-C', keep], check=True)
        print(f'fixture build {n}: restored from {tar}')
    if os.path.islink(link) or os.path.exists(link):
        if os.path.realpath(link) == os.path.realpath(kept):
            continue
        print(f'fixture build {n}: {link} is another dir, left alone'); bad += 1; continue
    os.symlink(kept, link)
    print(f'fixture build {n}: {link} -> {kept}')
print(f'snapshot fixtures: {len(need)} builds, {bad} problems')
sys.exit(1 if bad else 0)
E
