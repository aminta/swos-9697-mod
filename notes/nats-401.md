# Own nationalities for the World 2026-27 nations (4.0.1, session '4.0') — table for the regia's review

Estimate: 8 h in all (about 1.5 h spent: audit + this table).

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
| 204 | see D1 | Macao | CHN |
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
- **D1 Macao / 141 'MAU'.**
  - tmmaps reads 141 MAU as Mauritius. But in the original table it sits in the Asian block (… CHI SGP **MAU**
    MYA PAP …); the African block ends at 117 MLW. So 141 is most likely Macau: FIFA's MAC is taken by 47
    Macedonia, so the game wrote MAU.
  - Proposal: treat 141 MAU as Macao (no new code), and give Mauritius a new code, MRI (FIFA), as 204.
  - The alternative: keep MAU = Mauritius and give Macao MAO.
  - The count stays at 58 either way.
- **D2 one code set for all four languages** (as the original 153). The alternative is per-language codes as in 3.1;
  I see no established local acronym for any of these nations.

## Tests (release recipe, 1 DOSBox slot, not Sat 08-13)
- A Montenegrin and an Andorran player show MNE / AND on the squad screen and in the foreign market, in all 4 exes.
- The 1996-97 and 1984-85 national teams are unchanged (byte compare of nationalTeams + the 1984-85 call-up
  scenario).
- An old save (4.0 release build) loads and plays on.
- The coach nationality list is unchanged (world8485_nat_menu).
