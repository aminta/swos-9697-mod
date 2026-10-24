## English

**SWOS 96/97 Mod 4.0.1**

4.0.1 brings a joypad that works out of the box on GOG and, in the World 2026-27, more leagues in their real format
(Mexico, Peru, Colombia, Uruguay), a nationality for every player, cups that follow promotions and relegations,
line-ups by role, simpler menus and a safer install, plus fixes for some 4.0 bugs. Everything in 4.0 stays as it was;
careers saved with 4.0 load and play on.

### What's new

#### Joypad ready
- **Plug the joypad in and play.** On a GOG install, the one-click install now sets everything up: the joypad is
  player 1 and the keyboard is player 2, with a ready calibration, and both the stick and the d-pad work. The keyboard
  still works as before.
- **No joypad, no problem.** The game now checks at start whether a joypad is connected and goes to the keyboard
  automatically when there is none, so keyboard players do not have to change anything.
- **Your own settings.** The install page has a tick, 'GOG version: I have a joypad / gamepad', already on for GOG: untick it to
  keep your own controls settings, and run the install again without the tick to put the originals back (the changed
  files are backed up).
- **Your own DOSBox (CD installs):** its own box, 'Using your own DOSBox (CD, eXoDOS, other)?', is off by default. Tick it if you have a joypad (it changes
  only SETUP.DAT) and add three
  lines to your DOSBox configuration (`[joystick]`, `joysticktype=2axis`, `timed=false`); mapping the d-pad and what
  to do in DOSBox-X are explained in the README and on the install page.

#### Mexico, exactly
- **Liga MX and the Liga de Expansión MX** now play their real 2026-27 season. Each has two tournaments a season: the
  *Apertura* (the opening tournament) and the *Clausura* (the closing one). Each tournament is a single table, the
  Clausura starting again from zero points. The Apertura 2026 is played on its real match days (from Transfermarkt).
  Each tournament is followed by its own final phase, the *liguilla* (Mexican for the play-off): the top 8 go straight in
  (Liga MX has no play-in from the Apertura 2026), 1st v 8th, 2nd v 7th, 3rd v 6th, 4th v 5th, re-seeded
  semi-finals, all over two legs (a tie level on aggregate goes to the better placed club) and a final with extra
  time and penalties. Your club can play every phase.
- **Liga MX: the Campeón de Campeones.** The winners of the Apertura and the Clausura meet in one match at a
  neutral ground (a draw goes to penalties, no extra time); a club that won both gets the trophy without a match.
  The Liga MX has held it every year since 2023 (sources: Mediotiempo, Fox Sports México, La Razón).
- **Liga de Expansión MX:** 16 clubs, the same liguillas and its own Campeón de Campeones, over two legs. No
  promotion or relegation in 2026-27.
- Declared:
  - The Clausura 2027 calendars are not published yet: each Clausura plays its Apertura's match days mirrored (home and away
    swapped) until the real ones are out.
  - Expansión's Campeón de Campeones over two legs (second leg at the better placed club, extra time and
    penalties) is our reading: no source gives its format for 2026-27 (the 2021-22 one went to penalties).
  - One Expansión Apertura match (Atlético La Paz v Leones Negros, match day 8) is missing from the published
    fixtures (Transfermarkt): it is played at Leones Negros, so every club has 7 home and 7 away matches.

#### South America: Peru, Colombia and Uruguay, the tournaments of the year
- **Peru** (Liga 1, 18 clubs): the Apertura and the Clausura, 17 match days each, everybody once, on the real 2026
  calendar; the Clausura starts again from zero points. Each tournament's table leader wins it. The accumulated table
  (Apertura + Clausura) is in STAT > ANNUAL TABLE. The national title goes to the Liga 1 play-offs: the two
  tournament winners (if they are in the accumulated top 8) and the accumulated table's top 2. A tournament winner in
  the top 2 waits in the final; with four clubs the semi-finals are 1st v 4th and 2nd v 3rd by the accumulated
  table. Everything is over two legs. A club that wins both tournaments is champion without playing.
- **Colombia** (Primera A, 20 clubs): the Apertura, 19 match days on the real calendar. Its top 8 then play
  quarter-finals 1st v 8th, 4th v 5th, 2nd v 7th and 3rd v 6th, semi-finals and a final, all over two legs, with
  the second leg at the better placed club and penalties if level. The *Finalización* (Colombia's second tournament)
  is 19 match days from zero points. Its top 8 then play two *cuadrangulares* (groups of four, home and away): the 1st
  and the 2nd head the groups and the other six are drawn, three per group, as the Dimayor (Colombia's league
  organiser) draws them. The two group winners play a two-legged final.
- **Uruguay** (16 clubs): the Apertura (15 match days, real calendar), then the *Intermedio* (the mid-year
  tournament), then the Clausura (15 match days, real calendar), each from zero points.
  - The Intermedio splits the clubs into two series by the Apertura table, in a snake order: series A = 1st, 4th, 5th,
    8th, 9th, 12th, 13th, 16th. Each series is one round, and its winners meet in a final on neutral ground (extra
    time and penalties).
  - The annual table adds up all three tournaments.
  - The title: a single-match semi-final on neutral ground between the Apertura and the Clausura champions, then a
    two-legged final against the annual table's leader. The final is not played when the semi-final's winner leads
    the annual table. A club that wins both the Apertura and the Clausura is champion at once (the rules of the AUF,
    Uruguay's football association, for the coincidence of titles).
- Your club can play every final phase. Every tournament's winner is listed on the WINNERS page.
- Declared:
  - The Clausura and Finalización calendars are the Apertura's mirrored, match day by match day, as every published
    match day shows. The last match days not yet published (Peru 4, Colombia 2, Uruguay 3) follow that mirror. Their
    dates are a week apart: for Peru that ends on 22 November, the real last day.
  - Uruguay's Intermedio uses the game's own calendar of the two series, dated between the Apertura and the Clausura.
  - Colombia's cuadrangulares: the group fixtures are the game's, so the heads are not always at home on the last
    match day; clubs level on points in a group are separated by goal difference, where the Dimayor uses the better
    regular-season place.
  - Peru's play-offs: a tournament winner outside the accumulated top 8 gives its place to the next club of that
    table (the tournament rules do not say what happens); a tie level on aggregate goes to penalties, and the final's better
    placed club is at home in the second leg.
  - Relegation by *promedio* (the average of points over the last seasons: 3 seasons in Colombia, 2 in Uruguay) is
    not in. Peru and Colombia have one division in the world, so nobody goes down there. Uruguay relegates the last 3
    of the end-of-season table.
  - Paraguay's two tournaments are not here yet (see "Declared for 4.0.2").

#### A nationality for every player
- Players from 58 nations that the original game did not have now show their own nationality instead of the
  nearest one: Montenegro (MNE), Kosovo (KOS), Andorra (AND), Gibraltar (GIB), Kazakhstan (KAZ), Cape Verde (CPV),
  Curaçao (CUW), Haiti (HAI), Cuba (CUB), the Dominican Republic (DOM), Lebanon (LBN), Palestine (PLE), Hong Kong
  (HKG), Thailand (THA), Indonesia (IDN), Tahiti (TAH) and more. The nationality is the three-letter FIFA code, as in
  the original game, the same in every language, on the squad and transfer screens.
- Rule: these nations have no national team in the game, so their players are not called up (before, a Montenegrin
  could be called up by Yugoslavia, an Andorran by Spain).
- Careers of the 1996-97 game and of the Europe 1984-85 world are unchanged.

#### World 2026-27 cups
- **National and league cups follow promotions and relegations** (World 2026-27). In 4.0 every cup kept the same
  clubs every season, so a promoted or relegated club never joined its new division's cup (Mestre, promoted to
  Serie C, played no Coppa Italia Serie C). Now, from the second season, each cup takes its clubs from the divisions
  as they are that season, with the real format: each division sends as many clubs, and gets as many byes, as in the
  real cup (the Coppa Italia Serie C: 5, 7 and 5 from the three Serie C groups; the Copa del Rey: 20 from LaLiga and 21
  from LaLiga 2). Within a division, the clubs relegated from the division above come first, then the clubs that
  stayed, then the promoted ones, each by last season's final place; your club always takes part when its division
  does. The first season keeps the real 2026-27 draw. Every national and league cup of the world follows this rule
  (101 of 102); the one cup that includes a club from outside its country's league keeps its fixed list. The rule is on each
  cup's FORMAT page.
- The main Coppa Italia keeps its real shape (its 16 clubs are from Serie A and Serie B), so a Serie C club does not
  enter it; the Coppa Italia Serie D is unchanged.
- Saves: the clubs' final places are saved with the career. A 4.0 save loads and plays on; its first new season
  orders the clubs as the game lists them until a season has been completed.

#### Line-ups that make sense
- The computer teams of the World 2026-27, of Europe 1984-85 and of the historic season packs (since 3.0) used to field
  their starters in the order of the team list, so the left-back stood at centre-back and the left midfielder in central midfield.
  Now each team's 11 starters follow their roles (goalkeeper, right-back, two centre-backs, left-back, right
  midfielder, two central midfielders, left midfielder, two forwards): 3,529 teams corrected. The original 1996-97
  teams and the hand-written line-ups of the historic tourneys are unchanged.
- In a career started before 4.0.1, the clubs the career already holds in memory keep their old line-up.

#### Menus and screens
- **Buying a foreign player** now opens straight on the continents (World 2026-27) or on the nations (Europe
  1984-85), without a CARR. STORICHE (CLASSIC CAREERS) menu in front (in the World 2026-27 that was a violet entry).
- **Career calendar:** the two-line labels of the UEFA qualifying rounds are short enough for their line, e.g. "PRELIM.
  CL" over "TURNO 1 AND." (each language with its own round word).
- **UEFA qualifying rounds**: when your club wins a qualifying tie, the next round now appears in the career calendar
  straight after the return leg. Before, it was added only when you went on to the next match, so for a while the
  calendar seemed to have no next round.
- **Match titles** are fitted to the title bar by their real width: no title is cut any more (the 4.0 limit on long
  titles is gone) and none starts with a stray space. We checked the longest title of every competition.
- **WINNERS page:** a competition's long name is shown in full when it fits (TROFEO DE CAMPEONES, not TROFEO CAMP.).

#### Install
- **GOG:** GOG's own shortcut starts the English version. When the one-click install finds GOG's DOSBox, it writes
  one launcher per language beside the game: "SWOS Mod - Italiano.bat", "SWOS Mod - English.bat", "SWOS Mod -
  Francais.bat" and "SWOS Mod - Deutsch.bat" (for the languages GOG's folder has a configuration for). Start the game with
  them. A re-run writes back a launcher that was deleted.
- **A half-finished install** is now caught twice. The one-click page shows "Writing the mod: i / N files... Do not close
  or reload the page", checks every file it wrote and ends with "Done: N / N files written and verified" or, in
  red, "INSTALL INCOMPLETE: only k of N files were written correctly ... choose the game folder again" (this part was
  already in the 23 October re-issue of 4.0). And if
  some World 2026-27 files are still missing, choosing the world (CLASSIC CAREERS, the green CAREER 2026-27 button,
  or Europe 1984-85) no longer quits to DOS: the game says "INCOMPLETE INSTALL: RUN THE PATCHER AGAIN" (in each
  language) and goes back to the menu.

### Known issues of 4.0, revisited
- **European places**: the 4.0 notes warned that in some seasons a European place could go to a club of the wrong
  country. This had already been fixed in 4.0 before its release and has not happened since: every country gets its
  right European places.
- **Serie D groups with an odd number of clubs**: in such a group one club rests on each match day. If yours rests on
  the last one, it does not play the Poule Scudetto or its group play-off: they are decided by simulation. The 4.0
  notes announced a fix for 4.0.1; the fix we tried could make the season impossible to finish, so it is planned for
  4.0.2.
- **Copa Libertadores group thirds**: in 4.0 their move to the Copa Sudamericana play-off was simulated. Now your club,
  third in its Libertadores group, plays the play-off (both legs, January). This works from your career's second
  season, because the first season's continental cups are the world's own. The rest of the Sudamericana, and the
  Libertadores round of 16 for a group winner or runner-up (both from February), are still simulated at the season
  end, because they come after the domestic season has ended (Argentina's ends in December). Planned for 4.0.2.
- **Serie D**: a career saved after its Coppa Italia Serie D tie was drawn no longer starts the play-offs after a few
  match days when loaded (the tie is played; 4.0 saves affected are repaired on load). Gianmarco.
- Careers saved during a season in which a play-off or title decider was settled without your club (for example
  Argentina's Apertura / Clausura knockouts when your club missed them, or Malta's decider when one club won both
  rounds) no longer start the next season with an empty league after loading (the match screen could not be played).
- **World 2026-27**: a career saved with an earlier version no longer shows garbled titles on the European cup finals
  at the season end (seen in 4.0 too).
- **Menu buttons**: the 4.0 notes mentioned a few wrong pixels on the menu buttons after a job offer. It was not a
  problem of the released 4.0 (it only showed up in a test version), so we took it off the list. If you see it, let
  us know.

### Declared for 4.0.2
- **AFC Challenge League:** its group stage (5 groups of 4, everybody once; the 5 winners and the 3 best runners-up go
  to the quarter-finals) is still simulated; your club joins at the quarter-finals. Playing the groups needs a
  ranking of the runners-up across the groups, which is not ready.
- **AFC Champions League Elite:** its league stage (all the clubs in one table) is still simulated; it will be
  played in 4.0.2.
- **Guatemala, El Salvador and Paraguay:** their real 44-match-day calendars (two tournaments a season) are longer
  than the game's calendar can hold today; they keep the format they had in 4.0 until then.
- **Calendars not yet published:** the Clausura 2027 of Mexico, Costa Rica, Honduras and Panama, and the last match
  days of Peru, Colombia and Uruguay, repeat the first half's fixtures with home and away swapped until the real
  calendars are out.
- **Colombia's cuadrangulares:** the real order of the group fixtures and the tie-break by regular-season place.
  Planned for 4.0.2.
- **Single-match ties**: in some cups a single match (for example the Copa do Brasil final) that ends level goes to
  extra time before the penalties, while the real rule goes straight to penalties. This has been so since 3.2; it will
  follow the real rule in 4.0.2.
- **Management record**: for a season in which your club went out in a European qualifying round, the record shows the
  qualifying competition with 'FINALIST' instead of the round in which it went out. It will show the round in 4.0.2.
- **Serie D rest day and the Libertadores continuation:** see "Known issues of 4.0, revisited".

### Thanks
Thanks to Roman for the nationalities, to Gianmarco for the install report, the line-ups and the Serie D report, to
Filippo for the GOG launch, to Pietro for the Champions League qualifying report and to Marco and Luigi for the
joypad question.

## Italiano

**SWOS 96/97 Mod 4.0.1**

La 4.0.1 porta un joypad che funziona subito su GOG e, nel Mondo 2026-27, altri campionati con la loro formula vera
(Messico, Perù, Colombia, Uruguay), una nazionalità per ogni giocatore, coppe che seguono promozioni e retrocessioni,
formazioni secondo i ruoli, menu più semplici e un'installazione più sicura, più le correzioni di alcuni errori della
4.0. Tutto quello che c'era nella 4.0 resta com'era; le carriere salvate con la 4.0 si caricano e continuano.

### Novità

#### Joypad pronto
- **Collega il joypad e gioca.** Su un'installazione GOG, l'installazione con un clic ora imposta tutto: il joypad è il
  giocatore 1 e la tastiera il giocatore 2, con una calibrazione già pronta, e funzionano sia lo stick sia la croce
  direzionale. La tastiera funziona come prima.
- **Senza joypad, nessun problema.** Ora il gioco controlla all'avvio se c'è un joypad collegato e passa alla tastiera
  da solo se non c'è, quindi chi gioca con la tastiera non deve cambiare nulla.
- **Le tue impostazioni.** La pagina d'installazione ha una spunta, 'Versione GOG: ho un joypad / gamepad', già attiva su GOG:
  toglila per tenere le tue impostazioni dei comandi, e rifai l'installazione senza spunta per rimettere gli originali
  (i file modificati restano in copia).
- **Il tuo DOSBox (installazioni da CD):** la sua casella, 'Usi un tuo DOSBox (CD, eXoDOS, altro)?', è disattivata di default. Attivala se hai un joypad (cambia solo
  SETUP.DAT) e aggiungi tre righe alla configurazione del tuo DOSBox (`[joystick]`, `joysticktype=2axis`, `timed=false`); come
  associare la croce direzionale e cosa fare in DOSBox-X sono spiegati nel README e nella pagina d'installazione.

#### Il Messico, esattamente
- **La Liga MX e la Liga de Expansión MX** giocano la loro vera stagione 2026-27. Ognuna ha due tornei a stagione:
  l'*Apertura* (il torneo d'apertura) e la *Clausura* (quello di chiusura). Ogni torneo è una sola classifica, la
  Clausura riparte da zero punti. L'Apertura 2026 si gioca sulle sue giornate vere (da Transfermarkt). Ogni torneo è
  seguito dalla sua fase finale, la *liguilla* (il play-off messicano): le prime 8 entrano
  direttamente (la Liga MX non ha il play-in dall'Apertura 2026), 1ª-8ª, 2ª-7ª, 3ª-6ª, 4ª-5ª, semifinali con nuovo
  abbinamento, tutto con andata e ritorno (in parità nel doppio confronto passa la meglio piazzata) e una finale con
  supplementari e rigori. La tua squadra può giocare ogni fase.
- **Liga MX: il Campeón de Campeones.** Le vincitrici di Apertura e Clausura si sfidano in una sola partita in campo
  neutro (in parità si va ai rigori, senza supplementari); chi ha vinto entrambi i tornei ha il trofeo senza giocare.
  La Liga MX lo gioca ogni anno dal 2023 (fonti: Mediotiempo, Fox Sports México, La Razón).
- **Liga de Expansión MX:** 16 squadre, le stesse liguilla e il suo Campeón de Campeones, con andata e ritorno.
  Nessuna promozione né retrocessione nel 2026-27.
- Dichiarato:
  - I calendari della Clausura 2027 non sono ancora pubblicati: ogni Clausura gioca le giornate della sua Apertura a
    campi invertiti finché non escono quelli veri.
  - Il Campeón de Campeones della Expansión con andata e ritorno (ritorno in casa della meglio piazzata, supplementari
    e rigori) è una nostra interpretazione: nessuna fonte ne dà la formula 2026-27 (quella del 2021-22 andò ai rigori).
  - Una partita dell'Apertura della Expansión (Atlético La Paz-Leones Negros, giornata 8) manca dal calendario
    pubblicato (Transfermarkt): si gioca in casa del Leones Negros, così ogni squadra ha 7 partite in casa e 7 fuori.

#### Sudamerica: Perù, Colombia e Uruguay, i tornei dell'anno
- **Perù** (Liga 1, 18 squadre): Apertura e Clausura, 17 giornate di sola andata ciascuno, sul calendario vero 2026; la
  Clausura riparte da zero punti. Ogni torneo lo vince la prima della sua classifica. La classifica accumulata
  (Apertura + Clausura) è in STAT > CLASSIFICA ANNUALE. Il titolo nazionale si gioca nei playoff della Liga 1: i
  vincitori dei due tornei (se tra i primi 8 dell'accumulata) e le prime 2 dell'accumulata. Un vincitore tra le
  prime 2 aspetta in finale; con quattro squadre le semifinali sono 1ª contro 4ª e 2ª contro 3ª dell'accumulata.
  Tutto con andata e ritorno. Chi vince entrambi i tornei è campione senza giocare.
- **Colombia** (Primera A, 20 squadre): l'Apertura, 19 giornate sul calendario vero. Le prime 8 giocano poi quarti
  1ª-8ª, 4ª-5ª, 2ª-7ª e 3ª-6ª, semifinali e finale, tutto con andata e ritorno, ritorno in casa della meglio piazzata
  e rigori in parità. Il *Finalización* (il secondo torneo colombiano) è di 19 giornate da zero punti. Le prime 8
  giocano poi due *cuadrangulares* (gironi da quattro, andata e ritorno): 1ª e 2ª sono teste di serie e le altre sei
  si sorteggiano, tre per gruppo, come fa la Dimayor (l'organizzatrice del campionato colombiano). Le due vincenti
  giocano la finale di andata e ritorno.
- **Uruguay** (16 squadre): l'Apertura (15 giornate, calendario vero), poi l'*Intermedio* (il torneo di metà anno), poi
  la Clausura (15 giornate, calendario vero), ognuno da zero punti.
  - L'Intermedio divide le squadre in due serie secondo la classifica dell'Apertura, a serpentina: serie A = 1ª, 4ª,
    5ª, 8ª, 9ª, 12ª, 13ª, 16ª. Ogni serie gioca una volta sola e le due prime si giocano la finale in campo neutro
    (supplementari e rigori).
  - La classifica annuale somma tutti e tre i tornei.
  - Il titolo: semifinale in gara unica in campo neutro tra i campioni di Apertura e Clausura, poi finale di andata e
    ritorno contro la prima dell'annuale. La finale non si gioca se chi vince la semifinale è prima nell'annuale. Chi
    vince Apertura e Clausura è subito campione (le regole dell'AUF, la federazione uruguaiana, per la coincidenza dei
    titoli).
- La tua squadra può giocare ogni fase finale. I vincitori di ogni torneo sono nella pagina VINCITORI.
- Dichiarato:
  - I calendari di Clausura e Finalización sono quelli dell'Apertura a campi invertiti, giornata per giornata, come
    mostra ogni giornata pubblicata. Le ultime non ancora pubblicate (Perù 4, Colombia 2, Uruguay 3) seguono lo stesso
    specchio. Le loro date sono a una settimana di distanza: per il Perù si arriva al 22 novembre, l'ultima giornata
    vera.
  - L'Intermedio uruguaiano usa il calendario del gioco per le due serie, con date tra Apertura e Clausura.
  - Quadrangolari colombiani: il calendario dei gironi è quello del gioco, quindi le teste di serie non sempre giocano
    in casa l'ultima giornata; a pari punti nel girone decide la differenza reti, mentre la Dimayor usa il miglior
    piazzamento nella fase regolare.
  - Playoff del Perù: un vincitore di torneo fuori dai primi 8 dell'accumulata lascia il posto alla squadra
    successiva di quella classifica (il regolamento non lo dice); in parità dopo andata e ritorno si va ai rigori, e in
    finale la meglio piazzata gioca il ritorno in casa.
  - La retrocessione per *promedio* (la media dei punti delle ultime stagioni: 3 in Colombia, 2 in Uruguay) non c'è.
    Perù e Colombia hanno una sola divisione nel mondo, quindi lì non retrocede nessuno. In Uruguay retrocedono le
    ultime 3 della classifica di fine stagione.
  - I due tornei del Paraguay non ci sono ancora (vedi "Dichiarato per la 4.0.2").

#### Una nazionalità per ogni giocatore
- I giocatori di 58 nazioni che il gioco originale non aveva ora mostrano la propria nazionalità invece di quella più
  vicina: Montenegro (MNE), Kosovo (KOS), Andorra (AND), Gibilterra (GIB), Kazakistan (KAZ), Capo Verde (CPV), Curaçao
  (CUW), Haiti (HAI), Cuba (CUB), Repubblica Dominicana (DOM), Libano (LBN), Palestina (PLE), Hong Kong (HKG),
  Thailandia (THA), Indonesia (IDN), Tahiti (TAH) e altre. La nazionalità è la sigla FIFA di tre lettere, come nel
  gioco originale, uguale in ogni lingua, nelle schermate della rosa e dei trasferimenti.
- Regola: queste nazioni non hanno una nazionale nel gioco, quindi i loro giocatori non vengono convocati (prima un
  montenegrino poteva essere convocato dalla Jugoslavia, un andorrano dalla Spagna).
- Le carriere del gioco 1996-97 e del mondo Europa 1984-85 non cambiano.

#### Coppe del Mondo 2026-27
- **Le coppe nazionali e di lega seguono promozioni e retrocessioni** (Mondo 2026-27). Nella 4.0 ogni coppa aveva le
  stesse squadre ogni stagione, così una squadra promossa o retrocessa non entrava mai nella coppa della sua nuova
  categoria (il Mestre, promosso in Serie C, non giocava la Coppa Italia Serie C). Ora, dalla seconda stagione, ogni
  coppa prende le squadre dalle categorie come sono in quella stagione, con la formula vera: ogni categoria manda
  tante squadre, e ha tanti esenti, quanti nella coppa vera (la Coppa Italia Serie C: 5, 7 e 5 dai tre gironi di
  Serie C; la Copa del Rey: 20 dalla LaLiga e 21 dalla LaLiga 2). Dentro una categoria vengono prima le retrocesse
  dalla categoria superiore, poi le squadre rimaste, poi le promosse, ognuna secondo il piazzamento finale della
  stagione prima; la tua squadra c'è sempre se la sua categoria partecipa. La prima stagione mantiene il sorteggio
  vero 2026-27. Tutte le coppe nazionali e di lega del mondo seguono questa regola (101 su 102); l'unica con una
  squadra che non è del campionato del suo paese mantiene la lista fissa. La regola è nella pagina FORMULA di
  ogni coppa.
- La Coppa Italia mantiene la sua forma vera (le sue 16 squadre sono di Serie A e Serie B), quindi una squadra di
  Serie C non vi entra; la Coppa Italia Serie D non cambia.
- Salvataggi: i piazzamenti finali delle squadre si salvano con la carriera. Un salvataggio della 4.0 si carica e
  prosegue; la sua prima stagione nuova ordina le squadre come le elenca il gioco finché non si è completata una stagione.

#### Formazioni sensate
- Le squadre del computer del Mondo 2026-27, di Europa 1984-85 e dei pacchetti di stagioni storiche (dalla 3.0)
  schieravano i titolari nell'ordine della lista della squadra, così il terzino sinistro giocava da difensore centrale e il
  centrocampista di sinistra a centrocampo. Ora gli 11 titolari di ogni squadra seguono i loro ruoli (portiere,
  terzino destro, due difensori centrali, terzino sinistro, ala destra, due centrocampisti centrali, ala sinistra, due
  attaccanti): 3.529 squadre corrette. Le squadre originali del 1996-97 e le formazioni scritte a mano dei tornei
  storici non cambiano.
- In una carriera iniziata prima della 4.0.1, i club che la carriera ha già in memoria tengono la vecchia formazione.

#### Menu e schermate
- **L'acquisto di un giocatore straniero** si apre ora direttamente sui continenti (Mondo 2026-27) o sulle nazioni
  (Europa 1984-85), senza un menu CARR. STORICHE davanti (nel Mondo 2026-27 era una voce viola).
- **Calendario della carriera:** le etichette su due righe dei turni di qualificazione UEFA stanno nella loro riga, per
  esempio "PRELIM. CL" sopra "TURNO 1 AND." (ogni lingua con la sua parola per "turno").
- **Turni preliminari UEFA**: quando il tuo club supera un turno preliminare, il turno successivo compare nel calendario
  della carriera subito dopo la partita di ritorno. Prima veniva aggiunto solo quando passavi alla partita successiva,
  quindi per un po' il calendario sembrava senza il turno dopo.
- **I titoli delle partite** si adattano alla barra del titolo secondo la larghezza vera: nessun titolo viene più
  tagliato (il limite della 4.0 sui titoli lunghi non c'è più) e nessuno comincia con uno spazio vagante. Abbiamo
  controllato il titolo più lungo di ogni competizione.
- **Pagina VINCITORI:** il nome lungo di una competizione si vede per intero quando ci sta (TROFEO DE CAMPEONES, non
  TROFEO CAMP.).

#### Installazione
- **GOG:** il collegamento di GOG avvia la versione inglese. Quando l'installazione con un clic trova il DOSBox di GOG,
  scrive accanto al gioco un avviatore per lingua: "SWOS Mod - Italiano.bat", "SWOS Mod - English.bat", "SWOS Mod -
  Francais.bat" e "SWOS Mod - Deutsch.bat" (per le lingue di cui la cartella di GOG ha la configurazione). Avvia il gioco con
  questi. Se ne cancelli uno, un nuovo passaggio lo riscrive.
- **Un'installazione a metà** viene ora rilevata due volte. La pagina a un clic mostra "Scrivo la mod: i / N file... Non
  chiudere né ricaricare la pagina", controlla ogni file che ha scritto e finisce con "Fatto: N / N file scritti e verificati"
  oppure, in rosso, "INSTALLAZIONE INCOMPLETA: solo k file su N sono stati scritti correttamente ... scegli di nuovo la
  cartella del gioco" (questa parte era già nella riedizione della 4.0 del 23 ottobre). E se mancano ancora dei file del Mondo 2026-27, scegliere il mondo (CARR.
  STORICHE, il pulsante verde CARRIERA 2026-27 o Europa 1984-85) non fa più uscire a DOS: il gioco dice
  "INSTALLAZIONE INCOMPLETA: RILANCIA IL PATCHER" (in ogni lingua) e torna al menu.

### Problemi noti della 4.0, rivisti
- **Posti europei**: le note della 4.0 avvisavano che in alcune stagioni un posto europeo poteva andare a un club della
  nazione sbagliata. Era già stato corretto nella 4.0 prima dell'uscita e non è più successo: ogni nazione ha i suoi
  posti europei giusti.
- **Gironi di Serie D con un numero dispari di squadre**: in un girone così una squadra riposa a ogni giornata. Se la
  tua riposa all'ultima, non gioca la Poule Scudetto né il play-off del girone: vengono decisi con una simulazione. Le
  note della 4.0 annunciavano la correzione nella 4.0.1; quella che abbiamo provato poteva rendere impossibile finire
  la stagione, quindi è prevista nella 4.0.2.
- **Terze dei gironi di Copa Libertadores**: nella 4.0 il loro passaggio allo spareggio della Copa Sudamericana era
  simulato. Ora la tua squadra, terza nel suo girone di Libertadores, gioca lo spareggio (andata e ritorno, a
  gennaio). Vale dalla seconda stagione della carriera, perché nella prima le coppe continentali sono quelle del
  mondo. Il resto della Sudamericana, e gli ottavi di Libertadores per chi è prima o seconda in un girone (entrambi da
  febbraio), sono ancora simulati a fine stagione, perché vengono dopo la fine del campionato nazionale (quello
  argentino finisce a dicembre). Previsto nella 4.0.2.
- **Serie D**: una carriera salvata dopo il sorteggio del turno di Coppa Italia Serie D, una volta caricata, non fa più
  partire i play-off dopo poche giornate (il turno si gioca; i salvataggi 4.0 colpiti vengono riparati al
  caricamento). Gianmarco.
- Le carriere salvate durante una stagione in cui un play-off o uno spareggio per il titolo è stato deciso senza il tuo
  club (per esempio i knockout di Apertura / Clausura in Argentina quando il tuo club non c'era, o lo spareggio di
  Malta quando un club ha vinto entrambe le fasi) non iniziano più la stagione successiva con un campionato vuoto dopo
  il caricamento (la schermata della partita non si poteva giocare).
- **Mondo 2026-27**: una carriera salvata con una versione precedente non mostra più titoli illeggibili sulle finali
  delle coppe europee a fine stagione (difetto presente anche nella 4.0).
- **Pulsanti dei menu**: le note della 4.0 citavano alcuni pixel sbagliati sui pulsanti dei menu dopo un'offerta di
  lavoro. Non era un problema della 4.0 pubblicata (compariva solo in una versione di prova), quindi l'abbiamo tolto
  dall'elenco. Se ti capita di vederlo, segnalacelo.

### Dichiarato per la 4.0.2
- **AFC Challenge League:** la fase a gironi (5 gironi da 4, tutti contro tutti una volta; le 5 prime e le 3 migliori
  seconde ai quarti) resta simulata; la tua squadra entra dai quarti di finale. Per giocare i gironi serve la
  classifica delle seconde fra i gironi, che non è pronta.
- **AFC Champions League Elite:** la fase a campionato (tutte le squadre in una sola classifica) resta simulata; sarà
  giocata nella 4.0.2.
- **Guatemala, El Salvador e Paraguay:** i loro calendari veri di 44 giornate (due tornei a stagione) sono più lunghi di
  quello che il calendario del gioco può contenere oggi; fino ad allora tengono la formula che avevano nella 4.0.
- **Calendari non ancora pubblicati:** la Clausura 2027 di Messico, Costa Rica, Honduras e Panama, e le ultime giornate
  di Perù, Colombia e Uruguay, ripetono le partite del girone d'andata a campi invertiti finché non escono i
  calendari veri.
- **Quadrangolari colombiani:** l'ordine vero delle partite dei gironi e lo spareggio per piazzamento nella fase
  regolare. Previsto nella 4.0.2.
- **Partite secche**: in alcune coppe una partita unica (per esempio la finale della Copa do Brasil) che finisce in
  parità va ai supplementari prima dei rigori, mentre la regola vera va direttamente ai rigori. È così dalla 3.2; nella
  4.0.2 seguirà la regola vera.
- **Elenco di gestione**: per una stagione in cui il tuo club è uscito in un turno preliminare europeo, l'elenco mostra la
  competizione preliminare con 'FINALISTA' invece del turno in cui è uscito. Nella 4.0.2 mostrerà il turno.
- **Giorno di riposo in Serie D e prosecuzione della Libertadores:** vedi "Problemi noti della 4.0, rivisti".

### Ringraziamenti
Grazie a Roman per le nazionalità, a Gianmarco per la segnalazione sull'installazione, sulle formazioni e sulla Serie D,
a Filippo per l'avvio da GOG, a Pietro per la segnalazione sulle qualificazioni di Champions League e a Marco e Luigi
per la domanda sul joypad.
