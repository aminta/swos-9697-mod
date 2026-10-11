## English

**SWOS 96/97 Mod 3.0: Classic careers — Europe 1984-85, and the 1947-48 Serie A**

*Take a club of 1984-85 Europe, from Juventus and Liverpool down to the Icelandic league, and play a whole career through the
leagues, national cups and European cups of the time.*

### Europe 1984-85 (CLASSIC CAREERS)

- A new **CLASSIC CAREERS** button in Career mode (IT `CARR. STORICHE`, FR `CARR. D'ANTAN`, DE `KLASS. KARRIERE`) lists the
  historic worlds; the first one is **EUROPE 1984-85**: **32 European countries, 949 clubs**, starting from the 1984-85 season.
  A career in this world sees only these clubs and countries; normal careers are unchanged. Future worlds will be added to the
  same list. Country names follow the game's language (INGHILTERRA, GERMANIA OVEST, URSS... in the Italian game).
- No national-team jobs in this world for now (the game's national teams are the 1996 ones): era national teams are planned
  for 3.1.
- **Squads:** the real 1984-85 players, from the database by **DaniSwos** (CM01/02 Retro Update Team), converted to SWOS ratings.
- **Leagues:** every country with its top division (two or more divisions where the data has them: England 4, Scotland 3, West
  Germany, Italy, Spain, the Netherlands, Belgium, Austria, Switzerland, Denmark, Hungary and the USSR 2), clubs in the 1983-84 final order, promotion and relegation. Wales has no league: Wrexham plays
  in England, as in reality.
- **National cups:** the real 1984-85 brackets for 15 countries in the first season (FA Cup third round with non-league clubs such
  as Dagenham and Telford, DFB-Pokal, Coppa Italia, Copa del Rey, KNVB beker, Scottish Cup...), with the cup-only clubs that took
  part. In the other countries the first season's cup is generated from the league clubs. From the second season on, all cups
  are run by the game.
- **European cups as in 1984-85:** Champions' Cup 32 clubs, Cup Winners' Cup 32, UEFA Cup 64, all knockout; the first season has
  the real first-round ties. The holders play in addition to their country's places; a league champion that also holds the Cup
  Winners' Cup or the UEFA Cup plays the Champions' Cup, as at the time (its holder place goes to the next club of its table).
- **Coaches:** the real coaches of 222 clubs (complete for Italy and the Netherlands, almost complete for Spain and West
  Germany). The others are missing: **anyone who finds them is welcome to add them** (column `coach` of `clubs.csv` in
  `packs/europe-1984-85/<country>`, see `packs/CAREERS.md`) and send them to us.
- Short club names in SWOS style (MALAGA, MAGDEBURG, WISMUT AUE...). Club names that the original game already had keep the
  game's name.

### Classic seasons: Serie A 1947-48 (CLASSIC SEASONS)

- **Season > CLASSIC SEASONS > ITALY 1947-48** (IT `ITALIA 1947-48`, FR `ITALIE 1947-48`, DE `ITALIEN 1947-48`), also in
  CLASSIC TOURNEYS as SERIE A 1947-48: the season of the Grande Torino.
- **21 clubs** (Triestina readmitted in July 1947: the only odd-sized Serie A, one club rests each round), home and away, 42
  rounds / 40 matches per club, 2 points per win, 4 relegated (Salernitana, Alessandria, Vicenza, Napoli). Napoli was placed
  last for an attempted bribe (Bologna-Napoli): the game cannot reproduce that, the bottom 4 on the pitch go down.
- League only: no Coppa Italia (not played from 1943 to 1958) and no European club cups in 1947-48.
- Clubs in the final-table order with their 1948 names; real squads, coaches and kits (it.wikipedia season pages of the 21
  clubs, RSSSF, inter.it, national-football-teams.com); foreign players with their real nationality.
- Ratings: **Torino** from the SWOS 2020 "1900s Retro Pack Teams (1900-1970)" by **FrancescoManetti82** and **Gorzo** (SWOS
  United) — thanks! The other 20 clubs are calibrated on the final points.
- Engine: leagues with an odd number of clubs now work in Season and Career mode.
- **DDR 1988-89 recalibrated:** the clubs' skills now follow the real 1988-89 table (2.6 made Wismut Aue too strong and Zwickau
  too weak).
- New tool `tools/itwiki_season.py`: drafts any Italian season from it.wikipedia (see `packs/README.md`).

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

- New files: `DATA/TEAM.101` to `DATA/TEAM.144` and `DATA/WORLD04.TMD` (the 1984-85 world), `DATA/TEAM.145` (Serie A
  1947-48), created together with `TEAM.020`; `DATA/TEAM.092` (DDR) is updated.
- As before, it upgrades any earlier version of the mod (1.0 to 2.7.0, CD and GOG) and keeps your saves. The
  `ENGLISH.EXE + SWOS++` row is still there.
- Tested with an automated DOSBox-X harness: a full Italian season, save/load round trip, the European draws of a 1998-99
  career, and two seasons of the 1984-85 world with save and reload; Serie A 1947-48 playtested by Davide.

## Italiano

**SWOS 96/97 Mod 3.0: Carriere storiche — Europa 1984-85, e la Serie A 1947-48**

*Prendi un club dell'Europa 1984-85, dalla Juventus e dal Liverpool fino al campionato islandese, e gioca un'intera carriera tra
campionati, coppe nazionali e coppe europee dell'epoca.*

### Europa 1984-85 (CARRIERE STORICHE)

- Un nuovo pulsante **CARR. STORICHE** in modalità Carriera (EN `CLASSIC CAREERS`, FR `CARR. D'ANTAN`, DE `KLASS. KARRIERE`)
  elenca i mondi storici; il primo è **EUROPA 1984-85**: **32 paesi europei, 949 club**, a partire dalla stagione 1984-85. Una
  carriera in questo mondo vede solo questi club e paesi; le carriere normali non cambiano. I prossimi mondi si aggiungeranno
  allo stesso elenco. I nomi dei paesi seguono la lingua del gioco (INGHILTERRA, GERMANIA OVEST, URSS... nel gioco italiano).
- Per ora in questo mondo non arrivano offerte dalle nazionali (le nazionali del gioco sono quelle del 1996): le nazionali
  dell'epoca sono previste per la 3.1.
- **Rose:** i giocatori reali del 1984-85, dal database di **DaniSwos** (CM01/02 Retro Update Team), convertiti nei valori di SWOS.
- **Campionati:** ogni paese con la sua massima serie (due o più divisioni dove i dati ci sono: Inghilterra 4, Scozia 3, Germania
  Ovest, Italia, Spagna, Olanda, Belgio, Austria, Svizzera, Danimarca, Ungheria e URSS 2), club nell'ordine finale 1983-84, promozioni e retrocessioni. Il Galles non ha un campionato:
  il Wrexham gioca in Inghilterra, come nella realtà.
- **Coppe nazionali:** i tabelloni reali 1984-85 di 15 paesi nella prima stagione (terzo turno di FA Cup con i dilettanti come
  Dagenham e Telford, DFB-Pokal, Coppa Italia, Copa del Rey, KNVB beker, Scottish Cup...), con i club che giocavano solo la coppa.
  Negli altri paesi la coppa della prima stagione è generata dai club del campionato. Dalla seconda stagione tutte le coppe le
  organizza il gioco.
- **Coppe europee come nel 1984-85:** Coppa dei Campioni 32 club, Coppa delle Coppe 32, Coppa UEFA 64, tutte a eliminazione
  diretta; la prima stagione ha gli accoppiamenti reali del primo turno. I detentori giocano in più rispetto ai posti del loro
  paese; un campione nazionale che detiene anche la Coppa delle Coppe o la Coppa UEFA gioca la Coppa dei Campioni, come all'epoca
  (il suo posto da detentore va al club successivo della sua classifica).
- **Allenatori:** quelli reali di 222 club (completi per Italia e Olanda, quasi completi per Spagna e Germania Ovest). Gli altri
  mancano: **chi li trova è il benvenuto se li aggiunge** (colonna `coach` di `clubs.csv` in `packs/europe-1984-85/<paese>`,
  vedi `packs/CAREERS.it.md`) e ce li manda.
- Nomi brevi dei club nello stile di SWOS (MALAGA, MAGDEBURG, WISMUT AUE...). I club che il gioco originale aveva già tengono il
  nome del gioco.

### Stagioni storiche: Serie A 1947-48 (STAG. STORICHE)

- **Stagione > STAG. STORICHE > ITALIA 1947-48** (EN `ITALY 1947-48`, FR `ITALIE 1947-48`, DE `ITALIEN 1947-48`), anche nei
  TORNEI STORICI come SERIE A 1947-48: la stagione del Grande Torino.
- **21 squadre** (Triestina riammessa nel luglio 1947: l'unica Serie A con un numero dispari di squadre, ogni giornata una
  riposa), andata e ritorno, 42 giornate / 40 partite a squadra, 2 punti a vittoria, 4 retrocessioni (Salernitana, Alessandria,
  Vicenza, Napoli). Il Napoli fu messo ultimo per un tentato illecito (Bologna-Napoli): il gioco non può riprodurlo, retrocedono
  le ultime 4 sul campo.
- Solo campionato: niente Coppa Italia (non si giocò dal 1943 al 1958) e nessuna coppa europea per club nel 1947-48.
- Squadre nell'ordine della classifica finale con i nomi del 1948; rose, allenatori e maglie reali (pagine it.wikipedia della
  stagione delle 21 squadre, RSSSF, inter.it, national-football-teams.com); stranieri con la loro vera nazionalità.
- Valori: il **Torino** dal "1900s Retro Pack Teams (1900-1970)" di SWOS 2020 di **FrancescoManetti82** e **Gorzo** (SWOS
  United) — grazie! Le altre 20 squadre sono tarate sui punti finali.
- Motore: i campionati con un numero dispari di squadre ora funzionano in Stagione e in Carriera.
- **DDR 1988-89 ricalibrata:** i valori dei club ora seguono la classifica reale 1988-89 (nella 2.6 il Wismut Aue era troppo
  forte e lo Zwickau troppo debole).
- Nuovo strumento `tools/itwiki_season.py`: prepara una bozza di qualsiasi stagione italiana da it.wikipedia (vedi
  `packs/README.it.md`).

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

- File nuovi: da `DATA/TEAM.101` a `DATA/TEAM.144` e `DATA/WORLD04.TMD` (il mondo 1984-85), `DATA/TEAM.145` (Serie A
  1947-48), creati insieme a `TEAM.020`; `DATA/TEAM.092` (DDR) è aggiornato.
- Come prima, aggiorna qualsiasi versione precedente della mod (dalla 1.0 alla 2.7.0, CD e GOG) e non tocca i salvataggi. La riga
  `ENGLISH.EXE + SWOS++` c'è ancora.
- Provato con un banco di prova automatico in DOSBox-X: una stagione italiana completa, salvataggio e ricaricamento, i sorteggi
  europei di una carriera 1998-99 e due stagioni del mondo 1984-85 con salvataggio e ricaricamento; Serie A 1947-48 provata da Davide.
