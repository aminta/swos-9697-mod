# Tornei storici: aggiungere un torneo storico alle COMPETIZIONI PREDEFINITE

*English: [TOURNEYS.md](TOURNEYS.md).*

Un **pacchetto torneo** (3.2) è una cartella di soli dati che aggiunge un torneo storico in **COMP. PREDEFINITA >
TORNEI STORICI**, accanto al Mondiale 1982, alla Coppa Mitropa 1934 e alla FA Cup 1871-72. Niente codice: la formula
(gironi, turni a eliminazione, finale per il 3° posto, ripetizioni) si descrive in `pack.json`. Il primo è
[`world-cup-1934`](world-cup-1934): il Mondiale 1934 con il suo tabellone reale.

Un campionato giocato come torneo (girone all'italiana) non ha bisogno di un pacchetto torneo: un pacchetto stagione
con `"classic_tourney": true` sul campionato compare anche lì ([README.it.md](README.it.md)).

## In breve

1. Copia [`_template_tourney`](_template_tourney) e rinominala (es. `world-cup-1938`).
2. `clubs.csv`: una riga per squadra, nell'ordine del sorteggio (gironi: prima le squadre del girone A, poi B ...;
   se si parte a eliminazione: come il primo turno di `ties.csv`).
3. Rose: `players.csv` (nomi e ruoli, oppure tutte le abilità: gli stessi formati del pacchetto stagione, vedi
   [README.it.md](README.it.md)), oppure squadre intere prese da un file di squadre di SWOS (`records`, sotto).
4. `pack.json`: i nomi nelle quattro lingue, le fasi, `win_points`.
5. Partenza a eliminazione con il tabellone reale: `ties.csv` con tutte le sfide e chi passa (come per le coppe del
   pacchetto stagione).
6. `python3 tools/mkseason.py check packs/<tua cartella>`, poi mandacelo (una issue con la cartella zippata, o nei
   gruppi di SWOS). Noi gli diamo un numero di file squadre e un id di competizione e lo mettiamo nella build.

## pack.json

Un esempio completo è [`world-cup-1934/pack.json`](world-cup-1934/pack.json).

- `files`: un file squadre, `base` sempre 1786 (tutti i tornei storici condividono 32 numeri globali: al massimo 32
  squadre).
- `stages` (da 2 a 6, in ordine; l'ultima è la finale, eliminazione a 2):
  - `{"type": "groups", "teams": 24, "groups": 6}`: gironi da `teams / groups`, tutti contro tutti una volta. Vanno
    anche i gironi dispari (1982: gironi da 3). La fase dopo prende le migliori di ogni girone; se le sue squadre non
    sono un multiplo dei gironi, il gioco aggiunge le migliori dei piazzamenti successivi (come le terze del 1986).
  - `{"type": "knockout", "teams": 8, "matches": "..."}`: 2, 4, 8, 16 o 32 squadre, passa la metà.
  - `{"type": "third_place", "matches": "..."}`: le perdenti delle semifinali, subito prima della finale.
  - `"from": ["1A", "2B", "1C", "2D", ...]` sulla fase dopo un girone: dove va ogni qualificata (1A = prima del girone
    A); sfida 1 = le prime due, sfida 2 le due dopo... (per i gironi: girone A = le prime). Senza, sorteggia il gioco.
- `matches`:

  | valore | partita | pareggio |
  |---|---|---|
  | `single` | gara secca | come le coppe del gioco |
  | `single_et` | gara secca | supplementari, rigori |
  | `two_legs` | andata e ritorno | gol in trasferta, supplementari, rigori |
  | `single_replay` | gara secca | si ripete; una ripetizione pari si decide col sorteggio |
  | `two_legs_replay` | andata e ritorno | spareggio; uno spareggio pari si decide col sorteggio |

  Il gioco non sa giocare i supplementari prima di una ripetizione. Un torneo usa o le ripetizioni (`*_replay`) o i
  rigori, non tutti e due.
- `draw`: `fixed` (predefinito): l'eliminazione segue il tabellone, la sfida k di un turno = le vincenti delle sfide
  2k-1 e 2k del turno prima (con `ties.csv` il tabellone reale); `random`: il gioco sorteggia ogni turno.
- `win_points`: punti per vittoria nei gironi (2 prima del 1994, 3 dopo).
- `id`: l'id di competizione, lo assegniamo noi (esadecimale; ED per il 1934).

## Rose

- `explicit`, `calibrate`, `game`: come nel pacchetto stagione ([README.it.md](README.it.md)).
- `records`: squadre intere (giocatori, abilità, maglie, modulo, allenatore) da un file di squadre di SWOS: un
  `TEAM.xxx` o un `CUSTOMS.EDT` di SWOS 2020. Colonna `record` di `clubs.csv` = il nome della squadra in quel file;
  `name`, e `coach` se non è vuoto, sostituiscono i suoi; `kit1` / `kit2` facoltativi. I file di altri autori si
  usano solo con il loro permesso e citandoli, e restano fuori dal repository (`orig/swos2020/`).

## Cosa vede il giocatore

COMP. PREDEFINITA > TORNEI STORICI > il nome del torneo: la scelta delle squadre (tutte al computer, o alcune ai
giocatori), poi i turni come nelle coppe del gioco. Le ripetizioni hanno "REPLAY" nel titolo del turno; un sorteggio
compare come "... VINCE AL SORTEGGIO" nei risultati.

## Limiti (oggi)

- Niente esenzioni (ogni turno a eliminazione dimezza le squadre); al massimo 32 squadre, 6 fasi, gironi da 24.
- Due fasi con lo stesso numero di squadre non possono avere entrambe l'ordine fisso (usa `draw: random`).
- Solo in COMP. PREDEFINITA (non in Stagione né in Carriera).
