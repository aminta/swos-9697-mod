<!-- DRAFT 4.0.6 (Note session, 02/11). Items marked [TO COMPLETE: owner] wait for the owner's text. Not merged, not published. -->

## English

**SWOS 96/97 Mod 4.0.6**

4.0.6 is a round of requests from players: **two players on one keyboard**, the computer's clubs now get red cards and injuries like you do, shirt numbers you can edit on the squad screen, an easier install (new patcher button and clearer messages), more realistic club finances, a smarter training match, and a good number of fixes. Everything in 4.0 to 4.0.5 stays as it was; careers saved with those versions load and play on.

### What's new

#### Two players on one keyboard
- **CONTROLS: new device "P1 AND P2 ON KEYBOARD".** Two people can now play on the same keyboard. Player 2 has a second set of keys, by default **W / S / A / D** to move and **left SHIFT** to fire; you can change them in OPTIONS > CONTROLS like the first set, and they are saved in a file of their own (CONTROL2.DAT). Player 1 keeps his usual keys.
- Good to know: many keyboards cannot read too many keys pressed at once (this is called *ghosting*: the keyboard "forgets" a key when several others are held down). If a direction or the fire key does not answer when both players press a lot at once, choose other keys for player 2 that are far from player 1's.
- With SWOS++ this device is not offered (SWOS++ has its own controls).

#### The computer's clubs play by the same rules as you
- **Two new OPTIONS rows, both ON by default:** the computer's clubs now get **red cards** (a sent-off player is suspended, like yours) and **injuries** (an injured player of a computer's club misses the following matches instead of being fit again at once). Turn a row OFF to get the original game behaviour back.
- Under SWOS++ the two rows are hidden and the original behaviour applies.

#### Continental cups page (World 2026-27)
In a 2026-27 career, VIEW COMPETITIONS has a new entry, CONTINENTAL CUPS. It shows how the other continents' club
cups are going: the Copa Libertadores and the other CONMEBOL cups, CONCACAF, AFC, CAF, OFC and FIFA. Pick a
confederation to see its cups. If your club plays in one of them, its confederation is listed first.

- Each cup shows its holder, then its rounds in calendar order.
- In a knockout round, the club that went through is shown in brackets, e.g. CARABOBO - (FLAMENGO).
- A group shows its clubs in their final order once it has been played.
- A round that has not been played yet says TO BE PLAYED. Rounds only appear once their draw is due in the
  season, so the page never gives away what is still to come.
- The page lists who went through, not the scores.
- In the first season of a career, the early qualifying rounds were played before your career began. They show as
  one line, EARLIER ROUNDS PLAYED BEFORE THE SEASON, and the page starts from the main round's draw.
- Opening the page changes nothing in your career. Careers saved with 4.0.5 load and show the page as normal.

#### Super Cups and intercontinental cups (World 2026-27)
- **UEFA Super Cup.**
  - It is played in mid-August (week of 12 August), before the national Super Cup: the Champions League winner against the Europa League winner of the season just ended.
  - One match on neutral ground. If it is level after 90 minutes, it goes straight to penalties (no extra time, as in the real one since 2025).
  - If the same club won both cups, its opponent is the Conference League winner. If there is no other winner, the match is not played.
  - It starts from the second season: in the world's first season the real 2026 edition has already been played.
  - You play it when your club is one of the two. It is in the calendar and in the season record.
  - Its rules are on the Champions League's FORMAT page.
- **Recopa Sudamericana** moves to February, as the real one. Two legs, with the Libertadores champion at home in the second. If the tie is level on aggregate: extra time, then penalties (2026 edition: Lanús won in Rio after extra time).
- **CAF Super Cup** moves to October, as the 2025 edition. One match on neutral ground, straight to penalties.
- **FIFA Intercontinental Cup.** The Derby of the Americas (the Libertadores winner against the CONCACAF champion) moves to December, as the real one, followed by the Challenger Cup and the final. The play-off stays at the end of August and the Africa-Asia-Pacific Cup in September.

#### Stoppage time
- **Stoppage time (an idea of Davide and Marco):** every half now has real added time. At 45:00 and 90:00 the clock stops and a "+N" appears next to it, like the fourth official's board: N added minutes, more when the half had goals, substitutions and cards (in the World 2026-27 career also the time lost with the ball out of play, as in today's football) - at most 3 in the 1996-97 game (2 in the first half), 5 in the World 2026-27 career (3 in the first half), 2 in the Europe 1984-85 career (1 in the first half); each extra-time half gets 1. The historic seasons and tournaments before 1970 (Italy 1947-48, World Cup 1934) give at most 1 and often none, as in those days. The added minutes always run at the pace of a 10-minute match, whatever match length you chose, so they can really be played: about 15 seconds of play for +3 and 26 for +5 (in a 3-minute match +3 would otherwise be gone in under 5 seconds). As always the clock stops when the ball is out of play, and when the added time is over the referee still lets a running attack finish. A goal in added time shows as 45+2 or 90+3 in the scorers' list. Not with SWOS++.

#### Two-row benches in the match
- **Two-row benches.** With a long bench (more than 5 substitutes) every substitute now has a seat: the coach and substitutes 1-7 sit in the back row, substitutes 8-15 in the front row. The dugouts are a little longer and wider to make room, on every pitch and in 16-colour mode too.
- **Both benches in view.** When you call your bench, the camera stops at the halfway line, so you see your own bench and your opponent's together, top to bottom.
- The cursor arrow follows you onto the front row (it points the other way there). A player you pick from the back row stands up in front of the front row, so nobody walks through his team-mates.
- **The match clock steps aside.** While the bench is open, the clock moves to the top right, next to the spinning S, so it no longer covers the coach and the first seats. It goes back to its place when you close the bench.
- Fixed a bug of the original game: when you called the bench with the ball in the top half of the pitch, the bench sometimes ignored the cursor keys and you couldn't pick anyone. The camera now settles properly and the bench always responds.
- Training matches keep the original one-row bench and clock.

#### Long benches: scrolling as in the original game
- **Long benches** (thanks to Marco): the player lists scroll as in the original game again.
  - Moving the cursor up and down the names never scrolls the list.
  - DOWN on the last name goes straight to the entry below. In a career that is the coach line (PLAY :), then PLAY MATCH. On the club squad screen it is the buttons; in the tactics editor, its own button.
  - To see the other substitutes, put the cursor on the face next to the last player and press FIRE. Each press shows the next one, and after the last it starts again from the top.
  - A player you have picked stays picked while you browse.
  - Same on the pre-match screen, the club squad screen, the tactics editor, the squad view and the national team call-ups.
  - VIEW OPPONENT is unchanged: there UP / DOWN still browse the opponent's substitutes (you can only look).
  - On the pre-match screen the cursor goes from the last substitute to the coach/player choice, then to PLAY MATCH, as in the original game (thanks to Marco). The original UP move from EXIT and LEFT move from the columns are back too [TO COMPLETE: exact wording from Panchina].

#### Training, squad and market
- **Training games: bench and kits** (thanks to Marco). Training games (career, squad screen > TRAINING) have the game's own rule again: 2 substitutes from 2 on the bench. In 4.0.5 a training game took the bench of your current league: at a Serie A club the dugout showed 5 players a team, and the training squad screen had a bench of 12. Your next real match has the full league bench again.
  - In a training game both teams are your club, so SELECT KITS lists them as "ROMA A" and "SQUADRA B". They now keep their own kits: team A in the kit you pick for A, team B in the kit you pick for B. Before, both teams wore team A's choice.
  - In a training game SELECT KITS hides the "this match only / always" choice, and your club's saved kits are never changed by a training game.
- **Shirt numbers on the squad screen.** You can now edit your club's shirt numbers on the squad screen too, as you already could on the team screen before a match: press LEFT on a player, then UP / DOWN or type the number; ESC cancels. The number no longer touches the player's name, and its shadow shows.
- **Transfer market keeps its place** (reported by Enzo). When you look at a player in the national or foreign market list (MAKE OFFER) and come back with EXIT, the list stays on the page you were on, with the cursor on that player, instead of jumping back to the first page.

#### Looks
- **White hair for Ravanelli** (1996-97): his famous white hair is now white. More players can be added to the list in the future.

#### An easier install (thanks to Roman)
- **Install into a new folder.** The patcher page has a second button, "Install into a new folder (Program Files, CD)". First pick the game's folder: your GOG install, a copy on disk, or the CD. Then pick (or create) an empty folder of your own outside Program Files, for example Documents\SWOS 96-97 Mod. The page copies the game there and installs the mod in the copy. The original game is not touched. Play from the new folder: the GOG shortcut still starts the original game.
  - Why: Windows does not let a web page write inside Program Files or on a CD. This was the most common reason an install failed.
- **Clearer messages.** When something goes wrong, the page now says what happened and what to do:
  - The wrong folder: which files it looks for (ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE or GERMAN.EXE, and the DATA folder with TEAM.020). It also looks inside subfolders.
  - A folder it cannot write to (Program Files, a CD): nothing was changed; use the second button.
  - A system folder Chrome refuses: choose the game's own folder, or use the second button.
  - A new folder that is not empty, or that is inside the game folder: choose an empty folder elsewhere.
  - An install stopped half-way: nothing is lost. Choose the same folder again and the page finishes the job. To go back, the replaced files are in MOD_BACKUP.
- All messages in Italian, English, French and German.

#### Club finances closer to real football (thanks to Nicola)
Nicola noticed that in a career with a big club you end every season deep in the red, even winning everything, and
have to sell players to stay afloat. That is how the original game works:
- **What the original charged.** At every match the club pays its players' wages and the club's *running costs*.
  The game sets the running costs at the start of each season to about 3.2 times the wage bill, so a club
  really pays about **4.2 times its wages**. A star squad has big wages, so it pays a lot.
- **What the original paid in.** Gate receipts (based on your league position, not on the size of the club), the
  prize money at the end of the season, and now and then a small random sponsorship. None of these grows with
  the club: in our tests the gate per match of Manchester City and of Brentford was about the same.
- **The result.** In the World 2026-27, where today's squads cost what they cost today, a big club lost
  10 to 20 million a season (Real Madrid -16.9 M, Manchester City -18.5 M, Inter -10.9 M in the first season),
  while a small club's books stayed roughly level.

**What 4.0.6 changes.** With every match charge, your club now also receives its share of the season's
**TV and commercial income**:
- a **base** that depends on the division: 3.0 M a season in the top division, 1.2 M in the second, 0.5 M in the
  third, 0.2 M in the fourth and below (a division played in parallel groups, such as Serie C or Serie D,
  counts as one level);
- plus **1.1 times your season's wage bill**: a bigger club earns more from TV and sponsors.
The money arrives a little at a time, with each match charge, and shows under SPONSORSHIP on the finance screen.
Expenses are exactly as in the original game.

Why it is closer to real football:
- In the big European leagues wages typically take well over half of a club's revenue (a general real-world figure, not something we measured): income that grows with the payroll
  (1.1 times the wages, on top of the gate and the prizes) puts a well-run club in that range.
- TV and commercial income grow with the size of the club. Domestic TV money, by contrast, is shared fairly evenly
  within a division, and that is the base by division.
- Clubs receive this money in instalments during the season, not in one lump. So you can't spend it all on the
  first day of the transfer market.

**The stadium bug.** The gate receipts of a single match were stored in a number that could not go above about
1.05 million. Above that, the count started again from zero, so a bigger crowd could pay much less than a smaller
one. It could happen to a club with a cheap squad and a big crowd, because the game divides the gate by the
squad's average price. Now a gate stops at its maximum instead.

What it looks like in a career (World 2026-27, first two seasons, a club that wins its matches):
| Club (division) | 4.0.5: start / end of season 1 / end of season 2 (lowest) | 4.0.6: start / end of season 1 / end of season 2 (lowest) |
|---|---|---|
| Real Madrid (LaLiga) | 7.9 / -9.0 / -32.3 M (-34.4) | 10.4 / 15.3 / 10.3 M (3.5) |
| Manchester City (Premier League) | 9.2 / -9.2 / -22.1 M (-27.9) | 7.8 / 5.2 / 7.8 M (-3.0) |
| Inter (Serie A) | 6.1 / -4.8 / -15.5 M (-18.5) | 6.2 / 3.8 / -0.1 M (-1.9) |
| Brentford (Premier League) | 5.6 / 2.5 / -2.9 M (-4.6) | 4.9 / 6.7 / 5.3 M (3.6) |
| Ligorna (Serie D) | 0.29 / -0.14 / -0.43 M (-0.58) | 0.33 / 0.84 / 1.15 M (0.32) |
| Catania (Serie C) | - | 0.61 / 0.35 / 0.89 M (0.07) |
(The starting balance is set by the game and varies a little from career to career.)

Old careers: nothing is stored in the save. A career started with an older version gets the new income from its
next match.

#### Coming in this version, text to come
- **The opponent's squad during a match**. During a match you can now look at the opponent's squad. Open the bench menu (where you make substitutions), put the cursor on your coach and press UP. The list shows the opponent's name on top, in their colours.
  - The first page shows their 11 players on the pitch. Press DOWN for their substitutes, 11 a page, and UP to go back a page.
  - The list is read-only: you cannot pick or change anything in it. FIRE, LEFT or RIGHT closes it, and the cursor goes back to your coach.
  - With SWOS++ the list is switched off: UP on the coach works as before.
- [TO COMPLETE: Motore — B-team call-ups: one match and season attachment, real rules per country, ages.]

#### Fixes
- **New Zealand, last round of the Championship group.** If your club rests in the last round of the Championship group, the menu now offers FINISH SEASON. Press it: if your club reached the Grand Final, MATCH comes back and you play it; otherwise the season ends. (Before, the menu could offer a match on the rest day.) The real champion was already right; this removes the confusing final that did not count mentioned in the 4.0.5 notes.
- **Buying a club's extra squad players** (thanks to Enzo). Fixed: after taking over a club, a player you had bought from it (one of its extra squad players) could reappear in its squad, so he was in two clubs at once. Fixed: buying one of another club's extra squad players (players 17 to 30) could make the career crash at the start of a later season, or spoil another club's squad. Careers saved with 4.0.2 to 4.0.5 play on safely.
- **A play-off entrant that refuses the place** no longer makes the game read wrong data at the season end (it showed up with San Marino; found by Ben Baker).

### Good to know
- [TO COMPLETE when the items above are final: declared limits, list of what is off under SWOS++.]

### Thanks
Thanks to Roman for asking for an easier install, to Marco for the training, shirt-number and keyboard ideas, to Enzo for the market-list report, to Nicola for the finance report, to Francesco, and to Ben Baker for the San Marino report. [TO CHECK: exact credits per item with the owners.]

## Italiano

**SWOS 96/97 Mod 4.0.6**

La 4.0.6 è un giro di richieste dei giocatori: **due giocatori sulla stessa tastiera**, le squadre del computer ora subiscono espulsioni e infortuni come te, i numeri di maglia modificabili anche nella schermata della rosa, un'installazione più facile, finanze dei club più realistiche, un allenamento più furbo e diverse correzioni. Tutto ciò che c'è dalla 4.0 alla 4.0.5 resta com'era; le carriere salvate con quelle versioni si caricano e si giocano.

### Novità

#### Due giocatori sulla stessa tastiera
- **COMANDI: nuovo dispositivo "G1 E G2 SU TASTIERA".** Due persone possono giocare sulla stessa tastiera. Il giocatore 2 ha un secondo gruppo di tasti, di default **W / S / A / D** per muoversi e **MAIUSC sinistro** per il fuoco; si cambiano in OPZIONI > COMANDI come il primo gruppo e si salvano in un file a parte (CONTROL2.DAT). Il giocatore 1 tiene i suoi tasti di sempre.
- Da sapere: molte tastiere non riescono a leggere troppi tasti premuti insieme (si chiama *ghosting*: la tastiera "dimentica" un tasto quando ne sono premuti molti altri). Se una direzione o il fuoco non risponde quando i due giocatori premono tanto insieme, scegli per il giocatore 2 altri tasti lontani da quelli del giocatore 1.
- Con SWOS++ questo dispositivo non c'è (SWOS++ ha i suoi comandi).

#### Le squadre del computer giocano con le tue regole
- **Due nuove righe in OPZIONI, entrambe attive di default:** le squadre del computer ora prendono **cartellini rossi** (un espulso è squalificato, come i tuoi) e **infortuni** (un infortunato di una squadra del computer salta le partite seguenti invece di essere subito di nuovo a posto). Metti una riga su NO per riavere il comportamento originale del gioco.
- Con SWOS++ le due righe sono nascoste e vale il comportamento originale.

#### Pagina COPPE CONTINENTALI (Mondo 2026-27)
Nelle carriere del mondo 2026-27, VISUAL. COMPETIZ. ha una nuova voce: COPPE CONTINENTALI. Mostra come vanno le
coppe per club degli altri continenti: la Copa Libertadores e le altre coppe CONMEBOL, CONCACAF, AFC, CAF, OFC e FIFA.
Scegli una confederazione per vedere le sue coppe. Se il tuo club gioca in una di queste coppe, la sua
confederazione è la prima della lista.

- Per ogni coppa: il detentore, poi i turni in ordine di calendario.
- Nei turni a eliminazione diretta, chi passa il turno è tra parentesi, per esempio CARABOBO - (FLAMENGO).
- Un girone già giocato mostra le squadre nell'ordine della classifica finale.
- Un turno non ancora giocato è indicato DA GIOCARE. I turni compaiono solo quando, nella stagione, arriva il loro
  sorteggio: la pagina non anticipa mai quello che deve ancora succedere.
- La pagina dice chi è passato, non i punteggi.
- Nella prima stagione di una carriera, i turni preliminari si sono giocati prima che la carriera iniziasse.
  Compaiono come una sola riga, TURNI PRECEDENTI GIOCATI PRIMA DELLA STAGIONE, e la pagina parte dal sorteggio del
  turno principale.
- Aprire la pagina non cambia niente nella carriera. Le carriere salvate con la 4.0.5 si caricano e mostrano la
  pagina normalmente.

#### Supercoppe e coppe intercontinentali (Mondo 2026-27)
- **Supercoppa UEFA.**
  - Si gioca a metà agosto (la settimana del 12 agosto), prima della Supercoppa nazionale: la vincitrice della Champions League contro la vincitrice dell'Europa League della stagione appena finita.
  - Gara unica in campo neutro. In parità dopo 90 minuti si va subito ai rigori (niente supplementari, come nella vera dal 2025).
  - Se la stessa squadra ha vinto entrambe le coppe, l'avversaria è la vincitrice della Conference League. Se manca anche questa, la partita non si gioca.
  - Parte dalla seconda stagione: nella prima stagione del mondo l'edizione vera 2026 è già stata giocata.
  - La giochi se la tua squadra è una delle due. È nel calendario e nel registro della stagione.
  - Le regole sono nella pagina FORMAT della Champions League.
- **Recopa Sudamericana** passa a febbraio, come la vera. Andata e ritorno, con la campione della Libertadores in casa al ritorno. In parità nel totale: supplementari, poi rigori (edizione 2026: il Lanús ha vinto a Rio ai supplementari).
- **Supercoppa CAF** passa a ottobre, come l'edizione 2025. Gara unica in campo neutro, subito rigori.
- **Coppa Intercontinentale FIFA.** Il Derby delle Americhe (la vincitrice della Libertadores contro la campione CONCACAF) passa a dicembre, come quello vero, seguito dalla Challenger Cup e dalla finale. Il play-off resta a fine agosto e la Coppa Africa-Asia-Pacifico a settembre.

#### Recupero
- **Recupero (un'idea di Davide e Marco):** ogni tempo ora ha il suo recupero vero. A 45:00 e a 90:00 l'orologio si ferma e accanto compare "+N", come il cartello del quarto uomo: N minuti di recupero, di più se nel tempo ci sono stati gol, sostituzioni e cartellini (nella carriera Mondo 2026-27 anche il tempo perso a palla non in gioco, come nel calcio di oggi) - al massimo 3 nel gioco 1996-97 (2 nel primo tempo), 5 nella carriera Mondo 2026-27 (3 nel primo tempo), 2 nella carriera Europa 1984-85 (1 nel primo tempo); ogni tempo supplementare ne ha 1. Le stagioni e i tornei storici prima del 1970 (Italia 1947-48, Mondiali 1934) danno al massimo 1 minuto, spesso nessuno, come allora. I minuti di recupero scorrono sempre al ritmo di una partita da 10 minuti, qualunque durata tu abbia scelto, così si giocano davvero: circa 15 secondi di gioco per +3 e 26 per +5 (in una partita da 3 minuti +3 durerebbe meno di 5 secondi). Come sempre l'orologio si ferma a palla non in gioco, e finito il recupero l'arbitro lascia comunque finire l'azione in corso. Un gol nel recupero compare come 45+2 o 90+3 nell'elenco dei marcatori. Non con SWOS++.

#### Panchine su due file in partita
- **Panchine su due file.** Con una panchina lunga (più di 5 riserve) ogni riserva ha il suo posto: l'allenatore e le riserve 1-7 nella fila dietro, le riserve 8-15 nella fila davanti. Per fare spazio i dugout sono un po' più lunghi e larghi, su tutti i campi e anche nella modalità a 16 colori.
- **Tutte e due le panchine in vista.** Quando chiami la panchina la telecamera si ferma sulla linea di metà campo: vedi insieme la tua panchina e quella degli avversari, dall'alto in basso.
- La freccia del cursore ti segue anche sulla fila davanti (lì punta dall'altra parte). Il giocatore scelto dalla fila dietro si alza davanti alla fila anteriore, senza passare in mezzo ai compagni.
- **L'orologio si sposta.** Con la panchina aperta il tempo di gioco va in alto a destra, accanto alla S che gira, così non copre più l'allenatore e i primi posti. Quando chiudi la panchina torna al suo posto.
- Corretto un difetto del gioco originale: se chiamavi la panchina con la palla nella metà campo in alto, a volte la panchina non rispondeva ai tasti del cursore e non potevi scegliere nessuno. Ora la telecamera si ferma bene e la panchina risponde sempre.
- Le partite di allenamento mantengono la panchina e l'orologio originali, su una sola fila.

#### Panchine lunghe: si scorre come nel gioco originale
- **Panchine lunghe** (grazie a Marco): gli elenchi dei giocatori tornano a scorrere come nel gioco originale.
  - Muovere il cursore su e giù sui nomi non fa più scorrere l'elenco.
  - GIÙ sull'ultimo nome va subito alla voce sotto. In carriera è la riga dell'allenatore (GIOCA :), poi GIOCA PARTITA. Nella rosa del club sono i pulsanti; nell'editor tattico, il suo pulsante.
  - Per vedere le altre riserve si mette il cursore sulla faccina accanto all'ultimo giocatore e si preme FUOCO. A ogni pressione compare la riserva successiva, e dopo l'ultima si riparte dall'inizio.
  - Il giocatore già selezionato resta selezionato mentre si scorre.
  - Vale per la schermata prepartita, la rosa del club, l'editor tattico, la visualizzazione della rosa e le convocazioni della nazionale.
  - VISUALIZZA AVVERSARIO non cambia: lì SU / GIÙ scorrono ancora le riserve avversarie (si può solo guardare).
  - Nella schermata prima della partita il cursore passa dall'ultima riserva alla scelta allenatore/giocatore, poi a GIOCA PARTITA, come nel gioco originale (grazie a Marco). Tornano anche il movimento originale SU da ESCI e SINISTRA dalle colonne [DA COMPLETARE: formulazione esatta da Panchina].

#### Allenamento, rosa e mercato
- **Allenamento: panchina e maglie** (grazie a Marco). Le partite di allenamento (carriera, schermata della rosa > PRATICA) tornano alla regola del gioco: 2 sostituti su 2 in panchina. In 4.0.5 l'allenamento prendeva la panchina del tuo campionato: con un club di Serie A la panchina mostrava 5 giocatori per squadra e la schermata della rosa in allenamento una panchina da 12. La partita vera successiva ha di nuovo la panchina intera del campionato.
  - In allenamento le due squadre sono entrambe il tuo club, e MAGLIE le mostra come "ROMA A" e "SQUADRA B". Ora ognuna tiene le sue maglie: la squadra A quella scelta per A, la squadra B quella scelta per B. Prima entrambe vestivano la scelta della squadra A.
  - In allenamento MAGLIE nasconde la scelta SOLO PARTITA / SEMPRE, e le maglie salvate del tuo club non vengono mai cambiate da una partita di allenamento.
- **Numeri di maglia nella schermata della rosa.** Ora puoi modificare i numeri di maglia del tuo club anche nella schermata della rosa, come già potevi nella schermata della squadra prima della partita: premi SINISTRA su un giocatore, poi SU / GIÙ o scrivi il numero; ESC annulla. Il numero non tocca più il nome del giocatore e se ne vede l'ombra.
- **Il mercato ricorda la pagina** (segnalato da Enzo). Quando guardi un giocatore nell'elenco del mercato nazionale o estero (FAI OFFERTA) e torni con ESCI, l'elenco resta sulla pagina in cui eri, con il cursore su quel giocatore, invece di tornare alla prima pagina.

#### Aspetto
- **Capelli bianchi per Ravanelli** (1996-97): i suoi famosi capelli bianchi ora sono bianchi. In futuro si potranno aggiungere altri giocatori all'elenco.

#### Installazione più semplice (grazie a Roman)
- **Installa in una cartella nuova.** La pagina del patcher ha un secondo pulsante, «Installa in una cartella nuova (Program Files, CD)». Prima si sceglie la cartella del gioco: l'installazione GOG, una copia su disco o il CD. Poi si sceglie (o si crea) una cartella vuota propria fuori da Program Files, per esempio Documenti\SWOS 96-97 Mod. La pagina ci copia il gioco e installa la mod nella copia. Il gioco originale non viene toccato. Si gioca dalla cartella nuova: il collegamento GOG continua ad avviare il gioco originale.
  - Perché: Windows non permette a una pagina web di scrivere dentro Program Files o su un CD. Era il motivo più comune per cui l'installazione non riusciva.
- **Messaggi più chiari.** Quando qualcosa va storto, la pagina ora dice cosa è successo e cosa fare:
  - La cartella sbagliata: quali file cerca (ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE o GERMAN.EXE, e la cartella DATA con TEAM.020). Cerca anche nelle sottocartelle.
  - Una cartella in cui non può scrivere (Program Files, un CD): non è stato cambiato niente; usa il secondo pulsante.
  - Una cartella di sistema che Chrome rifiuta: scegli la cartella del gioco stessa, oppure usa il secondo pulsante.
  - Una cartella nuova non vuota, o dentro la cartella del gioco: scegli una cartella vuota altrove.
  - Un'installazione fermata a metà: non è perso niente. Scegli di nuovo la stessa cartella e la pagina finisce il lavoro. Per tornare indietro, i file sostituiti sono in MOD_BACKUP.
- Tutti i messaggi in italiano, inglese, francese e tedesco.

#### Conti dei club più vicini al calcio vero (grazie a Nicola)
Nicola ha notato un problema: in una carriera con un grande club si chiude ogni stagione in forte rosso, anche
vincendo tutto, e bisogna vendere giocatori per restare a galla. È il funzionamento del gioco originale:
- **Cosa addebitava l'originale.** A ogni partita il club paga gli stipendi dei giocatori e i *costi di gestione*.
  A inizio stagione il gioco fissa i costi di gestione a circa 3,2 volte il monte stipendi, quindi un club paga
  in tutto circa **4,2 volte gli stipendi**. Una rosa di campioni ha stipendi alti, quindi paga moltissimo.
- **Cosa incassava l'originale.** Gli incassi dello stadio (legati alla posizione in classifica, non alla
  grandezza del club), i premi di fine stagione e, ogni tanto, una piccola sponsorizzazione a caso. Nessuna di
  queste voci cresce con il club: nelle nostre prove il Manchester City e il Brentford incassavano più o meno lo
  stesso a partita.
- **Il risultato.** Nel Mondo 2026-27, dove le rose costano quanto costano oggi, un grande club perdeva da 10 a
  20 milioni a stagione: nella prima stagione Real Madrid −16,9 M, Manchester City −18,5 M, Inter −10,9 M. Un
  club piccolo invece restava più o meno in pari.

**Cosa cambia nella 4.0.6.** A ogni partita il tuo club riceve anche la sua quota degli **incassi da diritti TV e
sponsor** della stagione:
- una **base** che dipende dalla serie: 3,0 M a stagione nella massima serie, 1,2 M nella seconda, 0,5 M nella
  terza, 0,2 M dalla quarta in giù (una serie a gironi paralleli, come la Serie C o la Serie D, conta come un
  solo livello);
- più **1,1 volte il monte stipendi della stagione**: un club più grande guadagna di più da TV e sponsor.
I soldi arrivano un po' alla volta, partita dopo partita, e compaiono alla voce SPONSORIZZAZIONE nella schermata dei
conti. Le spese restano esattamente quelle del gioco originale.

Perché è più vicino al calcio vero:
- Nei grandi campionati europei gli stipendi assorbono di solito ben più della metà dei ricavi di un club (è una cifra generale del calcio vero, non misurata da noi). Un incasso che cresce
  con il monte stipendi (1,1 volte gli stipendi, oltre a stadio e premi) porta un club ben gestito in
  quell'ordine di grandezza.
- I ricavi da TV e sponsor crescono con la grandezza del club. I diritti TV nazionali invece si dividono in modo
  abbastanza uniforme tra i club della stessa serie: è la base per serie.
- I club ricevono questi soldi a rate durante la stagione, non tutti insieme. Quindi non si possono spendere tutti
  il primo giorno di mercato.

**Il difetto dello stadio.** L'incasso di una singola partita era conservato in un numero che non poteva superare
circa 1,05 milioni. Oltre quel limite il conto ripartiva da zero, quindi un pubblico più numeroso poteva rendere
molto meno di uno più piccolo. Poteva succedere a un club con una rosa economica e molto pubblico, perché il gioco
divide l'incasso per il prezzo medio della rosa. Ora l'incasso si ferma al massimo.

Come si vede in carriera (Mondo 2026-27, prime due stagioni, un club che vince le sue partite):
| Club (serie) | 4.0.5: inizio / fine stagione 1 / fine stagione 2 (minimo) | 4.0.6: inizio / fine stagione 1 / fine stagione 2 (minimo) |
|---|---|---|
| Real Madrid (LaLiga) | 7,9 / -9,0 / -32,3 M (-34,4) | 10,4 / 15,3 / 10,3 M (3,5) |
| Manchester City (Premier League) | 9,2 / -9,2 / -22,1 M (-27,9) | 7,8 / 5,2 / 7,8 M (-3,0) |
| Inter (Serie A) | 6,1 / -4,8 / -15,5 M (-18,5) | 6,2 / 3,8 / -0,1 M (-1,9) |
| Brentford (Premier League) | 5,6 / 2,5 / -2,9 M (-4,6) | 4,9 / 6,7 / 5,3 M (3,6) |
| Ligorna (Serie D) | 0,29 / -0,14 / -0,43 M (-0,58) | 0,33 / 0,84 / 1,15 M (0,32) |
| Catania (Serie C) | - | 0,61 / 0,35 / 0,89 M (0,07) |
(Il saldo iniziale lo fissa il gioco e varia un po' da una carriera all'altra.)

Carriere già iniziate: nel salvataggio non viene memorizzato niente. Una carriera iniziata con una versione
precedente riceve i nuovi incassi dalla partita successiva.

#### In arrivo in questa versione, testo da completare
- **La rosa dell'avversario durante la partita**. Durante la partita ora puoi vedere la rosa dell'avversario. Apri il menu della panchina (quello dei cambi), porta il cursore sull'allenatore e premi SU. In cima all'elenco c'è il nome della squadra avversaria, nei suoi colori.
  - La prima pagina mostra i loro 11 in campo. GIÙ mostra le loro riserve, 11 per pagina, e SU torna alla pagina prima.
  - L'elenco è in sola lettura: non si può scegliere né cambiare niente. FUOCO, SINISTRA o DESTRA lo chiudono, e il cursore torna sull'allenatore.
  - Con SWOS++ l'elenco è disattivato: SU sull'allenatore funziona come prima.
- [DA COMPLETARE: Motore — convocazioni dalla squadra B: una partita e aggregazione stagionale, regole vere per paese, età.]

#### Correzioni
- **Nuova Zelanda, ultima giornata del gruppo del Championship.** Se il tuo club riposa nell'ultima giornata del gruppo del Championship, il menu ora offre FINISCI STAGIONE. Premilo: se il tuo club è arrivato alla Grand Final torna PARTITA e la giochi; altrimenti la stagione finisce. (Prima il menu poteva offrire una partita nel giorno di riposo.) Il campione vero era già giusto; questo toglie la finale confusa che non contava, citata nelle note della 4.0.5.
- **Acquisto dei giocatori extra di una squadra** (grazie a Enzo). Corretto: prendendo una squadra, un giocatore che le avevi comprato (uno dei suoi giocatori extra della rosa) poteva ricomparire nella sua rosa, quindi in due squadre insieme. Corretto: comprare uno dei giocatori extra della rosa di un'altra squadra (dal 17° al 30°) poteva bloccare la carriera all'inizio di una stagione successiva o rovinare la rosa di un'altra squadra. Le carriere salvate con le versioni 4.0.2-4.0.5 proseguono senza problemi.
- **Una squadra di play-off che rifiuta il posto** non fa più leggere al gioco dati sbagliati a fine stagione (si vedeva con San Marino; trovato da Ben Baker).

### Da sapere
- [DA COMPLETARE a testi definitivi: limiti dichiarati, elenco di cosa è disattivato con SWOS++.]

### Ringraziamenti
Grazie a Roman per aver chiesto un'installazione più semplice, a Marco per le idee su allenamento, numeri di maglia e tastiera, a Enzo per la segnalazione sull'elenco del mercato, a Nicola per quella sulle finanze, a Francesco e a Ben Baker per la segnalazione su San Marino. [DA VERIFICARE: crediti esatti per voce con i proprietari.]
