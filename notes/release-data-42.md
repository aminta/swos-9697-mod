# 4.2 release data (the data dirs live in internal/world2526, outside git; this note is their record)

Recipe (run from a checkout root, all 8 exes: IT / EN / FR / DE, CD + GOG):

    NOPATCHER=1 zsh internal/release-tools/buildrel.sh <REL dir under c/> world5tm-h3s7      # 4.2 with S3 + S7

Chain of the data (each a copy with cp -RL, the previous dir and its .bak untouched):

| name | made from | what changed |
|------|-----------|--------------|
| world5tm-h3p | h3 line, post-NETO (15/11 07:06) | real Serie A / B line-ups, tactics, NETO override on JUVENTUS' bench |
| world5tm-h3s | h3p | S3 shape: ita/pack.json only, ko_playoffs +3 entries (b_po, b_pout, c_po; c_po with the exact C.U. 209/A cup place, "real": true). compile_spec of the 3 = the engine's ita_s3r.spec byte for byte |
| world5tm-h3s7 | h3s | S7 shape (Davide 15/11 "Completa nella 4.2"): the two-file Italy |
| world5tm-h3s7r | h3s7 | the corrected lat / lon of ALL 298 Italy clubs (S7 redraw oracle; MC 15/11): becomes the release recipe in the same merge as the redraw C, not before |

h3s7 vs h3s (cmp of every file; the rest of the world is byte-identical):
- ita/pack.json = internal/s7pack-real/ita/pack.json (files.league 102 divisions 0..4, files.league_b 144 divisions 5..13, geo)
  with the S3 shape appended to its ko_playoffs: 26 S7 entries (a_title ... dA_title, dA_reltie, dB..dI play-offs / play-outs,
  poule_scudetto) + b_po, b_pout, c_po taken from h3s = 29 entries, compile_spec 1270 B.
- ita/clubs.csv = s7pack-real's: the same 298 clubs; only `file` (162 Serie D clubs league -> league_b) and `division` (6) differ from
  h3s, plus the new lat / lon columns (the Serie D geography chain). No other column differs.
- ita/import41.csv, ita/newpool41.csv: new (the 4.1 -> 4.2 save import), from s7pack-real.
- ita/players.csv stays h3s's, NOT s7pack-real's: s7pack-real's file predates the NETO override; its only 9 differing rows are
  Juventus' (NETO's place, GRABARA's price). complist.json, cupd.json, ties.csv are identical in h3s, h3s7 and s7pack-real.
- world5tm-h3s7.txt: the ITA line = the S7 file 102 (100 clubs, 5 x 20) + a comment line for file 144 (a second line with the word
  "file" would be read by buildrel as a pack); world5tm-h3s7.NOTES.txt has the same text.

S7 turns on by data alone (gplay.gp_s7: the pack's ko_playoffs cross league structs); no environment switch, and CD_KN stays a test switch
(buildrel clears it), so the CDKN band is not in a release build.

h3s7r vs h3s7 (cmp of every file): only ita/clubs.csv differs, and only its lat / lon columns (no other column, 298 rows, none without coordinates): the 100
file-102 clubs get theirs (tools/s7pack_towns.csv), 69 of the 198 Serie D + pool clubs change (23 by more than 3 km: the old points were province centres; the new
ones are closer to Wikipedia's own map points for 20 of the 21 clubs that can be checked). Recipe: NOPATCHER=1 zsh internal/release-tools/buildrel.sh <REL> world5tm-h3s7r,
in the SAME merge as Shaved's redraw C (today's S7GEO chain reads the coordinates: data changes only with its engine).
