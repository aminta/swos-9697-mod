#!/bin/zsh
# tools/hosttest/mkshaped.sh DEST [S7PACK]: a shaped IT test build (Italy = the S7 pack, HOSTTEST_SYMS=1) of this checkout into DEST
# (a new dir, built by mkfixtures.sh inside c/FX-<sha>/). The recipe of the old scratch scripts (s7env.sh + mkshaped.sh): the
# release-recipe packs of world5tm-h2 with its Italy pack replaced by S7PACK (default internal/s7pack-real/ita).
set -eu
cd "$(git rev-parse --show-toplevel)"
export PATH=/opt/homebrew/bin:$PATH
M=$HOME/swos-mod; DEST=$1; export S7PACK=${2:-$M/internal/s7pack-real/ita}
test -e $DEST && { echo "mkshaped: $DEST exists"; exit 1; }
W=$M/internal/world2526/world5tm-h2
EU=$(ls -d $PWD/packs/europe-1984-85/*/ | sed 's|/$||' | paste -sd, -)
export SEASON_PACKS="ddr-1988-89,italia-1947-48,world-cup-1934,$EU,$(grep ' file ' $W.txt | awk -v w=$W '{print w"/"tolower($1)}' | sed "s|$W/ita\$|$S7PACK|" | paste -sd, -)"
CLR=($(python3 -c "import sys; sys.path.insert(0, 'tools'); import modver; print(' '.join(getattr(modver, 'BUILD_SWITCHES', modver.TEST_VARS)))") ${(k)parameters[(I)*_FORCE*]})
for v in $CLR; do unset $v; done
export HOSTTEST_SYMS=1
for kv in ${=MKSHAPED_ENV:-}; do export $kv; done      # (test switches this fixture wants, e.g. S7_WSITES_TEST=1)
mkdir -p $DEST/SWOS/DATA
rsync -a --exclude DATA --exclude ITALIAN.EXE --exclude ENGLISH.EXE --exclude FRENCH.EXE --exclude GERMAN.EXE $M/c/REL40rc2/SWOS/ $DEST/SWOS/
cp -p orig/DATA/* $DEST/SWOS/DATA/
python3 $M/internal/release-tools/bfull.py orig/ITALIAN.EXE $DEST/SWOS/ITALIAN.EXE it $DEST/SWOS/DATA > $DEST/build-it.log 2>&1 \
  || { tail -20 $DEST/build-it.log; exit 1; }
test -s $DEST/SWOS/ITALIAN.syms.json
echo "$(git rev-parse --short HEAD), S7PACK ${S7PACK:t}, HOSTTEST_SYMS=1 (tools/hosttest/mkshaped.sh $(date +%F))" >> $DEST/build-it.log
