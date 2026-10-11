# Carriere storiche: costruire un intero mondo storico

Un **pacchetto stagione** ([README.it.md](README.it.md)) porta una stagione storica da giocare nella modalità
Stagione. Una **carriera storica** va oltre: un intero **mondo** calcistico di un'epoca (per esempio l'Europa del
1984-85) giocato come *carriera*, stagione dopo stagione, con promozioni e retrocessioni, coppe nazionali e coppe
europee, tutto fra i club di quel mondo. Compare nel selettore squadra della carriera sotto **CARR. STORICHE**.

Un mondo è un insieme di **pacchetti carriera**, uno per nazione. Ogni pacchetto carriera ha gli stessi file di un
pacchetto stagione (`pack.json`, `clubs.csv`, `players.csv`, `ties.csv`), più qualche campo in `pack.json`. Niente
di tutto questo è codice: tu prepari i dati, noi li compiliamo.

*English: [CAREERS.md](CAREERS.md).*

## In breve

1. Copia la cartella [`_template_world`](_template_world). È un piccolo mondo valido con due nazioni: `alpha` (due
   divisioni da 4 club, una coppa da 8) e `beta` (una divisione da 4, una coppa da 4).
2. Crea una cartella per ogni nazione del tuo mondo (rinomina `alpha` e `beta`, aggiungine altre) e sostituisci le
   righe con i tuoi dati. Tutto quello che riguarda `clubs.csv`, `players.csv`, `ties.csv` e le rose è uguale ai
   pacchetti stagione: vedi [README.it.md](README.it.md).
3. Compila i campi del mondo in ogni `pack.json` (sotto).
4. Facoltativo, se hai Python 3: controlla tutto il mondo in una volta, con tutte le sue cartelle sulla stessa riga:

   ```bash
   python3 tools/mkseason.py check packs/mio-mondo/alpha packs/mio-mondo/beta
   ```

   Controlla ogni nazione, poi stampa il mondo: primo anno, nazioni, dimensione di ogni coppa europea e i club che
   la giocano nella prima stagione.
5. Mandacelo: apri una issue su questo repository con la cartella compressa (oppure pubblicala nei gruppi SWOS dove
   ci trovi).

Come per i pacchetti stagione, non devi occuparti di `files` (numeri dei file e numeri globali), degli `id` delle
competizioni, di `squads` e di `dates_from`: li assegniamo noi quando il mondo entra nella build.

## Cosa cambia in pack.json

```json
{
  "format": 1,
  "id": "europa-1984-85-ita",
  "kind": "career",
  "button": "ITALIA",
  "continent": "europe",
  "world": 1,
  "europe_places": {"cc": 1, "cwc": 1, "uefa": 4},
  "first_europe": {"cc": ["juventus"], "cwc": ["roma"], "uefa": ["inter", "torino", "fiorentina", "verona"]},
  "world_cups": {"start_year": 1984},
  ...
}
```

| Campo | Significato |
|---|---|
| `kind` | `"career"` (un pacchetto stagione ha `"season"` o niente) |
| `button` | il pulsante della nazione nel mondo |
| `button_names` | facoltativo: il pulsante per lingua del gioco, es. `{"it": "INGHILTERRA", "en": "ENGLAND", "fr": "ANGLETERRE", "de": "ENGLAND"}` (predefinito `button`) |
| `world` | il numero del mondo: tutte le nazioni di un mondo hanno lo stesso numero |
| `europe_places` | posti di questa nazione in Coppa dei Campioni (`cc`), Coppa delle Coppe (`cwc`) e Coppa UEFA (`uefa`) |
| `first_europe` | facoltativo: i club che giocano ogni coppa europea nella **prima** stagione (chiavi dei club di questa nazione). Predefinito: i club in ordine di campionato, prima la divisione più alta (prima la Coppa dei Campioni, poi la Coppa delle Coppe, poi la UEFA) |
| `world_cups` | in **un solo** pacchetto del mondo (la nazione *principale*): `start_year` (la prima stagione, es. `1984` per il 1984-85), `name` (il nome del mondo nell'elenco CARR. STORICHE, anche per lingua: `{"it": "EUROPA 1984-85", "en": "EUROPE 1984-85"}`; predefinito `1984-85`) e, se serve, i turni (`rounds`) di ogni coppa, es. `{"cc": {"rounds": ["two_legs", "two_legs", "two_legs", "two_legs", "single"]}}`. Turni predefiniti: andata e ritorno, finale secca |

**Campionati con più divisioni.** Una nazione può avere più divisioni con promozioni e retrocessioni: nella
competizione del campionato, `divisions` le elenca dalla più alta (`teams`, `promoted`, `relegated`, `names`), e
`clubs.csv` ha una colonna `division` (0 = prima divisione, 1 = la successiva, …). La nazione `alpha` del modello
mostra come.

## Come funzionano le coppe europee

- Sono coppe a **eliminazione diretta** (niente gironi). Il numero di club di ogni coppa deve essere una **potenza
  di 2**: Coppa dei Campioni e Coppa delle Coppe al massimo **32**, Coppa UEFA al massimo **64**, tutte e tre
  insieme al massimo **128** (il vero formato 1984-85: 32 / 32 / 64, andata e ritorno, nessun turno di riposo).
- **Posti per nazione**: al massimo un posto in Coppa dei Campioni (la campione) e uno in Coppa delle Coppe (la
  vincitrice della coppa); i posti UEFA vanno ai club successivi della prima divisione (al massimo circa 6: il gioco
  legge le prime 9).
- **Il detentore ha un posto suo**: dimensione della coppa = posti di tutte le nazioni + 1. Esempio: 31 nazioni con
  un posto in Coppa dei Campioni + il detentore = 32 club. Nella prima stagione il posto del detentore va alla
  nazione principale (il suo `first_europe` ha un club in più per coppa).
- **Dalla seconda stagione i club si qualificano dalla stagione appena giocata**: Coppa dei Campioni = la squadra
  campione; Coppa delle Coppe = la vincitrice della coppa nazionale; Coppa UEFA = i piazzamenti successivi della
  classifica. Il detentore gioca sempre la sua coppa da detentore: se vince anche il campionato (o la coppa, o un
  posto UEFA), quel posto va al club successivo.
- I nomi sono quelli del gioco (COPPA CAMPIONI EUROPEA, …) e non hanno l'anno, perché una carriera dura molte
  stagioni.

## Cosa vede il giocatore

- L'anno parte da `start_year` (CAMP. 1984/85, poi 1985/86, …).
- VISUALIZZA MONDO mostra solo questo mondo: le sue nazioni e le sue tre coppe europee.
- L'acquisto di giocatori stranieri mostra solo i club di questo mondo.
- Nazionali (3.1, mondi con la cartella `national`): le nazionali del mondo (nel mondo Europa 1984-85: Germania Ovest
  e Est, URSS, Cecoslovacchia, Jugoslavia; nessuna nazione nata dopo il 1990). Le nazionali dei paesi del mondo
  offrono la panchina; si convocano i giocatori dei club del mondo; ciclo Mondiali/Europei di quell'epoca (1984-85:
  qualificazioni a Messico '86, poi Messico '86, le qualificazioni a Euro '88, Euro '88). Senza la cartella
  `national`: nessuna panchina di nazionale, come prima.
- Gli altri club non si scambiano mai giocatori fra loro: tengono le loro rose ogni stagione (SWOS 96/97 funziona
  così); compra e vende solo la tua squadra.

## Nazionali (cartella `national`, 3.1)

`packs/<mondo>/national` contiene le nazionali del mondo, un file squadre per ogni file nazionale del gioco (TEAM.080
Europa … TEAM.085 Oceania), **nello stesso ordine** (una squadra prende il posto di quella del 1996-97 in quella
posizione: la Germania Est in quello della Croazia, l'URSS in quello della Russia); la carriera del mondo carica
questi file al posto di quelli del gioco.

- `pack.json`: `"kind": "national"`, `world`, `files` (`{"nat80": {"file": 180, "base": 0, "as": 80}, …}`),
  `squads` (explicit) e `national`: le competizioni (sotto).
- `clubs.csv`, `players.csv`: come per le rose esplicite (16 giocatori ciascuna).
- `nations.csv`: per squadra `code` (il paese del mondo: quella nazionale offre la panchina e convoca "in casa" dal
  campionato di quel paese; vuoto = nessuna panchina in questo mondo), `nat` (codice nazionalità dei giocatori, per
  esempio 153 = GDR, nuovo nella 3.1), `home` (il campionato di un altro paese per le convocazioni in casa, per
  esempio Galles → ENG), `unused` (1 = nazione che in quell'epoca non esiste: non gioca nulla).
- `national`: `win_points`, `wc_holder`, `wc_teams` (24) / `ec_teams` (8) e `cycles` (uno ogni 4 stagioni:
  qualificazioni ai Mondiali, Mondiali, qualificazioni agli Europei, Europei): `wc_host`, `ec_host`, `wcq` / `ecq` =
  fino a 8 gironi `[posti, [squadre]]` (al massimo 6 squadre; l'ottavo al massimo 4), `wc_direct` = le qualificate
  degli altri continenti in ordine (le riserve prendono il posto di chi è già dentro). Detentore e paesi ospitanti
  escono dai gironi all'inizio della stagione. Dopo l'ultimo ciclo si ripete l'ultimo.

Le nazionali del mondo Europa 1984-85 sono costruite da un convertitore dallo stesso database dei club (i giocatori di
ogni nazionalità, prima i nazionali) e verificate con il test automatico `world8485_nat`.

## Cosa ci serve da chi contribuisce

Per ogni nazione del mondo, nella stagione di partenza:

- i club di ogni divisione, nell'ordine della classifica finale della stagione precedente (è l'ordine che si vede);
- le rose (almeno 16 giocatori per club con il ruolo, meglio se in ordine di presenze) e gli allenatori;
- il tabellone della coppa nazionale della prima stagione, con le vincitrici (`ties.csv`, come per le stagioni);
- i posti nelle tre coppe europee, e i club che le giocarono nella prima stagione.

Le abilità sono facoltative (vengono calibrate sulla forza del club); abilità reali prese da un altro database (per
esempio Championship Manager) si possono usare con il permesso dei suoi autori e citandoli.

## Limiti (oggi)

- Fino a circa 90 club per nazione (tutte le divisioni insieme) e circa 150 nazioni (file squadre 101–251).
- Coppe europee: solo eliminazione diretta, con le dimensioni dette sopra.
- Un solo nome di menu per tutti i mondi (CARR. STORICHE); arriverà un nome per ogni mondo.
- Le carriere lunghe (5 stagioni e oltre) non sono ancora state giocate: raccontaci cosa vedi.
