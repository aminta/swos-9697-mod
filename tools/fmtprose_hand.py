"""Hand-written FORMAT texts (4.0, regia / Davide): the formats the generator tells too tersely. Keyed by (world, the
Italian title); 4 languages, plain sentences, the same facts as the release notes and the packs' data."""

_SB_PO = {
    'it': "Le prime 2 salgono in Serie A. La 3a sale direttamente se ha più di 14 punti di vantaggio sulla 4a; "
          "altrimenti dalla 3a all'8a si gioca il play-off per il terzo posto: turno preliminare 5a contro 8a e 6a "
          "contro 7a in gara unica in casa della meglio piazzata (supplementari, poi passa la meglio piazzata); "
          "semifinali 3a e 4a contro le vincenti, andata e ritorno, in parità passa la meglio piazzata; finale andata "
          "e ritorno, in parità passa la meglio piazzata, ma a pari punti in campionato si va a supplementari e rigori.",
    'en': "The top 2 go up to Serie A. The 3rd goes up directly if more than 14 points clear of the 4th; otherwise "
          "the 3rd to 8th play off for the third place: a preliminary round, 5th v 8th and 6th v 7th, single match at "
          "the better-placed club (extra time, then the better-placed club goes through); semi-finals, 3rd and 4th v "
          "the winners, over two legs, if level the better-placed club goes through; a two-legged final, if level the "
          "better-placed club, but clubs level on league points go to extra time and penalties.",
    'fr': "Les 2 premiers montent en Serie A. Le 3e monte directement s'il a plus de 14 points d'avance sur le 4e ; "
          "sinon du 3e au 8e on joue les barrages pour la troisième place : tour préliminaire 5e contre 8e et 6e "
          "contre 7e sur un match chez le mieux classé (prolongation, puis le mieux classé passe) ; demi-finales, 3e "
          "et 4e contre les vainqueurs, en aller et retour, en cas d'égalité le mieux classé passe ; finale en aller "
          "et retour, en cas d'égalité le mieux classé, mais à égalité de points en championnat prolongation et tirs "
          "au but.",
    'de': "Die ersten 2 steigen in die Serie A auf. Der 3. steigt direkt auf, wenn er mehr als 14 Punkte vor dem 4. "
          "liegt; sonst spielen der 3. bis 8. um den dritten Platz: Vorrunde 5. gegen 8. und 6. gegen 7. in einem "
          "Spiel beim besser Platzierten (Verlängerung, dann kommt der besser Platzierte weiter); Halbfinale, 3. und "
          "4. gegen die Sieger, mit Hin- und Rückspiel, bei Gleichstand der besser Platzierte; Finale mit Hin- und "
          "Rückspiel, bei Gleichstand der besser Platzierte, bei gleichen Ligapunkten aber Verlängerung und "
          "Elfmeterschießen.",
}
_SB_PU = {
    'it': "Retrocedono le ultime 3. La 17a retrocede direttamente se la 16a ha più di 4 punti di vantaggio; "
          "altrimenti si gioca il play-out 16a contro 17a, andata e ritorno con l'andata in casa della 17a: in parità "
          "resta la 16a, ma a pari punti in campionato si va a supplementari e rigori.",
    'en': "The bottom 3 go down. The 17th goes down directly if the 16th is more than 4 points clear; otherwise the "
          "16th and 17th play out over two legs, the first at the 17th: if level the 16th stays up, but clubs level "
          "on league points go to extra time and penalties.",
    'fr': "Les 3 derniers descendent. Le 17e descend directement si le 16e a plus de 4 points d'avance ; sinon le 16e "
          "et le 17e jouent un barrage de maintien en aller et retour, l'aller chez le 17e : en cas d'égalité le 16e "
          "reste, mais à égalité de points en championnat prolongation et tirs au but.",
    'de': "Die letzten 3 steigen ab. Der 17. steigt direkt ab, wenn der 16. mehr als 4 Punkte vorn liegt; sonst "
          "spielen der 16. und der 17. die Relegation mit Hin- und Rückspiel, das Hinspiel beim 17.: bei Gleichstand "
          "bleibt der 16. drin, bei gleichen Ligapunkten aber Verlängerung und Elfmeterschießen.",
}
_SC_PO = {
    'it': "La quarta promossa in Serie B esce da un play-off di 28 squadre: dalla 2a alla 10a dei tre gironi e la "
          "vincitrice della Coppa Italia Serie C. Fase dei gironi: 5a contro 10a, 6a contro 9a, 7a contro 8a in gara "
          "unica in casa della meglio piazzata (in parità passa la meglio piazzata), poi le vincenti con la 4a. Fase "
          "nazionale: due turni con teste di serie, andata e ritorno, in parità passa la testa di serie. Final Four: "
          "sorteggio libero, semifinali e finale di andata e ritorno, supplementari e rigori.",
    'en': "The fourth club going up to Serie B comes from a 28-club play-off: the 2nd to 10th of the three groups and "
          "the Coppa Italia Serie C winner. Group phase: 5th v 10th, 6th v 9th, 7th v 8th, single match at the "
          "better-placed club (if level the better-placed club), then the winners with the 4th. National phase: two "
          "seeded rounds over two legs, if level the seeded club. Final Four: a free draw, two-legged semi-finals and "
          "final, extra time and penalties.",
    'fr': "Le quatrième promu en Serie B sort de barrages à 28 clubs : du 2e au 10e des trois groupes et le vainqueur "
          "de la Coppa Italia Serie C. Phase des groupes : 5e contre 10e, 6e contre 9e, 7e contre 8e sur un match chez "
          "le mieux classé (en cas d'égalité le mieux classé), puis les vainqueurs avec le 4e. Phase nationale : deux "
          "tours avec têtes de série en aller et retour, en cas d'égalité la tête de série. Final Four : tirage libre, "
          "demi-finales et finale en aller et retour, prolongation et tirs au but.",
    'de': "Der vierte Aufsteiger in die Serie B kommt aus Playoffs mit 28 Vereinen: der 2. bis 10. der drei Gruppen "
          "und der Sieger der Coppa Italia Serie C. Gruppenphase: 5. gegen 10., 6. gegen 9., 7. gegen 8. in einem "
          "Spiel beim besser Platzierten (bei Gleichstand der besser Platzierte), dann die Sieger mit dem 4. "
          "Nationale Phase: zwei Runden mit Gesetzten, Hin- und Rückspiel, bei Gleichstand der Gesetzte. Final Four: "
          "freie Auslosung, Halbfinale und Finale mit Hin- und Rückspiel, Verlängerung und Elfmeterschießen.",
}
_SC = {
    'it': ["Il girone ha 20 squadre che si affrontano in andata e ritorno: 38 giornate. La vittoria vale 3 punti, il "
           "pareggio 1. La prima sale in Serie B.", _SC_PO['it'],
           "L'ultima retrocede in Serie D. Si giocano anche i play-out, 16a contro 19a e 17a contro 18a, andata e "
           "ritorno: in parità resta la meglio piazzata, e non si giocano con 8 punti o più di distacco; chi perde "
           "retrocede."],
    'en': ["The group has 20 clubs who play each other home and away: 38 matchdays. A win is worth 3 points, a draw "
           "1. The champions go up to Serie B.", _SC_PO['en'],
           "The last club goes down to Serie D. Play-outs too, 16th v 19th and 17th v 18th over two legs: if level "
           "the better-placed club stays up, and they are not played with a gap of 8 points or more; the losers go "
           "down."],
    'fr': ["Le groupe compte 20 clubs qui s'affrontent en aller et retour : 38 journées. La victoire vaut 3 points, "
           "le nul 1. Le premier monte en Serie B.", _SC_PO['fr'],
           "Le dernier descend en Serie D. Barrages de maintien aussi, 16e contre 19e et 17e contre 18e en aller et "
           "retour : en cas d'égalité le mieux classé reste, et pas de barrage avec 8 points d'écart ou plus ; les "
           "perdants descendent."],
    'de': ["Die Gruppe hat 20 Vereine, die mit Hin- und Rückspiel gegeneinander spielen: 38 Spieltage. Ein Sieg "
           "zählt 3 Punkte, ein Remis 1. Der Meister steigt in die Serie B auf.", _SC_PO['de'],
           "Der Letzte steigt in die Serie D ab. Dazu Abstiegs-Playoffs, 16. gegen 19. und 17. gegen 18. mit Hin- "
           "und Rückspiel: bei Gleichstand bleibt der besser Platzierte, nicht gespielt bei 8 oder mehr Punkten "
           "Abstand; die Verlierer steigen ab."],
}
_POULE = {
    'it': ["Le 9 vincitrici dei gironi di Serie D si dividono in tre triangolari (gironi A-B-C, D-E-F, G-H-I), di "
           "sola andata. Le 3 vincitrici e la migliore seconda giocano semifinali sorteggiate di andata e ritorno: "
           "contano punti e gol, senza gol in trasferta, poi i rigori, senza supplementari. La finale è in gara unica "
           "in campo neutro, senza supplementari, poi i rigori. Chi vince è Campione d'Italia Dilettanti."],
    'en': ["The 9 winners of the Serie D groups play three triangulars (groups A-B-C, D-E-F, G-H-I), single round. "
           "The 3 winners and the best runner-up play drawn two-legged semi-finals: points, then goals, no away goals, "
           "then penalties, no extra time. The final is a single match on neutral ground, no extra time, then "
           "penalties. The winner is Italian Amateur Champion."],
    'fr': ["Les 9 vainqueurs des groupes de Serie D jouent trois triangulaires (groupes A-B-C, D-E-F, G-H-I), en "
           "matchs simples. Les 3 vainqueurs et le meilleur deuxième jouent des demi-finales tirées au sort en aller "
           "et retour : points, puis buts, sans buts à l'extérieur, puis tirs au but, sans prolongation. La finale se "
           "joue sur un match sur terrain neutre, sans prolongation, puis tirs au but. Le vainqueur est champion "
           "d'Italie amateur."],
    'de': ["Die 9 Gruppensieger der Serie D spielen drei Dreiergruppen (Gruppen A-B-C, D-E-F, G-H-I), einfache "
           "Runde. Die 3 Sieger und der beste Zweite spielen ausgeloste Halbfinals mit Hin- und Rückspiel: Punkte, "
           "dann Tore, ohne Auswärtstore, dann Elfmeterschießen, ohne Verlängerung. Das Finale ist ein Spiel auf "
           "neutralem Platz, ohne Verlängerung, dann Elfmeterschießen. Der Sieger ist italienischer Amateurmeister."],
}
_MLS = {
    'it': ["Le 30 squadre sono divise in due conference da 15, Est e Ovest, e giocano 34 partite in una sola "
           "classifica; chi fa più punti vince il Supporters' Shield. Non retrocede nessuno.",
           "Le prime 9 di ogni conference vanno ai play-off della MLS Cup: 8a contro 9a in gara unica (wild card, in "
           "parità rigori), poi il primo turno al meglio delle 3 gare, poi semifinali e finali di conference e la MLS "
           "Cup in gara unica in casa della meglio piazzata, con supplementari e rigori."],
    'en': ["The 30 clubs are split into two conferences of 15, East and West, and play 34 matches in one table; the "
           "club with the most points wins the Supporters' Shield. Nobody goes down.",
           "The top 9 of each conference go to the MLS Cup playoffs: 8th v 9th in a single match (the wild card, if "
           "level penalties), then a best-of-three first round, then the conference semi-finals and finals and the "
           "MLS Cup, single matches at the better-placed club, with extra time and penalties."],
    'fr': ["Les 30 clubs sont répartis en deux conférences de 15, Est et Ouest, et jouent 34 matchs dans un seul "
           "classement ; le club qui a le plus de points gagne le Supporters' Shield. Personne ne descend.",
           "Les 9 premiers de chaque conférence vont aux play-offs de la MLS Cup : 8e contre 9e sur un match (wild "
           "card, en cas d'égalité tirs au but), puis un premier tour au meilleur des 3 matchs, puis les demi-finales "
           "et finales de conférence et la MLS Cup sur un match chez le mieux classé, avec prolongation et tirs au "
           "but."],
    'de': ["Die 30 Vereine sind in zwei Conferences zu 15 geteilt, Ost und West, und spielen 34 Spiele in einer "
           "Tabelle; wer die meisten Punkte holt, gewinnt den Supporters' Shield. Niemand steigt ab.",
           "Die ersten 9 jeder Conference kommen in die MLS-Cup-Playoffs: 8. gegen 9. in einem Spiel (Wildcard, bei "
           "Gleichstand Elfmeterschießen), dann eine erste Runde im Modus Best of Three, dann Conference-Halbfinale "
           "und -Finale und der MLS Cup in einem Spiel beim besser Platzierten, mit Verlängerung und "
           "Elfmeterschießen."],
}
_CPL = {
    'it': ["Le prime 4 della Canadian Premier League giocano i play-off: semifinali di andata e ritorno, con "
           "supplementari e rigori, e finale in gara unica in casa della meglio piazzata, con supplementari e rigori. "
           "Chi vince è campione del Canada."],
    'en': ["The top 4 of the Canadian Premier League play the playoffs: two-legged semi-finals, with extra time and "
           "penalties, and a single-match final at the better-placed club, with extra time and penalties. The winner "
           "is the Canadian champion."],
    'fr': ["Les 4 premiers de la Canadian Premier League jouent les play-offs : demi-finales en aller et retour, avec "
           "prolongation et tirs au but, et finale sur un match chez le mieux classé, avec prolongation et tirs au "
           "but. Le vainqueur est champion du Canada."],
    'de': ["Die ersten 4 der Canadian Premier League spielen die Playoffs: Halbfinale mit Hin- und Rückspiel, mit "
           "Verlängerung und Elfmeterschießen, und ein Finale in einem Spiel beim besser Platzierten, mit Verlängerung "
           "und Elfmeterschießen. Der Sieger ist kanadischer Meister."],
}
_AUS = {
    'it': ["Le prime 6 della A-League giocano la Finals Series: la 3a contro la 6a e la 4a contro la 5a in gara unica "
           "in casa della meglio piazzata; le vincenti affrontano la 1a e la 2a in semifinali di andata e ritorno; la "
           "Grand Final è in gara unica in casa della meglio piazzata. In parità supplementari e rigori. Chi vince è "
           "campione d'Australia."],
    'en': ["The top 6 of the A-League play the Finals Series: 3rd v 6th and 4th v 5th in single matches at the "
           "better-placed club; the winners meet the 1st and 2nd in two-legged semi-finals; the Grand Final is a single "
           "match at the better-placed club. If level, extra time and penalties. The winner is the Australian "
           "champion."],
    'fr': ["Les 6 premiers de l'A-League jouent les Finals Series : 3e contre 6e et 4e contre 5e sur un match chez le "
           "mieux classé ; les vainqueurs affrontent le 1er et le 2e en demi-finales aller et retour ; la Grand Final "
           "se joue sur un match chez le mieux classé. En cas d'égalité, prolongation et tirs au but. Le vainqueur est "
           "champion d'Australie."],
    'de': ["Die ersten 6 der A-League spielen die Finals Series: 3. gegen 6. und 4. gegen 5. in einem Spiel beim "
           "besser Platzierten; die Sieger treffen im Halbfinale mit Hin- und Rückspiel auf den 1. und 2.; das Grand "
           "Final ist ein Spiel beim besser Platzierten. Bei Gleichstand Verlängerung und Elfmeterschießen. Der Sieger "
           "ist australischer Meister."],
}
_CRC = {
    'it': ["Le prime 4 giocano i play-off: semifinali e finale di andata e ritorno, in parità passa la meglio "
           "piazzata. Se la vincente non è la prima della classifica, le due si affrontano nella gran finale, andata e "
           "ritorno con supplementari e rigori. Chi vince è campione di Costa Rica."],
    'en': ["The top 4 play the playoffs: two-legged semi-finals and final, if level the better-placed club goes "
           "through. If the winner is not the table's leader, the two meet in the grand final, two legs with extra "
           "time and penalties. The winner is the champion of Costa Rica."],
    'fr': ["Les 4 premiers jouent les play-offs : demi-finales et finale en aller et retour, en cas d'égalité le "
           "mieux classé passe. Si le vainqueur n'est pas le premier du classement, les deux se retrouvent en grande "
           "finale, en aller et retour avec prolongation et tirs au but. Le vainqueur est champion du Costa Rica."],
    'de': ["Die ersten 4 spielen die Playoffs: Halbfinale und Finale mit Hin- und Rückspiel, bei Gleichstand kommt "
           "der besser Platzierte weiter. Ist der Sieger nicht der Tabellenführer, treffen beide im großen Finale "
           "aufeinander, mit Hin- und Rückspiel, Verlängerung und Elfmeterschießen. Der Sieger ist Meister von Costa "
           "Rica."],
}
_MLT = {
    'it': ["Le prime 4 delle fasi del campionato giocano la Final Four in campo neutro: semifinali e finale in gara "
           "unica, con supplementari e rigori. Chi vince è campione di Malta."],
    'en': ["The top 4 of the league's phases play the Final Four on neutral ground: single-match semi-finals and "
           "final, with extra time and penalties. The winner is the champion of Malta."],
    'fr': ["Les 4 premiers des phases du championnat jouent le Final Four sur terrain neutre : demi-finales et finale "
           "sur un match, avec prolongation et tirs au but. Le vainqueur est champion de Malte."],
    'de': ["Die ersten 4 der Ligaphasen spielen das Final Four auf neutralem Platz: Halbfinale und Finale in einem "
           "Spiel, mit Verlängerung und Elfmeterschießen. Der Sieger ist Meister von Malta."],
}


def _cup(it, en, fr, de):
    return {'it': [it], 'en': [en], 'fr': [fr], 'de': [de]}


HAND = {
    (5, 'ITALIA SERIE B'): {l: [{'it': "Il campionato ha 20 squadre che si affrontano in andata e ritorno: 38 giornate. "
                                       "La vittoria vale 3 punti, il pareggio 1.",
                                 'en': "The league has 20 clubs who play each other home and away: 38 matchdays. A win "
                                       "is worth 3 points, a draw 1.",
                                 'fr': "Le championnat compte 20 clubs qui s'affrontent en aller et retour : 38 "
                                       "journées. La victoire vaut 3 points, le nul 1.",
                                 'de': "Die Liga hat 20 Vereine, die mit Hin- und Rückspiel gegeneinander spielen: 38 "
                                       "Spieltage. Ein Sieg zählt 3 Punkte, ein Remis 1."}[l], _SB_PO[l], _SB_PU[l]]
                                for l in _SB_PO},
    (5, 'ITALIA PLAY-OFF SERIE B'): {l: [_SB_PO[l]] for l in _SB_PO},
    (5, 'ITALIA PLAY-OUT SERIE B'): {l: [_SB_PU[l]] for l in _SB_PU},
    (5, 'ITALIA PLAY-OFF SERIE C'): {l: [_SC_PO[l]] for l in _SC_PO},
    (5, 'ITALIA SERIE C GIRONE A'): _SC, (5, 'ITALIA SERIE C GIRONE B'): _SC, (5, 'ITALIA SERIE C GIRONE C'): _SC,
    (5, 'ITALIA POULE SCUDETTO SERIE D'): _POULE,
    (5, 'USA MAJOR LEAGUE SOCCER'): _MLS, (5, 'USA MLS CUP PLAYOFFS'): {l: _MLS[l][1:] for l in _MLS},
    (5, 'CANADA CPL PLAYOFFS'): _CPL, (5, 'AUSTRALIA A-LEAGUE FINALS SERIES'): _AUS,
    (5, 'COSTA RICA PLAYOFFS'): _CRC, (5, 'MALTA PREMIER LEAGUE FINAL FOUR'): _MLT,
    (5, 'ITALIA COPPA ITALIA'): _cup(
        "Coppa a eliminazione diretta. Nel gioco la si gioca dagli ottavi, con 16 squadre: ottavi e quarti in gara "
        "unica, con supplementari e rigori; semifinali di andata e ritorno; finale in gara unica, con supplementari e "
        "rigori. Il primo turno è quello del sorteggio vero.",
        "A knockout cup. In the game it is played from the round of 16, with 16 clubs: the round of 16 and the "
        "quarter-finals in single matches, with extra time and penalties; two-legged semi-finals; a single-match "
        "final, with extra time and penalties. The first round is the real draw.",
        "Coupe à élimination directe. Dans le jeu elle se joue à partir des huitièmes, avec 16 clubs : huitièmes et "
        "quarts sur un match, avec prolongation et tirs au but ; demi-finales en aller et retour ; finale sur un "
        "match, avec prolongation et tirs au but. Le premier tour est celui du vrai tirage.",
        "Ein K.-o.-Pokal. Im Spiel ab dem Achtelfinale mit 16 Vereinen: Achtel- und Viertelfinale in einem Spiel, mit "
        "Verlängerung und Elfmeterschießen; Halbfinale mit Hin- und Rückspiel; Finale in einem Spiel, mit Verlängerung "
        "und Elfmeterschießen. Die erste Runde ist die echte Auslosung."),
    (5, 'INGHILTERRA FA CUP'): _cup(
        "Coppa a eliminazione diretta: nel gioco 64 squadre, dal terzo turno. Ogni turno in gara unica in casa della "
        "squadra sorteggiata per prima, con supplementari e rigori e senza ripetizioni; semifinali e finale a Wembley.",
        "A knockout cup: 64 clubs in the game, from the third round. Every round a single match at the club drawn "
        "first, with extra time and penalties and no replays; semi-finals and final at Wembley.",
        "Coupe à élimination directe : 64 clubs dans le jeu, à partir du troisième tour. Chaque tour sur un match "
        "chez le club tiré en premier, avec prolongation et tirs au but, sans match à rejouer ; demi-finales et "
        "finale à Wembley.",
        "Ein K.-o.-Pokal: 64 Vereine im Spiel, ab der dritten Runde. Jede Runde ein Spiel beim zuerst gezogenen "
        "Verein, mit Verlängerung und Elfmeterschießen, ohne Wiederholungsspiele; Halbfinale und Finale in Wembley."),
    (5, 'SPAGNA COPA DEL REY'): _cup(
        "Coppa a eliminazione diretta, in gara unica in casa della squadra di categoria inferiore, con supplementari e "
        "rigori; le squadre di coppa europea entrano più tardi. Semifinali di andata e ritorno; finale in gara unica "
        "in campo neutro.",
        "A knockout cup, single matches at the lower-division club, with extra time and penalties; the clubs in "
        "European cups enter later. Two-legged semi-finals; a single-match final on neutral ground.",
        "Coupe à élimination directe, sur un match chez le club de division inférieure, avec prolongation et tirs au "
        "but ; les clubs européens entrent plus tard. Demi-finales en aller et retour ; finale sur un match sur "
        "terrain neutre.",
        "Ein K.-o.-Pokal, ein Spiel beim klassentieferen Verein, mit Verlängerung und Elfmeterschießen; die "
        "Europapokal-Teilnehmer steigen später ein. Halbfinale mit Hin- und Rückspiel; Finale in einem Spiel auf "
        "neutralem Platz."),
    (5, 'GERMANIA DFB-POKAL'): _cup(
        "Coppa a eliminazione diretta con 64 squadre, in gara unica: la squadra dilettante o di categoria inferiore "
        "gioca in casa. In parità supplementari e rigori. Finale a Berlino.",
        "A knockout cup with 64 clubs, single matches: the amateur or lower-division club plays at home. If level, "
        "extra time and penalties. The final in Berlin.",
        "Coupe à élimination directe à 64 clubs, sur un match : le club amateur ou de division inférieure reçoit. En "
        "cas d'égalité, prolongation et tirs au but. Finale à Berlin.",
        "Ein K.-o.-Pokal mit 64 Vereinen, ein Spiel: der Amateur- oder klassentiefere Verein hat Heimrecht. Bei "
        "Gleichstand Verlängerung und Elfmeterschießen. Finale in Berlin."),
    (5, 'FRANCIA COUPE DE FRANCE'): _cup(
        "Coppa a eliminazione diretta aperta a tutti i club, in gara unica in casa della squadra di categoria "
        "inferiore. In parità si va direttamente ai rigori, senza supplementari, tranne in finale. Finale allo Stade "
        "de France.",
        "A knockout cup open to every club, single matches at the lower-division club. If level, straight to "
        "penalties, no extra time, except in the final. The final at the Stade de France.",
        "Coupe à élimination directe ouverte à tous les clubs, sur un match chez le club de division inférieure. En "
        "cas d'égalité, directement les tirs au but, sans prolongation, sauf en finale. Finale au Stade de France.",
        "Ein K.-o.-Pokal für alle Vereine, ein Spiel beim klassentieferen Verein. Bei Gleichstand direkt "
        "Elfmeterschießen, ohne Verlängerung, außer im Finale. Finale im Stade de France."),
}
