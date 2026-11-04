<!-- DRAFT 4.0.6 (Note session, 02/11). Items marked [TO COMPLETE: owner] wait for the owner's text. Not merged, not published. -->

## English

**SWOS 96/97 Mod 4.0.6**

4.0.6 is a round of requests from players: **two players on one keyboard**, the computer's clubs now get red cards and injuries like you do, shirt numbers you can edit on the squad screen, an easier install (new patcher button and clearer messages), more realistic club finances, a smarter training match, and a good number of fixes. Everything in 4.0 to 4.0.5 stays as it was; careers saved with those versions load and play on.

### What's new

#### Two players on one keyboard
- **CONTROLS: new device "P1 AND P2 ON KEYBOARD".** Two people can now play on the same keyboard. Player 2 has a second set of keys, by default **W / S / A / D** to move and **left SHIFT** to fire; you can change them in OPTIONS > CONTROLS like the first set, and they are saved in a file of their own (CONTROL2.DAT). Player 1 keeps his usual keys.
- Good to know: many keyboards cannot read too many keys pressed at once (this is called *ghosting*: the keyboard "forgets" a key when several others are held down). If a direction or the fire key does not answer when both players press a lot at once, choose other keys for player 2 that are far from player 1's.
- With SWOS++ this device is not offered (SWOS++ has its own controls).
- **The keyboard is never blocked by the joypad.** When the controls are set to a joypad for player 1 and the keyboard for
  player 2 (the default when the patcher's "I have a joypad" is ticked), a joypad that is not centred - not calibrated,
  worn, or reading a corner - used to win over the keyboard: in the menus a direction held on the keyboard could do
  nothing (for example DOWN, with a stick leaning up). Now a direction held on the keyboard always counts, in the menus
  and for your team in a match, as long as nobody else is playing on the keyboard in that match. With KEYBOARD ONLY, TWO
  JOYPADS or SWOS++ nothing changes.

#### The computer's clubs play by the same rules as you
- **Two new OPTIONS rows, both ON by default:** the computer's clubs now get **red cards** (a sent-off player is suspended, like yours) and **injuries** (an injured player of a computer's club misses the following matches instead of being fit again at once). Turn a row OFF to get the original game behaviour back.
- Under SWOS++ the two rows are hidden and the original behaviour applies.
- **Goalkeepers get injured too.** In the original game a goalkeeper almost never gets injured. Now, after every
  match, each team's goalkeeper has a 1 in 25 chance of an injury. You see it afterwards, on the team screen, not
  during the match. He misses the next match or the next two, then he is fit again like any injured player. It is
  the goalkeeper on the pitch at the final whistle, and matches you only view the result of count too. The
  computer's goalkeepers get injured in every competition except friendlies, while CPU INJURIES is ON.
  In a DIY or preset competition the computer's injured and suspended players now get better after each match,
  like yours (before, they stayed out for the whole competition). To switch it off: OPTIONS > GOALKEEPER INJURIES
  (IT INFORTUNI PORTIERI, FR BLESSURES DES GARDIENS, DE TORWARTVERLETZUNGEN). It is ON by default and saved with
  the career; an older career loads it ON. Not with SWOS++.
#### Continental cups in the game's own screens (World 2026-27)
- **CONTINENTAL CUPS** (VIEW COMPETITIONS): pick a confederation and you get a menu of its rounds already drawn,
  in the order they are played. Each round opens in the game's own cup screen, exactly as far as your career has got:
  - knockout rounds with both legs, the aggregate, extra time, away goals and penalties;
  - group stages with their tables and the fixtures match day by match day (NEXT shows the next stage, as in any
    cup of the game).
  - **SUMMARY** shows all the confederation's cups on one text page, as before.
- **VIEW WORLD**: every continent now shows its continental cups as green buttons above its nations - SOUTH AMERICA
  the Libertadores, the Sudamericana and the Recopa, EUROPE the Champions League, Europa League and Conference League,
  WORLD the Intercontinental, and so on. A button opens the same menu of rounds for that cup.
- When the game's own screen can't show a round, you get the text page instead:
  - in the first season of a career;
  - for the AFC Champions League Elite league stage, a format the game's screens don't have;
  - in the rare cases where it couldn't be shown safely (too many clubs loaded at once, a club missing from the data).
- Looking at the cups never changes your career or its save: everything is put back exactly as it was when you leave
  the screen.
- If your club is playing a continental group stage, its round shows the real group you are playing in.
- **Continental cups, first season:** in a new World 2026-27 career, CONTINENTAL CUPS now shows each cup's drawn round from the very first week: open it to see the groups or ties still to be played. The Intercontinental Cup, whose clubs are the first season's winners, lists its rounds still to be played.
- **More realistic scores in the continental cups:** about 2.6 goals a match instead of more than 5. A career saved with an earlier version finishes its current continental season with the old scores; from the next season on it uses the new ones.

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

#### Stadium names (World 2026-27)
- **Stadium names.** In World 2026-27 the match intro screen (the one with the two teams) now shows where the match is played: the home club's stadium, under the two team names. Cup finals played at a neutral ground show that ground instead - for example the Champions League final at the Metropolitano, the FA Cup final at Wembley, the Coppa Italia final at the Olimpico. When the stadium of a club is not known, no line is shown: a name is never made up. The intro screen does not wait any longer than before. The other worlds and the original 1996-97 game are unchanged.

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
  - VIEW OPPO is unchanged: there UP / DOWN still browse the opponent's substitutes (you can only look).
  - **Cursor on the team screen before a match, as in the original game** (thanks to Marco). When you are a player-coach, the line where you choose to play or only coach is reached exactly as in the original 1996-97 game:
    - DOWN from the last player name goes to that line, DOWN again to PLAY MATCH; UP goes back the same way;
    - UP from EXIT goes to that line;
    - LEFT from the tactics column (the rows USER_A, USER_C, USER_E) goes to that line.
    As a plain manager that line is not shown, and the cursor skips it as before (from the last name straight to PLAY MATCH).

#### CPU replacements when you buy a player (thanks to Nicola)
**CPU replacements (World 2026-27).** When you buy one of the first 16 players of a computer-controlled club, the club
fills his place at once. Until now the game always invented a new player for it (a made-up name). A new button in
TRANSFERS > BUY PLAYER, right of EXIT, lets you choose:
- **CPU REPL.: INVENTED** - as before (the default);
- **CPU REPL.: FROM SQUAD** - one of the club's own players from place 17 on takes the place instead: the most valuable
  one in the same role (goalkeeper, defender, midfielder, forward); if there is none, the most valuable outfield
  player. A goalkeeper is only ever replaced by a goalkeeper, and a goalkeeper never fills an outfield place. A player on
  the transfer list is not used. If nobody fits, the game invents one as before.
Buying a player from place 17 on never brings a replacement (as before). The choice is saved with the career; a new
career starts with INVENTED. Older saves load with INVENTED.

#### Training, squad and market
- **Training games: bench and kits** (thanks to Marco). Training games (career, squad screen > TRAINING) have the game's own rule again: 2 substitutes from 2 on the bench. In 4.0.5 a training game took the bench of your current league: at a Serie A club the dugout showed 5 players a team, and the training squad screen had a bench of 12. Your next real match has the full league bench again.
  - In a training game both teams are your club, so SELECT KITS lists them as "ROMA A" and "SQUADRA B". They now keep their own kits: team A in the kit you pick for A, team B in the kit you pick for B. Before, both teams wore team A's choice.
  - In a training game SELECT KITS hides the "this match only / always" choice, and your club's saved kits are never changed by a training game.
- **Easier-to-read numbers.** In the team screen before a match and in the tactics editor the player names now start 2 pixels further right, so a two-digit shirt number no longer touches the face box or the name: there is a clear gap on both sides. The squad screen already had that gap and is unchanged.
- **Shirt numbers on the squad screen.** You can now edit your club's shirt numbers on the squad screen too, as you already could on the team screen before a match: press LEFT on a player, then UP / DOWN or type the number; ESC cancels. The number no longer touches the player's name, and its shadow shows.
- **Transfer market keeps its place** (reported by Enzo). When you look at a player in the national or foreign market list (MAKE OFFER) and come back with EXIT, the list stays on the page you were on, with the cursor on that player, instead of jumping back to the first page.

#### New looks: white hair and bald heads before the kick-off
**White hair.** A new look joins the blond, bald and shaved ones: grey-white hair. The first player to wear it is
Fabrizio Ravanelli at Middlesbrough in the 1996-97 game, as he really looked. On the pitch his hair is white with a
darker grey on its shaded side; on the squad screen his face icon shows the whole white hairline.

**Bald and white heads before the kick-off.** The line-ups screen before a match (the little players lined up in the
stadium while the teams are presented) used to give everyone normal hair. Now those little players look as they do
on the pitch: white hair is white, a shaved head is a light skull in the player's own skin tone, and a balding
player keeps his hair only on the sides, in his own hair colour.

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

#### B-team call-ups (World 2026-27)
**Call up your B team.** In a World 2026-27 career, a club that has a B team (its second team or under-23 side) can
now bring its young players up to the first team. That is 20 clubs: Juventus (Juventus Next Gen), Atalanta (Atalanta
U23), Inter (Inter U23) and Milan (Milan Futuro) in Italy; Real Sociedad in Spain; Stuttgart and Hoffenheim in
Germany; Porto, Benfica and Sporting in Portugal; PSV, Utrecht, AZ and Ajax in the Netherlands; Sydney FC, Western
Sydney, Melbourne City and Brisbane Roar in Australia; Auckland FC and Wellington Phoenix in New Zealand.

On your squad screen a new **B TEAM** button, next to EXIT, opens the B team's squad (two pages: the whole squad, up to
30 players). Players you have already called up are greyed out. Pick one, then choose:
- **Next match only**: he plays for you in the next match and goes back to the B team right after it. Players under 23
  and goalkeepers can always be called; older players only up to the country's limit: 4 in Italy, Spain and Portugal,
  3 in Germany, no limit in the Netherlands. In Australia and New Zealand the reserve teams are under-23 sides, so only
  players under 23 can be called, goalkeepers included. At most 4 players a match. He costs nothing and you pay him no
  wages.
- **For the season**: he joins your squad until the end of the season and you pay his normal wages; the B team takes a
  youth player in his place. At most 3 in each transfer window, and only while the window is open: in Europe from
  1 July to 1 September and in January; in Australia and New Zealand from 24 June to 15 September and from 12 January
  to 8 February.

There is never a transfer fee: calling a player up does not touch your bank balance. If a call-up is not allowed, the
page tells you why (for example "already called up" or "transfer window closed"). On your squad screen a called-up
player's shirt number shows a B, in yellow (for example 12B), and his value reads LOAN: he cannot be sold or put on
the transfer list. Everyone goes back to the B team at the end of the season, or when you take a job at another club.
Your squad still holds at most 30 players. A player whose year of birth we do not know counts as under 23.
For New Zealand we found no official rule for the reserves' ages, so they follow the Australian one: an approximation.
With the new button in place, a long coach's name on the squad screen is shown shortened (the name itself is kept).

#### Fixes
- **New Zealand, last round of the Championship group.** If your club rests in the last round of the Championship group, the menu now offers FINISH SEASON. Press it: if your club reached the Grand Final, MATCH comes back and you play it; otherwise the season ends. (Before, the menu could offer a match on the rest day.) The real champion was already right; this removes the confusing final that did not count mentioned in the 4.0.5 notes.
- **Buying a club's extra squad players** (thanks to Enzo). Fixed: after taking over a club, a player you had bought from it (one of its extra squad players) could reappear in its squad, so he was in two clubs at once. Fixed: buying one of another club's extra squad players (players 17 to 30) could make the career crash at the start of a later season, or spoil another club's squad. Careers saved with 4.0.2 to 4.0.5 play on safely.
- **TRANSFERS stays available after viewing a cup.** After looking at a cup from VIEW WORLD, TRANSFERS was greyed out until the next match and the menu cursor jumped
  into the fixtures (since 4.0.5). Now the career menu stays as it was.
- **The UP and DOWN arrows stopped working after a match** (thanks to Salvatore). In 4.0.5 the UP and DOWN arrows could stop working in every menu after a match. It happened if you pressed VIEW OPPO on the pre-match screen and started the match from there (PLAY MATCH): the arrows stayed dead until the next pre-match screen, even after loading another career (LEFT and RIGHT still worked). Now they always work, and on the pre-match screen UP and DOWN still scroll the opponent's long squad as before.
- **Two-row benches drew stray pieces.** The patcher used to install only one of the five pitch picture files, so the new two-row benches showed dirty pieces on some pitches. It now installs all five.
- **Club names without the "&" sign:** O Y M, TREFELIN BGC, SB VLASIM and HARLAND WOLFF.
- **A play-off entrant that refuses the place** no longer makes the game read wrong data at the season end (it showed up with San Marino; found by Ben Baker).

### Good to know
- **With SWOS++** (SWOS++ has its own controls and its own match code) these 4.0.6 features are off or hidden: the "P1 AND P2 ON KEYBOARD" device, the OPTIONS rows for the computer's cards and injuries and for goalkeeper injuries, the opponent's squad list in the match and stoppage time. [TO CHECK with the owners: the full list, including the B-team button and the two-row benches.]
- **New Zealand, B-team call-ups:** the age rule for the New Zealand clubs' reserves is an approximation (see above).
- **Finances:** the new income applies to every career from its next match, including older ones; it changes the money, not the squads.

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
- **La tastiera non viene mai bloccata dal joypad.** Con i comandi impostati su joypad per il giocatore 1 e tastiera per il
  giocatore 2 (il valore che si ottiene spuntando "Ho un joypad" nel patcher), un joypad non centrato - non calibrato,
  consumato o che legge un angolo - vinceva sulla tastiera: nei menu una direzione tenuta sulla tastiera poteva non fare
  nulla (per esempio GIÙ, con la leva che pende in alto). Ora una direzione tenuta sulla tastiera conta sempre, nei menu e
  per la tua squadra in partita, purché nessun altro giochi con la tastiera in quella partita. Con SOLO TASTIERA, DUE
  JOYPAD o SWOS++ non cambia nulla.

#### Le squadre del computer giocano con le tue regole
- **Due nuove righe in OPZIONI, entrambe attive di default:** le squadre del computer ora prendono **cartellini rossi** (un espulso è squalificato, come i tuoi) e **infortuni** (un infortunato di una squadra del computer salta le partite seguenti invece di essere subito di nuovo a posto). Metti una riga su NO per riavere il comportamento originale del gioco.
- Con SWOS++ le due righe sono nascoste e vale il comportamento originale.
- **Anche i portieri si infortunano.** Nel gioco originale un portiere non si infortuna quasi mai. Ora, dopo ogni
  partita, il portiere di ogni squadra ha 1 probabilità su 25 di infortunarsi. Lo vedi dopo, nella schermata della
  squadra, non durante la partita. Salta la partita successiva o le due successive, poi torna disponibile come
  qualunque infortunato. Conta il portiere in campo al fischio finale, e valgono anche le partite di cui guardi solo
  il risultato. I portieri del computer si infortunano in ogni competizione tranne le amichevoli, con INFORTUNI ALLA CPU attivato.
  In una competizione personalizzata o predefinita anche infortunati e squalificati del computer ora guariscono
  dopo ogni partita, come i tuoi (prima restavano fuori per tutta la competizione). Per spegnerlo:
  OPZIONI > INFORTUNI PORTIERI (EN GOALKEEPER INJURIES, FR BLESSURES DES GARDIENS, DE TORWARTVERLETZUNGEN). È
  attivato all'inizio e si salva con la carriera; una carriera più vecchia lo carica attivato. Non con SWOS++.
#### Coppe continentali nelle schermate del gioco (Mondo 2026-27)
- **COPPE CONTINENTALI** (VISUAL. COMPETIZ.): scegli una confederazione e trovi un menu dei suoi turni già
  sorteggiati, nell'ordine in cui si giocano. Ogni turno si apre nella schermata di coppa del gioco, esattamente fin
  dove è arrivata la tua carriera:
  - turni a eliminazione diretta con andata e ritorno, il totale, i supplementari, i gol in trasferta e i rigori;
  - fasi a gironi con le classifiche e le partite giornata per giornata (PASSA mostra la fase successiva, come in ogni
    coppa del gioco).
  - **RIEPILOGO** mostra tutte le coppe della confederazione in una pagina di testo, come prima.
- **VISUALIZZA MONDO**: ogni continente ora mostra le sue coppe continentali come pulsanti verdi sopra le nazioni -
  SUDAMERICA la Libertadores, la Sudamericana e la Recopa, EUROPA Champions League, Europa League e Conference League,
  MONDO l'Intercontinentale, e così via. Un pulsante apre lo stesso menu dei turni di quella coppa.
- Quando la schermata del gioco non può mostrare un turno, compare invece la pagina di testo:
  - nella prima stagione della carriera;
  - per la fase campionato della AFC Champions League Elite, una formula che le schermate del gioco non hanno;
  - nei rari casi in cui non si potrebbe mostrare in sicurezza (troppe squadre caricate insieme, un club che manca nei
    dati).
- Guardare le coppe non cambia mai la carriera né il suo salvataggio: quando esci dalla schermata tutto torna
  esattamente com'era.
- Se la tua squadra sta giocando una fase a gironi continentale, il suo turno mostra il girone vero in cui stai
  giocando.
- **Coppe continentali, prima stagione:** in una nuova carriera Mondo 2026-27, COPPE CONTINENTALI mostra fin dalla prima settimana il turno sorteggiato di ogni coppa: aprilo per vedere i gironi o gli accoppiamenti da giocare. La Coppa Intercontinentale, che riunisce le vincitrici della prima stagione, elenca i suoi turni da giocare.
- **Risultati più realistici nelle coppe continentali:** circa 2,6 gol a partita invece di oltre 5. Una carriera salvata con una versione precedente finisce la stagione continentale in corso con i punteggi di prima; dalla stagione successiva usa quelli nuovi.

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

#### Nomi degli stadi (Mondo 2026-27)
- **Nomi degli stadi.** Nel Mondo 2026-27 la schermata che presenta la partita (quella con le due squadre) ora dice dove si gioca: lo stadio del club di casa, sotto i nomi delle due squadre. Le finali di coppa in campo neutro mostrano quello stadio - per esempio la finale di Champions League al Metropolitano, la finale di FA Cup a Wembley, la finale di Coppa Italia all'Olimpico. Se lo stadio di un club non è noto la riga non compare: un nome non viene mai inventato. La schermata non resta ferma più a lungo di prima. Gli altri mondi e il gioco originale 1996-97 non cambiano.

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
  - AVVERSARI non cambia: lì SU / GIÙ scorrono ancora le riserve avversarie (si può solo guardare).
  - **Cursore nella schermata della squadra prima della partita, come nel gioco originale** (grazie a Marco). Quando sei giocatore-allenatore la riga in cui scegli se giocare o solo allenare si raggiunge esattamente come nel gioco originale 1996-97:
    - GIÙ dall'ultimo nome della lista va su quella riga, ancora GIÙ su GIOCA PARTITA; SU torna indietro allo stesso modo;
    - SU da ESCI va su quella riga;
    - SINISTRA dalla colonna delle tattiche (le righe UTN A, C, E) va su quella riga.
    Da semplice allenatore quella riga non c'è e il cursore la salta come prima (dall'ultimo nome direttamente a GIOCA PARTITA).

#### Rimpiazzi della CPU quando compri un giocatore (grazie a Nicola)
**Rimpiazzi della CPU (Mondo 2026-27).** Quando compri uno dei primi 16 giocatori di un club guidato dal computer, il
club copre subito il suo posto. Finora il gioco inventava sempre un giocatore nuovo (un nome di fantasia). Un nuovo
pulsante in TRASFERIMENTI > ACQUISTA GIOCATORE, a destra di ESCI, permette di scegliere:
- **RIMP. CPU: INVENTATI** - come prima (il valore iniziale);
- **RIMP. CPU: DALLA ROSA** - al suo posto sale uno dei giocatori del club dal 17° in poi: quello di valore più alto nello
  stesso ruolo (portiere, difensore, centrocampista, attaccante); se non c'è, il giocatore di movimento di valore più alto.
  Un portiere è sostituito solo da un portiere, e un portiere non prende mai il posto di un giocatore di movimento. Chi è
  sul mercato dei trasferimenti non viene usato. Se nessuno va bene, il gioco ne inventa uno come prima.
Comprando un giocatore dal 17° in poi non arriva mai un rimpiazzo (come prima). La scelta si salva con la carriera; una
carriera nuova parte da INVENTATI. I salvataggi precedenti si caricano con INVENTATI.

#### Allenamento, rosa e mercato
- **Allenamento: panchina e maglie** (grazie a Marco). Le partite di allenamento (carriera, schermata della rosa > PRATICA) tornano alla regola del gioco: 2 sostituti su 2 in panchina. In 4.0.5 l'allenamento prendeva la panchina del tuo campionato: con un club di Serie A la panchina mostrava 5 giocatori per squadra e la schermata della rosa in allenamento una panchina da 12. La partita vera successiva ha di nuovo la panchina intera del campionato.
  - In allenamento le due squadre sono entrambe il tuo club, e MAGLIE le mostra come "ROMA A" e "SQUADRA B". Ora ognuna tiene le sue maglie: la squadra A quella scelta per A, la squadra B quella scelta per B. Prima entrambe vestivano la scelta della squadra A.
  - In allenamento MAGLIE nasconde la scelta SOLO PARTITA / SEMPRE, e le maglie salvate del tuo club non vengono mai cambiate da una partita di allenamento.
- **Numeri più leggibili.** Nella schermata della squadra prima della partita e nell'editor delle tattiche i nomi dei giocatori partono 2 pixel più a destra, così un numero di maglia a due cifre non tocca più il riquadro della faccia né il nome: c'è uno spazio libero da entrambi i lati. La schermata della rosa aveva già quello spazio e non cambia.
- **Numeri di maglia nella schermata della rosa.** Ora puoi modificare i numeri di maglia del tuo club anche nella schermata della rosa, come già potevi nella schermata della squadra prima della partita: premi SINISTRA su un giocatore, poi SU / GIÙ o scrivi il numero; ESC annulla. Il numero non tocca più il nome del giocatore e se ne vede l'ombra.
- **Il mercato ricorda la pagina** (segnalato da Enzo). Quando guardi un giocatore nell'elenco del mercato nazionale o estero (FAI OFFERTA) e torni con ESCI, l'elenco resta sulla pagina in cui eri, con il cursore su quel giocatore, invece di tornare alla prima pagina.

#### Nuovi look: capelli bianchi e teste calve prima del calcio d'inizio
**Capelli bianchi.** Un nuovo look si aggiunge a biondi, calvi e rasati: i capelli grigio-bianchi. Il primo giocatore
che li porta è Fabrizio Ravanelli del Middlesbrough nel gioco 1996-97, com'era davvero. In campo ha i capelli bianchi
con un grigio più scuro sul lato in ombra; nella schermata della rosa la sua faccina mostra tutta la capigliatura
bianca.

**Teste calve e bianche prima del calcio d'inizio.** La schermata delle formazioni prima della partita (gli omini
schierati nello stadio mentre vengono presentate le squadre) dava a tutti i capelli normali. Ora quegli omini sono come
in campo: i capelli bianchi sono bianchi, la testa rasata è chiara, nel colore della pelle del giocatore, e chi è
stempiato ha i capelli solo ai lati, nel suo colore.

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

#### Convocazioni dalla squadra B (Mondo 2026-27)
**Convoca dalla squadra B.** In una carriera nel Mondo 2026-27, un club che ha una squadra B (la seconda squadra o
l'under 23) ora può portare i suoi giovani in prima squadra. Sono 20 club: Juventus (Juventus Next Gen), Atalanta
(Atalanta U23), Inter (Inter U23) e Milan (Milan Futuro) in Italia; Real Sociedad in Spagna; Stoccarda e Hoffenheim in
Germania; Porto, Benfica e Sporting in Portogallo; PSV, Utrecht, AZ e Ajax in Olanda; Sydney FC, Western Sydney,
Melbourne City e Brisbane Roar in Australia; Auckland FC e Wellington Phoenix in Nuova Zelanda.

Nella schermata della rosa un nuovo pulsante **SQ. B**, accanto a ESCI, apre la rosa della squadra B (due pagine: tutta
la rosa, fino a 30 giocatori). I giocatori già convocati sono in grigio. Scegline uno, poi:
- **Solo prossima partita**: gioca con te la prossima partita e torna alla squadra B subito dopo. Gli under 23 e i
  portieri si possono sempre convocare; i più grandi solo fino al limite del paese: 4 in Italia, Spagna e Portogallo, 3
  in Germania, nessun limite in Olanda. In Australia e Nuova Zelanda le riserve sono squadre under 23: si possono
  convocare solo gli under 23, portieri compresi. Al massimo 4 a partita. Non costa nulla e non gli paghi lo stipendio.
- **Per la stagione**: resta nella tua rosa fino alla fine della stagione e gli paghi il suo stipendio normale; la
  squadra B prende un giovane al suo posto. Al massimo 3 per ogni finestra di mercato, e solo a mercato aperto: in
  Europa dal 1° luglio al 1° settembre e a gennaio; in Australia e Nuova Zelanda dal 24 giugno al 15 settembre e dal
  12 gennaio all'8 febbraio.

Non c'è mai un costo di cartellino: convocare un giocatore non tocca la tua banca. Se una convocazione non è permessa,
la pagina ti dice perché (per esempio "già convocato" o "mercato chiuso"). Nella schermata della rosa il numero di
maglia di un convocato ha una B, in giallo (per esempio 12B), e il suo valore dice PRES.: non si può vendere né mettere
in lista. Tutti tornano alla squadra B a fine stagione, o quando accetti un lavoro in un altro club. La rosa resta di
massimo 30 giocatori. Un giocatore di cui non conosciamo l'anno di nascita conta come under 23.
Per la Nuova Zelanda non abbiamo trovato una regola ufficiale sull'età delle riserve, quindi vale quella australiana:
è un'approssimazione.
Con il nuovo pulsante, un nome dell'allenatore lungo nella schermata della rosa viene mostrato accorciato (il nome
resta quello).

#### Correzioni
- **Nuova Zelanda, ultima giornata del gruppo del Championship.** Se il tuo club riposa nell'ultima giornata del gruppo del Championship, il menu ora offre FINISCI STAGIONE. Premilo: se il tuo club è arrivato alla Grand Final torna PARTITA e la giochi; altrimenti la stagione finisce. (Prima il menu poteva offrire una partita nel giorno di riposo.) Il campione vero era già giusto; questo toglie la finale confusa che non contava, citata nelle note della 4.0.5.
- **Acquisto dei giocatori extra di una squadra** (grazie a Enzo). Corretto: prendendo una squadra, un giocatore che le avevi comprato (uno dei suoi giocatori extra della rosa) poteva ricomparire nella sua rosa, quindi in due squadre insieme. Corretto: comprare uno dei giocatori extra della rosa di un'altra squadra (dal 17° al 30°) poteva bloccare la carriera all'inizio di una stagione successiva o rovinare la rosa di un'altra squadra. Le carriere salvate con le versioni 4.0.2-4.0.5 proseguono senza problemi.
- **TRASFERIMENTI resta disponibile dopo aver guardato una coppa.** Dopo aver guardato una coppa da VISUALIZZA MONDO, TRASFERIMENTI restava grigio fino alla partita successiva e il
  cursore del menu saltava nelle partite (dalla 4.0.5). Ora il menu della carriera resta com'era.
- **Le frecce SU e GIÙ smettevano di funzionare dopo una partita** (grazie a Salvatore). Nella 4.0.5 le frecce SU e GIÙ potevano smettere di funzionare in tutti i menu dopo una partita. Succedeva se nella schermata prima della partita guardavi la rosa avversaria (AVVERSARI) e facevi partire la partita da lì: le frecce restavano bloccate fino alla schermata prima della partita successiva, anche caricando un'altra carriera (SINISTRA e DESTRA funzionavano). Ora funzionano sempre, e nella schermata prima della partita SU e GIÙ scorrono ancora la rosa lunga dell'avversario come prima.
- **Le panchine su due file mostravano pezzi sporchi.** Il patcher installava solo uno dei cinque file con le immagini dei campi, quindi le nuove panchine su due file mostravano pezzi sporchi su alcuni campi. Ora li installa tutti e cinque.
- **Nomi di club senza il segno "&":** O Y M, TREFELIN BGC, SB VLASIM e HARLAND WOLFF.
- **Una squadra di play-off che rifiuta il posto** non fa più leggere al gioco dati sbagliati a fine stagione (si vedeva con San Marino; trovato da Ben Baker).

### Da sapere
- **Con SWOS++** (SWOS++ ha i suoi comandi e il suo codice di partita) queste novità della 4.0.6 sono disattivate o nascoste: il dispositivo "G1 E G2 SU TASTIERA", le righe di OPZIONI per cartellini e infortuni del computer e per gli infortuni dei portieri, l'elenco della rosa avversaria in partita e il recupero. [DA VERIFICARE con i proprietari: l'elenco completo, compresi il pulsante della squadra B e le panchine su due file.]
- **Nuova Zelanda, convocazioni dalla squadra B:** la regola sull'età per le riserve dei club neozelandesi è un'approssimazione (vedi sopra).
- **Finanze:** i nuovi incassi valgono per ogni carriera dalla partita successiva, anche per quelle già iniziate; cambiano i soldi, non le rose.

### Ringraziamenti
Grazie a Roman per aver chiesto un'installazione più semplice, a Marco per le idee su allenamento, numeri di maglia e tastiera, a Enzo per la segnalazione sull'elenco del mercato, a Nicola per quella sulle finanze, a Francesco e a Ben Baker per la segnalazione su San Marino. [DA VERIFICARE: crediti esatti per voce con i proprietari.]
