import os

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
        'en': ["The league is played as two tournaments, the Apertura and the Clausura. In each, the 30 clubs are split into two zones of 15: every club meets the other 14 of its zone once, its traditional rival from the other zone and one drawn opponent (16 matchdays). The top 8 of each zone go into the round of 16, crossed between the zones (1st v 8th and so on), then quarter-finals, semi-finals and a final on neutral ground: the winner is the tournament's champion.", 'The annual table adds up both tournaments and gives the Campeon de Liga title and the Libertadores and Sudamericana places. Relegated: the club with the worst promedio (the average points of the last 3 seasons) and the last of the annual table.'],
        'fr': ["Le championnat se joue en deux tournois, l'Apertura et le Clausura. Dans chacun, les 30 clubs sont répartis en deux zones de 15 : chaque club affronte une fois les 14 autres de sa zone, son rival historique de l'autre zone et un adversaire tiré au sort (16 journées). Les 8 premiers de chaque zone vont en huitièmes, croisés entre les zones (1er contre 8e et ainsi de suite), puis quarts, demi-finales et finale sur terrain neutre : le vainqueur est champion du tournoi.", 'Le classement annuel additionne les deux tournois et donne le titre de Campeon de Liga et les places en Libertadores et Sudamericana. Descendent le club au plus mauvais promedio (la moyenne de points des 3 dernières saisons) et le dernier du classement annuel.'],
        'de': ['Die Liga wird in zwei Turnieren gespielt, Apertura und Clausura. In jedem sind die 30 Vereine in zwei Zonen zu 15 geteilt: jeder Verein spielt einmal gegen die anderen 14 seiner Zone, seinen Traditionsrivalen aus der anderen Zone und einen ausgelosten Gegner (16 Spieltage). Die ersten 8 jeder Zone kommen ins Achtelfinale, über Kreuz zwischen den Zonen (1. gegen 8. usw.), dann Viertelfinale, Halbfinale und ein Finale auf neutralem Platz: der Sieger ist Meister des Turniers.', 'Die Jahrestabelle zählt beide Turniere zusammen und vergibt den Titel Campeon de Liga und die Plätze in Libertadores und Sudamericana. Absteiger: der Verein mit dem schlechtesten Promedio (Punkteschnitt der letzten 3 Saisons) und der Letzte der Jahrestabelle.'],
    },
    (5, 'UEFA CHAMPIONS LEAGUE'): {
        'it': ["Alla fase campionato partecipano 36 squadre, divise in 4 fasce da 9. Ogni squadra gioca 8 partite, "
               "contro 2 avversarie di ogni fascia, una in casa e una in trasferta, mai contro una squadra della sua "
               "federazione e al massimo contro 2 della stessa.",
               "C'e una sola classifica: le prime 8 vanno direttamente agli ottavi, dalla 9a alla 24a si giocano gli "
               "spareggi (9a e 10a contro 23a e 24a e cosi via, ritorno in casa della meglio piazzata), dalla 25a in "
               "giu si esce.",
               "Ottavi, quarti e semifinali seguono un tabellone fisso dai piazzamenti, con andata e ritorno: in "
               "parita supplementari e rigori, senza gol in trasferta. La finale si gioca in gara unica.",
               "A parita di punti contano la differenza reti, i gol segnati, i gol in trasferta, le vittorie, le "
               "vittorie in trasferta, poi punti, differenza reti e gol delle avversarie, i punti disciplinari e il "
               "coefficiente.",
               "Prima della fase campionato si giocano i turni preliminari dell'access list 2026-27 (percorso "
               "campioni e percorso piazzate); chi viene eliminato scende in Europa League o Conference League."],
        'en': ['36 clubs take part in the league phase, in 4 pots of 9. Each club plays 8 matches, against 2 opponents from each pot, one at home and one away, never a club of its own association and at most 2 from the same one.', 'There is a single table: the top 8 go straight into the round of 16, the 9th to 24th play the knockout play-offs (9th and 10th v 23rd and 24th and so on, second leg at the better-placed club), from 25th down the clubs are out.', 'The round of 16, quarter-finals and semi-finals follow a bracket fixed by the places, over two legs: if level, extra time and penalties, with no away goals. The final is a single match.', "Level on points, the order is decided by goal difference, goals scored, away goals, wins, away wins, then the opponents' points, goal difference and goals, disciplinary points and the coefficient.", 'Before the league phase come the qualifying rounds of the 2026-27 access list (champions path and league path); the clubs knocked out drop into the Europa League or the Conference League.'],
        'fr': ["36 clubs disputent la phase de ligue, en 4 chapeaux de 9. Chaque club joue 8 matchs, contre 2 adversaires de chaque chapeau, un à domicile et un à l'extérieur, jamais contre un club de son association et au plus contre 2 d'une même association.", 'Il y a un classement unique : les 8 premiers vont directement en huitièmes, du 9e au 24e on joue les barrages (9e et 10e contre 23e et 24e et ainsi de suite, retour chez le mieux classé), à partir du 25e on est éliminé.', "Huitièmes, quarts et demi-finales suivent un tableau fixé par les places, en aller et retour : en cas d'égalité, prolongation et tirs au but, sans buts à l'extérieur. La finale se joue sur un match.", "À égalité de points comptent la différence de buts, les buts marqués, les buts à l'extérieur, les victoires, les victoires à l'extérieur, puis les points, la différence de buts et les buts des adversaires, les points disciplinaires et le coefficient.", "Avant la phase de ligue se jouent les tours de qualification de la liste d'accès 2026-27 (voie des champions et voie de la ligue), les éliminés descendent en Ligue Europa ou en Ligue Conférence."],
        'de': ['36 Vereine spielen die Ligaphase, in 4 Töpfen zu 9. Jeder Verein bestreitet 8 Spiele, gegen 2 Gegner aus jedem Topf, eines daheim und eines auswärts, nie gegen einen Verein des eigenen Verbands und höchstens gegen 2 aus demselben.', 'Es gibt eine einzige Tabelle: die ersten 8 kommen direkt ins Achtelfinale, der 9. bis 24. spielen die K.-o.-Playoffs (9. und 10. gegen 23. und 24. usw., Rückspiel beim besser Platzierten), ab dem 25. ist man ausgeschieden.', 'Achtel-, Viertel- und Halbfinale folgen einem festen Tableau nach den Plätzen, mit Hin- und Rückspiel: bei Gleichstand Verlängerung und Elfmeterschießen, ohne Auswärtstore. Das Finale ist ein einziges Spiel.', 'Bei Punktgleichheit zählen Tordifferenz, erzielte Tore, Auswärtstore, Siege, Auswärtssiege, dann Punkte, Tordifferenz und Tore der Gegner, Disziplinarpunkte und der Koeffizient.', 'Vor der Ligaphase stehen die Qualifikationsrunden der Zugangsliste 2026-27 (Meisterweg und Ligaweg); die Ausgeschiedenen rutschen in die Europa League oder die Conference League.'],
    },
}


def _el(lang, conf):
    """The Europa League / Conference League text from the Champions League one (their league phases' differences)."""
    p = list(PROSE[(5, 'UEFA CHAMPIONS LEAGUE')][lang])
    if conf:
        p[0] = {'it': "Alla fase campionato partecipano 36 squadre, divise in 6 fasce da 6. Ogni squadra gioca 6 partite, "
                      "una contro ogni fascia, 3 in casa e 3 in trasferta, mai contro una squadra della sua federazione e al "
                      "massimo contro 2 della stessa.",
                'en': "36 clubs take part in the league phase, in 6 pots of 6. Each club plays 6 matches, one against each "
                      "pot, 3 at home and 3 away, never a club of its own association and at most 2 from the same one.",
                'fr': "36 clubs disputent la phase de ligue, en 6 chapeaux de 6. Chaque club joue 6 matchs, un contre chaque "
                      "chapeau, 3 à domicile et 3 à l'extérieur, jamais contre un club de son association et au plus contre "
                      "2 d'une même association.",
                'de': "36 Vereine spielen die Ligaphase, in 6 Töpfen zu 6. Jeder Verein bestreitet 6 Spiele, eines gegen "
                      "jeden Topf, 3 daheim und 3 auswärts, nie gegen einen Verein des eigenen Verbands und höchstens gegen "
                      "2 aus demselben."}[lang]
    p[-1] = {'it': ("Prima della fase campionato si giocano i turni preliminari dell'access list 2026-27; vi entrano anche "
                    "le squadre eliminate dai turni della coppa superiore."),
             'en': ("Before the league phase come the qualifying rounds of the 2026-27 access list, joined by the clubs "
                    "knocked out of the cup above."),
             'fr': ("Avant la phase de ligue se jouent les tours de qualification de la liste d'accès 2026-27, rejoints "
                    "par les éliminés de la coupe supérieure."),
             'de': ("Vor der Ligaphase stehen die Qualifikationsrunden der Zugangsliste 2026-27, zu denen die "
                    "Ausgeschiedenen des höheren Pokals stoßen.")}[lang]
    return p


PACK = {}       # 4.0.1: hand texts a pack brings ('format_prose', fmtgame.from_pack): {(world, Italian title): {lang: [..]}}


def text(world, title, lang):
    """The paragraphs for this competition, or None (the schematic lines stay)."""
    t = title.strip()
    if world == 5 and t in ('UEFA EUROPA LEAGUE', 'UEFA CONFERENCE LEAGUE'):
        return _el(lang, t.endswith('CONFERENCE LEAGUE'))
    import fmtprose_hand
    p = (PACK.get((world, t)) or fmtprose_hand.HAND.get((world, t)) or PROSE.get((world, t), {})).get(lang)
    return list(p) if p else None


# ---- the generator (4.0): every league in plain prose from its data; other competitions: their lines as sentences
L = {
    'it': dict(ord=lambda n: f'{n}a', the_league='Il campionato', the_group='Il girone',
               has='{w} ha {n} squadre che si affrontano {g}: {d} giornate', rest=', e ogni giornata una squadra riposa',
               g={1: 'una volta', 2: 'in andata e ritorno', 3: 'tre volte', 4: 'quattro volte'},
               pts='La vittoria vale {w} punti, il pareggio 1.',
               up1='La prima sale in {u}.', upk='Le prime {k} salgono in {u}.', upper='la categoria superiore',
               down1="L'ultima retrocede in {l}.", downk='Le ultime {k} retrocedono in {l}.', lower='la categoria inferiore',
               realpo="; la {q} giocherebbe lo spareggio", realpo0k="Le {q} giocherebbero lo spareggio contro squadre di {to}, che non è nel mondo: qui non retrocede nessuno.", realdownk="Le {p} scenderebbero in {to}, che non è nel mondo{po}: qui non retrocede nessuno.", realpok="; le {q} giocherebbero lo spareggio", realpo0="La {q} giocherebbe lo spareggio contro una squadra di {to}, che non è nel mondo: qui non retrocede nessuno.", realdown="La {p} scenderebbe in {to}, che non è nel mondo{po}: qui non retrocede nessuno.", none='Non retrocede nessuno.',
               split='Dopo {a} giornate la classifica si divide: {groups}.', grp='{name} ({a}-{b}) {r}', grp0='le squadre dalla {a} alla {b} {r}', rngl='Le squadre {x}', andw='e',
               grprp={0: 'si fermano', 1: 'giocano una volta', 2: 'giocano andata e ritorno'}, grpr={0: 'si ferma', 1: 'gioca una volta', 2: 'gioca andata e ritorno'},
               full=', con tutti i punti della prima fase', half=', con i punti dimezzati', reset=', ripartendo da zero',
               po='{rng} si giocano {kind}: {rules}.', win='La vincente sale in {d}.',
               kind={'promotion': 'i play-off promozione', 'playout': 'i play-out', 'placement': 'gli spareggi',
                     'europe': "i play-off per l'Europa", 'title': 'i play-off per il titolo'},
               rng='Dalla {a} alla {b}', rng1='La {a}', grpround='gironi da {n}', drawn='accoppiamenti sorteggiati', up1x="La prima sale di categoria.", upkx="Le prime {k} salgono di categoria.", down1x="L'ultima retrocede.", downkx="Le ultime {k} retrocedono.", po1="{rng} gioca {kind}: {rules}.", legs={1: 'gara unica', 2: 'andata e ritorno'},
               host={'better': 'in casa della meglio piazzata', 'neutral': 'in campo neutro'},
               level={'et_pens': 'in parità supplementari e rigori', 'pens': 'in parità rigori',
                      'better': 'in parità passa la meglio piazzata',
                      'et_better': 'in parità supplementari, poi passa la meglio piazzata'},
               gap='non si giocano se il distacco è di {n} punti o più', rnd='turno {k}: {r}'),
    'en': dict(ord=lambda n: f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}',
               the_league='The league', the_group='The group',
               has='{w} has {n} clubs who play each other {g}: {d} matchdays', rest=', with one club resting each matchday',
               g={1: 'once', 2: 'home and away', 3: 'three times', 4: 'four times'},
               pts='A win is worth {w} points, a draw 1.',
               up1='The champions go up to {u}.', upk='The top {k} go up to {u}.', upper='the division above',
               down1='The last club goes down to {l}.', downk='The bottom {k} go down to {l}.', lower='the division below',
               realpo="; the {q} would play the relegation play-off", realpo0k="The {q} would play the relegation play-offs against clubs from {to}, which is not in the world: here nobody goes down.", realdownk="The {p} would go down to {to}, which is not in the world{po}: here nobody goes down.", realpok="; the {q} would play the relegation play-offs", realpo0="The {q} would play the relegation play-off against a club from {to}, which is not in the world: here nobody goes down.", realdown="The {p} would go down to {to}, which is not in the world{po}: here nobody goes down.", none='Nobody goes down.',
               split='After {a} matchdays the table splits: {groups}.', grp='{name} ({a}-{b}) {r}', grp0='the clubs from {a} to {b} {r}', rngl='The clubs {x}', andw='and',
               grprp={0: 'stop', 1: 'play once more', 2: 'play home and away'}, grpr={0: 'stops', 1: 'plays once more', 2: 'plays home and away'},
               full=', keeping all the points of the first phase', half=', with points halved', reset=', starting from zero',
               po='{rng} play {kind}: {rules}.', win='The winner goes up to {d}.',
               kind={'promotion': 'the promotion play-offs', 'playout': 'the play-outs', 'placement': 'the placement play-offs',
                     'europe': 'the European play-offs', 'title': 'the title play-offs'},
               rng='The clubs from {a} to {b}', rng1='The {a}', grpround='groups of {n}', drawn='ties drawn', up1x="The champions go up.", upkx="The top {k} go up.", down1x="The last club goes down.", downkx="The bottom {k} go down.", po1="{rng} plays {kind}: {rules}.", legs={1: 'a single match', 2: 'two legs'},
               host={'better': 'at the better-placed club', 'neutral': 'on neutral ground'},
               level={'et_pens': 'if level, extra time and penalties', 'pens': 'if level, penalties',
                      'better': 'if level, the better-placed club goes through',
                      'et_better': 'if level, extra time, then the better-placed club'},
               gap='not played with a gap of {n} points or more', rnd='round {k}: {r}'),
    'fr': dict(ord=lambda n: f'{n}e', the_league='Le championnat', the_group='Le groupe',
               has="{w} compte {n} clubs qui s'affrontent {g} : {d} journées", rest=', avec un club au repos à chaque journée',
               g={1: 'une fois', 2: 'en aller et retour', 3: 'trois fois', 4: 'quatre fois'},
               pts='La victoire vaut {w} points, le nul 1.',
               up1='Le premier monte en {u}.', upk='Les {k} premiers montent en {u}.', upper='division supérieure',
               down1='Le dernier descend en {l}.', downk='Les {k} derniers descendent en {l}.', lower='division inférieure',
               realpo="; le {q} jouerait le barrage", realpo0k="Les {q} joueraient le barrage contre des clubs de {to}, qui n'est pas dans le monde : ici personne ne descend.", realdownk="Les {p} descendraient en {to}, qui n'est pas dans le monde{po} : ici personne ne descend.", realpok="; les {q} joueraient le barrage", realpo0="Le {q} jouerait le barrage contre un club de {to}, qui n'est pas dans le monde : ici personne ne descend.", realdown="Le {p} descendrait en {to}, qui n'est pas dans le monde{po} : ici personne ne descend.", none='Personne ne descend.',
               split='Après {a} journées le classement se divise : {groups}.', grp='{name} ({a}-{b}) {r}', grp0='les clubs du {a} au {b} {r}', rngl='Les clubs {x}', andw='et',
               grprp={0: "s'arrêtent", 1: 'jouent une fois', 2: 'jouent en aller et retour'}, grpr={0: "s'arrête", 1: 'joue une fois', 2: 'joue en aller et retour'},
               full=', en gardant tous les points de la première phase', half=', points divisés par deux', reset=', en repartant de zéro',
               po='{rng} jouent {kind} : {rules}.', win='Le vainqueur monte en {d}.',
               kind={'promotion': 'les barrages de montée', 'playout': 'les barrages de maintien',
                     'placement': 'les barrages de classement', 'europe': "les barrages pour l'Europe",
                     'title': 'les play-offs du titre'},
               rng='Les clubs du {a} au {b}', rng1='Le {a}', grpround='groupes de {n}', drawn='affiches tirées au sort', up1x="Le premier monte.", upkx="Les {k} premiers montent.", down1x="Le dernier descend.", downkx="Les {k} derniers descendent.", po1="{rng} joue {kind} : {rules}.", legs={1: 'un seul match', 2: 'aller et retour'},
               host={'better': 'chez le mieux classé', 'neutral': 'sur terrain neutre'},
               level={'et_pens': "en cas d'égalité, prolongation et tirs au but", 'pens': "en cas d'égalité, tirs au but",
                      'better': "en cas d'égalité, le mieux classé passe",
                      'et_better': "en cas d'égalité, prolongation, puis le mieux classé"},
               gap="pas joués avec {n} points d'écart ou plus", rnd='tour {k} : {r}'),
    'de': dict(ord=lambda n: f'{n}.', the_league='Die Liga', the_group='Die Gruppe',
               has='{w} hat {n} Vereine, die {g} gegeneinander spielen: {d} Spieltage', rest=', an jedem Spieltag hat ein Verein frei',
               g={1: 'einmal', 2: 'mit Hin- und Rückspiel', 3: 'dreimal', 4: 'viermal'},
               pts='Ein Sieg zählt {w} Punkte, ein Remis 1.',
               up1='Der Meister steigt in die {u} auf.', upk='Die ersten {k} steigen in die {u} auf.', upper='höhere Liga',
               down1='Der Letzte steigt in die {l} ab.', downk='Die letzten {k} steigen in die {l} ab.', lower='tiefere Liga',
               realpo="; der {q} würde die Relegation spielen", realpo0k="Die {q} würden die Relegation gegen Vereine aus der {to} spielen, die nicht in der Welt ist: hier steigt niemand ab.", realdownk="Die {p} würden in die {to} absteigen, die nicht in der Welt ist{po}: hier steigt niemand ab.", realpok="; die {q} würden die Relegation spielen", realpo0="Der {q} würde die Relegation gegen einen Verein aus der {to} spielen, die nicht in der Welt ist: hier steigt niemand ab.", realdown="Der {p} würde in die {to} absteigen, die nicht in der Welt ist{po}: hier steigt niemand ab.", none='Niemand steigt ab.',
               split='Nach {a} Spieltagen wird die Tabelle geteilt: {groups}.', grp='{name} ({a}-{b}) {r}', grp0='die Vereine vom {a} bis zum {b} {r}', rngl='Die Vereine {x}', andw='und',
               grprp={0: 'hören auf', 1: 'spielen einmal', 2: 'spielen mit Hin- und Rückspiel'}, grpr={0: 'hört auf', 1: 'spielt einmal', 2: 'spielt mit Hin- und Rückspiel'},
               full=', mit allen Punkten der ersten Phase', half=', mit halbierten Punkten', reset=', bei null beginnend',
               po='{rng} spielen {kind}: {rules}.', win='Der Sieger steigt in die {d} auf.',
               kind={'promotion': 'die Aufstiegs-Playoffs', 'playout': 'die Abstiegs-Playoffs',
                     'placement': 'die Platzierungsspiele', 'europe': 'die Europapokal-Playoffs',
                     'title': 'die Meister-Playoffs'},
               rng='Die Vereine vom {a} bis zum {b}', rng1='Der {a}', grpround='Gruppen zu {n}', drawn='ausgeloste Paarungen', up1x="Der Meister steigt auf.", upkx="Die ersten {k} steigen auf.", down1x="Der Letzte steigt ab.", downkx="Die letzten {k} steigen ab.", po1="{rng} spielt {kind}: {rules}.", legs={1: 'ein Spiel', 2: 'Hin- und Rückspiel'},
               host={'better': 'beim besser Platzierten', 'neutral': 'auf neutralem Platz'},
               level={'et_pens': 'bei Gleichstand Verlängerung und Elfmeterschießen', 'pens': 'bei Gleichstand Elfmeterschießen',
                      'better': 'bei Gleichstand kommt der besser Platzierte weiter',
                      'et_better': 'bei Gleichstand Verlängerung, dann der besser Platzierte'},
               gap='nicht gespielt bei {n} oder mehr Punkten Abstand', rnd='Runde {k}: {r}'),
}


def _cap(s):
    return s[:1].upper() + s[1:]


def _rule(r, l):
    if 'group' in r:
        return l['grpround'].format(n=len(r.get('members', [])))
    p = [l['legs'][r.get('legs', 1)]]
    if r.get('pairing') == 'draw':
        p.append(l['drawn'])
    if r.get('host') in l['host']:
        p.append(l['host'][r['host']])
    if r.get('level') in l['level']:
        p.append(l['level'][r['level']])
    return ', '.join(p)


def league(div, k, lg, win, lang, pos, lowest, nm, real_down=None):
    """Paragraphs for division k (flattened) of a league model (complist._league): nm(names) -> name in lang."""
    l = L[lang]
    levels = lg['levels']
    li = next(i for i, lv in enumerate(levels) if any(x is div for x in lv))
    grouped = len(levels[li]) > 1
    n, g = div['clubs'], div['games']
    d = (n if n % 2 else n - 1) * g
    fx = [st for st in ((div.get('split') or {}).get('stages') or []) if 'fixtures' in st]
    if fx:                                      # (a fixture-list league: its own matchdays)
        d = sum(len(st['fixtures']) for st in fx)
    s1 = l['has'].format(w=l['the_group'] if grouped else l['the_league'], n=n, g=l['g'].get(g, l['g'][2]), d=d)
    s1 += (l['rest'] if n % 2 else '') + '. ' + l['pts'].format(w=win)
    out = [s1]
    sp = div.get('split') or {}
    for st in (sp.get('stages') or ([sp] if sp.get('groups') else [])):
        if 'fixtures' in st or not st.get('groups'):
            continue
        gs = []
        for gr in st['groups']:
            a, b = gr['places']
            ri = {'none': 0, 'single': 1, 'double': 2}[gr.get('rounds', 'single')]
            r = (l['grpr'] if gr.get('title') else l['grprp'])[ri]
            if ri:                              # (a group that plays on: how its points carry over)
                r += {'half_up': l['half'], 'half_down': l['half'], 'reset': l['reset']}.get(gr.get('points', 'full'), l['full'])
            if gr.get('title'):
                gs.append(l['grp'].format(name=nm(gr['title']), a=l['ord'](a), b=l['ord'](b), r=r))
            else:
                gs.append(l['grp0'].format(a=l['ord'](a), b=l['ord'](b), r=r))
        out.append(l['split'].format(a=st['after'], groups='; '.join(gs)))
    s2 = []
    def lvname(lv):                             # a level's name: its division's, or the groups' common start
        ns = [nm(x['name']) for x in lv]
        if len(ns) == 1:
            return ns[0]
        c = os.path.commonprefix(ns).rstrip()
        for w in (' GIRONE', ' GROUP', ' ZONA', ' ZONE'):
            c = c[:-len(w)] if c.upper().endswith(w) else c
        return c.strip() or None
    upname = lvname(levels[li - 1]) if li > 0 else None
    if div.get('up'):
        s2.append((l['up1'] if div['up'] == 1 else l['upk']).format(k=div['up'], u=upname) if upname else
                  (l['up1x'] if div['up'] == 1 else l['upkx']).format(k=div['up']))
    if div.get('down'):
        loname = lvname(levels[li + 1]) if li + 1 < len(levels) else None
        s2.append((l['down1'] if div['down'] == 1 else l['downk']).format(k=div['down'], l=loname) if loname else
                  (l['down1x'] if div['down'] == 1 else l['downkx']).format(k=div['down']))
    elif lowest and real_down and not real_down.get('n') and real_down.get('po'):   # (only a real play-off below)
        to = real_down.get('to')
        to = to if isinstance(to, str) else (to or {}).get(lang) or (to or {}).get('*', '')
        q0 = n - real_down['po'] + 1
        s2.append(l['realpo0' if q0 == n else 'realpo0k'].format(q=l['ord'](n) if q0 == n else f"{l['ord'](q0)}-{l['ord'](n)}", to=to))
    elif lowest and real_down and real_down.get('n'):   # (data: the real relegation below the world's lowest division)
        a = n - real_down['n'] + 1
        to = real_down.get('to')
        to = to if isinstance(to, str) else (to or {}).get(lang) or (to or {}).get('*', '')
        pp = l['ord'](a) if a == n else f"{l['ord'](a)}-{l['ord'](n)}"
        po_ = ''
        if real_down.get('po'):                 # (the real relegation play-off places above them)
            b = a - 1
            q0 = b - real_down['po'] + 1
            po_ = l['realpo' if q0 == b else 'realpok'].format(q=l['ord'](b) if q0 == b else f"{l['ord'](q0)}-{l['ord'](b)}")
        s2.append(l['realdown' if a == n else 'realdownk'].format(p=pp, to=to, po=po_))
    elif lowest:
        s2.append(l['none'])
    if s2:
        out.append(' '.join(s2))
    for po in pos:
        pl = sorted(e[1] for e in po.get('entrants', []) if isinstance(e, list) and e[0] == k)
        if not pl or po.get('kind') == 'promedio':
            continue
        if len(pl) == 1:
            rng = l['rng1'].format(a=l['ord'](pl[0]))
        elif pl == list(range(pl[0], pl[-1] + 1)):
            rng = l['rng'].format(a=l['ord'](pl[0]), b=l['ord'](pl[-1]))
        else:
            os_ = [l['ord'](x) for x in pl]
            rng = l['rngl'].format(x=', '.join(os_[:-1]) + f" {l['andw']} " + os_[-1])
        rs = [_rule(r, l) for r in po.get('rounds', [])]
        rules = rs[0] if rs and all(x == rs[0] for x in rs) else '; '.join(l['rnd'].format(k=i + 1, r=x) for i, x in enumerate(rs))
        if any(r.get('gap') for r in po.get('rounds', [])):
            rules += ' (' + l['gap'].format(n=max(r.get('gap') or 0 for r in po['rounds'])) + ')'
        kind = l['kind'].get(po.get('kind', 'promotion'), l['kind']['promotion'])
        if po.get('names') and po.get('kind') in ('title', 'europe'):
            kind += f" ({nm(po['names'])})"
        rs = [x for i, x in enumerate(rs) if not (i and 'group' in po['rounds'][i] and 'group' in po['rounds'][i - 1])]
        rules = rs[0] if rs and all(x == rs[0] for x in rs) else '; '.join(l['rnd'].format(k=i + 1, r=x) for i, x in enumerate(rs))
        if any(r.get('gap') for r in po.get('rounds', [])):
            rules += ' (' + l['gap'].format(n=max(r.get('gap') or 0 for r in po['rounds'])) + ')'
        s = (l['po1'] if len(pl) == 1 else l['po']).format(rng=rng, kind=kind, rules=rules)
        if po.get('kind', 'promotion') == 'promotion' and isinstance(po.get('winner_div'), int) and po['winner_div'] < k:
            s += ' ' + l['win'].format(d=nm(lg['names'][po['winner_div']]))
        out.append(s)
    return out


def sentences(lines):
    """Other competitions: their schematic lines as one paragraph of sentences."""
    xs = [x.rstrip(' :') for x in lines if x.strip()]
    return [_cap('. '.join(x[:1] + x[1:].lower() for x in xs) + '.')] if xs else []



# ---- the other confederations' cups (conti.py data: format + access + guests), 4.0: a short story of the cup
def _rd(art, inn, to, pl=False):
    return dict(art=art, inn=inn, to=to, pl=pl)


_ORD = {'it': ['primo', 'secondo', 'terzo', 'quarto'], 'en': ['first', 'second', 'third', 'fourth'],
        'fr': ['premier', 'deuxième', 'troisième', 'quatrième'], 'de': ['erste', 'zweite', 'dritte', 'vierte']}
RD = {
    'it': dict(n=lambda o: _rd(f'il {o} turno', f'nel {o} turno', f'al {o} turno'),
               q=lambda o: _rd(f'il {o} turno preliminare', f'nel {o} turno preliminare', f'al {o} turno preliminare'),
               pre=_rd('il turno preliminare', 'nel turno preliminare', 'al turno preliminare'),
               r1=_rd('il primo turno', 'nel primo turno', 'al primo turno'),
               qual=_rd('il turno di qualificazione', 'nel turno di qualificazione', 'al turno di qualificazione'),
               groups=_rd('la fase a gironi', 'nella fase a gironi', 'alla fase a gironi'),
               league=_rd('la fase campionato', 'nella fase campionato', 'alla fase campionato'),
               po=_rd('gli spareggi', 'negli spareggi', 'agli spareggi', True), r16=_rd('gli ottavi', 'negli ottavi', 'agli ottavi', True),
               qf=_rd('i quarti', 'nei quarti', 'ai quarti', True), sf=_rd('le semifinali', 'nelle semifinali', 'alle semifinali', True),
               final=_rd('la finale', 'in finale', 'alla finale')),
    'en': dict(n=lambda o: _rd(f'the {o} round', f'in the {o} round', f'to the {o} round'),
               q=lambda o: _rd(f'the {o} qualifying round', f'in the {o} qualifying round', f'to the {o} qualifying round'),
               pre=_rd('the preliminary round', 'in the preliminary round', 'to the preliminary round'),
               r1=_rd('the first round', 'in the first round', 'to the first round'),
               qual=_rd('the qualifying stage', 'in the qualifying stage', 'to the qualifying stage'),
               groups=_rd('the group stage', 'in the group stage', 'to the group stage'),
               league=_rd('the league stage', 'in the league stage', 'to the league stage'),
               po=_rd('the play-offs', 'in the play-offs', 'to the play-offs', True),
               r16=_rd('the round of 16', 'in the round of 16', 'to the round of 16'),
               qf=_rd('the quarter-finals', 'in the quarter-finals', 'to the quarter-finals', True),
               sf=_rd('the semi-finals', 'in the semi-finals', 'to the semi-finals', True),
               final=_rd('the final', 'in the final', 'to the final')),
    'fr': dict(n=lambda o: _rd(f'le {o} tour', f'au {o} tour', f'au {o} tour'),
               q=lambda o: _rd(f'le {o} tour préliminaire', f'au {o} tour préliminaire', f'au {o} tour préliminaire'),
               pre=_rd('le tour préliminaire', 'au tour préliminaire', 'au tour préliminaire'),
               r1=_rd('le premier tour', 'au premier tour', 'au premier tour'),
               qual=_rd('la phase de qualification', 'en phase de qualification', 'en phase de qualification'),
               groups=_rd('la phase de groupes', 'en phase de groupes', 'en phase de groupes'),
               league=_rd('la phase de ligue', 'en phase de ligue', 'en phase de ligue'),
               po=_rd('les barrages', 'aux barrages', 'aux barrages', True),
               r16=_rd('les huitièmes de finale', 'en huitièmes de finale', 'en huitièmes de finale', True),
               qf=_rd('les quarts de finale', 'en quarts de finale', 'en quarts de finale', True),
               sf=_rd('les demi-finales', 'en demi-finales', 'en demi-finales', True),
               final=_rd('la finale', 'en finale', 'en finale')),
    'de': dict(n=lambda o: _rd(f'die {o} Runde', f'in der {o}n Runde', f'in die {o} Runde'),
               q=lambda o: _rd(f'die {o} Qualifikationsrunde', f'in der {o}n Qualifikationsrunde', f'in die {o} Qualifikationsrunde'),
               pre=_rd('die Vorrunde', 'in der Vorrunde', 'in die Vorrunde'),
               r1=_rd('die erste Runde', 'in der ersten Runde', 'in die erste Runde'),
               qual=_rd('die Qualifikation', 'in der Qualifikation', 'in die Qualifikation'),
               groups=_rd('die Gruppenphase', 'in der Gruppenphase', 'in die Gruppenphase'),
               league=_rd('die Ligaphase', 'in der Ligaphase', 'in die Ligaphase'),
               po=_rd('die Playoffs', 'in den Playoffs', 'in die Playoffs', True),
               r16=_rd('das Achtelfinale', 'im Achtelfinale', 'ins Achtelfinale'),
               qf=_rd('das Viertelfinale', 'im Viertelfinale', 'ins Viertelfinale'),
               sf=_rd('das Halbfinale', 'im Halbfinale', 'ins Halbfinale'),
               final=_rd('das Finale', 'im Finale', 'ins Finale')),
}
REG = {'it': dict(fifa='del mondo', conmebol='del Sudamerica', concacaf='del Nord e Centro America e dei Caraibi', afc="dell'Asia",
                  caf="dell'Africa", ofc="dell'Oceania"),
       'en': dict(fifa='of the world', conmebol='of South America', concacaf='of North and Central America and the Caribbean', afc='of Asia',
                  caf='of Africa', ofc='of Oceania'),
       'fr': dict(fifa='du monde', conmebol="d'Amérique du Sud", concacaf="d'Amérique du Nord, d'Amérique centrale et des Caraïbes",
                  afc="d'Asie", caf="d'Afrique", ofc="d'Océanie"),
       'de': dict(fifa='der Welt', conmebol='Südamerikas', concacaf='Nord- und Mittelamerikas und der Karibik', afc='Asiens', caf='Afrikas',
                  ofc='Ozeaniens')}
CP = {
    'it': dict(tier=['La {c} riunisce le migliori squadre {reg}.', 'La {c} è la seconda coppa per club {reg}.',
                     'La {c} è la terza coppa per club {reg}.'],
               sup='La {c} mette di fronte le vincitrici della {a} e della {b}.',
               n='Dal mondo partecipano {n} squadre: {lst}.', n1='Dal mondo partecipa una sola squadra: {x}.',
               eachk='{x} {k} ciascuna', enter='Si entra in turni diversi, secondo il piazzamento in campionato o la coppa nazionale: {lst}.',
               at='{k} {inn}', andw='e', num=['', 'un', 'due', 'tre', 'quattro'],
               guests='Gli altri posti vanno a squadre di federazioni che non sono nel mondo: sono ospiti, con la rosa vera, e le guida il computer.',
               gonly='Partecipano solo squadre di federazioni che non sono nel mondo: sono ospiti, con la rosa vera, e le guida il computer.',
               holder='La detentrice entra {inn}.', holderc='La vincitrice della {c} entra {inn}.',
               start='Si parte con {x}, {how}.', startq='{n} turni preliminari a eliminazione diretta', allko='Si gioca tutto a eliminazione diretta.',
               then='Poi ', groups='{pre}le {n} squadre vengono divise in {g} gironi da {s}, {legs}: {out}.',
               group1='{pre}le {s} squadre giocano un girone unico, {legs}: {out}.', legs2='con andata e ritorno', legs1='in gara unica',
               league='{pre}le {n} squadre giocano la fase campionato in {z} zone da {pz}: ognuna gioca {m} partite e le prime {q} di ogni zona vanno {to}.',
               top2='le prime due vanno {to}', topk='le prime {k} vanno {to}', win='le prime vanno {to}', win1='la prima va {to}',
               pos='le {w} vanno {to}', best='le migliori {w} vanno {to}', cup='le {w} passano {to} della {c}',
               pw=['prime', 'seconde', 'terze', 'quarte'],
               ko='{s} si {v} {legs}{nt}{lv}.', v=('gioca', 'giocano'), two='in andata e ritorno', one='in gara unica',
               nt=' in campo neutro', pens=', con i rigori in caso di parità', etp=', con supplementari e rigori in caso di parità',
               away='Vale la regola dei gol in trasferta.', noaway='Non vale la regola dei gol in trasferta.',
               losers='Chi perde {art} passa {to} della {c}.', inn='Dalla {c} arrivano anche {lst}.',
               wl='le squadre eliminate {inn}, che entrano {to}', wt='le terze dei gironi, che entrano {to}'),
    'en': dict(tier=['The {c} brings together the best clubs {reg}.', 'The {c} is the second club cup {reg}.',
                     'The {c} is the third club cup {reg}.'],
               sup='The {c} puts the winners of the {a} and of the {b} against each other.',
               n='From the world, {n} clubs take part: {lst}.', n1='Only one club of the world takes part: {x}.',
               eachk='{x} {k} each', enter='They enter at different stages, by league place or national cup: {lst}.',
               at='{k} {inn}', andw='and', num=['', 'one', 'two', 'three', 'four'],
               guests='The other places go to clubs of associations that are not in the world: they are guests, with their real squads, run by the computer.',
               gonly='Only clubs of associations that are not in the world take part: they are guests, with their real squads, run by the computer.',
               holder='The holders enter {inn}.', holderc='The {c} winners enter {inn}.',
               start='It starts with {x}, {how}.', startq='{n} knockout qualifying rounds', allko='It is a knockout competition from start to finish.',
               then='Then ', groups='{pre}the {n} clubs are split into {g} groups of {s}, {legs}: {out}.',
               group1='{pre}the {s} clubs play one group, {legs}: {out}.', legs2='home and away', legs1='in single matches',
               league='{pre}the {n} clubs play the league stage in {z} regions of {pz}: each plays {m} matches and the top {q} of each region go {to}.',
               top2='the top two go {to}', topk='the top {k} go {to}', win='the group winners go {to}', win1='the winner goes {to}',
               pos='the {w} go {to}', best='the best {w} go {to}', cup='the {w} move {to} of the {c}',
               pw=['winners', 'runners-up', 'thirds', 'fourths'],
               ko='{s} {v} played {legs}{nt}{lv}.', v=('is', 'are'), two='over two legs', one='as one match',
               nt=' at a neutral ground', pens=', with penalties if level', etp=', with extra time and penalties if level',
               away='The away goals rule applies.', noaway='There is no away goals rule.',
               losers='The losers of {art} go {to} of the {c}.', inn='From the {c} also come {lst}.',
               wl='the clubs knocked out {inn}, who enter {to}', wt='the thirds of the groups, who enter {to}'),
    'fr': dict(tier=['La {c} réunit les meilleurs clubs {reg}.', 'La {c} est la deuxième coupe des clubs {reg}.',
                     'La {c} est la troisième coupe des clubs {reg}.'],
               sup='La {c} oppose les vainqueurs de la {a} et de la {b}.',
               n='Du monde, {n} clubs participent : {lst}.', n1='Un seul club du monde participe : {x}.',
               eachk='{x} {k} chacun', enter='Ils entrent à des tours différents, selon leur place en championnat ou la coupe nationale : {lst}.',
               at='{k} {inn}', andw='et', num=['', 'un', 'deux', 'trois', 'quatre'],
               guests="Les autres places vont à des clubs de fédérations qui ne sont pas dans le monde : ce sont des invités, avec leur vrai effectif, dirigés par l'ordinateur.",
               gonly="Seuls des clubs de fédérations qui ne sont pas dans le monde participent : ce sont des invités, avec leur vrai effectif, dirigés par l'ordinateur.",
               holder='Le tenant du titre entre {inn}.', holderc='Le vainqueur de la {c} entre {inn}.',
               start='On commence par {x}, {how}.', startq='{n} tours préliminaires à élimination directe',
               allko='Tout se joue à élimination directe.',
               then='Ensuite, ', groups='{pre}les {n} clubs sont répartis en {g} groupes de {s}, {legs} : {out}.',
               group1='{pre}les {s} clubs jouent un groupe unique, {legs} : {out}.', legs2='en aller et retour', legs1='en matchs uniques',
               league='{pre}les {n} clubs jouent la phase de ligue en {z} zones de {pz} : chacun joue {m} matchs et les {q} premiers de chaque zone vont {to}.',
               top2='les deux premiers vont {to}', topk='les {k} premiers vont {to}', win='les premiers vont {to}', win1='le premier va {to}',
               pos='les {w} vont {to}', best='les meilleurs {w} vont {to}', cup='les {w} passent {to} de la {c}',
               pw=['premiers', 'deuxièmes', 'troisièmes', 'quatrièmes'],
               ko='{s} se {v} {legs}{nt}{lv}.', v=('joue', 'jouent'), two='en aller et retour', one='en un seul match',
               nt=' sur terrain neutre', pens=", avec tirs au but en cas d'égalité", etp=", avec prolongation et tirs au but en cas d'égalité",
               away="Les buts à l'extérieur comptent.", noaway="Il n'y a pas de règle des buts à l'extérieur.",
               losers='Qui perd {art} passe {to} de la {c}.', inn='De la {c} arrivent aussi {lst}.',
               wl='les clubs éliminés {inn}, qui entrent {to}', wt='les troisièmes des groupes, qui entrent {to}'),
    'de': dict(tier=['Die {c} vereint die besten Vereine {reg}.', 'Die {c} ist der zweite Klubwettbewerb {reg}.',
                     'Die {c} ist der dritte Klubwettbewerb {reg}.'],
               sup='Die {c} bringt die Sieger der {a} und der {b} zusammen.',
               n='Aus der Welt nehmen {n} Vereine teil: {lst}.', n1='Nur ein Verein der Welt nimmt teil: {x}.',
               eachk='{x} je {k}', enter='Je nach Ligaplatz oder Pokalsieg steigen sie in verschiedenen Runden ein: {lst}.',
               at='{k} {inn}', andw='und', num=['', 'eine', 'zwei', 'drei', 'vier'],
               guests='Die übrigen Plätze gehen an Vereine von Verbänden, die nicht in der Welt sind: Gäste mit ihrem echten Kader, vom Computer geführt.',
               gonly='Nur Vereine von Verbänden, die nicht in der Welt sind, nehmen teil: Gäste mit ihrem echten Kader, vom Computer geführt.',
               holder='Der Titelverteidiger steigt {inn} ein.', holderc='Der Sieger der {c} steigt {inn} ein.',
               start='Es beginnt mit {x}, {how}.', startq='{n} K.-o.-Qualifikationsrunden', allko='Gespielt wird durchgehend im K.-o.-System.',
               then='Danach ', first='Zuerst ', groups='{pre}werden die {n} Vereine in {g} Gruppen zu {s} geteilt, {legs}: {out}.',
               group1='{pre}spielen die {s} Vereine eine Gruppe, {legs}: {out}.', legs2='mit Hin- und Rückspiel', legs1='mit je einem Spiel',
               league='{pre}spielen die {n} Vereine die Ligaphase in {z} Regionen zu {pz}: jeder spielt {m} Spiele, die ersten {q} jeder Region kommen {to}.',
               top2='die ersten zwei kommen {to}', topk='die ersten {k} kommen {to}', win='die Gruppensieger kommen {to}', win1='der Erste kommt {to}',
               pos='die {w} kommen {to}', best='die besten {w} kommen {to}', cup='die {w} wechseln {to} der {c}',
               pw=['Ersten', 'Zweiten', 'Dritten', 'Vierten'],
               ko='{s} {v} {legs}{nt} gespielt{lv}.', v=('wird', 'werden'), two='mit Hin- und Rückspiel', one='in einem Spiel',
               nt=' auf neutralem Platz', pens=', bei Gleichstand mit Elfmeterschießen', etp=', bei Gleichstand mit Verlängerung und Elfmeterschießen',
               away='Die Auswärtstorregel gilt.', noaway='Es gibt keine Auswärtstorregel.',
               losers='Wer {art} verliert, wechselt {to} der {c}.', inn='Aus der {c} kommen außerdem {lst}.',
               wl='die {inn} ausgeschiedenen Vereine, die {to} einsteigen', wt='die Gruppendritten, die {to} einsteigen'),
}


def _list(xs, l):
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + f" {l['andw']} " + xs[-1]


def _round(key, lang):
    r = RD[lang]
    if key[:1] == 'q' and key[1:].isdigit():
        return r['q'](_ORD[lang][int(key[1:]) - 1])
    return r.get({'first': 'r1'}.get(key, key).replace('_best', '')) or _rd(key, key, key)


def conti(c, acc, lang, cname, aname, conf, tier, guests=False):
    """A continental cup's FORMAT page as a short story in plain prose, from conti's data: what the cup is (its
    confederation, its tier), the world's entrants per association and their entry rounds, the holders, the guests,
    then its rounds in order (the qualifying knockouts, the groups / league stage and where each place goes, the
    knockouts to the final), the away goals rule and the links to the other cups. cname / aname: a cup's / an
    association's name in the language; tier: 0 / 1 / 2 (its place among its confederation's cups)."""
    l = CP[lang]
    R = lambda k: _round(k, lang)
    acc = acc or {}
    rds = c['rounds']
    keys = [rd['key'] for rd in rds]
    per = {a: v for a, v in acc.items() if isinstance(v, list)}
    hold = acc.get('holders') or {}
    s = []
    if not per and len(hold) == 2 and not (acc.get('outside') or guests):
        a, b = list(hold)
        s.append(l['sup'].format(c=cname(c['key']), a=cname(a), b=cname(b)))
    else:
        s.append(l['tier'][min(tier, 2)].format(c=cname(c['key']), reg=REG[lang].get(conf, '')))
    if per:
        by = {}
        for a, v in per.items():
            by.setdefault(len(v), []).append(aname(a))
        nn = sum(len(v) for v in per.values())
        if nn == 1:
            s.append(l['n1'].format(x=aname(next(iter(per)))))
        else:
            lst = [(f'{by[k][0]} {k}' if len(by[k]) == 1 else l['eachk'].format(k=k, x=', '.join(by[k])))
                   for k in sorted(by, reverse=True)]
            s.append(l['n'].format(n=nn, lst=', '.join(lst)))
        at = {}
        for v in per.values():
            for r, _ in v:
                at[r] = at.get(r, 0) + 1
        if len(at) > 1:
            s.append(l['enter'].format(lst=_list([l['at'].format(k=at[r], inn=R(r)['inn']) for r in
                                                  sorted(at, key=lambda r: -keys.index(r) if r in keys else 0)], l)))
    if acc.get('outside') or guests:
        s.append(l['guests'] if per else l['gonly'])
    if per or len(hold) != 2:
        for k, r in hold.items():
            if r in keys and r != keys[0]:
                s.append((l['holder'] if k == c['key'] else l['holderc']).format(inn=R(r)['inn'], c=cname(k)))
    out = [' '.join(_cap(x) for x in s)]

    def how(rd):
        lv = l['etp'] if rd.get('level') == 'et_pens' else l['pens']
        return (l['two'] if rd.get('legs', 2) == 2 else l['one']), (l['nt'] if rd.get('host') == 'neutral' else ''), lv
    s, i = [], 0
    stages = [j for j, rd in enumerate(rds) if rd['kind'] in ('groups', 'league_stage')]
    if not stages and len(rds) > 1:
        s.append(l['allko'])
    if stages and stages[0] > 0:                 # the qualifying knockouts before the first group / league stage
        first = rds[:stages[0]]
        if all(how(rd) == how(first[0]) for rd in first):
            lg, nt, lv = how(first[0])
            if len(first) > 1 and all(rd['key'][:1] == 'q' and rd['key'][1:].isdigit() for rd in first):
                x = l['startq'].format(n=l['num'][min(len(first), 4)])
            else:
                x = _list([R(rd['key'])['art'] for rd in first], l)
                if lang == 'de':
                    x = _list([R(rd['key'])['inn'][3:] for rd in first], l)
            s.append(l['start'].format(x=x, how=(lg + nt + lv).lstrip(', ')))
            i = stages[0]
    while i < len(rds):
        rd = rds[i]
        pre = l['then'] if s or i else l.get('first', '')
        if rd['kind'] == 'league_stage':
            q = max((int(k.split('-')[1]) for k in (rd.get('out') or {}) if '-' in k), default=8)
            to = next(iter((rd.get('out') or {}).values()), 'r16')
            z, pz = rd.get('regions', 1), rd.get('clubs_per_region', 0)
            s.append(l['league'].format(pre=pre, n=z * pz, z=z, pz=pz, m=rd.get('matches', 0), q=q, to=R(to)['to']))
            i += 1
            continue
        if rd['kind'] == 'groups':
            nxt = {}
            for p, to in sorted((rd.get('out') or {}).items()):
                nxt.setdefault(to, []).append(int(p))
            parts = []
            for to, ps in nxt.items():
                if ':' in to:
                    ck, tr = to.split(':')
                    parts += [l['cup'].format(w=l['pw'][p - 1], to=R(tr)['to'], c=cname(ck)) for p in ps]
                elif ps == [1]:
                    parts.append((l['win1'] if rd['groups'] == 1 else l['win']).format(to=R(to)['to']))
                elif len(ps) > 1 and ps == list(range(1, len(ps) + 1)):
                    parts.append((l['top2'] if len(ps) == 2 else l['topk']).format(k=len(ps), to=R(to)['to']))
                elif to.endswith('_best'):
                    parts += [l['best'].format(w=l['pw'][p - 1], to=R(to)['to']) for p in ps]
                else:
                    parts += [l['pos'].format(w=l['pw'][p - 1], to=R(to)['to']) for p in ps]
            s.append((l['group1'] if rd['groups'] == 1 else l['groups']).format(
                pre=pre, n=rd['groups'] * rd['size'], g=rd['groups'], s=rd['size'],
                legs=l['legs2'] if rd.get('rounds', 2) == 2 else l['legs1'], out=_list(parts, l) if parts else '-'))
            i += 1
            continue
        j = i
        while j + 1 < len(rds) and rds[j + 1]['kind'] not in ('groups', 'league_stage') and how(rds[j + 1]) == how(rd):
            j += 1
        subj = [R(r['key']) for r in rds[i:j + 1]]
        lg, nt, lv = how(rd)
        s.append(l['ko'].format(s=_list([x['art'] for x in subj], l), v=l['v'][len(subj) > 1 or subj[0]['pl']],
                                legs=lg, nt=nt, lv=lv))
        i = j + 1
    s.append(l['away'] if any(rd.get('level') == 'away_pens' for rd in rds) else l['noaway'])
    out.append(' '.join(_cap(x) for x in s))
    s = []
    for rk, to in (c.get('losers') or {}).items():
        ck, tr = to.split(':')
        s.append(l['losers'].format(art=R(rk)['art'], to=R(tr)['to'], c=cname(ck)))
    ins = {}
    for tr, what in (c.get('in') or {}).items():         # ('po': 'lib:groups 3rds', 'groups': 'lib:q3 losers')
        ck, rest = what.split(':', 1)
        r, w = (rest.split() + [''])[:2]
        ins.setdefault(ck, []).append((l['wt'] if w == '3rds' else l['wl']).format(inn=R(r)['inn'], to=R(tr)['inn']))
    for ck, lst in ins.items():
        s.append(l['inn'].format(c=cname(ck), lst=_list(lst, l)))
    if s:
        out.append(' '.join(_cap(x) for x in s))
    if lang in ('it', 'fr'):                     # (l'AFC, dell'AFC, de l'OFC: before a name starting with a vowel)
        import re
        el = [(r"\bLa (?=[AEIOU][A-Z])", "L'"), (r"\bla (?=[AEIOU][A-Z])", "l'"), (r"\bdella (?=[AEIOU][A-Z])", "dell'"),
              (r"\balla (?=[AEIOU][A-Z])", "all'"), (r"\bDalla (?=[AEIOU][A-Z])", "Dall'"), (r"\bde la (?=[AEIOU][A-Z])", "de l'"),
              (r"\bDe la (?=[AEIOU][A-Z])", "De l'")]
        for a, b in el:
            out = [re.sub(a, b, x) for x in out]
    return out


# ---- national cups (complist._cup: the real cup's size, the game's knockout slice), 4.0: the same plain story
NC = {
    'it': dict(real='La coppa vera ha {n} squadre, che entrano in turni diversi secondo la categoria.',
               game='Nel gioco si parte con {n} squadre a eliminazione diretta.', game_r='Nel gioco ne restano {n}, a eliminazione diretta.',
               byes='{b} di loro passano direttamente al secondo turno.', drawn='Il primo turno ricalca il sorteggio vero.',
               away=', con la regola dei gol in trasferta', rep=', e in caso di parità si ripete', po=', e in caso di parità si gioca uno spareggio',
               ord=['primo', 'secondo', 'terzo', 'quarto', 'quinto', 'sesto', 'settimo']),
    'en': dict(real='The real cup has {n} clubs, who enter at different rounds by division.',
               game='In the game it starts with {n} clubs, knockout.', game_r='In the game {n} of them are left, knockout.',
               byes='{b} of them go straight to the second round.', drawn='The first round follows the real draw.',
               away=', with the away goals rule', rep=', with a replay if level', po=', with a play-off if level',
               ord=['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']),
    'fr': dict(real='La vraie coupe compte {n} clubs, qui entrent à des tours différents selon leur division.',
               game="Dans le jeu, on commence avec {n} clubs, à élimination directe.", game_r='Dans le jeu, il en reste {n}, à élimination directe.',
               byes='{b} d\'entre eux passent directement au deuxième tour.', drawn='Le premier tour suit le vrai tirage.',
               away=", avec la règle des buts à l'extérieur", rep=", et un match à rejouer en cas d'égalité", po=", et un barrage en cas d'égalité",
               ord=['premier', 'deuxième', 'troisième', 'quatrième', 'cinquième', 'sixième', 'septième']),
    'de': dict(real='Der echte Pokal hat {n} Vereine, die je nach Liga in verschiedenen Runden einsteigen.',
               game='Im Spiel beginnt es mit {n} Vereinen im K.-o.-System.', game_r='Im Spiel sind davon {n} übrig, im K.-o.-System.',
               byes='{b} davon steigen direkt in der zweiten Runde ein.', drawn='Die erste Runde folgt der echten Auslosung.',
               away=', mit Auswärtstorregel', rep=', bei Gleichstand mit Wiederholungsspiel', po=', bei Gleichstand mit Entscheidungsspiel',
               ord=['erste', 'zweite', 'dritte', 'vierte', 'fünfte', 'sechste', 'siebte']),
}


def cup(cp, lang):
    """A knockout cup's FORMAT page as plain prose: the real cup (its size), the game's slice (clubs, byes), its rounds
    by name (the last 16 / quarter-finals / semi-finals / final, else the n-th round) and how each is played.
    Returns {'prose': [paragraphs], 'real': the real cup's sentence or None}."""
    l, c, nc = CP[lang], RD[lang], NC[lang]
    real = cp.get('real') and len(cp['real']['rounds']) > 1
    s1 = [nc['real'].format(n=cp['real']['clubs'])] if real else []
    s1.append((nc['game_r'] if real else nc['game']).format(n=cp['clubs']))
    if cp.get('byes'):
        s1.append(nc['byes'].format(b=cp['byes']))
    codes = cp.get('rounds') or []
    n, byes, names = cp['clubs'], cp.get('byes') or 0, []
    for i in range(len(codes)):
        left = len(codes) - i                    # (the rounds to go: 1 = the final)
        play = n - (byes if i == 0 else 0)       # (a round's name by its clubs only when they fit: 8 = the quarters)
        key = {1: 'final', 2: 'sf', 3: 'qf', 4: 'r16'}.get(left) if play == 2 ** left else None
        names.append(c[key] if key else c['n'](nc['ord'][min(i, 6)]))
        n = play // 2 + (byes if i == 0 else 0)
    how = lambda code: {'single': (l['one'], l['pens']), 'single_et': (l['one'], l['etp']),
                        'two_legs': (l['two'], nc['away']), 'single_replay': (l['one'], nc['rep']),
                        'two_legs_pens': (l['two'], l['pens']), 'two_legs_replay': (l['two'], nc['po'])}.get(code, (l['one'], l['pens']))
    s2, i = [], 0
    while i < len(codes):
        j = i
        while j + 1 < len(codes) and codes[j + 1] == codes[i]:
            j += 1
        subj = names[i:j + 1]
        lg, lv = how(codes[i])
        s2.append(l['ko'].format(s=_list([x['art'] for x in subj], l), v=l['v'][len(subj) > 1 or subj[0]['pl']],
                                 legs=lg, nt='', lv=lv))
        i = j + 1
    if cp.get('src') == 'real':
        s2.append(nc['drawn'])
    out = [' '.join(_cap(x) for x in s1)]
    if s2:
        out.append(' '.join(_cap(x) for x in s2))
    return {'prose': out, 'real': s1[0] if real else None}


POW = {'it': dict(one='la {o}', rng='le squadre dalla {a} alla {b}', of=' di {d}', s='{who} {v} {kind}.', v=('gioca', 'giocano')),
       'en': dict(one='the {o}', rng='the clubs from {a} to {b}', of=' of {d}', s='{who} {v} {kind}.', v=('plays', 'play')),
       'fr': dict(one='le {o}', rng='les clubs du {a} au {b}', of=' de {d}', s='{who} {v} {kind}.', v=('joue', 'jouent')),
       'de': dict(one='der {o}', rng='die Vereine vom {a} bis zum {b}', of=' der {d}', s='{who} {v} {kind}.', v=('spielt', 'spielen'))}


def po_who(po, names, lang, nm):
    """A play-off contest's first sentence: who plays it ('La 1a di SEGUNDA OCCIDENTE e la 1a di SEGUNDA ORIENTE
    giocano i play-off promozione.'); None when its entrants are not division places."""
    l, w = L[lang], POW[lang]
    ent = po.get('entrants', [])
    if not ent or not all(isinstance(e, list) for e in ent):
        return None
    by = {}
    for d, p in ent:
        by.setdefault(d, []).append(p)
    items = []
    for d, ps in sorted(by.items()):
        ps = sorted(ps)
        if len(ps) == 1:
            x = w['one'].format(o=l['ord'](ps[0]))
        elif ps == list(range(ps[0], ps[-1] + 1)):
            x = w['rng'].format(a=l['ord'](ps[0]), b=l['ord'](ps[-1]))
        else:
            x = w['one'].format(o=_list([l['ord'](p) for p in ps], CP[lang]))
        items.append(x + (w['of'].format(d=nm(names[d])) if len(by) > 1 and names else ''))
    many = len(items) > 1 or len(ent) > 1
    kind = l['kind'].get(po.get('kind', 'promotion'), l['kind']['promotion'])
    return _cap(w['s'].format(who=_list(items, CP[lang]), v=w['v'][many], kind=kind))


# ---- the Brazilian state championships (statecup / statespec stages), 4.0: the same plain story
SP = {
    'it': dict(n='Il campionato statale riunisce {n} squadre.', g1='Si comincia con un girone unico da {s} squadre, {legs}',
               g='Si comincia con {g} gironi da {s} squadre, {legs}', g2='Poi le squadre vengono divise in {g} gironi da {s}.',
               once='in sola andata', twice='in andata e ritorno', cross1=", e ogni squadra affronta quelle dell'altro girone",
               crossn=', e ogni squadra affronta quelle degli altri gironi',
               ko='Poi le migliori {n} giocano la fase finale a eliminazione diretta.',
               byes='{who} passano direttamente al turno successivo.', bye1='{who} passa direttamente al turno successivo.',
               grp='del girone {x}', pts='La vittoria vale {w} punti.', down1="L'ultima retrocede.", downk='Le ultime {n} retrocedono.',
               two='in andata e ritorno', one='in gara unica', pens=', con i rigori in caso di parità',
               etp=', con supplementari e rigori in caso di parità', best=', e in caso di parità passa la meglio piazzata'),
    'en': dict(n='The state championship brings together {n} clubs.', g1='It starts with one group of {s} clubs, {legs}',
               g='It starts with {g} groups of {s} clubs, {legs}', g2='Then the clubs are split into {g} groups of {s}.',
               once='each meeting once', twice='home and away', cross1=", each club playing those of the other group",
               crossn=', each club playing those of the other groups',
               ko='Then the best {n} play the knockout finals.',
               byes='{who} go straight to the next round.', bye1='{who} goes straight to the next round.',
               grp='of group {x}', pts='A win is worth {w} points.', down1='The last club goes down.',
               downk='The bottom {n} go down.', two='over two legs', one='as single matches', pens=', with penalties if level',
               etp=', with extra time and penalties if level', best=', the better placed club going through if level'),
    'fr': dict(n='Le championnat d\'État réunit {n} clubs.', g1='On commence par un groupe unique de {s} clubs, {legs}',
               g='On commence par {g} groupes de {s} clubs, {legs}', g2='Ensuite, les clubs sont répartis en {g} groupes de {s}.',
               once='en matchs simples', twice='en aller et retour', cross1=", chaque club affrontant ceux de l'autre groupe",
               crossn=', chaque club affrontant ceux des autres groupes',
               ko='Ensuite, les {n} meilleurs jouent la phase finale à élimination directe.',
               byes='{who} passent directement au tour suivant.', bye1='{who} passe directement au tour suivant.',
               grp='du groupe {x}', pts='La victoire vaut {w} points.', down1='Le dernier descend.',
               downk='Les {n} derniers descendent.', two='en aller et retour', one='en un seul match',
               pens=", avec tirs au but en cas d'égalité", etp=", avec prolongation et tirs au but en cas d'égalité",
               best=", le mieux classé passant en cas d'égalité"),
    'de': dict(n='Die Staatsmeisterschaft vereint {n} Vereine.', g1='Sie beginnt mit einer Gruppe zu {s} Vereinen, {legs}',
               g='Sie beginnt mit {g} Gruppen zu {s} Vereinen, {legs}', g2='Danach werden die Vereine in {g} Gruppen zu {s} geteilt.',
               once='mit je einem Spiel', twice='mit Hin- und Rückspiel', cross1=', jeder Verein gegen die der anderen Gruppe',
               crossn=', jeder Verein gegen die der anderen Gruppen',
               ko='Danach spielen die besten {n} die Endrunde im K.-o.-System.',
               byes='{who} kommen direkt in die nächste Runde.', bye1='{who} kommt direkt in die nächste Runde.',
               grp='der Gruppe {x}', pts='Ein Sieg zählt {w} Punkte.', down1='Der Letzte steigt ab.',
               downk='Die letzten {n} steigen ab.', two='mit Hin- und Rückspiel', one='in einem Spiel',
               pens=', bei Gleichstand mit Elfmeterschießen', etp=', bei Gleichstand mit Verlängerung und Elfmeterschießen',
               best=', bei Gleichstand kommt der besser Platzierte weiter'),
}
_ART1 = {'it': 'la {o}', 'en': 'the {o}', 'fr': 'le {o}', 'de': 'der {o}'}


def state(c, lang):
    """A state championship's FORMAT page as plain prose (stages: groups, knockout rounds with byes; points,
    relegation)."""
    l, ln, cp, nc, rd = SP[lang], L[lang], CP[lang], NC[lang], RD[lang]
    how = lambda code: {'single': (cp['one'], cp['pens']), 'single_et': (cp['one'], cp['etp']),
                        'two_legs': (cp['two'], nc['away']), 'single_replay': (cp['one'], nc['rep']),
                        'two_legs_pens': (cp['two'], cp['pens']), 'two_legs_replay': (cp['two'], nc['po'])}.get(
                            code, (cp['two'] if code.startswith('two') else cp['one'], cp['pens']))
    s = [l['n'].format(n=len(c.get('clubs', [])))]
    stages, k, first = c.get('stages', []), 0, True
    while k < len(stages):
        st = stages[k]
        if st['type'] == 'groups':
            g, n = st.get('groups', 1), st['teams']
            if first:
                legs = l['twice'] if st.get('meetings', 1) == 2 else l['once']
                x = (l['g1'].format(s=n, legs=legs) if g == 1 else l['g'].format(g=g, s=n // g, legs=legs))
                if st.get('cross') and g > 1:
                    x += l['cross1'] if g == 2 else l['crossn']
                s.append(x + '.')
            else:
                s.append(l['g2'].format(g=g, s=n // g))
            k += 1
            first = False
            continue
        ko = []                                  # the knockout rounds that follow, by name
        while k < len(stages) and stages[k]['type'] == 'knockout':
            ko.append(stages[k])
            k += 1
        s.append(l['ko'].format(n=ko[0]['teams']))
        for st in ko:
            if st.get('byes'):                  # ('1A' = the 1st of group A)
                one = (stages or [{}])[0].get('groups', 1) == 1
                who = [_ART1[lang].format(o=ln['ord'](int(b[:-1]))) + ('' if one else ' ' + l['grp'].format(x=b[-1]))
                       for b in st['byes']]
                s.append((l['bye1'] if len(who) == 1 else l['byes']).format(who=_list(who, cp)))
        names = []
        for j, st in enumerate(ko):
            key = {2: 'final', 4: 'sf', 8: 'qf', 16: 'r16'}.get(st['teams'])
            names.append(rd[key] if key else rd['n'](nc['ord'][min(j, 6)]))
        j = 0
        while j < len(ko):
            e = j
            while e + 1 < len(ko) and ko[e + 1].get('matches', 'single') == ko[j].get('matches', 'single'):
                e += 1
            subj = names[j:e + 1]
            lg, lv = how(ko[j].get('matches', 'single'))
            s.append(cp['ko'].format(s=_list([x['art'] for x in subj], cp), v=cp['v'][len(subj) > 1 or subj[0]['pl']],
                                     legs=lg, nt='', lv=lv))
            j = e + 1
        first = False
    s.append(l['pts'].format(w=c.get('win_points', 3)))
    if c.get('relegated'):
        s.append(l['down1'] if c['relegated'] == 1 else l['downk'].format(n=c['relegated']))
    return [' '.join(_cap(x) for x in s)]
