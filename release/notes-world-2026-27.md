<!-- DRAFT (2026-10-16), not released. Kept up to date at each milestone by the world 2026-27 sessions.
     Data parts: Transfermarkt converter session. TODO parts marked [TODO <session>]. Never publish without Davide's ok. -->

## English

**SWOS 96/97 Mod: World 2026-27 career** (DRAFT)

A historic career world of the **2026-27 season**: 87 countries, 1,562 clubs, real squads at the end of the summer
2026 transfer window. In CLASSIC CAREERS choose WORLD 2026-27, then the continent and the country (EUROPE lists the
first 43 UEFA associations by ranking, the others are under OTHER NATIONS).

- **Countries and leagues**: all 54 playing UEFA associations, each a real country (Liechtenstein, which has no league
  of its own, plays a mini league of its 6 first teams), and Russia (league only: no European places while suspended);
  England on 3 levels, Scotland on 4, Italy with Serie A, B and the three Serie C groups, the second tiers of Spain,
  Germany (and 3. Liga), France, Netherlands, Portugal, Turkey; Brazil Serie A and B, the full MLS, Canada, Mexico,
  Central America, every CONMEBOL country, Saudi Arabia, Qatar, UAE, Iran, Japan, Korea, China, Australia, Egypt,
  Morocco, Tunisia, Algeria, South Africa, New Zealand. Calendar-year leagues play their 2026 season.
- **Club order**: each division in the order of its 2025-26 final table (2025 for calendar-year leagues): the clubs
  that stayed by final position, then the relegated, then the promoted; promoted clubs from a tier the world does
  not hold come last, by squad value.
- **Squads**: Transfermarkt squads, 16 per club in the team files. **The club you manage has 25**: when you start a
  career or take a new job, its 16 are joined by 9 real reserves (the club's next players on Transfermarkt) instead
  of the 10 reserves the game invents for a new club; the 25 are saved with the career. As in the original game,
  trial players may still join during the season while the squad is under 30. Computer clubs always play with their
  16. Real shirt numbers, nationality (the game's closest nation where the game has none: Kosovo -> Albania,
  Montenegro / Serbia -> Yugoslavia, Kazakhstan -> Russia ...). Coaches from Transfermarkt.
- **Skills**: each player's level comes from his market value (corrected for age) mapped onto the original game's own
  distribution of player prices, blended with his EA SPORTS FC overall rating where he exists in EA's ratings; the 7
  skills follow his EA attributes (passing, shooting, heading, tackling, ball control, speed, finishing; the 2 best are
  the key skills) or, for players not in EA, the profile of his position. The clubs of a division are then moved
  toward the strength their 2025-26 final position suggests, so a simulated season resembles the real table.
- **Faces**: dark or light by nationality (dark when any of the player's nationalities is in the game's list of
  dark-face nations), with a hand-made correction list; Transfermarkt and EA's public ratings have no such field.
- **Kits**: from the Wikipedia infobox of each club (home and away colours; stripes and hoops read from the kit
  pattern images; purple where the club wears it).
- **National cups 2026-27**: where the cup has already started, the clubs already knocked out in reality stay out and
  the real drawn ties are kept in the first round; the rounds not drawn yet are drawn by the mod (see the rules below).
  Cups not started yet (FA Cup proper, among others) are drawn by the mod from the league clubs.
- **European cups**: the first season's Champions League, Europa League and Conference League are the real 2026-27
  league phases (36 clubs each). The format is UEFA's since 2024-25:
  - **League phase**: one table of 36. The draw is made by the game at the start of every season, in four pots by club
    coefficient (the Champions League holder first): two opponents from each pot, one at home and one away, never a
    club of the same association and at most two of one association. 8 matchdays; table order by points, goal
    difference, goals, away goals, wins, away wins, then the opponents' points, goal difference and goals (UEFA's
    rules, the disciplinary points aside). Places 1-8 go to the round of 16, 9-24 play the knockout play-offs (two
    legs, 9-16 seeded), 25-36 are out; the round of 16 and the bracket to the final follow UEFA's fixed shape.
  - **Qualifying rounds** (from the second season): the real access list of 2024-27 (as for 2026-27) for all three
    competitions: first to fourth qualifying round of the Champions League (champions and league paths), Europa
    League and Conference League (with its champions path), the losers dropping into the next competition as in
    reality. Draws seeded by club coefficient, never two clubs of one association; two-leg ties. Your club plays its
    own ties (PRELIM. CHAMPIONS LEAGUE, rounds named first to fourth); the other ties are decided by the strength of
    the squads.
  - **Simulated UEFA coefficients**: they start from the real association coefficients (5 seasons, 2021-22 ..
    2025-26) and the real club coefficients at the 2025-26 draws; then every season adds the points of the world's
    own European results (league phase: a win 2, a draw 1; Champions League participation 6; the league-phase place
    bonus; each knockout round reached; a knockout tie gives its winner 3 and its loser 1, a qualifying tie half of
    that). An association's season = its clubs' points / its clubs (those out in the qualifying included); a club's
    coefficient = its 5 seasons, at least 20% of its association's. Both rankings set the next season's pots and seeds.
  - **Places by association rank**: each season the access list is filled by the simulated association ranking
    (places per rank as in 2024-27), plus the 2 European Performance Spots (the 2 best associations of the season).
  - **Holders**: the Champions League holder and the Europa League winner enter the Champions League league phase,
    the Conference League winner the Europa League league phase; when a holder already qualifies through its league,
    the access list is rebalanced as UEFA does.
- **Foreign market**: real players of clubs outside the world (the tiers just below its divisions: Primera
  Federacion, FNL, Challenger Pro League, NordicBet Liga, OBOS-ligaen, Superettan, Challenge League, National, League
  Two ...), 900 of them, instead of the game's 1996 players.
- **Two historic career worlds in one game**: Europe 1984-85 and World 2026-27 sit side by side under CLASSIC
  CAREERS. Each world has its own countries, leagues and cups, so neither takes anything from the other.
- World 2026-27 has its own team files, DATA/TMW5.nnn (players, kits, squads). The 1984-85 world keeps its
  DATA/TEAM.nnn files unchanged.
- Saves: a career save knows its world and reopens it. 1984-85 careers saved with earlier versions load and play as
  before. You can switch between the two worlds' careers in the same session.
- Other game modes (friendlies, seasons, tourneys, the 1996-97 career) are unchanged.

**Mod rules of this world**
- Extras of the managed club (25-man squads): each of the 9 reserves keeps his real name, role, nationality and face,
  but his skill total is at most the weakest of the club's 16 (outfield vs outfield, keeper vs keeper) and his price
  = his skill total, so no extra is better than the weakest of the club's 16 and the club's best 11 do not change.
  (Note: they are on average a little stronger than the 10 reserves the game invents (Randers: 12.3 against 8.8 per
  player); [PENDING Davide: keep this cap or tighten it].)
- National cups: the bracket has no byes (a career's national cup cannot have first-round byes in the engine): it
  starts from the power of two at or below the clubs still in, keeping the clubs of the real drawn ties and then the strongest squads
  (when the clubs still in are nearer the next power of two, the country's best clubs already out take the free
  places); the mod draws the rounds not drawn yet. Every match is played by the game, so the real results of the
  rounds already played are not imposed.
- Players without a Transfermarkt value get an estimate (from their club's and division's values); in the lowest
  divisions (Scotland's League One and Two) the squads are so close that a simulated season does not follow the real
  table closely.
- Odd leagues lose their last club (the engine needs an even number): Gibraltar, New Zealand (11 -> 10).

**Known limits**
- EA's public ratings still held FC 26-era rosters when this world was built (2026-10-16): attributes are matched by
  player (name and birth date), not by club, so they are a year old; they will be refreshed when EA publishes FC 27.
- About a third of the players are in EA's ratings (most of the big leagues, few of the small ones).
- Squads (engine): at most 32 players in the managed club (25 + up to 7 purchases or trial players; at 32 pending
  purchases are cancelled), 5 substitutes on the bench, 16 per computer club. When you leave a club, it keeps the first 16
  of your squad order (as in the original game) and the others are dropped; if you come back later, its 9 reserves
  join again, also any you had sold, and a reserve you had moved into the first 16 can then appear twice.
- Team cache (engine): the game keeps at most 100 different clubs in memory during a season; a career in this world
  uses a bigger cache of 160 (an English lower-division club in a European league phase needs about 130). Other
  careers and modes keep the game's own.
- National cups (engine): a career's national cup cannot have first-round byes (hence the power-of-two brackets
  above); the qualifying ties and the league phases are the mod's own and need none.
- European results that the game does not play match by match (the computer's knockout ties, the qualifying ties
  between computer clubs) count for the coefficients as whole ties (winner 3 / loser 1, qualifying half of that).

**Data and credits**
- Squads, market values, coaches, league members 2026-27 and tables 2025-26: **Transfermarkt** (transfermarkt.com).
- Player attributes: **EA SPORTS FC** ratings (ea.com), FC 26-era data.
- Kits: **Wikipedia contributors** (CC BY-SA 4.0); club to article links from **Wikidata** (CC0).
- UEFA association and club coefficients: Bert Kassies' UEFA coefficients site (kassiesa.net).

## Italiano

**SWOS 96/97 Mod: carriera Mondo 2026-27** (BOZZA)

Un mondo di carriera storica della **stagione 2026-27**: 87 nazioni, 1.562 club, rose reali alla fine del mercato
estivo 2026. In CARR. STORICHE scegli MONDO 2026-27, poi il continente e la nazione (EUROPA elenca le prime 43
federazioni UEFA per ranking, le altre sono in ALTRE NAZIONI).

- **Nazioni e campionati**: tutte le 54 federazioni UEFA che giocano, ognuna come nazione vera (il Liechtenstein, che
  non ha un campionato suo, gioca un mini campionato con le sue 6 prime squadre), e la Russia (solo campionato:
  nessun posto europeo finché è sospesa); Inghilterra su 3 livelli, Scozia su 4, Italia con Serie A, B e i tre gironi
  di Serie C, le seconde serie di Spagna, Germania (e 3. Liga), Francia, Olanda, Portogallo, Turchia; Brasile Serie A
  e B, tutta la MLS, Canada, Messico, Centro America, tutte le nazioni CONMEBOL, Arabia Saudita, Qatar, Emirati, Iran,
  Giappone, Corea, Cina, Australia, Egitto, Marocco, Tunisia, Algeria, Sudafrica, Nuova Zelanda. I campionati ad anno
  solare giocano la loro stagione 2026.
- **Ordine dei club**: ogni divisione nell'ordine della sua classifica finale 2025-26 (2025 per i campionati ad anno
  solare): prima i club rimasti, per posizione, poi le retrocesse, poi le promosse; le promosse da una serie che il
  mondo non contiene vanno in fondo, per valore della rosa.
- **Rose**: rose Transfermarkt, 16 per club nei file squadra. **Il club che alleni ne ha 25**: quando inizi una
  carriera o accetti un nuovo incarico, ai suoi 16 si aggiungono 9 riserve vere (i giocatori successivi del club su
  Transfermarkt) al posto delle 10 riserve che il gioco inventa per un club nuovo; i 25 vengono salvati con la
  carriera. Come nel gioco originale, durante la stagione possono ancora arrivare giocatori in prova finché la rosa
  ha meno di 30 giocatori. I club del computer giocano sempre con i loro 16.
  Numeri di maglia reali, nazionalità (la nazione più vicina del gioco dove il gioco non ce l'ha: Kosovo -> Albania,
  Montenegro / Serbia -> Jugoslavia, Kazakistan -> Russia ...). Allenatori da Transfermarkt.
- **Abilità**: il livello di ogni giocatore viene dal suo valore di mercato (corretto per l'età) riportato sulla
  distribuzione dei prezzi dei giocatori del gioco originale, mescolato con la sua valutazione complessiva EA SPORTS FC
  quando è nelle valutazioni EA; le 7 abilità seguono i suoi attributi EA (passaggio, tiro, colpo di testa, contrasto,
  controllo di palla, velocità, finalizzazione; le 2 migliori sono le abilità chiave) oppure, per chi non è in EA, il
  profilo del suo ruolo. I club di ogni divisione vengono poi avvicinati alla forza che suggerisce la loro posizione
  finale 2025-26, così una stagione simulata somiglia alla classifica vera.
- **Volti**: scuri o chiari secondo la nazionalità (scuro quando una delle nazionalità del giocatore è nell'elenco
  delle nazioni a volto scuro del gioco), con una lista di correzioni a mano; Transfermarkt e le valutazioni pubbliche
  EA non hanno questo dato.
- **Maglie**: dall'infobox Wikipedia di ogni club (colori di casa e trasferta; righe e cerchi letti dalle immagini dei
  motivi delle maglie; viola dove il club lo veste).
- **Coppe nazionali 2026-27**: dove la coppa è già iniziata, i club già eliminati nella realtà restano fuori e le
  coppie già sorteggiate restano al primo turno; i turni non ancora sorteggiati li sorteggia la mod (vedi le regole
  sotto). Le coppe non ancora iniziate (tra cui la FA Cup) le sorteggia la mod tra i club del campionato.
- **Coppe europee**: Champions League, Europa League e Conference League della prima stagione sono le vere fasi
  campionato 2026-27 (36 club ciascuna). Il formato è quello UEFA dal 2024-25:
  - **Fase campionato**: una sola classifica da 36. Il sorteggio lo fa il gioco all'inizio di ogni stagione, in
    quattro fasce per coefficiente dei club (prima il detentore della Champions League): due avversarie per fascia,
    una in casa e una fuori, mai un club della stessa federazione e al massimo due della stessa federazione.
    8 giornate; classifica per punti, differenza reti, gol fatti, gol fuori casa, vittorie, vittorie fuori casa, poi
    punti, differenza reti e gol delle avversarie (regole UEFA, esclusi i punti disciplinari). I posti 1-8 vanno agli
    ottavi, i 9-24 giocano gli spareggi (andata e ritorno, 9-16 teste di serie), i 25-36 sono eliminati; ottavi e
    tabellone fino alla finale seguono lo schema fisso UEFA.
  - **Turni preliminari** (dalla seconda stagione): la vera lista di accesso 2024-27 (come per il 2026-27) per tutte e
    tre le competizioni: dal primo al quarto turno preliminare della Champions League (percorso campioni e percorso
    piazzate), Europa League e Conference League (con il suo percorso campioni), con le eliminate che scendono nella
    competizione successiva come nella realtà. Sorteggi con teste di serie per coefficiente dei club, mai due club
    della stessa federazione; sfide di andata e ritorno. Il tuo club gioca le sue sfide (PRELIM. CHAMPIONS LEAGUE,
    turni dal primo al quarto); le altre sfide le decide la forza delle rose.
  - **Coefficienti UEFA simulati**: partono dai veri coefficienti delle federazioni (5 stagioni, dal 2021-22 al
    2025-26) e dai veri coefficienti dei club ai sorteggi 2025-26; poi ogni stagione aggiunge i punti dei risultati
    europei del mondo (fase campionato: vittoria 2, pareggio 1; partecipazione alla Champions League 6; il bonus per il
    piazzamento nella fase campionato; ogni turno a eliminazione raggiunto; una sfida a eliminazione dà 3 a chi passa
    e 1 a chi esce, una sfida preliminare la metà). La stagione di una federazione = punti dei suoi club / suoi club
    (compresi quelli usciti nei preliminari); il coefficiente di un club = le sue 5 stagioni, almeno il 20% di quello
    della sua federazione. I due ranking decidono fasce e teste di serie della stagione dopo.
  - **Posti per ranking**: ogni stagione la lista di accesso si riempie secondo il ranking simulato delle federazioni
    (posti per posizione come nel 2024-27), più i 2 European Performance Spots (le 2 federazioni migliori della stagione).
  - **Detentori**: il detentore della Champions League e la vincitrice dell'Europa League entrano nella fase campionato
    della Champions League, la vincitrice della Conference League in quella dell'Europa League; quando un detentore si
    qualifica già col suo campionato, la lista di accesso viene ribilanciata come fa la UEFA.
- **Mercato estero**: giocatori veri di club fuori dal mondo (le serie subito sotto le sue divisioni: Primera
  Federacion, FNL, Challenger Pro League, NordicBet Liga, OBOS-ligaen, Superettan, Challenge League, National, League
  Two ...), 900, al posto dei giocatori del 1996 del gioco.
- **Due mondi di carriera storica nello stesso gioco**: Europa 1984-85 e Mondo 2026-27 stanno affiancati in CARR.
  STORICHE. Ogni mondo ha i suoi paesi, campionati e coppe, quindi nessuno dei due toglie qualcosa all'altro.
- Il Mondo 2026-27 ha i suoi file squadra, DATA/TMW5.nnn (giocatori, divise, rose). Il mondo 1984-85 tiene i suoi
  DATA/TEAM.nnn invariati.
- Salvataggi: una carriera salvata sa a quale mondo appartiene e lo riapre. Le carriere 1984-85 salvate con le
  versioni precedenti si caricano e si giocano come prima. Nella stessa sessione si può passare da una carriera di un
  mondo a quella dell'altro.
- Le altre modalità (amichevoli, stagioni, tornei, carriera 1996-97) non cambiano.

**Regole della mod per questo mondo**
- Riserve del club allenato (rose da 25): ognuna delle 9 riserve tiene nome, ruolo, nazionalità e volto veri, ma la
  somma delle sue abilità non supera quella del più debole dei 16 del club (giocatori di movimento con giocatori di
  movimento, portieri con portieri) e il suo prezzo è uguale a quella somma: nessuna riserva è migliore del più debole
  dei 16 e i migliori 11 del club non cambiano. (Nota: in media sono un po' più forti delle 10 riserve che il gioco
  inventa (Randers: 12,3 contro 8,8 per giocatore); [IN ATTESA di Davide: tenere questo limite o renderlo più
  stretto].)
- Coppe nazionali: il tabellone non ha turni di riposo (nel motore una coppa nazionale di carriera non può avere
  turni di riposo al primo turno): parte dalla potenza di 2 pari o inferiore ai club ancora in corsa, tenendo i club delle coppie sorteggiate davvero e
  poi le rose più forti (quando i club in corsa sono più vicini alla potenza di 2 successiva, i posti liberi vanno ai
  migliori club della nazione già eliminati); i turni non ancora sorteggiati li sorteggia la mod. Ogni partita la gioca
  il gioco, quindi i risultati veri dei turni già giocati non sono imposti.
- I giocatori senza valore su Transfermarkt ricevono una stima (dai valori del club e della divisione); nelle divisioni
  più basse (League One e League Two scozzesi) le rose sono così vicine che una stagione simulata non segue da vicino la
  classifica vera.
- I campionati con un numero dispari di club perdono l'ultimo (il motore vuole un numero pari): Gibilterra, Nuova
  Zelanda (11 -> 10).

**Limiti noti**
- Quando questo mondo è stato costruito (16-10-2026) le valutazioni pubbliche EA avevano ancora le rose dell'era FC 26:
  gli attributi sono abbinati per giocatore (nome e data di nascita), non per club, quindi sono vecchi di un anno;
  verranno aggiornati quando EA pubblicherà FC 27.
- Circa un terzo dei giocatori è nelle valutazioni EA (gran parte dei campionati maggiori, pochi di quelli minori).
- Rose (motore): al massimo 32 giocatori nel club allenato (25 + fino a 7 acquisti o giocatori in prova; a 32 gli
  acquisti in sospeso vengono annullati), 5 sostituti in panchina, 16 per ogni club del computer. Quando lasci un club,
  questo tiene i primi 16 del tuo ordine di rosa (come nel gioco originale) e gli altri vengono tolti; se ci torni più
  avanti, le sue 9 riserve rientrano, anche quelle che avevi venduto, e una riserva che avevi portato tra i primi 16
  può comparire due volte.
- Cache delle squadre (motore): il gioco tiene in memoria al massimo 100 club diversi durante una stagione; una
  carriera in questo mondo usa una cache più grande, da 160 (un club inglese di serie minore in una fase campionato
  europea ne richiede circa 130). Le altre carriere e modalità tengono quella del gioco.
- Coppe nazionali (motore): la coppa nazionale di una carriera non può avere turni di riposo al primo turno (da qui i
  tabelloni a potenza di 2 descritti sopra); le sfide preliminari e le fasi campionato sono della mod e non ne hanno
  bisogno.
- I risultati europei che il gioco non gioca partita per partita (le sfide a eliminazione del computer, le sfide
  preliminari tra club del computer) contano per i coefficienti come sfide intere (3 a chi passa, 1 a chi esce, la
  metà nei preliminari).

**Dati e crediti**
- Rose, valori di mercato, allenatori, partecipanti 2026-27 e classifiche 2025-26: **Transfermarkt**
  (transfermarkt.com).
- Attributi dei giocatori: valutazioni **EA SPORTS FC** (ea.com), dati dell'era FC 26.
- Maglie: **contributori di Wikipedia** (CC BY-SA 4.0); collegamenti club -> voce da **Wikidata** (CC0).
- Coefficienti UEFA di federazioni e club: il sito sui coefficienti UEFA di Bert Kassies (kassiesa.net).
