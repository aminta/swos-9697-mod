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
- **Squads**: Transfermarkt squads (16 per club; [TODO squads session] the managed club gets 25: 16 + 9 real
  reserves). Real shirt numbers, nationality (the game's closest nation where the game has none: Kosovo -> Albania,
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
  league phases (36 clubs each). [TODO integrator: league phase format, exact qualifying rounds, simulated UEFA
  coefficients (association and club rankings from 2021-22 .. 2025-26), places by association rank, holders.]
- **Foreign market**: real players of clubs outside the world (the tiers just below its divisions: Primera
  Federacion, FNL, Challenger Pro League, NordicBet Liga, OBOS-ligaen, Superettan, Challenge League, National, League
  Two ...), 900 of them, instead of the game's 1996 players.
- [TODO namespace session: the world's own team files / country numbers.]

**Mod rules of this world**
- Extras of the managed club (25-man squads): each of the 9 reserves keeps his real name, role, nationality and face,
  but his skill total is at most the weakest of the club's 16 (outfield vs outfield, keeper vs keeper) and his price
  = his skill total, so the extras never make the managed club stronger or richer than the game's invented reserves.
- National cups: the bracket has no byes (the engine allows a bye in one season-pack cup only): it starts from the
  power of two at or below the clubs still in, keeping the clubs of the real drawn ties and then the strongest squads
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
- [TODO integrator / squads: engine limits (team cache, cups, per-world contest ids), the manager's club results in
  'view results' seasons.]

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
- **Rose**: rose Transfermarkt (16 per club; [TODO sessione rose] il club allenato ne ha 25: 16 + 9 riserve vere).
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
  campionato 2026-27 (36 club ciascuna). [TODO integratore: formato fase campionato, turni preliminari esatti,
  coefficienti UEFA simulati (ranking federazioni e club dal 2021-22 al 2025-26), posti per ranking, detentori.]
- **Mercato estero**: giocatori veri di club fuori dal mondo (le serie subito sotto le sue divisioni: Primera
  Federacion, FNL, Challenger Pro League, NordicBet Liga, OBOS-ligaen, Superettan, Challenge League, National, League
  Two ...), 900, al posto dei giocatori del 1996 del gioco.
- [TODO sessione namespace: i file squadra / numeri di nazione propri del mondo.]

**Regole della mod per questo mondo**
- Riserve del club allenato (rose da 25): ognuna delle 9 riserve tiene nome, ruolo, nazionalità e volto veri, ma la
  somma delle sue abilità non supera quella del più debole dei 16 del club (giocatori di movimento con giocatori di
  movimento, portieri con portieri) e il suo prezzo è uguale a quella somma: le riserve non rendono il club allenato
  più forte o più ricco delle riserve inventate dal gioco.
- Coppe nazionali: il tabellone non ha turni di riposo (il motore ne consente uno in una sola coppa dei pacchetti):
  parte dalla potenza di 2 pari o inferiore ai club ancora in corsa, tenendo i club delle coppie sorteggiate davvero e
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
- [TODO integratore / rose: limiti del motore (cache squadre, coppe, id delle competizioni per mondo), i risultati del
  club allenato nelle stagioni giocate solo coi risultati.]

**Dati e crediti**
- Rose, valori di mercato, allenatori, partecipanti 2026-27 e classifiche 2025-26: **Transfermarkt**
  (transfermarkt.com).
- Attributi dei giocatori: valutazioni **EA SPORTS FC** (ea.com), dati dell'era FC 26.
- Maglie: **contributori di Wikipedia** (CC BY-SA 4.0); collegamenti club -> voce da **Wikidata** (CC0).
- Coefficienti UEFA di federazioni e club: il sito sui coefficienti UEFA di Bert Kassies (kassiesa.net).
