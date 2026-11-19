# Il calendario della carriera (contratto del calendario C)

*Versione inglese: [calendar.md](calendar.md).*

Questa pagina descrive come la mod ragiona sulle settimane di una stagione di carriera. Copre il modello, il suo unico punto di accesso, quale pezzo possiede quali settimane e le regole che il test automatico (harness) controlla su ogni menu della carriera. Progetto: MC, 13/11 (`internal/handoff/c-calendar-contract.md`).

## Il modello

- **Settimana di carriera**: il byte della settimana nel calendario, 8 settimane al mese, contate da gennaio del primo anno della stagione. Un anno è 96 settimane. `split.week_of` converte una data in una settimana.
- **Giorno di carriera**: una voce del calendario del gioco (obj2). Ogni voce ha il suo slot (0 = il campionato, 1..4 = le altre competizioni), la settimana, il turno e i segni di partita giocata.
- **Unità di campionato**: la settimana di una giornata di campionato di una divisione, turni di riposo compresi. Vengono dal pack e dalle strutture dei campionati dell'exe originale (i byte 3 e 4 dell'intestazione danno la prima e l'ultima settimana).
- **Finestra**: (tipo, B, E, fonte). B è la prima settimana in cui la finestra è aperta, E l'ultima (compresa). La fonte è `data` (dal pack) o `default`.

## Un solo punto di accesso: `tools/cal.py`

Ogni pezzo che ha bisogno delle settimane di carriera le legge da `cal.py`, mai da una propria copia dei calcoli. I calcoli stanno in `fport.py` (il fixture port, P3 di Motore) e non sono duplicati.

| Funzione | Restituisce |
|---|---|
| `season_start(pk)` | S, la prima settimana di carriera della stagione (la prima unità di campionato di qualunque divisione) |
| `league_units(pk)` | le unità di campionato per divisione |
| `reserved(pk)` | le finestre riservate dello slot 4 (= `fport.windows`, JSON identico sui 91 paesi) |
| `transfer_windows(pk)` | le finestre estiva e invernale del paese |
| `season_end(pk)` | (E, fonte): la settimana alla cui fine la stagione del paese è finita |
| `window_at(wins, week)` | (tipo, w) con w = week - B, oppure None |
| `country(pk)`, `world(src)` | tutto quanto sopra per un paese / un mondo di carriera |

## Chi possiede quali settimane

| Settimane | Proprietario | Note |
|---|---|---|
| Giornate di campionato (slot 0) | il gioco + i costruttori di stagioni / mondi (`mkseason.py`, `careerworld.py`) | i veri turni infrasettimanali condividono la settimana di carriera del fine settimana, a 8 settimane al mese (MLS, Honduras, Perù, Colombia) |
| Finestre riservate dello slot 4 | il fixture port (`fport.py`, `fpad.c`) | play-off di fine stagione (dplay, gplay ko_playoffs), titoli di fase, supercoppe, Coppa Italia Serie D. Un sovrainsieme statico: B non è mai più tardi dell'avanzamento reale |
| Finestre di mercato | `cal.py`, lette dal mercato della CPU (4.3) | per paese. Le date reali FIFA TMS da `transfer_windows` di pack.json, altrimenti il default: estate da S per 8 settimane, inverno da S + 40 per 4 settimane (la W di Davide, ancora aperta) |
| Fine stagione | `cal.py season_end` | `native` (una fase si gioca alla fine stagione della carriera), altrimenti la più tarda tra l'ultima unità di campionato e l'ultima E riservata (`league` / `reserved`). Mondo 2026-27: 57 league, 27 native, 7 reserved |
| Finestre FIFA | nessuna per ora (4.5) | il tipo esiste perché la struttura della tabella non cambi |

La tabella delle finestre usata a runtime (C2, CALW in obj4, 8 B per finestra) viene collegata solo quando qualcuno la usa. Il primo sarà il mercato della CPU nella 4.3.

## Le regole (C1-C4)

Le stesse quattro regole sono controllate in due posti:

- **Sul Mac (host)**: `tools/hosttest/tests/test_calendar_lib.py` (Panchina). I suoi riferimenti sono rossi sui bug della 4.0.5 ripristinati (Grand Final NZ, Libertadores q2, FINISCI STAGIONE in Serie D, supercoppa anticipata) e verdi sulle correzioni.
- **Dal vivo, in ogni scenario dei mondi**: `swostest.py cal_check`, su ogni schermata del menu della carriera di `advance()`. Legge il calendario del gioco dalla memoria, senza codice nell'exe e senza interruttori di test. Una violazione fa fallire lo scenario; la riga del risultato mostra `[cal: N checks (M C4 at the menu), 0 violations]`. `SWOSTEST_CALCHECK=0` lo spegne, solo per una prova di debug.

| Regola | Cosa deve valere |
|---|---|
| C1 | il calendario è ben formato: `count` voci di almeno 8 byte, settimane mai decrescenti |
| C2 | il campionato ha al massimo due giorni di carriera in una settimana (un terzo è un turno duplicato). Le altre competizioni possono giocarsi in blocco (una final four, le fasi finali della nazionale): registrato, mai un FAIL |
| C3 | nessun giorno di carriera resta davanti al cursore in una settimana già raggiunta |
| C4 | FINISCI STAGIONE (careerFinished) è attivo esattamente quando non resta nessun giorno di carriera davanti, sulle schermate che mostrano il pulsante e fuori dal cambio di stagione |

C4 è anche il **contratto del menu**: il menu della carriera offre FINISCI STAGIONE esattamente quando non resta niente da giocare.

## Punti aperti

- La W di Davide: le lunghezze di default delle finestre estiva e invernale (8 / 4 settimane).
- Dati per la 4.3 (regola dell'esattezza): le vere finestre di mercato dei 91 paesi nei loro pack.
- C2 CALW: progettata (per mondo x paese, voci `end` per la fine stagione di ogni paese), da collegare con gli agganci del mercato.
