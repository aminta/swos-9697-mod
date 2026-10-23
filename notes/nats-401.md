# Own nationalities for the World 2026-27 nations (4.0.1, session '4.0') — table for the regia's review

Estimate: 8 h in all; about 5 h spent (audit, table, converter diff, engine, 3 harness scenarios).

## Facts checked
- **152 'CUS' is not Cuba.** It is the custom teams' nationality.
  - `ref/docs/SWOS/teams.txt` lists 152 - CUS beside "team.072 customs".
  - The originals use it only in TEAM.CUS (766 players) and TEAM.072 (566).
  - So Cuba gets its own code (CUB), and so does the Dominican Republic (DOM).
- **The game has no long names for nationalities.** A player's nationality appears only as the 3-letter code
  (shortCountryNames: squad screen, foreign market, the career's coach nationality field).
  - The long-name lists in the exes (ALBANIA / ALBANIAN ...) belong to the team-file countries, not to the
    nationality byte.
  - So the review covers only the codes.
- **The 153 original codes are the same in all four exes** (ESP, SUI, HOL ... in the German exe too).
  - Proposal: the new codes are the same in all four languages as well.
  - 3.1's GDR / URS / FRG differ per language (RDT / RDA / DDR) because those historic states have established
    local acronyms. None of the 58 nations below has one.

## Engine audit (no fixed-length table to extend by hand)
- shortCountryNames has 3 references (squad display, foreign market, career nationality field). 3.1 already
  retargets them to NATSHORT in the cave; the table just gets longer. The 4th reference
  (`shortCountryNames+1CBh`, an empty string) stays where it is.
- No other table is indexed by the nationality byte. The national teams are searched by equality:
  - GetNationalTeamNumber returns -1 when no team has the code (as for the 1996-97 codes without a national team);
  - nationalTeams' records carry a code, they are not indexed by it.
- Byte range: codes 156..213. 255 is the OTHER sentinel of the coach list only. mkseason accepts 0..255.
- MENU_NATS (the coach's nationalities) stays unchanged.
- Side effect (wanted): with World 2026-27 on the game's national teams, a Montenegrin is no longer called up by
  Yugoslavia, nor an Andorran by Spain. These nations have no national team in the game, so their players are not
  called up at all.

## Proposed codes (numbers 156.. in this order; FIFA codes unless they clash with an existing game code)
| # | Code | Nation | today |
|---|---|---|---|
| 156 | MNE | Montenegro | YUG |
| 157 | KOS | Kosovo | ALB |
| 158 | AND | Andorra | ESP |
| 159 | GIB | Gibraltar | ENG |
| 160 | KAZ | Kazakhstan | RUS |
| 161 | KGZ | Kyrgyzstan | UZB |
| 162 | BLZ | Belize | HON |
| 163 | HAI | Haiti | JAM |
| 164 | CUW | Curacao | HOL |
| 165 | ARU | Aruba | HOL |
| 166 | DOM | Dominican Republic | JAM (via CUB) |
| 167 | CUB | Cuba | JAM |
| 168 | PUR | Puerto Rico | USA |
| 169 | GRN | Grenada | TRI |
| 170 | GLP | Guadeloupe | FRA |
| 171 | MTQ | Martinique | FRA |
| 172 | GUF | French Guiana | FRA |
| 173 | ATG | Antigua and Barbuda | BAR |
| 174 | SKN | St. Kitts & Nevis | BAR |
| 175 | LCA | St. Lucia | BAR |
| 176 | MSR | Montserrat | BAR |
| 177 | CAY | Cayman Islands | JAM |
| 178 | CPV | Cape Verde | SEN |
| 179 | GNB | Guinea-Bissau | GUI |
| 180 | EQG | Equatorial Guinea | GAB |
| 181 | MTN | Mauritania | SEN |
| 182 | NER | Niger (NIG is Nigeria) | MLI |
| 183 | RWA | Rwanda | BUR |
| 184 | COM | Comoros | MDG |
| 185 | CTA | Central African Republic | CHD |
| 186 | SSD | South Sudan | SUD |
| 187 | ERI | Eritrea | ETH |
| 188 | SOM | Somalia | KEN |
| 189 | NAM | Namibia | SAF |
| 190 | LBY | Libya | TUN |
| 191 | DJI | Djibouti | ETH |
| 192 | STP | Sao Tome and Principe | GAB |
| 193 | REU | Reunion | FRA |
| 194 | MYT | Mayotte | FRA |
| 195 | LBN | Lebanon (LIB is Liberia) | SYR |
| 196 | PLE | Palestine | JOR |
| 197 | BHR | Bahrain | QAT |
| 198 | HKG | Hong Kong (TM: 'Hongkong' and 'Hong Kong') | CHN |
| 199 | THA | Thailand | VIE |
| 200 | IDN | Indonesia | MLY |
| 201 | CAM | Cambodia | LAO |
| 202 | AFG | Afghanistan | PAK |
| 203 | NEP | Nepal | IND |
| 204 | MAO | Macao (MAC is Macedonia) | CHN |
| 205 | MGL | Mongolia | CHN |
| 206 | MDV | Maldives | SRI |
| 207 | TLS | Timor-Leste | MLY |
| 208 | GUM | Guam | PHI |
| 209 | NCL | New Caledonia | FIJ |
| 210 | TAH | Tahiti | FIJ |
| 211 | VAN | Vanuatu | SOL |
| 212 | SAM | Samoa | FIJ |
| 213 | TGA | Tonga | FIJ |

## Doubts for the regia
- **D1 Macao / 141 'MAU' (settled).** 141 MAU sits in the original's Asian block, but the game's own data use it for
  Mauritius: the MAURITIUS national teams in TEAM.068 and TEAM.084 (16 players each) and the 1984-85 Mauritius.
  So 141 stays Mauritius (as tmmaps reads it), and Macao gets a new MAO (FIFA's MAC is 47 Macedonia).
- **D2 one code set for all four languages** (as the original 153). The alternative is per-language codes as in 3.1;
  I see no established local acronym for any of these nations.

## Converter (internal, applied after the merge: data after engine)
- `internal/world2526/tmmaps_401nats.py` = tmmaps.py with the 58 '~' entries -> their own codes and
  `GAME[code] = 156..213`. It replaces tmmaps.py once 4.0.1-nats is merged.
- Re-run of mkworld_tm (private), baseline vs new:
  - players.csv: only the nat column, 1568 players, all to 156..213;
  - eng/POOL.DAT: 20 nat bytes;
  - conti guests: nat, plus the 12 generated guest clubs of DJI / GNB / NAM / SOM / SSD / LBN / DOM, which now take
    their own nation's names and coaches (before: the 'Nigeria' fallback). The regia's ok, 2026-10-23.
- Test data: `internal/world2526/world5tm-401nats` = world5tm-rel40-winnames-1031 + the regenerated files.

## Tests (release recipe c/REL401nats, buildrel.sh NOPATCHER=1, data world5tm-401nats)
- `world_nats` (new), PASS in all 4 exes (SWOSTEST_UI it/en/fr/de, the language's exe run as ITALIAN.EXE):
  - CORDOBA career: IKER ALVAREZ's nationality byte in the game's memory = AND 158;
  - squad screen: the last row's byte poked to 156 / 158 / 213 shows (MNE) / (AND) / (TGA);
  - foreign market (TRASFERIMENTI > ACQUISTA GIOCATORE > VISUAL. MERCATO STRANIERO > ELENCA): a listed player's byte
    poked the same way shows (MNE) / (AND) / (TGA).
  - (Rule 15: forced by pokes. The squad rows are drawn through one template entry, so only the last row's text
    can be read back; screenshots in the run dirs show the real (AND) on IKER ALVAREZ's row.)
- 1996-97 / 1984-85 national teams unchanged:
  - DATA differs from c/REL40hf only in the world-5 files (TMW5 / XTW5 / RS5 / POOL05 / WORLD05);
  - the game's nationalTeams (142 x 6 B) is byte-identical in all 4 exes;
  - `world8485_nat` PASS: coach list ... YUG RFT URS RDT unchanged, call-ups, Euro 88.
- Old save: `world_nats_oldsave` (new): a 4.0 (REL40hf) save at season 2's start, loaded on 4.0.1 and played
  to the season end: PASS (season 1 on 4.0: 145 steps, checkw1 ok; season 2 on 4.0.1 from that save: 147 steps,
  checkw1 ok). Not verified: whether a European career's season actually plays the CAF / AFC / CONCACAF guests'
  ties (a career in those confederations would show it).

## Release notes (draft)
EN — Players from 58 nations that the original game did not have now show their own nationality instead of the
nearest one: Montenegro (MNE), Kosovo (KOS), Andorra (AND), Gibraltar (GIB), Kazakhstan (KAZ), Cape Verde (CPV),
Curacao (CUW), Haiti (HAI), Cuba (CUB), the Dominican Republic (DOM), Lebanon (LBN), Palestine (PLE), Hong Kong (HKG),
Thailand (THA), Indonesia (IDN), Tahiti (TAH) and more. They appear in the squad and transfer screens of every
language with the FIFA code. Rule: these nations have no national team in the game, so their players are not called
up (before, a Montenegrin could be called up by Yugoslavia).

IT — I giocatori di 58 nazioni che il gioco originale non aveva ora mostrano la propria nazionalità invece di quella
più vicina: Montenegro (MNE), Kosovo (KOS), Andorra (AND), Gibilterra (GIB), Kazakistan (KAZ), Capo Verde (CPV),
Curaçao (CUW), Haiti (HAI), Cuba (CUB), Repubblica Dominicana (DOM), Libano (LBN), Palestina (PLE), Hong Kong (HKG),
Thailandia (THA), Indonesia (IDN), Tahiti (TAH) e altre. Compaiono nelle schermate della rosa e dei trasferimenti in
ogni lingua con la sigla FIFA. Regola: queste nazioni non hanno una nazionale nel gioco, quindi i loro giocatori non
vengono convocati (prima un montenegrino poteva essere convocato dalla Jugoslavia).
