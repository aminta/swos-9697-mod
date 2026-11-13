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

T=$C/HTfix.$$
trap 'rm -rf $T' EXIT
mkdir -p $T/SWOS/DATA
rsync -a --exclude DATA --exclude ITALIAN.EXE --exclude ENGLISH.EXE --exclude FRENCH.EXE --exclude GERMAN.EXE $C/REL40rc2/SWOS/ $T/SWOS/
cp -p orig/DATA/* $T/SWOS/DATA/
python3 $M/internal/release-tools/bfull.py orig/ITALIAN.EXE $T/SWOS/ITALIAN.EXE it $T/SWOS/DATA > $T/build-it.log 2>&1 \
  || { tail -20 $T/build-it.log; exit 1; }
test -s $T/SWOS/ITALIAN.syms.json
echo "$(git rev-parse --short HEAD), data ${W:t}, HOSTTEST_SYMS=1 (tools/hosttest/mkfixtures.sh $(date +%F))" >> $T/build-it.log
for d in HTW HTO4 HTOMM HTPC2; do
  rm -rf $C/$d.old; [ -e $C/$d ] && mv $C/$d $C/$d.old
  cp -a $T $C/$d && rm -rf $C/$d.old
  echo "c/$d: $(md5 -q $C/$d/SWOS/ITALIAN.EXE)  $(tail -1 $C/$d/build-it.log)"
done

# 1b. test_sreg's pair (42-fixn7, MC 13/11): c/HTn7rf (SREG_FORCE=1) and c/HTn7rd (dormant), HOSTTEST_SYMS=1, the release
#     recipe on world5tm-h2 (its own SEASON_PACKS); hand-built before, stale after 42-swcnew (a FAIL on the old exes)
W2=$M/internal/world2526/world5tm-h2
P2="ddr-1988-89,italia-1947-48,world-cup-1934,$EU,$(grep ' file ' $W2.txt | awk -v w=$W2 '{print w"/"tolower($1)}' | paste -sd, -)"
for d in HTn7rf HTn7rd; do
  N=$C/HTfix7.$$; rm -rf $N; mkdir -p $N/SWOS/DATA
  rsync -a --exclude DATA --exclude ITALIAN.EXE --exclude ENGLISH.EXE --exclude FRENCH.EXE --exclude GERMAN.EXE $C/REL40rc2/SWOS/ $N/SWOS/
  cp -p orig/DATA/* $N/SWOS/DATA/
  F=(); [ $d = HTn7rf ] && F=(SREG_FORCE=1)
  env SEASON_PACKS=$P2 $F python3 $M/internal/release-tools/bfull.py orig/ITALIAN.EXE $N/SWOS/ITALIAN.EXE it $N/SWOS/DATA \
    > $N/build-it.log 2>&1 || { tail -20 $N/build-it.log; rm -rf $N; exit 1; }
  test -s $N/SWOS/ITALIAN.syms.json
  echo "$(git rev-parse --short HEAD), data ${W2:t}, HOSTTEST_SYMS=1 ${F[*]} (tools/hosttest/mkfixtures.sh $(date +%F))" >> $N/build-it.log
  rm -rf $C/$d.old; [ -e $C/$d ] && mv $C/$d $C/$d.old
  mv $N $C/$d && rm -rf $C/$d.old
  echo "c/$d: $(md5 -q $C/$d/SWOS/ITALIAN.EXE)  $(tail -1 $C/$d/build-it.log)"
done

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
