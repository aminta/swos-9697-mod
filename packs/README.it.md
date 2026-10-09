# Pacchetti stagione

Un **pacchetto stagione** (season pack) è una cartella di soli dati, senza codice, che descrive una stagione storica:
club, rose, campionato e coppe. `tools/mkseason.py` li compila dentro la mod (file squadre + tabelle dell'exe). Il
compilatore è **deterministico**: lo stesso pacchetto dà sempre gli stessi byte. Il primo pacchetto è `ddr-1988-89`
(la DDR 1988-89 della 2.6, menu STAG. STORICHE).

Controllare un pacchetto (verifica e riepilogo, non scrive nulla):

```bash
python3 tools/mkseason.py check packs/ddr-1988-89
```

I pacchetti che entrano nella build sono elencati in `mkseason.ENABLED`.

*English: [README.md](README.md).*

## Costruisci la tua stagione

Chiunque può preparare una stagione e mandarcela: noi la controlliamo, completiamo la parte tecnica e la inseriamo in
una release.

1. Copia la cartella [`_template`](_template) e rinominala (per esempio `italia-1984-85`). È un piccolo esempio
   valido (campionato a 4 squadre, coppa a 8): sostituisci le sue righe con i tuoi dati.
2. Compila `clubs.csv`, `players.csv` e `ties.csv` (con Excel o un altro foglio di calcolo: salva come "CSV UTF-8"),
   poi in `pack.json` il testo del pulsante, le competizioni (nomi, regole, turni) e le fonti.
3. Facoltativo, se hai Python 3: `python3 tools/mkseason.py check packs/<tua cartella>` ti dice cosa non va.
4. Mandacela: apri una issue su questo repository con la cartella compressa (oppure pubblicala nei gruppi SWOS dove
   ci trovi).

Non devi preoccuparti di `files` (numeri dei file e numeri globali), degli `id` delle competizioni, di `squads` e di
`dates_from`: li assegniamo noi quando il pacchetto entra nella build. Va bene anche un foglio di calcolo con le
stesse colonne, o l'esportazione di un database (per esempio di Championship Manager): dicci da dove viene.

## I file

| File | Contenuto |
|---|---|
| `pack.json` | testo del pulsante, file squadre, costruzione delle rose, competizioni e regole, chi gioca quale coppa europea |
| `clubs.csv` | una riga per club |
| `players.csv` | una riga per giocatore, in ordine di rosa |
| `ties.csv` | una riga per ogni accoppiamento di ogni coppa (il tabellone) |
| `raw/` | facoltativa: i dati delle fonti così come scaricati (solo documentazione, il compilatore non li legge) |

I CSV sono in UTF-8, separati da virgole, con una riga di intestazione (in Excel: "CSV UTF-8").

### clubs.csv

| Colonna | Significato |
|---|---|
| `key` | identificativo breve e unico usato dagli altri file (per esempio `dresden`) |
| `name` | nome del club come appare nel gioco: maiuscolo, al massimo 16 caratteri |
| `coach` | nome dell'allenatore (vuoto = nessuno) |
| `country` | codice della nazione (`GDR`, `FRG`, `ITA`, `ESP`…: vedi `mkseason.COUNTRY`) |
| `file` | il file squadre in cui va il club: una chiave di `files` in `pack.json` |
| `template`, `target`, `kit` | costruzione della rosa, vedi sotto |
| `source` | il nome del club nella fonte (documentazione) |

L'ordine dei club in ogni file conta: per il file del campionato è l'ordine mostrato nel gioco (per esempio la
classifica finale della stagione).

### players.csv

`club` (una chiave di club), `name`, `role` (`G` portiere, `D` difensore, `M` centrocampista, `A` attaccante). Elenca
i giocatori in ordine di importanza (per esempio minuti giocati), con 2 portieri. Ogni club ha 16 giocatori: il
compilatore riempie ciascuno dei 16 posti della rosa con il prossimo giocatore del ruolo di quel posto (o di un ruolo
vicino quando quello è finito). `?` come nome = giocatore sconosciuto: ne viene inventato uno.

### ties.csv

`competition` (la chiave di una coppa di `pack.json`), `round` (1, 2, …), `home`, `away`, `winner` (chiavi di club).

- Turno 1: tutti gli accoppiamenti in ordine di tabellone; un club **esentato** (entra direttamente al turno 2, come
  il detentore di una coppa) è una riga con `away` vuoto e se stesso come `winner`, dopo le altre righe del turno 1.
- Turni successivi: gli accoppiamenti reali, prima la squadra di casa. Ogni club deve aver vinto il turno precedente.
- La finale non ha vincitore (si gioca nel gioco).

Il compilatore ne ricava il sorteggio fisso di ogni turno: se vincono le stesse squadre della realtà, il gioco
ripropone il tabellone vero.

### pack.json

```json
{
  "format": 1,
  "id": "ddr-1988-89",
  "button": "DDR 1988-89",
  "continent": "europe",
  "sources": ["..."],
  "files": {"league": {"file": 92, "base": 1786}, "cuponly": {"file": 93, "base": 1800}, "cc": {"file": 94, "base": 1850}},
  "shared_base_files": ["cc"],
  "squads": [ ... ],
  "competitions": [ ... ],
  "season": {"league": "oberliga", "cup": "pokal", "europe": {"bfc": "cc"}, "europe_placeholder": "cc"}
}
```

- `button`: il testo del pulsante della nazione in STAG. STORICHE (uguale in tutte le lingue).
- `files`: i file squadre del pacchetto (`file` = numero del file, TEAM.0nn) e il primo **numero globale** di
  ciascuno (l'identificativo di un club nel gioco, 0–1999: base + posizione nel file). Il campionato deve stare da
  solo nel suo file (il gioco conta i club di una nazione da queste basi), quindi i club che giocano solo la coppa
  hanno un file a parte. `shared_base_files`: file che possono riusare gli stessi numeri (in una stagione ne gira
  uno solo, per esempio le squadre straniere di ogni coppa europea).
- `squads`: come si costruiscono i record, una voce per gruppo di file:
  - `calibrate`: ogni club sul record `template` (posizione) di un file squadre `source` (ruoli, maglia, abilità);
    `kit` = un altro record di quel file per i colori; abilità spostate verso `target` (valore medio dei giocatori);
    i giocatori trovati per nome nella fonte tengono le sue abilità (per i file in `reuse_ratings`).
  - `game`: ogni club sul proprio record del gioco 1996-97 quando c'è, altrimenti su un club della sua nazione; i
    giocatori già presenti nel gioco tengono le loro abilità.
  - `seed`: il seme casuale dei giocatori inventati (fa parte del determinismo).
- `competitions`: in ordine.
  - campionato: `id` (identificativo della competizione, esadecimale), `clubs` (la chiave del suo file),
    `dates_from` (nazione di cui copia il calendario), `games` (2 = andata e ritorno), `win_points`, `relegated`,
    `classic_tourney` (anche in TORNEI STORICI), `names`.
  - coppa: `id`, `layout` (struttura `national` o `european`), `dates_from` (per `national`), `rounds` (uno per
    turno: `two_legs` andata e ritorno, `single` partita secca, `single_et` partita secca con supplementari e
    rigori), `names`.
  - `names`: per lingua (`it`, `en`, `fr`, `de`, oppure `*` per tutte): `[nome lungo, nome corto]`, in maiuscolo,
    nome corto al massimo 16 caratteri.
- `season`: cosa gioca un club in modalità Stagione: il campionato (`league`), la coppa nazionale (`cup`) e in
  `europe` quale club del campionato gioca quale coppa europea (`europe_placeholder`: una qualsiasi di quelle coppe,
  sostituita durante il gioco).

## Cosa ci serve da chi contribuisce

Il minimo per una nuova stagione: la classifica del campionato (club in ordine finale), le rose (almeno 16 giocatori
per club con il ruolo, meglio se in ordine di presenze), gli allenatori e i tabelloni delle coppe con le vincitrici.
Le abilità sono facoltative (vengono calibrate sulla forza del club); abilità reali prese da un altro database si
possono usare con il permesso del suo autore e citandolo.

## Limiti (fase A)

- Un pacchetto alla volta nella build (l'aggancio della modalità Stagione gestisce un solo campionato).
- Un solo campionato nazionale per pacchetto, a una divisione.
- I file squadre liberi (92–99) e i numeri globali liberi sono pochi: ogni pacchetto deve starci.
