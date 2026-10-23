## English

**SWOS 96/97 Mod 4.0.1** (draft)

### Known issues of 4.0, revisited
- **European places**: 4.0's notes said that in some seasons one of the 108 European places could go to a club of
  another association. The one wrong-association place came from the access list's rank-44 row: the association the
  world ranks 44th (North Macedonia) got Liechtenstein's cup-winner-only row. That was fixed in 4.0 itself (22/10,
  before the release): Liechtenstein keeps its own row wherever it ranks, and the 44th association gets the regular
  row. It has not been seen since; the check stays in the test suite.
- **Serie D groups with an odd number of clubs**: 4.0's notes said that a club resting on the last match day would
  play its Poule Scudetto or group play-off in 4.0.1. It is still decided by simulation in 4.0.1: the fix we tried
  kept the season going after the club's last match so that the rest day could be played, but a club with no
  play-off to follow then had no match left and the season could not end. A correct fix is planned for 4.0.2.

### World 2026-27 cups
- **National and league cups follow promotions and relegations** (World 2026-27). In 4.0 every cup kept the same
  clubs every season, so a promoted or relegated club never joined its new division's cup (Mestre, promoted to
  Serie C, played no Coppa Italia Serie C). Now, from the second season, each cup takes its clubs from the divisions
  as they are that season, with the real format: each division sends as many clubs, and gets as many byes, as in the
  real cup (the Coppa Italia Serie C: 5, 7 and 5 from the three Serie C groups; the Copa del Rey: 20 from LaLiga and 21
  from LaLiga 2). Within a division, the clubs relegated from the division above come first, then the clubs that
  stayed, then the promoted ones, each by last season's final place; your club always takes part when its division
  does. The first season keeps the real 2026-27 draw. Every national and league cup of the world follows this rule
  (101 of 102); the one cup with a club outside its country's league file keeps its fixed list. The rule is on each
  cup's FORMAT page.
- The main Coppa Italia keeps its real shape (its 16 clubs are from Serie A and Serie B), so a Serie C club does not
  enter it; the Coppa Italia Serie D is unchanged.
- Saves: the clubs' final places are saved with the career. A 4.0 save loads and plays on; its first new season
  orders the clubs by the team file until a season has been completed.

## Italiano

**SWOS 96/97 Mod 4.0.1** (bozza)

### Problemi noti della 4.0, rivisti
- **Posti europei**: le note della 4.0 dicevano che in alcune stagioni uno dei 108 posti europei poteva andare a un
  club di un'altra federazione. L'unico posto sbagliato veniva dalla riga 44 della lista d'accesso: la federazione
  che il mondo mette 44ª (Macedonia del Nord) riceveva la riga del Liechtenstein, con la sola vincitrice della coppa.
  È stato corretto già nella 4.0 (22/10, prima della pubblicazione): il Liechtenstein ha la sua riga dovunque si
  classifichi e la 44ª federazione la riga normale. Da allora non si è più visto; il controllo resta nei test.
- **Gironi di Serie D con un numero dispari di squadre**: le note della 4.0 dicevano che una squadra che riposa
  all'ultima giornata avrebbe giocato la Poule Scudetto o il play-off del girone nella 4.0.1. Nella 4.0.1 vengono
  ancora simulati: la correzione provata teneva aperta la stagione dopo l'ultima partita della squadra, per giocare
  il turno di riposo, ma una squadra senza play-off non aveva più partite e la stagione non poteva finire. La
  correzione giusta è prevista nella 4.0.2.

### Coppe del Mondo 2026-27
- **Le coppe nazionali e di lega seguono promozioni e retrocessioni** (Mondo 2026-27). Nella 4.0 ogni coppa aveva le
  stesse squadre ogni stagione, così una squadra promossa o retrocessa non entrava mai nella coppa della sua nuova
  categoria (il Mestre, promosso in Serie C, non giocava la Coppa Italia Serie C). Ora, dalla seconda stagione, ogni
  coppa prende le squadre dalle categorie come sono in quella stagione, con la formula vera: ogni categoria manda
  tante squadre, e ha tanti esenti, quanti nella coppa vera (la Coppa Italia Serie C: 5, 7 e 5 dai tre gironi di
  Serie C; la Copa del Rey: 20 dalla LaLiga e 21 dalla LaLiga 2). Dentro una categoria vengono prima le retrocesse
  dalla categoria superiore, poi le squadre rimaste, poi le promosse, ognuna secondo il piazzamento finale della
  stagione prima; la tua squadra c'è sempre se la sua categoria partecipa. La prima stagione mantiene il sorteggio
  vero 2026-27. Tutte le coppe nazionali e di lega del mondo seguono questa regola (101 su 102); l'unica con una
  squadra fuori dal file di campionato del suo paese mantiene la lista fissa. La regola è nella pagina FORMULA di
  ogni coppa.
- La Coppa Italia mantiene la sua forma vera (le sue 16 squadre sono di Serie A e Serie B), quindi una squadra di
  Serie C non vi entra; la Coppa Italia Serie D non cambia.
- Salvataggi: i piazzamenti finali delle squadre si salvano con la carriera. Un salvataggio della 4.0 si carica e
  prosegue; la sua prima stagione nuova ordina le squadre secondo il file finché non si è completata una stagione.
