"""The FORMAT page in plain prose (4.0, Davide: the schematic lines were hard to read). A competition's text explains,
in order, how its season is organised, who meets whom and how often, who goes through, how the title, the places and
the relegation are decided. Proposal stage: the first texts, for Davide's OK, before every competition gets one;
fmtgame uses a text here in place of its schematic lines (the table colours' lines follow).

PROSE: {(world, title as the game shows it): {lang: [paragraph, ...]}}. The small font has the apostrophe, no accents
(fmtgame's ascii_up drops them); lines wrap by pixel width (fmtgame.wrap_px).
"""

PROSE = {
    (5, 'ARGENTINA LIGA PROFESIONAL'): {
        'it': ["Il campionato si gioca in due tornei, Apertura e Clausura. In ognuno le 30 squadre sono divise in due "
               "zone da 15: ogni squadra affronta una volta le altre 14 della sua zona, il suo rivale storico "
               "dell'altra zona e un avversario sorteggiato (16 giornate). Le prime 8 di ogni zona vanno agli ottavi, "
               "incrociati tra le zone (1a contro 8a e cosi via), poi quarti, semifinali e finale in campo neutro: "
               "chi vince e campione del torneo.",
               "La classifica annuale somma i due tornei e assegna il titolo di Campeon de Liga e i posti in "
               "Libertadores e Sudamericana. Retrocede chi ha il peggior promedio (la media punti delle ultime 3 "
               "stagioni) e l'ultimo della classifica annuale."],
    },
    (5, 'ITALIA SERIE D GIRONE A'): {
        'it': ["Il girone ha 17 squadre che si affrontano in andata e ritorno: 34 giornate, e ogni giornata una "
               "squadra riposa. La vittoria vale 3 punti, il pareggio 1.",
               "La prima sale in Serie C. Dalla 2a alla 5a si giocano i play-off del girone (2a contro 5a, 3a contro "
               "4a, poi la finale): gara unica in casa della meglio piazzata, supplementari e poi passa la meglio "
               "piazzata. Non promuovono nessuno: decidono la graduatoria dei ripescaggi.",
               "Dalla 12a alla 15a si giocano i play-out (12a contro 15a, 13a contro 14a) con le stesse regole: chi "
               "perde retrocede, e non si giocano se le due squadre sono distanti 8 punti o piu. Le ultime 2 "
               "retrocedono in Eccellenza.",
               "Le 9 vincitrici dei gironi giocano la Poule Scudetto per il titolo di Campione d'Italia Dilettanti: "
               "tre triangolari, poi semifinali sorteggiate di andata e ritorno e la finale in campo neutro."],
    },
    (5, 'UEFA CHAMPIONS LEAGUE'): {
        'it': ["Alla fase campionato partecipano 36 squadre, divise in 4 fasce da 9. Ogni squadra gioca 8 partite, "
               "contro 2 avversarie di ogni fascia, una in casa e una in trasferta, mai contro una squadra della sua "
               "federazione e al massimo contro 2 della stessa.",
               "C e una sola classifica: le prime 8 vanno direttamente agli ottavi, dalla 9a alla 24a si giocano gli "
               "spareggi (9a e 10a contro 23a e 24a e cosi via, ritorno in casa della meglio piazzata), dalla 25a in "
               "giu si esce.",
               "Ottavi, quarti e semifinali seguono un tabellone fisso dai piazzamenti, con andata e ritorno: in "
               "parita supplementari e rigori, senza gol in trasferta. La finale si gioca in gara unica.",
               "A parita di punti contano la differenza reti, i gol segnati, i gol in trasferta, le vittorie, le "
               "vittorie in trasferta, poi punti, differenza reti e gol delle avversarie, i punti disciplinari e il "
               "coefficiente.",
               "Prima della fase campionato si giocano i turni preliminari dell access list 2026-27 (percorso "
               "campioni e percorso piazzate); chi viene eliminato scende in Europa League o Conference League."],
    },
}


def text(world, title, lang):
    """The paragraphs for this competition, or None (the schematic lines stay)."""
    p = PROSE.get((world, title.strip()), {}).get(lang)
    return list(p) if p else None
