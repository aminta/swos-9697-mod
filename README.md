# SWOS 96/97 Mod

**[Italiano](#italiano) · [English](#english)**

## Italiano

Patch per **Sensible World of Soccer 96/97** (versione DOS su CD): ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE, GERMAN.EXE.

- **Italia a 4 divisioni:** Serie A, B, C1 e C2 (18 squadre ciascuna), con i club reali 1996-97, rose vere e allenatori. Risolto il blocco di fine stagione che affliggeva i mod del 1997.
- **Coppe sudamericane:** Copa Libertadores, Supercopa e Copa CONMEBOL nei menu, nella vista mondo e in carriera, con le qualificate prese dalle classifiche sudamericane e le regole della detentrice.
- **Coppa Intercontinentale:** a dicembre fra la vincitrice della Coppa Campioni e quella della Libertadores, aggiornata ogni stagione e salvata con la carriera.

### Installazione
1. Scarica `swos-9697-mod-patcher.html` dalla pagina [Releases](../../releases) e aprilo nel browser (funziona anche offline).
2. Trascina l'exe della tua lingua e `DATA\TEAM.020` dalla cartella del gioco, poi scarica i file modificati.
3. Copiali nella cartella del gioco (TEAM.020 in `DATA`), dopo aver fatto una copia di sicurezza. Inizia una carriera nuova.

Il patcher contiene solo differenze e controlla i file prima e dopo la modifica: serve una copia originale del gioco.

### Per sviluppatori
- Manuale tecnico: [italiano](https://aminta.github.io/swos-9697-mod/) (indirizzi di ITALIAN.EXE) · [inglese](https://aminta.github.io/swos-9697-mod/en.html) (indirizzi di ENGLISH.EXE)
- Build: metti gli exe e `DATA/TEAM.020` originali in `orig/`, poi `cd tools && python3 patch.py it|en|fr|de` (serve `nasm`). Patcher: `python3 tools/mkpatcher.py`.
- Il disassemblato di riferimento viene da [swos-port](https://github.com/zlatkok/swos-port) (`swos/swos.asm`, in `ref/`).
- Registro dettagliato di ogni sessione: [`notes/STATUS.md`](notes/STATUS.md).

## English

Patch for **Sensible World of Soccer 96/97** (DOS CD version): ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE, GERMAN.EXE.

- **Italy with 4 divisions:** Serie A, B, C1 and C2 (18 clubs each), with the real 1996-97 clubs, real squads and coaches. Fixes the end-of-season freeze that plagued the 1997 mods.
- **South American cups:** Copa Libertadores, Supercopa and Copa CONMEBOL in menus, world view and career mode, with qualifiers from the South American standings and the holder rules.
- **Intercontinental Cup:** in December between the Champions Cup winner and the Libertadores winner, updated every season and saved with the career.

### Install
1. Download `swos-9697-mod-patcher.html` from the [Releases](../../releases) page and open it in a browser (works offline too).
2. Drop your language's executable and `DATA\TEAM.020` from the game folder, then download the patched files.
3. Copy them into the game folder (TEAM.020 into `DATA`) after backing it up. Start a new career.

The patcher ships only differences and checks every file before and after patching: an original copy of the game is required.

### For developers
- Technical manual: [English](https://aminta.github.io/swos-9697-mod/en.html) (ENGLISH.EXE addresses) · [Italian](https://aminta.github.io/swos-9697-mod/) (ITALIAN.EXE addresses)
- Build: put the original executables and `DATA/TEAM.020` in `orig/`, then `cd tools && python3 patch.py it|en|fr|de` (needs `nasm`). Patcher: `python3 tools/mkpatcher.py`.
- The reference disassembly comes from [swos-port](https://github.com/zlatkok/swos-port) (`swos/swos.asm`, in `ref/`).
- Detailed log of every session: [`notes/STATUS.md`](notes/STATUS.md).

---
Mod by Davide Lorigliola, with Claude. Sensible World of Soccer © Sensible Software / Codemasters. Squad data from it.wikipedia 1996-97 club season pages.
