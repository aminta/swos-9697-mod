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
| `world` | il numero del mondo: tutte le nazioni di un mondo hanno lo stesso numero |
| `europe_places` | posti di questa nazione in Coppa dei Campioni (`cc`), Coppa delle Coppe (`cwc`) e Coppa UEFA (`uefa`) |
| `first_europe` | facoltativo: i club che giocano ogni coppa europea nella **prima** stagione (chiavi dei club di questa nazione). Predefinito: i club in ordine di campionato, prima la divisione più alta (prima la Coppa dei Campioni, poi la Coppa delle Coppe, poi la UEFA) |
| `world_cups` | in **un solo** pacchetto del mondo (la nazione *principale*): `start_year` (la prima stagione, es. `1984` per il 1984-85) e, se serve, i turni (`rounds`) di ogni coppa, es. `{"cc": {"rounds": ["two_legs", "two_legs", "two_legs", "two_legs", "single"]}}`. Turni predefiniti: andata e ritorno, finale secca |

**Campionati con più divisioni.** Una nazione può avere più divisioni con promozioni e retrocessioni: nella
competizione del campionato, `divisions` le elenca dalla più alta (`teams`, `promoted`, `relegated`, `names`), e
`clubs.csv` ha una colonna `division` (0 = prima divisione, 1 = la successiva, …). La nazione `alpha` del modello
mostra come.

## Come funzionano le coppe europee

- Sono coppe a **eliminazione diretta** (niente gironi). Il numero di club di ogni coppa deve essere una **potenza
  di 2**: Coppa dei Campioni al massimo **16**, Coppa delle Coppe e Coppa UEFA al massimo **32**, tutte e tre
  insieme al massimo **80**.
- **Il detentore ha un posto suo**: dimensione della coppa = posti di tutte le nazioni + 1. Esempio: 15 nazioni con
  un posto in Coppa dei Campioni + il detentore = 16 club. Nella prima stagione il posto del detentore va alla
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
- Nessuna offerta di panchina delle nazionali (le nazionali del gioco sono quelle del 1996-97).
- Gli altri club non si scambiano mai giocatori fra loro: tengono le loro rose ogni stagione (SWOS 96/97 funziona
  così); compra e vende solo la tua squadra.

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
