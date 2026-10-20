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
        'fr': ["36 clubs disputent la phase de ligue, en 4 chapeaux de 9. Chaque club joue 8 matchs, contre 2 adversaires de chaque chapeau, un à domicile et un à l'extérieur, jamais contre un club de son association et au plus contre 2 d'une même association.", 'Il y a un classement unique : les 8 premiers vont directement en huitièmes, du 9e au 24e on joue les barrages (9e et 10e contre 23e et 24e et ainsi de suite, retour chez le mieux classé), à partir du 25e on est éliminé.', "Huitièmes, quarts et demi-finales suivent un tableau fixé par les places, en aller et retour : en cas d'égalité, prolongation et tirs au but, sans buts à l'extérieur. La finale se joue sur un match.", "À égalité de points comptent la différence de buts, les buts marqués, les buts à l'extérieur, les victoires, les victoires à l'extérieur, puis les points, la différence de buts et les buts des adversaires, les points disciplinaires et le coefficient.", "Avant la phase de ligue se jouent les tours de qualification de la liste d'accès 2026-27 (voie des champions et voie de la ligue) ; les éliminés descendent en Ligue Europa ou en Ligue Conférence."],
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


def text(world, title, lang):
    """The paragraphs for this competition, or None (the schematic lines stay)."""
    t = title.strip()
    if world == 5 and t in ('UEFA EUROPA LEAGUE', 'UEFA CONFERENCE LEAGUE'):
        return _el(lang, t.endswith('CONFERENCE LEAGUE'))
    import fmtprose_hand
    p = (fmtprose_hand.HAND.get((world, t)) or PROSE.get((world, t), {})).get(lang)
    return list(p) if p else None


# ---- the generator (4.0): every league in plain prose from its data; other competitions: their lines as sentences
L = {
    'it': dict(ord=lambda n: f'{n}a', the_league='Il campionato', the_group='Il girone',
               has='{w} ha {n} squadre che si affrontano {g}: {d} giornate', rest=', e ogni giornata una squadra riposa',
               g={1: 'una volta', 2: 'in andata e ritorno', 3: 'tre volte', 4: 'quattro volte'},
               pts='La vittoria vale {w} punti, il pareggio 1.',
               up1='La prima sale in {u}.', upk='Le prime {k} salgono in {u}.', upper='la categoria superiore',
               down1="L'ultima retrocede in {l}.", downk='Le ultime {k} retrocedono in {l}.', lower='la categoria inferiore',
               none='Non retrocede nessuno.',
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
               none='Nobody goes down.',
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
               none='Personne ne descend.',
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
               none='Niemand steigt ab.',
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


def league(div, k, lg, win, lang, pos, lowest, nm):
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
