# SWOS 96/97 Mod

**[English](#english) · [Italiano](#italiano)**

## English

### Foreword

A long time ago - in 2004 - in a galaxy far, far away, where the Internet was only just leaving behind the sound of the modem, artificial intelligence was the stuff of science fiction novels and video games were sold in elegant cardboard boxes in shops, yours truly - together with Ali Erdinc Koroglu, Jan Wickberg, Martin Binet, Zlatko Karakas, Ross Mayhew and Steve Smith - founded the Swos Working Group (https://web.archive.org/web/20040831085727/http://swos.erdinc.info/) in honour of our all-time favourite video game: the 1996-1997 edition of Sensible World of Soccer. We were driven by a dream: to make that game even better by adding a few competitions whose absence we felt especially keenly. The Italian Serie C (split into C1 and C2), where players who would later become international stars, such as Simone Inzaghi and Gianluca Zambrotta, were playing, and the South American cups, above all the legendary Copa Libertadores, which, in an age when football on TV was still a novelty and far from plentiful, held for us the charm of exotic, faraway things. We would have loved to play these competitions above all in career mode, the SWOS players' absolute favourite: partly because in season mode and in the preset competitions we had already managed to add them, in a new edition of SWOS that was going to be called Swos 2004. The work was done by reverse engineering and hex editing; I remember the thrill of discovering the routines that add competitions, but also the bitter frustration of not being able to make them work in career mode, which would freeze every time. Today, in the year of grace 2026, I wanted to settle the score with this personal story that never left me over these two decades: the regret of having come close to a dream and never quite making it. After all, I told myself in an attempt at consolation, I ended up becoming a web and mobile developer; reverse engineering 1996 x86 code had already been a miracle, and hardly any of the many modern modders had managed the feat.

Today, thanks to AI, which has changed the very idea of programming forever, the feat is accomplished: you can now download the patch that adds, in every language of the game, Serie C1 and C2 to the Italian league, with the original squads of the time, and above all adds, for South America, the Copa Libertadores, the CONMEBOL and the Supercopa, with the entry rules of the day. And, as the icing on the cake, the Intercontinental Cup could not be missing. What matters to me, though, is not only the result but also the explanation of how we got there through AI. So here we publish, in English and Italian, the complete documentation of the method followed to create the patches, which finally revealed to me what we had not understood back in 2004, and which I hope will inspire other developers and lovers of the most beautiful video game in the world to expand its career mode even further. An immense thank you to the work of Zlatko Karakas, whose fundamental disassembly of the original executable I found after so many years of absence (https://github.com/zlatkok/swos-port).

This patch is dedicated to the memory of Steve Smith, an extraordinary compiler of updated squads for SWOS, who left us far too soon. And to everyone who hopes to see, sooner or later, a dream come true, even one that has lasted 22 years…

— Davide Lorigliola

### The patch

Patch for **Sensible World of Soccer 96/97** (DOS, CD or GOG version): ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE, GERMAN.EXE.

- **Italy with 4 divisions:** Serie A, B, C1 and C2 (18 clubs each), with the real 1996-97 clubs, real squads and coaches. Fixes the end-of-season freeze that plagued the 1997 mods.
- **South American cups:** Copa Libertadores, Supercopa and Copa CONMEBOL in menus, world view and career mode, with qualifiers from the South American standings and the holder rules.
- **Intercontinental Cup:** in December between the Champions Cup winner and the Libertadores winner, updated every season and saved with the career.
- **New countries (1.1):** Costa Rica with its league; Egypt, Morocco, Tunisia, Nigeria and Cameroon with their 1996-97 league (real clubs and final order) and national cup.
- **African club cups (1.1):** CAF Champions League, CAF Cup Winners Cup and CAF Cup in menus, world view and career mode, with qualifiers from the standings of the 8 African countries, saved with the career.
- **Copa Libertadores with 5 groups (1.3):** 20 clubs (champion and runner-up of each of the 10 countries) in 5 groups of 4, as in 1996-97; the top 3 of each group and the best 4th go to the round of 16. The game has no byes, so the holder plays the group stage in place of its country's runner-up: with 16 of 20 going through it is almost a bye. Thanks to Playaveli (Swos2020) for the report. Saves of 1.0–1.2 still load.
- **Asia and Central America (1.2):** South Korea, China, Saudi Arabia, Guatemala and Honduras with their 1996-97 league and national cup; Asian Club Championship, Asian Cup Winners Cup and the CONCACAF Champions Cup (6 countries), all in career mode.

**Invented players (1.1–1.2).** For the 138 clubs of Egypt, Morocco, Tunisia, Nigeria, Cameroon, South Korea, China, Saudi Arabia, Guatemala and Honduras we could not find the 1996-97 squads: no reliable source lists the players and coaches of those leagues for that season. Clubs, final order and relative strength are real; player and coach names are invented from common names of each country. If you have real squads from those years, even for a single club, please help us: open an [issue](../../issues) or write on the forum.

### Install
1. Download `swos-9697-mod-patcher.html` from the [Releases](../../releases) page and open it in a browser (works offline too).
2. Drop your language's executable and `DATA\TEAM.020` from the game folder, then download the patched files (from 1.1–1.2 also the new `TEAM.052`, `053`, `054`, `056`, `058`, `061`, `063`, `086`, `087`, `088`).
3. Copy them into the game folder (the TEAM files into `DATA`) after backing it up. Start a new career.

The patcher ships only differences and checks every file before and after patching: an original copy of the game is required. It works with both the original CD and the GOG version (from 1.0.1).

### For developers
- Technical manual: [English](https://aminta.github.io/swos-9697-mod/) (ENGLISH.EXE addresses) · [Italian](https://aminta.github.io/swos-9697-mod/it.html) (ITALIAN.EXE addresses)
- Build: put the original executables and `DATA/TEAM.020` in `orig/`, then `cd tools && python3 patch.py it|en|fr|de` (needs `nasm`). Patcher: `python3 tools/mkpatcher.py`.
- The reference disassembly comes from [swos-port](https://github.com/zlatkok/swos-port) (`swos/swos.asm`, in `ref/`).
- Detailed log of every session: [`notes/STATUS.md`](notes/STATUS.md).

## Italiano

### Premessa

Tanto tempo fa - anno 2004 - in una galassia lontana lontana, dove Internet stava appena separandosi dal suono del modem, l'intelligenza artificiale era un argomento da romanzi di fantascienza e i videogiochi si vendevano in eleganti scatole di cartone nei negozi, il sottoscritto - insieme ad Ali Erdinc Koroglu, Jan Wickberg, Martin Binet, Zlatko Karakas, Ross Mayhew e Steve Smith - fondò lo Swos Working Group (https://web.archive.org/web/20040831085727/http://swos.erdinc.info/) in onore del nostro videogioco preferito di sempre: l'edizione 1996-1997 di Sensible World of Soccer. Eravamo animati da un sogno: rendere ancora più bello quel gioco aggiungendo alcune competizioni la cui mancanza avvertivamo particolarmente amara. La serie C italiana (divisa in C1 e C2), in cui giocavano atleti che sarebbero poi diventati campioni a livello internazionale come Simone Inzaghi e Gianluca Zambrotta, e le coppe sudamericane, su tutte la mitica Copa Libertadores di cui, in un'epoca nella quale il calcio in tv era ancora una novità e non così abbondante, sentivamo il fascino delle cose esotiche e lontane. Ci sarebbe piaciuto giocare queste competizioni particolarmente in modalità carriera, quella preferita in assoluto dai giocatori di Swos: anche perché, nella modalità stagione e competizioni predefinite, eravamo già riusciti ad aggiungerle in una nuova edizione di Swos che si sarebbe dovuta chiamare Swos 2004. Il lavoro fu fatto con il reverse engineering e l'hex editing, ricordo l'emozione nello scoprire le routine di aggiunta delle competizioni ma anche l'amara frustrazione di non riuscire a farle funzionare in modalità carriera, che puntualmente si bloccava. Oggi, anno di grazia 2026, ho voluto chiudere il conto con questa storia personale che durante questi due decenni non mi aveva mai abbandonato, che era il rimpianto di essere arrivati vicino a un sogno e di non esserci mai riusciti. Del resto, mi dicevo per tentare di consolarmi, io alla fine sono diventato uno sviluppatore web e mobile, quello del reverse engineering su un codice x86 del 1996 era stato già un miracolo e per lo più nessuno dei tantissimi modder moderni era riuscito a compiere l'impresa.

Oggi, grazie alla AI, che ha cambiato per sempre il concetto stesso di programmazione, l'impresa è compiuta: potete ora scaricare la patch che aggiunge, in tutte le lingue del gioco, la serie C1 e C2 al campionato italiano, con le rose originali dell'epoca, ma soprattutto aggiunge per il Sud America la Coppa Libertadores, la Conmebol e la Supercopa, con le regole di ammissione di allora. E, come ciliegina sulla torta, non poteva mancare la Coppa Intercontinentale. Quello che mi interessa, però, non è solo il risultato, ma anche la spiegazione di come attraverso la AI ci si è arrivati. Quindi qui pubblichiamo, in inglese e in italiano, la documentazione completa del metodo seguito per creare le patch, che mi ha finalmente svelato cosa non avevamo capito nel lontano 2004 e spero possa ispirare altri sviluppatori e amanti del videogioco più bello del mondo a espanderne ulteriormente la modalità carriera. Un grazie immenso al lavoro di Zlatko Karakas, di cui dopo tanti anni di assenza ho trovato il fondamentale lavoro di disassemblaggio dell'exe originale (https://github.com/zlatkok/swos-port).

Questa patch è dedicata alla memoria di Steve Smith, straordinario compilatore di rose aggiornate per Swos, che ci ha lasciati troppo presto. E a tutti quelli che sperano di vedere, prima o poi, realizzato un sogno che può essere lungo anche 22 anni…

— Davide Lorigliola

### La patch

Patch per **Sensible World of Soccer 96/97** (versione DOS, CD o GOG): ITALIAN.EXE, ENGLISH.EXE, FRENCH.EXE, GERMAN.EXE.

- **Italia a 4 divisioni:** Serie A, B, C1 e C2 (18 squadre ciascuna), con i club reali 1996-97, rose vere e allenatori. Risolto il blocco di fine stagione che affliggeva i mod del 1997.
- **Coppe sudamericane:** Copa Libertadores, Supercopa e Copa CONMEBOL nei menu, nella vista mondo e in carriera, con le qualificate prese dalle classifiche sudamericane e le regole della detentrice.
- **Coppa Intercontinentale:** a dicembre fra la vincitrice della Coppa Campioni e quella della Libertadores, aggiornata ogni stagione e salvata con la carriera.
- **Nuove nazioni (1.1):** Costa Rica con il suo campionato; Egitto, Marocco, Tunisia, Nigeria e Camerun con il campionato 1996-97 (club e classifica finale reali) e la coppa nazionale.
- **Coppe africane per club (1.1):** CAF Champions League, Coppa delle Coppe CAF e CAF Cup nei menu, nella vista mondo e in carriera, con le qualificate prese dalle classifiche delle 8 nazioni africane e salvate con la carriera.
- **Copa Libertadores a 5 gironi (1.3):** 20 club (campione e seconda di ognuno dei 10 paesi) in 5 gironi da 4, come nel 1996-97; passano agli ottavi le prime 3 di ogni girone e la migliore quarta. Il gioco non prevede esenzioni, quindi la detentrice gioca i gironi al posto della seconda del suo paese: con 16 qualificate su 20 è quasi un'esenzione. Grazie a Playaveli (Swos2020) per la segnalazione. I salvataggi 1.0–1.2 si caricano ancora.
- **Asia e Centroamerica (1.2):** Corea del Sud, Cina, Arabia Saudita, Guatemala e Honduras con campionato 1996-97 e coppa nazionale; Asian Club Championship, Asian Cup Winners Cup e CONCACAF Champions Cup (6 nazioni), tutte in carriera.

**Giocatori inventati (1.1–1.2).** Per i 138 club di Egitto, Marocco, Tunisia, Nigeria, Camerun, Corea del Sud, Cina, Arabia Saudita, Guatemala e Honduras non siamo riusciti a trovare le rose 1996-97: non esistono fonti affidabili con i giocatori e gli allenatori di quei campionati in quella stagione. Club, classifica finale e forza relativa sono reali; i nomi di giocatori e allenatori sono invece inventati con nomi comuni di ogni paese. Se avete rose reali di quegli anni, anche di un solo club, aiutateci: aprite una [issue](../../issues) o scriveteci sul forum.

### Installazione
1. Scarica `swos-9697-mod-patcher.html` dalla pagina [Releases](../../releases) e aprilo nel browser (funziona anche offline).
2. Trascina l'exe della tua lingua e `DATA\TEAM.020` dalla cartella del gioco, poi scarica i file modificati (dalla 1.1–1.2 anche i nuovi `TEAM.052`, `053`, `054`, `056`, `058`, `061`, `063`, `086`, `087`, `088`).
3. Copiali nella cartella del gioco (i file TEAM in `DATA`), dopo aver fatto una copia di sicurezza. Inizia una carriera nuova.

Il patcher contiene solo differenze e controlla i file prima e dopo la modifica: serve una copia originale del gioco. Funziona sia con il CD originale sia con la versione GOG (dalla 1.0.1).

### Per sviluppatori
- Manuale tecnico: [italiano](https://aminta.github.io/swos-9697-mod/it.html) (indirizzi di ITALIAN.EXE) · [inglese](https://aminta.github.io/swos-9697-mod/) (indirizzi di ENGLISH.EXE)
- Build: metti gli exe e `DATA/TEAM.020` originali in `orig/`, poi `cd tools && python3 patch.py it|en|fr|de` (serve `nasm`). Patcher: `python3 tools/mkpatcher.py`.
- Il disassemblato di riferimento viene da [swos-port](https://github.com/zlatkok/swos-port) (`swos/swos.asm`, in `ref/`).
- Registro dettagliato di ogni sessione: [`notes/STATUS.md`](notes/STATUS.md).

---
Mod by Davide Lorigliola, with Claude. Sensible World of Soccer © Sensible Software / Codemasters. Squad data from it.wikipedia 1996-97 club season pages; African, Asian and Central American tables from RSSSF and Wikipedia.
