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

#### Training, squad and market
- **Training match:** [TO COMPLETE: Panchina — the bench in a training match has 2 reserves + 2 substitutes; kits A and B in training].
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

#### Finances
- [TO COMPLETE: Integratore, long text — why club finances were out of balance (running costs are about 3.2 times the wage bill, every week, while income did not follow the squad), what changed, with examples of big clubs; the 16-bit gate-receipts overflow fixed; thanks to Nicola for the report. Davide wants this explained at length.]

#### Coming in this version, text to come
- [TO COMPLETE: Panchina — opponent list in the match: UP on the coach in the bench menu shows the opponent's squad, read-only; not with SWOS++.]
- [TO COMPLETE: Motore — B-team call-ups: one match and season attachment, real rules per country, ages.]

#### Fixes
- **New Zealand, last round of the Championship group.** If your club rests in the last round of the Championship group, the menu now offers FINISH SEASON. Press it: if your club reached the Grand Final, MATCH comes back and you play it; otherwise the season ends. (Before, the menu could offer a match on the rest day.) The real champion was already right; this removes the confusing final that did not count mentioned in the 4.0.5 notes.
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

#### Allenamento, rosa e mercato
- **Partita di allenamento:** [DA COMPLETARE: Panchina — la panchina in allenamento ha 2 riserve + 2 sostituti; maglie A e B in allenamento].
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

#### Finanze
- [DA COMPLETARE: Integratore, testo lungo — perché le finanze dei club erano fuori equilibrio (i costi di gestione sono circa 3,2 volte il monte stipendi, ogni settimana, mentre gli incassi non seguivano la rosa), cosa è cambiato, con esempi di grandi club; il troncamento a 16 bit degli incassi della partita corretto; grazie a Nicola per la segnalazione. Davide vuole che sia spiegato a lungo.]

#### In arrivo in questa versione, testo da completare
- [DA COMPLETARE: Panchina — elenco avversari in partita: SU sull'allenatore nel menu panchina mostra la rosa dell'avversario, sola lettura; non con SWOS++.]
- [DA COMPLETARE: Motore — convocazioni dalla squadra B: una partita e aggregazione stagionale, regole vere per paese, età.]

#### Correzioni
- **Nuova Zelanda, ultima giornata del gruppo del Championship.** Se il tuo club riposa nell'ultima giornata del gruppo del Championship, il menu ora offre FINISCI STAGIONE. Premilo: se il tuo club è arrivato alla Grand Final torna PARTITA e la giochi; altrimenti la stagione finisce. (Prima il menu poteva offrire una partita nel giorno di riposo.) Il campione vero era già giusto; questo toglie la finale confusa che non contava, citata nelle note della 4.0.5.
- **Una squadra di play-off che rifiuta il posto** non fa più leggere al gioco dati sbagliati a fine stagione (si vedeva con San Marino; trovato da Ben Baker).

### Da sapere
- [DA COMPLETARE a testi definitivi: limiti dichiarati, elenco di cosa è disattivato con SWOS++.]

### Ringraziamenti
Grazie a Roman per aver chiesto un'installazione più semplice, a Marco per le idee su allenamento, numeri di maglia e tastiera, a Enzo per la segnalazione sull'elenco del mercato, a Nicola per quella sulle finanze, a Francesco e a Ben Baker per la segnalazione su San Marino. [DA VERIFICARE: crediti esatti per voce con i proprietari.]
