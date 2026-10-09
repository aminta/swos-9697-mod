## English

**SWOS 96/97 Mod 2.6.1: career fix**

The game content is the same as 2.6. This release fixes a bug in career mode that has been there since 1.2.

- **Fixed:** a new career started with a club that plays a European cup in its first season (Juventus, Milan, any club in the 1996-97 European Cup, Cup Winners' Cup or UEFA Cup) was not marked as "set up" until the save was loaded again. Two things could go wrong:
  - if another career had been loaded earlier in the same game session, the new career kept that career's lists of the other continents' club cups (Copa Libertadores, Supercopa, Copa CONMEBOL, the African, Asian and CONCACAF cups);
  - if, in a later season, the club was out of the European cups and the save had never been reloaded, the game took the career for a new one and reset those lists to the 1997 participants, losing the clubs that had really qualified from the South American, African and Asian leagues.
  
  Now every new career is set up at its first season, whatever cup the club plays. Saving and loading once was enough to avoid the problem with 2.6, so existing careers are fine.
- Internal changes to the classic seasons code (the DDR 1988-89 is now built from a data pack, and several packs can go into one build): nothing changes in the game.
- **Upgrade in place:** drop the executable and `DATA\TEAM.020` of your modded game (any release from 1.0 to 2.6, original CD or GOG) into the patcher. The TEAM files are the same as in 2.6.

## Italiano

**SWOS 96/97 Mod 2.6.1: correzione della carriera**

Il contenuto del gioco è quello della 2.6. Questa release corregge un errore della modalità carriera presente dalla 1.2.

- **Corretto:** una carriera nuova iniziata con un club che gioca una coppa europea nella prima stagione (Juventus, Milan, qualunque club in Coppa dei Campioni, Coppa delle Coppe o Coppa UEFA 1996-97) non veniva segnata come "avviata" finché il salvataggio non veniva ricaricato. Potevano succedere due cose:
  - se nella stessa sessione di gioco era stata caricata prima un'altra carriera, la nuova si teneva le liste delle coppe per club degli altri continenti di quella carriera (Copa Libertadores, Supercopa, Copa CONMEBOL, coppe africane, asiatiche e CONCACAF);
  - se in una stagione successiva il club restava fuori dalle coppe europee e il salvataggio non era mai stato ricaricato, il gioco credeva la carriera nuova e riportava quelle liste ai partecipanti del 1997, perdendo le squadre davvero qualificate dai campionati sudamericani, africani e asiatici.
  
  Ora ogni carriera nuova viene avviata alla prima stagione, qualunque coppa giochi il club. Con la 2.6 bastava salvare e ricaricare una volta per evitare il problema, quindi le carriere già in corso vanno bene.
- Modifiche interne al codice delle stagioni storiche (la DDR 1988-89 ora viene costruita da un pacchetto di dati, e in una build possono entrare più pacchetti): nel gioco non cambia nulla.
- **Aggiornamento sul posto:** trascina nel patcher l'exe e `DATA\TEAM.020` del gioco già modificato (una qualsiasi release dalla 1.0 alla 2.6, CD originale o GOG). I file TEAM sono gli stessi della 2.6.
