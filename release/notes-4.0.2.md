## English

**SWOS 96/97 Mod 4.0.2**

4.0.2 puts two things first: the game now always runs in **full graphics**, and the **real kits of 227 Italian
clubs**. It also brings bigger squads and buying players from other clubs' extra players, a CONTROLS menu inside
the game, editable shirt numbers, a keyboard mode for joypads on GOG, more leagues in their real format (Guatemala,
El Salvador, Paraguay), fixes to the European places and a long list of fixes to menus and screens. Everything in
4.0 and 4.0.1 stays as it was; careers saved with 4.0 or 4.0.1 load and play on (see "Good to know").

### What's new

#### In the spotlight
- **Full graphics, always.** The game used to start in the reduced graphics mode meant for slow PCs of 1996 whenever
  its settings file said so: that is how GOG's own settings file is made, and a slow MiSTer does the same. You
  got poorer graphics, no shirt numbers 17-99 over the players' heads, and players with dark skin and blond hair drawn as a
  block of pixels. Now the game always starts in full graphics. If you want the old reduced mode, start the game
  with `/H`. In the reduced mode the two problems above are fixed too.
- **The real kits of 227 Italian clubs.** Every Italian club from Serie A down to Serie D (227 clubs, checked one by
  one) now plays in its real 2026-27 kits: first and second shirt, shirt colours, shorts and socks. In Serie D many
  clubs had stand-in colours: now they are the right ones. Sources: the clubs' official shops and pages (Serie A to
  C), Wikipedia and the kit archives (Serie D).
- **Malen is no longer blond** (Donyell Malen, Roma): the game has no bald heads, so he has dark hair, the closest
  look. The "pile of pixels" that appeared in his place in a match is fixed (it was the reduced graphics mode, see
  above).

#### Bigger squads, and buying from other clubs' extra players
- **Bigger squads.** In the World 2026-27 career, the club you manage now starts with up to 30 real players (the 16
  of its team record plus up to 14 more, the club's next most important players), instead of the 16 plus 10 invented
  reserves. Computer clubs still play with their 16. The extra players are never better than the weakest of the
  club's 16, and they are paid like reserves (66%) until they are transferred. The game's squad limit is still
  30: a club that starts with 30 players has to sell before it can buy.
- **Buying other clubs' extra players.** The national transfer market can now offer players 17-30 of other clubs,
  with price and wage from the mod's scale. When you buy one he joins your squad and cannot be bought a second time
  in that career.
- **Looking at other clubs' full squads.** When you browse a club to buy, a second page (the button next to ESCI)
  lists its extra players. In STAT, VIS. SQUADRE (the squad view) now also shows a club's full squad, with a PAG. SUCC. button
  for the page of extras. These are for looking only: the computer club still plays with its 16.

#### Controls
- **A CONTROLS menu inside the game.** OPTIONS now has a COMANDI / CONTROLS / COMMANDES / STEUERUNG button (between
  ESCI A DOS and ESCI). There you choose the input (keyboard only, joypad 1 + keyboard 2, keyboard 1 + joypad 2, two
  joypads), set each key by pressing it (a key already used is refused, ESC keeps the old one), calibrate the joypads
  (stick centred, then every corner, with a live test line) and save: the choice is written into the game's SETUP.DAT.
  If no joypad is connected the game goes on with the keyboard. The button is not there with SWOS++.
- **Joypad in keyboard mode (GOG).** For joysticks that work in the menus but, in a match, only go up and left (two-axis
  sticks without a d-pad): the install page has a third tick, "GOG version, joypad in keyboard mode", off by default and
  used together with the first one. The stick, the d-pad and the buttons become the arrow keys and Ctrl; no calibration,
  any joystick or joypad works, and joypad and keyboard both control player 1. Untick it and install again to go back
  to the calibrated joypad.
- **Edit your shirt numbers.** On the team screen before a match, press LEFT on one of your players to light his
  number: UP / DOWN go to the next / previous free number from 1 to 99, or type the digits (a number already in use is
  swapped with its owner); FIRE, ENTER, LEFT or RIGHT confirm, ESC cancels. It works only on your own team. The first
  change gives every player of the team his own number; from then on the team keeps its numbers (no automatic 12-16 on
  the bench, no swapping of numbers, new players get a free one). Careers and seasons save the numbers; in a friendly
  they last for the session.
- **Numbers of two digits** are now drawn well on the tactics pitch, and in the bench list in a match (the number ends
  in one column, clear of the face icon, and the name starts a little further right).
- **The number over your player's head.** Some players had no number over their head in a match, even when you
  controlled them, mostly on GOG and on MiSTer. It was a game start-up problem: the game left some of its memory
  not cleared and only DOSBox-X happens to clear it. Now the game clears it. In the reduced graphics mode (`/H`)
  the numbers 17-99 are drawn too.

#### Cups, tournaments and leagues
- **European places.** A club that wins its league and the Conference League in the same season, and so already
  has a Champions League place, keeps the Champions League place (before, it was sent to the Europa League and its
  Champions League place was passed down). Reported by Pietro.
- **CONCACAF Champions Cup:** a tie level on aggregate goes to away goals, then extra time (where away goals no
  longer count), then penalties, as in the real 2026 competition. The CAF Champions League and Confederation Cup
  ties your club plays decide on away goals and then penalties, as in 2025-26.
- **Guatemala and El Salvador** now play their real 2026-27 season: two tournaments, the Apertura and the Clausura, each a
  double round robin of 12 clubs, points reset in between, and an annual table. Each tournament ends with its real
  final phase: the 3rd-6th and 4th-5th play-offs and the semi-finals over two legs (the better placed club goes through
  when level), then the final: over two legs in Guatemala, one match at a neutral ground in El Salvador, with extra
  time and penalties. Declared: the Clausura's calendar repeats the Apertura's with home and away swapped (the real
  2027 dates are not out yet); when the regular phase ends level on points, the game's order applies (goal
  difference, goals scored).
- **Paraguay** plays its real 2026 season: the Apertura and the Clausura, 22 match days each, home and away, on the
  real calendar, the Clausura from zero points. The leader of each table wins the tournament. Level on points, the order
  is decided by points in the matches between the clubs concerned (the "head-to-head"), then the head-to-head goal
  difference, the goal difference and the goals scored; an extra match at a neutral ground only if the clubs are still
  level on all of these. Declared: three or more clubs level at the top: no draw, the table's order after those
  criteria; no relegation (one division in the world).
- **Mexico: the right title on every screen.** The Liga MX and Liga de Expansión tables and calendars are titled with
  the tournament being played (LIGA MX APERTURA, then LIGA MX CLAUSURA; MX APERTURA / MX CLAUSURA in the calendar).
- **The WINNERS page.** For the play-offs that decide the title in your own league (for example Peru's Liga 1 play-offs, or Uruguay's
  CAMPEONATO URUGUAYO) it now says DA GIOCARE ("to be played") until the end of the season decides it, instead
  of leaving the line out. In Uruguay and Peru the champion is named as soon as one club leads both the Apertura and the
  Clausura (no play-off then).
- **Serie D play-offs.** The FORMAT page of the Serie D groups and of the play-off now says clearly that the group
  play-offs decide placings only and give no promotion (a user who won them twice expected to go up).

#### Menus and screens
- **Club buttons in the lists.** In the team choice of a career and in the club list of the transfer market, the buttons
  with the names of the Serie D clubs appeared in different, random colours. Now they all have their normal colour.
- **VISUALIZZA MONDO** (view the world) in the historic worlds (World 2026-27, Europe 1984-85, 1996-97) opens straight on
  the world's continents (or countries), with no one-entry menu first.
- **Save names.** A save called CON, NUL, PRN, AUX, COM1, LPT1 and the like (with or without an extension) used to write
  into the DOS device: no file, and the career was lost. The game now refuses the name with a message (NOME FILE NON VALIDO /
  INVALID FILENAME / NOM DE FICHIER INVALIDE / DATEINAME NICHT ERLAUBT) and goes back to the save box.
- **STATS menu.** Coming back from FORMAT or WINNERS the menu no longer changes (before, extra entries appeared and an
  empty page 'NESSUNA DESCRIZIONE').
- **Data corrections (World 2026-27).** The club AMERICA PE and TREFELIN B & G have their right names, 22 pairs of clubs
  with the same name are told apart, and 105 clubs that had no coach now have one. Further coaches are still missing
  for some clubs (El Salvador, Brazil, Australia, Italy, Suriname, Chinese Taipei).

### Good to know
- **Saves.** Careers saved with 4.0 or 4.0.1 load and play on. A career saved with 4.0.2 whose transfer market lists
  a player 17-30 of another club, or in which you have bought one, can only be loaded with 4.0.2 or later (older
  versions would read the player from the wrong place).
- **European qualifying rounds.** If your club drops from the Champions League qualifying into the Conference
  League (or the Europa League) qualifying, the calendar shows the rounds already played under the new cup's name too
  (for example "PRELIM. ECL" for the first round). Only the label is wrong: the draw, the opponents and the places
  you earn are right. This will be fixed in 4.0.3.
- **Planned for 4.0.3:** a nationality list for the coaches of each world, and bald players.
- **Reduced graphics:** the reduced mode is now only on request (`/H`); on a very slow PC `/F` and the low-memory
  rule work as before.

### Declared, as in 4.0.1
These were announced for 4.0.2 in the 4.0.1 notes and are **not** in this release; they stay as described there.
- **AFC Challenge League** groups and **AFC Champions League Elite** league stage: still simulated (your club joins at
  the quarter-finals / the knockout).
- **Calendars not yet published** (the Clausura 2027 of Mexico, Costa Rica, Honduras and Panama, and the last match days
  of Peru, Colombia and Uruguay): they repeat the first half's fixtures with home and away swapped.
- **Colombia's cuadrangulares:** the real order of the group fixtures and the tie-break by regular-season place.
- **Single-match ties** that end level (for example the Copa do Brasil final): extra time before the penalties,
  while the real rule goes straight to penalties.
- **Management record:** for a season in which your club went out in a European qualifying round, it shows the
  qualifying competition with 'FINALIST' instead of the round.
- **Serie D groups with an odd number of clubs:** if your club rests on the last match day, its Poule Scudetto or group
  play-off is decided by simulation.
- **Copa Libertadores / Sudamericana:** the rounds that come after the domestic season has ended (the Sudamericana
  after the play-off, a group winner's or runner-up's round of 16 in February) are simulated at the season end.

### Thanks
Thanks to Pietro for the Champions League report that led to the European places fix, to Marco for the joypad in
keyboard mode and the shirt numbers, and to everyone who sent a report from the site.

## Italiano

**SWOS 96/97 Mod 4.0.2**

La 4.0.2 mette in primo piano due cose: il gioco ora parte **sempre in grafica piena** e le squadre italiane hanno
le **maglie vere (227 squadre)**. Porta anche rose più grandi e l'acquisto dei giocatori extra degli altri club, un menu
COMANDI dentro il gioco, i numeri di maglia modificabili, una modalità tastiera per i joypad su GOG, più campionati
nel loro formato vero (Guatemala, El Salvador, Paraguay), correzioni ai posti europei e una lunga lista di correzioni
a menu e schermate. Tutto ciò che c'è nella 4.0 e nella 4.0.1 resta com'era; le carriere salvate con la 4.0 o la 4.0.1 si
caricano e si giocano (vedi "Da sapere").

### Novità

#### In primo piano
- **Grafica piena, sempre.** Il gioco partiva nella modalità grafica ridotta pensata per i PC lenti del 1996 quando il suo file
  delle impostazioni lo diceva: il file di fabbrica di GOG è fatto così, e lo stesso succede su un MiSTer lento.
  Risultato: grafica più povera, niente numeri 17-99 sopra la testa dei giocatori e giocatori con pelle scura e capelli biondi disegnati come un
  blocco di pixel. Ora il gioco parte sempre in grafica piena. Per la vecchia modalità ridotta avvia il gioco con `/H`.
  Anche nella modalità ridotta i due problemi sono corretti.
- **Le maglie vere di 227 squadre italiane.** Tutte le squadre italiane, dalla Serie A alla Serie D (227 squadre,
  controllate una per una), ora scendono in campo con le maglie vere della stagione 2026-27: prima e seconda maglia,
  colori di maglia, calzoncini e calzettoni. In Serie D molte squadre avevano colori provvisori: adesso sono quelli
  giusti. Fonti: i negozi ufficiali e le pagine delle squadre (Serie A-C), Wikipedia e gli archivi delle maglie (Serie D).
- **Malen non è più biondo** (Donyell Malen, Roma): il gioco non ha teste calve, quindi ha i capelli scuri, l'aspetto
  più vicino. Il "mucchio di pixel" che compariva al suo posto in partita è corretto (era la modalità grafica ridotta,
  vedi sopra).

#### Rose più grandi e acquisto degli extra degli altri club
- **Rose più grandi.** Nella carriera Mondo 2026-27 il club che gestisci parte con fino a 30 giocatori reali (i 16
  del suo record più fino a 14 altri, i successivi del club), invece di 16 più 10 riserve inventate. I club del
  computer giocano ancora con 16. Gli extra non sono mai più forti del più debole dei 16 del club e sono pagati come
  le riserve (66%) finché non vengono ceduti. Il limite del gioco resta 30: un club che parte con 30 giocatori deve
  vendere prima di poter comprare.
- **Acquisto degli extra degli altri club.** Il mercato nazionale può ora proporre giocatori dal 17° al 30° degli
  altri club, con prezzo e stipendio della scala del mod. Quando ne compri uno entra nella tua rosa e non si può
  comprare una seconda volta nella stessa carriera.
- **Vedere le rose complete degli altri club.** Quando guardi un club per comprare, una seconda pagina (il pulsante
  accanto a ESCI) elenca i suoi giocatori extra. In STAT, VIS. SQUADRE (la vista rosa) mostra ora anche la rosa
  completa di un club, con un pulsante PAG. SUCC. per la pagina degli extra. Servono solo per guardare: il club del
  computer gioca ancora con i suoi 16.

#### Comandi
- **Un menu COMANDI dentro il gioco.** In OPZIONI c'è ora un pulsante COMANDI / CONTROLS / COMMANDES / STEUERUNG (tra
  ESCI A DOS ed ESCI). Lì scegli i controlli (solo tastiera, joypad 1 + tastiera 2, tastiera 1 + joypad 2, due joypad),
  imposti ogni tasto premendolo (un tasto già usato viene rifiutato, ESC tiene il vecchio), calibri i joypad (leva al
  centro, poi tutti gli angoli, con una riga di prova dal vivo) e salvi: la scelta viene scritta nel SETUP.DAT del
  gioco. Se non c'è nessun joypad collegato il gioco continua con la tastiera. Con SWOS++ il pulsante non c'è.
- **Joypad in modalità tastiera (GOG).** Per i joystick che nei menu vanno ma in partita vanno solo in su e a sinistra
  (joystick a due assi senza croce direzionale): la pagina di installazione ha una terza spunta, "Versione GOG, joypad in
  modalità tastiera", disattivata di default e da usare insieme alla prima. Leva, croce e pulsanti diventano i tasti
  freccia e Ctrl; nessuna calibrazione, va con qualsiasi joystick o joypad, e joypad e tastiera comandano tutti e due il
  giocatore 1. Togli la spunta e rifai l'installazione per tornare al joypad calibrato.
- **Modifica i numeri di maglia.** Nella schermata della squadra prima della partita, premi SINISTRA su un tuo giocatore
  per accendere il suo numero: SU / GIÙ passano al numero libero successivo / precedente da 1 a 99, oppure scrivi le cifre
  (un numero già usato viene scambiato con chi lo ha); FUOCO, INVIO, SINISTRA o DESTRA confermano, ESC annulla. Vale solo
  per la tua squadra. La prima modifica dà a ogni giocatore della squadra un numero suo; da quel momento la squadra tiene i
  suoi numeri (niente 12-16 automatici in panchina, niente scambi di numeri, i nuovi arrivati prendono un numero libero).
  Carriere e stagioni salvano i numeri; in un'amichevole durano per la sessione.
- **Numeri a due cifre** disegnati bene nel campo tattico e nell'elenco della panchina in partita (il numero finisce
  in una colonna, lontano dall'icona del volto, e il nome comincia un po' più a destra).
- **Il numero sopra la testa del giocatore.** Alcuni giocatori in partita non avevano il numero sopra la testa, anche
  quando li controllavi, soprattutto su GOG e su MiSTer. Era un problema di avvio del gioco: il gioco lasciava non azzerata
  una parte della sua memoria e solo DOSBox-X la azzera da sé. Ora il gioco la azzera. Nella modalità grafica ridotta
  (`/H`) i numeri 17-99 vengono disegnati comunque.

#### Coppe, tornei e campionati
- **Posti europei.** Un club che vince il campionato e la Conference League nella stessa stagione, e quindi ha già un posto in Champions
  League, tiene il posto in Champions League (prima finiva in Europa League e il suo posto in Champions veniva passato
  a un altro). Segnalato da Pietro.
- **CONCACAF Champions Cup:** una sfida in parità nel punteggio complessivo va ai gol in trasferta, poi ai supplementari
  (dove i gol in trasferta non contano più), poi ai rigori, come nella competizione vera del 2026. Le sfide di CAF
  Champions League e Confederation Cup che gioca il tuo club si decidono con i gol in trasferta e poi i rigori, come
  nel 2025-26.
- **Guatemala ed El Salvador** giocano la vera stagione 2026-27: due tornei, Apertura e Clausura, ciascuno un girone
  all'italiana andata e ritorno a 12 squadre, punti azzerati tra i due e una classifica annuale. Ogni torneo si chiude
  con la sua vera fase finale: spareggi 3ª-6ª e 4ª-5ª e semifinali in andata e ritorno (in caso di parità passa la
  meglio piazzata), poi la finale: in andata e ritorno in Guatemala, in gara unica in campo neutro in El Salvador, con
  supplementari e rigori. Dichiarato: il calendario della Clausura ripete quello dell'Apertura con casa e trasferta
  invertite (le date vere del 2027 non sono ancora uscite); a parità di punti nella fase regolare vale l'ordine del
  gioco (differenza reti, gol fatti).
- **Paraguay** gioca la vera stagione 2026: Apertura e Clausura, 22 giornate ciascuno, andata e ritorno, sul calendario
  vero, la Clausura da zero punti. Ogni torneo lo vince la prima della classifica. A pari punti decidono i punti negli
  scontri diretti tra le squadre interessate, poi la differenza reti negli scontri diretti, la differenza reti e i gol;
  uno spareggio in campo neutro solo se le squadre restano pari su tutto. Dichiarato: tre o più squadre pari in testa:
  niente sorteggio, l'ordine della classifica dopo quei criteri; nessuna retrocessione (una sola divisione nel mondo).
- **Messico: il titolo giusto su ogni schermata.** Le classifiche e i calendari della Liga MX e della Liga de Expansión
  hanno il titolo del torneo in corso (LIGA MX APERTURA, poi LIGA MX CLAUSURA; MX APERTURA / MX CLAUSURA nel calendario).
- **La pagina VINCITORI.** Per i play-off che decidono il titolo nel tuo campionato (per esempio i play-off della Liga 1
  peruviana o il CAMPEONATO URUGUAYO) ora c'è la scritta DA GIOCARE finché la fine della stagione non lo decide, invece
  di lasciare la riga fuori. In Uruguay e in Perù il campione viene indicato appena una squadra guida sia l'Apertura sia
  la Clausura (allora non c'è play-off).
- **Play-off di Serie D.** La pagina FORMULA dei gironi di Serie D e quella del play-off ora dicono chiaramente che i
  play-off di girone decidono solo i piazzamenti e non danno la promozione (un utente che li aveva vinti due volte si
  aspettava di salire).

#### Menu e schermate
- **Pulsanti dei club nelle liste.** Nella scelta della squadra in carriera e nell'elenco squadre del mercato, i pulsanti con i nomi
  delle squadre di Serie D comparivano con colori diversi a caso. Ora hanno tutti il loro colore normale.
- **VISUALIZZA MONDO** nei mondi storici (Mondo 2026-27, Europa 1984-85, 1996-97) si apre direttamente sui continenti (o sulle
  nazioni) del mondo, senza il menu da una sola voce.
- **Nomi dei salvataggi.** Un salvataggio chiamato CON, NUL, PRN, AUX, COM1, LPT1 e simili (con o senza estensione)
  scriveva nel dispositivo DOS: nessun file, e la carriera era persa. Ora il gioco rifiuta il nome con un messaggio (NOME
  FILE NON VALIDO / INVALID FILENAME / NOM DE FICHIER INVALIDE / DATEINAME NICHT ERLAUBT) e torna alla finestra di salvataggio.
- **Menu STATISTICHE.** Tornando da FORMULA o VINCITORI il menu non cambia più (prima comparivano voci in più e una
  pagina vuota 'NESSUNA DESCRIZIONE').
- **Correzioni ai dati (Mondo 2026-27).** Il club AMERICA PE e TREFELIN B & G hanno il nome giusto, 22 coppie di club con lo
  stesso nome sono distinte, e 105 club che non avevano l'allenatore ora ce l'hanno. Mancano ancora gli allenatori di altri
  club (El Salvador, Brasile, Australia, Italia, Suriname, Taipei Cinese).

### Da sapere
- **Salvataggi.** Le carriere salvate con la 4.0 o la 4.0.1 si caricano e si giocano. Una carriera salvata con la 4.0.2 il
  cui mercato elenca un giocatore dal 17° al 30° di un altro club, o in cui ne hai comprato uno, si carica solo con la
  4.0.2 o successive (le versioni precedenti leggerebbero il giocatore nel posto sbagliato).
- **Turni preliminari europei.** Se il tuo club scende dai preliminari di Champions League a quelli di Conference League (o
  di Europa League), il calendario mostra anche i turni già giocati con il nome della nuova coppa (per esempio "PRELIM. ECL"
  per il primo turno). Sbagliata è solo l'etichetta: sorteggio, avversari e posti guadagnati sono giusti. Sarà corretto
  nella 4.0.3.
- **Previsto per la 4.0.3:** un elenco di nazionalità per gli allenatori di ogni mondo, e i giocatori calvi.
- **Grafica ridotta:** la modalità ridotta c'è solo su richiesta (`/H`); su un PC lentissimo `/F` e la regola della poca
  memoria funzionano come prima.

### Dichiarato, come nella 4.0.1
Erano annunciati per la 4.0.2 nelle note della 4.0.1 e **non** sono in questa versione; restano come descritti lì.
- **AFC Challenge League** (gironi) e **AFC Champions League Elite** (fase a girone unico): ancora simulati (il tuo club
  entra ai quarti / nella fase a eliminazione).
- **Calendari non ancora pubblicati** (la Clausura 2027 di Messico, Costa Rica, Honduras e Panama, e le ultime giornate di
  Perù, Colombia e Uruguay): ripetono le partite della prima metà con casa e trasferta invertite.
- **I cuadrangulares della Colombia:** l'ordine vero delle partite dei gironi e lo spareggio col piazzamento della stagione
  regolare.
- **Sfide a gara unica** finite in parità (per esempio la finale della Copa do Brasil): supplementari prima dei rigori,
  mentre la regola vera va direttamente ai rigori.
- **Elenco di gestione:** per una stagione in cui il tuo club è uscito in un turno preliminare europeo, mostra la
  competizione preliminare con 'FINALISTA' invece del turno.
- **Gironi di Serie D con un numero dispari di squadre:** se il tuo club riposa all'ultima giornata, la sua Poule Scudetto
  o il play-off di girone si decidono per simulazione.
- **Copa Libertadores / Sudamericana:** i turni che arrivano dopo la fine del campionato nazionale (la Sudamericana dopo lo
  spareggio, gli ottavi di una prima o seconda di girone a febbraio) vengono simulati a fine stagione.

### Ringraziamenti
Grazie a Pietro per la segnalazione sulla Champions League che ha portato alla correzione dei posti europei, a Marco per
il joypad in modalità tastiera e i numeri di maglia, e a tutti quelli che hanno scritto una segnalazione dal sito.
