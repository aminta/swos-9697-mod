## English

**SWOS 96/97 Mod 3.0: Classic careers — Europe 1984-85**

*Take a club of 1984-85 Europe, from Juventus and Liverpool down to the Icelandic league, and play a whole career through the
leagues, national cups and European cups of the time.*

### Europe 1984-85 (CLASSIC CAREERS)

- A new **CLASSIC CAREERS** button in Career mode (IT `CARR. STORICHE`, FR `CARR. D'ANTAN`, DE `KLASS. KARRIERE`) holds a whole
  world: **32 European countries, 949 clubs**, starting from the 1984-85 season. A career in this world sees only these clubs and
  countries; normal careers are unchanged.
- **Squads:** the real 1984-85 players, from the database by **DaniSwos** (CM01/02 Retro Update Team), converted to SWOS ratings.
- **Leagues:** every country with its top division (two or more divisions where the data has them: England 4, Scotland 3, West
  Germany, Italy, Spain, the Netherlands, Belgium, Austria, Switzerland, Denmark, Hungary and the USSR 2), clubs in the 1983-84 final order, promotion and relegation. Wales has no league: Wrexham plays
  in England, as in reality.
- **National cups:** the real 1984-85 brackets for 15 countries in the first season (FA Cup third round with non-league clubs such
  as Dagenham and Telford, DFB-Pokal, Coppa Italia, Copa del Rey, KNVB beker, Scottish Cup...), with the cup-only clubs that took
  part. In the other countries the first season's cup is generated from the league clubs. From the second season on, all cups
  are run by the game.
- **European cups as in 1984-85:** Champions' Cup 32 clubs, Cup Winners' Cup 32, UEFA Cup 64, all knockout; the first season has
  the real first-round ties. The holders play in addition to their country's places.
- **Coaches:** the real coaches of 222 clubs (complete for Italy and the Netherlands, almost complete for Spain and West
  Germany). The others are missing: **anyone who finds them is welcome to add them** (column `coach` of `clubs.csv` in
  `packs/europe-1984-85/<country>`, see `packs/CAREERS.md`) and send them to us.
- Short club names in SWOS style (MALAGA, MAGDEBURG, WISMUT AUE...). Club names that the original game already had keep the
  game's name.

### European cups in every career

- **No same-country ties in rounds 1 and 2** of the knockout European cups, as in the UEFA rule of the time: Cup Winners' Cup and
  UEFA Cup in normal careers, all three cups in classic careers. Thanks to **DaniSwos** for the report.
- Normal careers: from the second season on, the first round of the Cup Winners' Cup and of the UEFA Cup is **drawn**. Before, the
  clubs met in list order, country by country (up to 8 same-country ties out of 16).
- **Champions' Cup holder:** when the holder has not qualified through its league, it now takes the place of a club of **another
  country**. Before, it could push out its own national champion.
- **Bug fix (2.5 to 2.7.0):** a Champions' Cup winner that then played the Intercontinental Cup started the next season in the
  wrong European cup (Cup Winners' Cup), with mixed-up ties and a freeze at the season end. Fixed for new seasons. A career already
  saved in that broken state stays broken: continue from a save made before that season end.

### Kits

- **Smarter automatic kit choice:** black no longer clashes with blue or green, blue no longer with light blue, same-coloured
  shorts count less, and a game bug that turned a striped kit into a single colour is fixed.
- A new **KITS** button in the pre-match screen opens the **SELECT KITS** editor (like SWOS 2020's): first or second kit, shirt
  type and colours, shorts and socks, for that match only. Thanks to **DaniSwos** for the analysis.

### Patcher

- New files: `DATA/TEAM.101` to `DATA/TEAM.144` and `DATA/WORLD04.TMD` (the 1984-85 world), created together with `TEAM.020`.
- As before, it upgrades any earlier version of the mod (1.0 to 2.7.0, CD and GOG) and keeps your saves. The
  `ENGLISH.EXE + SWOS++` row is still there.
- Tested with an automated DOSBox-X harness: a full Italian season, save/load round trip, the European draws of a 1998-99
  career, and two seasons of the 1984-85 world with save and reload.

## Italiano

**SWOS 96/97 Mod 3.0: Carriere storiche — Europa 1984-85**

*Prendi un club dell'Europa 1984-85, dalla Juventus e dal Liverpool fino al campionato islandese, e gioca un'intera carriera tra
campionati, coppe nazionali e coppe europee dell'epoca.*

### Europa 1984-85 (CARRIERE STORICHE)

- Un nuovo pulsante **CARR. STORICHE** in modalità Carriera (EN `CLASSIC CAREERS`, FR `CARR. D'ANTAN`, DE `KLASS. KARRIERE`)
  contiene un mondo intero: **32 paesi europei, 949 club**, a partire dalla stagione 1984-85. Una carriera in questo mondo vede
  solo questi club e paesi; le carriere normali non cambiano.
- **Rose:** i giocatori reali del 1984-85, dal database di **DaniSwos** (CM01/02 Retro Update Team), convertiti nei valori di SWOS.
- **Campionati:** ogni paese con la sua massima serie (due o più divisioni dove i dati ci sono: Inghilterra 4, Scozia 3, Germania
  Ovest, Italia, Spagna, Olanda, Belgio, Austria, Svizzera, Danimarca, Ungheria e URSS 2), club nell'ordine finale 1983-84, promozioni e retrocessioni. Il Galles non ha un campionato:
  il Wrexham gioca in Inghilterra, come nella realtà.
- **Coppe nazionali:** i tabelloni reali 1984-85 di 15 paesi nella prima stagione (terzo turno di FA Cup con i dilettanti come
  Dagenham e Telford, DFB-Pokal, Coppa Italia, Copa del Rey, KNVB beker, Scottish Cup...), con i club che giocavano solo la coppa.
  Negli altri paesi la coppa della prima stagione è generata dai club del campionato. Dalla seconda stagione tutte le coppe le
  organizza il gioco.
- **Coppe europee come nel 1984-85:** Coppa dei Campioni 32 club, Coppa delle Coppe 32, Coppa UEFA 64, tutte a eliminazione
  diretta; la prima stagione ha gli accoppiamenti reali del primo turno. I detentori giocano in più rispetto ai posti del loro paese.
- **Allenatori:** quelli reali di 222 club (completi per Italia e Olanda, quasi completi per Spagna e Germania Ovest). Gli altri
  mancano: **chi li trova è il benvenuto se li aggiunge** (colonna `coach` di `clubs.csv` in `packs/europe-1984-85/<paese>`,
  vedi `packs/CAREERS.it.md`) e ce li manda.
- Nomi brevi dei club nello stile di SWOS (MALAGA, MAGDEBURG, WISMUT AUE...). I club che il gioco originale aveva già tengono il
  nome del gioco.

### Coppe europee in ogni carriera

- **Niente sfide tra squadre dello stesso paese al primo e al secondo turno** delle coppe europee a eliminazione diretta, come
  nella regola UEFA dell'epoca: Coppa delle Coppe e Coppa UEFA nelle carriere normali, tutte e tre le coppe nelle carriere
  storiche. Grazie a **DaniSwos** per la segnalazione.
- Carriere normali: dalla seconda stagione il primo turno della Coppa delle Coppe e della Coppa UEFA è **sorteggiato**. Prima i
  club si incontravano nell'ordine della lista, paese per paese (fino a 8 derby su 16 sfide).
- **Detentore della Coppa dei Campioni:** se non si è qualificato col campionato, ora prende il posto di un club di **un altro
  paese**. Prima poteva escludere il campione del suo stesso paese.
- **Bug corretto (dalla 2.5 alla 2.7.0):** chi vinceva la Coppa dei Campioni e poi giocava l'Intercontinentale iniziava la
  stagione dopo nella coppa europea sbagliata (Coppa delle Coppe), con accoppiamenti mescolati e un blocco a fine stagione.
  Corretto per le nuove stagioni. Una carriera già salvata in quello stato resta rovinata: riprendi da un salvataggio fatto prima
  di quella fine stagione.

### Maglie

- **Scelta automatica delle maglie più furba:** il nero non è più in conflitto con blu e verde, il blu non più con l'azzurro, i
  pantaloncini dello stesso colore contano meno, ed è corretto un bug del gioco che trasformava una maglia a righe in tinta unita.
- Un nuovo pulsante **MAGLIE** nella schermata pre-partita apre l'editor **SELEZIONA MAGLIE** (come in SWOS 2020): prima o seconda
  tenuta, tipo e colori della maglia, pantaloncini e calzettoni, solo per quella partita. Grazie a **DaniSwos** per l'analisi.

### Patcher

- File nuovi: da `DATA/TEAM.101` a `DATA/TEAM.144` e `DATA/WORLD04.TMD` (il mondo 1984-85), creati insieme a `TEAM.020`.
- Come prima, aggiorna qualsiasi versione precedente della mod (dalla 1.0 alla 2.7.0, CD e GOG) e non tocca i salvataggi. La riga
  `ENGLISH.EXE + SWOS++` c'è ancora.
- Provato con un banco di prova automatico in DOSBox-X: una stagione italiana completa, salvataggio e ricaricamento, i sorteggi
  europei di una carriera 1998-99 e due stagioni del mondo 1984-85 con salvataggio e ricaricamento.
