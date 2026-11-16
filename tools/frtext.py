"""4.2 preseason friendlies, part (b): the player-facing texts of the opponent pick (owner Mercato CPU).

What is here: the calendar label, the season record's line (name + won / drawn / lost) and the FORMAT page's prose, in
IT / EN / FR / DE, with their width and charset checks (CONVENTIONS 1, 2, 4). Nothing here patches an exe: the engine
(Motore, FRND) takes LABEL / REC_NAME / REC_LINE into its label table, and the FORMAT page is added by
    fmtgame.EXTRA += frtext.format_items(worlds)        # patch.py, before fmtgame.write(); worlds = those with FRSS
when the friendlies' slot-4 contest is named LABEL[lang] (the page is found by the contest's name, id = any).
The rules told by the prose are tools/frpick.h's; the fees are internal/handoff/friendlies-pick.md "Fee table".

    python3 tools/frtext.py         the table of every string with its width and bar, the FORMAT pages as the game
                                    shows them (EN), and every assert below; tools/hosttest/tests/test_frtext.py runs it
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import complist
import fmtgame
import fmtpage
import typofix

LANGS = ('it', 'en', 'fr', 'de')
EXE = {'it': 'ITALIAN.EXE', 'en': 'ENGLISH.EXE', 'fr': 'FRENCH.EXE', 'de': 'GERMAN.EXE'}

# The calendar label / the contest's name (decided: friendlies-a-interface.md). IT / EN / FR are each exe's own word
# for a friendly in a record (the national-team coach's FRIENDLY line, ref aFriendly_0); the German exe's own is
# FREUND-SP (same place) and FREUNDSCHAFTSSPIEL (menus): TESTSPIEL is the decided label, FREUND-SP the alternative.
LABEL = {'it': 'AMICHEVOLE', 'en': 'FRIENDLY', 'fr': 'AMICAL', 'de': 'TESTSPIEL'}
LABEL_NATIVE_DE = 'FREUND-SP'

# The season record (REGISTRO GESTIONE / ManagementRecordMenu): entry 7 = the competition (x 0, 144 px), entry 8 = its
# outcome (x 160, 144 px), small font. The game already has this very line for a national-team coach (cseg_3892C:
# 'FRIENDLIES' + 'WON %0  DRAWN %1  LOST %2', '-' when all three are 0): the same shape, each exe's own strings.
REC_NAME = {'it': 'AMICHEVOLI', 'en': 'FRIENDLIES', 'fr': 'MAT. AMICAUX', 'de': 'TESTSPIELE'}
REC_NAME_NATIVE_DE = 'FREUND-SP'
REC_LINE = {                             # the exe's own string, byte for byte (%0 won, %1 drawn, %2 lost: FR_ST +10
    'it': 'VINCITE %0 PAREGGI %1 SCON %2',      # bits 4-12, 3 bits each, 0 .. 4; IT: as the patched exe has it -
                                                #  typofix.py fixes the original's PARREGGI in place, Davide 16/11)
    'en': 'WON %0  DRAWN %1  LOST %2',
    'fr': 'GAGNES %0 NULS %1  PERDUS %2',
    'de': 'SIEG %0  UNENT %1  VERL %2',
}
REC_NONE = '-'                           # no friendly played yet (the game's own aDash)

CAL_PX = complist.CAL_PX                 # 70: the career calendar's label
REC_PX = 144                             # gplay.REC_PX: both columns of the season record
TITLE_PX = 302                           # rnames.PXMAX: the match screen's title bar
TITLE_MAX = 35                           # the contest's title field (bytes)


def rec_worst(s):
    """The record line at its widest: every count a 6-px digit (any digit but 1)."""
    return s.replace('%0', '4').replace('%1', '4').replace('%2', '4')


# ---- the FORMAT page (CONVENTIONS 4: discursive prose, the approved Libertadores style; fmtgame.ascii_up drops the
# accents and writes AE / OE / UE, wrap_px wraps at 298 px). No '%' (not a font glyph): 'per cent' in words; no ';'
# (the page shows it as ','); in French no ' :' (it would open a line). Paragraphs: 0 what they are + the record, 1 the
# venues, 2 the opponents, 3 the nearest level, 4 the fees + FFP (check() reads the fee paragraph by FEE_PARA).
FORMAT = {
    'it': [
        "Prima della prima partita ufficiale della stagione la tua squadra gioca quattro amichevoli estive. Non danno "
        "punti e non contano per nessuna classifica o coppa: servono a provare la squadra e a fare cassa, e il loro "
        "bilancio (vinte, pareggiate, perse) è tenuto a parte. All'inizio della stagione una pagina ti lascia "
        "scegliere le avversarie. Se non tocchi nulla le sceglie il gioco.",
        "Due amichevoli si giocano in casa e due in trasferta: ricevi le due avversarie più deboli delle quattro e "
        "vai in casa delle due più forti.",
        "Il gioco misura la forza di ogni squadra dal valore dei suoi undici giocatori migliori e sceglie una "
        "avversaria più forte della tua, due di forza simile e una più debole: sempre squadre straniere, di quattro "
        "paesi diversi quando è possibile, e non quelle dell'estate prima. Simile vuol dire entro un decimo circa "
        "della forza della tua squadra. Più forte o più debole vuol dire tra uno e quattro decimi di distanza.",
        "Quando una fascia è vuota il gioco prende la squadra più vicina per forza. La più forte del mondo, che non "
        "ha nessuno sopra, affronta la più forte rimasta. Le squadre più deboli, che non hanno nessuno sotto, trovano "
        "come avversaria facile la più debole del loro stesso livello.",
        "Ogni amichevole porta soldi, misurati sull'incasso di una tua partita di campionato in casa. In casa tieni "
        "l'incasso: intero (100 per cento) contro una squadra più forte, la metà (50) contro una simile, 30 per cento "
        "contro una più debole. In trasferta ricevi un ingaggio: 40 per cento da una squadra più forte, 20 da una "
        "simile, 10 da una più debole. Un'avversaria molto più forte, che incontri solo se la scegli tu o se non ce "
        "n'è una più vicina, vale 120 in casa e 50 fuori. Una molto più debole vale 20 e 5. Questi soldi contano come "
        "incassi da stadio, anche per il fair play finanziario.",
    ],
    'en': [
        "Before the first competitive match of the season your club plays four preseason friendlies. They bring no "
        "points and count for no table or cup: they are there to try the team out and to earn some money, and their "
        "record (won, drawn, lost) is kept apart. A page at the start of the season lets you choose the opponents. "
        "Leave it alone and the game picks them.",
        "Two friendlies are at home and two away: you host the two weakest of your four opponents and travel to the "
        "two strongest.",
        "The game rates every club by the value of its best eleven players and picks one opponent stronger than you, "
        "two of similar strength and one weaker: always foreign clubs, from four different countries where possible, "
        "and not the ones you met last summer. Similar means within about a tenth of your own club's strength. "
        "Stronger or weaker means between one and four tenths away.",
        "When a band is empty the game takes the club nearest in strength. The strongest club in the world, with "
        "nobody above it, meets the strongest club left. The weakest clubs, with nobody below them, get the weakest "
        "club of their own level as their easier opponent.",
        "Every friendly pays, measured against the gate of one of your home league matches. At home you keep the "
        "gate: a full one (100 per cent) against a stronger club, half (50) against a similar one, 30 per cent "
        "against a weaker one. Away you receive an appearance fee: 40 per cent from a stronger club, 20 from a "
        "similar one, 10 from a weaker one. A much stronger opponent, which you only meet by choosing it or when no "
        "nearer club exists, is worth 120 at home and 50 away. A much weaker one is worth 20 and 5. The money counts "
        "as gate income, for financial fair play too.",
    ],
    'fr': [
        "Avant le premier match officiel de la saison, ton club joue quatre matchs amicaux de préparation. Ils ne "
        "rapportent aucun point et ne comptent pour aucun classement ni aucune coupe. Ils servent à essayer l'équipe "
        "et à remplir la caisse, et leur bilan (gagnés, nuls, perdus) est tenu à part. Une page en début de saison "
        "te laisse choisir les adversaires. Si tu n'y touches pas, le jeu les choisit.",
        "Deux amicaux se jouent à domicile et deux à l'extérieur. Tu reçois les deux plus faibles de tes quatre "
        "adversaires et tu te déplaces chez les deux plus forts.",
        "Le jeu mesure la force de chaque club par la valeur de ses onze meilleurs joueurs et choisit un adversaire "
        "plus fort que toi, deux de force comparable et un plus faible, toujours des clubs étrangers, de quatre pays "
        "différents si possible, et pas ceux de l'été précédent. Comparable veut dire à un dixième environ de la "
        "force de ton club. Plus fort ou plus faible veut dire entre un et quatre dixièmes d'écart.",
        "Quand une tranche est vide, le jeu prend le club le plus proche en force. Le plus fort du monde, qui n'a "
        "personne au-dessus de lui, affronte le plus fort qui reste. Les clubs les plus faibles, qui n'ont personne "
        "en dessous, ont pour adversaire facile le plus faible de leur niveau.",
        "Chaque amical rapporte de l'argent, mesuré sur la recette d'un de tes matchs de championnat à domicile. À "
        "domicile tu gardes la recette, entière (100 pour cent) contre un club plus fort, la moitié (50) contre un "
        "club comparable, 30 pour cent contre un plus faible. À l'extérieur tu touches un cachet, 40 pour cent chez "
        "un club plus fort, 20 chez un club comparable, 10 chez un plus faible. Un adversaire beaucoup plus fort, que "
        "tu ne rencontres que si tu le choisis ou s'il n'y a aucun club plus proche, vaut 120 à domicile et 50 à "
        "l'extérieur. Un adversaire beaucoup plus faible vaut 20 et 5. Cet argent compte comme recette de "
        "billetterie, y compris pour le fair-play financier.",
    ],
    'de': [
        "Vor dem ersten Pflichtspiel der Saison bestreitet dein Verein vier Testspiele. Sie bringen keine Punkte und "
        "zählen für keine Tabelle und keinen Pokal: sie dienen dazu, die Mannschaft zu erproben und Geld einzunehmen, "
        "und ihre Bilanz (Siege, Unentschieden, Niederlagen) wird getrennt geführt. Auf einer Seite zu Saisonbeginn "
        "kannst du die Gegner wählen. Änderst du nichts, wählt das Spiel sie aus.",
        "Zwei Testspiele finden daheim statt und zwei auswärts: du empfängst die zwei schwächsten deiner vier Gegner "
        "und reist zu den zwei stärksten.",
        "Das Spiel misst die Stärke jedes Vereins am Wert seiner elf besten Spieler und wählt einen stärkeren Gegner, "
        "zwei etwa gleich starke und einen schwächeren: immer ausländische Vereine, möglichst aus vier verschiedenen "
        "Ländern, und nicht die des letzten Sommers. Gleich stark heißt bis etwa ein Zehntel von der Stärke deines "
        "Vereins entfernt. Stärker oder schwächer heißt zwischen einem und vier Zehnteln entfernt.",
        "Ist eine Stufe leer, kommt der nach Stärke nächste Verein. Der stärkste der Welt, über dem keiner steht, "
        "trifft auf den stärksten übrigen. Die schwächsten Vereine, unter denen keiner steht, bekommen als "
        "leichteren Gegner den schwächsten ihres Niveaus.",
        "Jedes Testspiel bringt Geld, gemessen an der Einnahme eines deiner Liga-Heimspiele. Daheim behältst du die "
        "Einnahme: die volle (100 Prozent) gegen einen stärkeren Verein, die halbe (50) gegen einen gleich starken, "
        "30 Prozent gegen einen schwächeren. Auswärts erhältst du ein Antrittsgeld: 40 Prozent bei einem stärkeren "
        "Verein, 20 bei einem gleich starken, 10 bei einem schwächeren. Ein viel stärkerer Gegner, auf den du nur "
        "triffst, wenn du ihn selbst wählst oder kein näherer Verein da ist, bringt 120 daheim und 50 auswärts. Ein "
        "viel schwächerer bringt 20 und 5. Das Geld zählt als Zuschauereinnahme, auch für das Financial Fair Play.",
    ],
}

# The fee table the prose tells (percent of one home league gate; friendlies-pick.md "Fee table", FINAL): band ->
# (home, away). check() holds every figure of it in every language's fee paragraph.
FEE_PARA = 4
FEES = {'far up': (120, 50), 'stronger': (100, 40), 'similar': (50, 20), 'weaker': (30, 10), 'far down': (20, 5)}


def on():
    """The friendlies' engine (FRND, Motore) is linked in this build. Its data ship only with it (data after engine:
    DATA\\FRSS.DAT, patch_exe, and the FORMAT page, write_new_teams): the switch is Motore's tools/frnd.py on(), the
    module that links FRND - no such module, off. One predicate for both, so neither can ship alone."""
    try:
        import frnd
    except ImportError:
        return False
    return bool(frnd.on())


def format_items(worlds):
    """fmtgame.EXTRA entries: the friendlies' FORMAT page in every world given (id None = any contest of that name)."""
    texts = {l: {'prose': list(FORMAT[l]), 'tail': []} for l in LANGS}
    # (both title forms, as fmtgame.world_items: a contest without a country is written ' ' + name, careerworld w_pfx)
    return [(w, None, t, texts) for w in worlds for t in (dict(LABEL), {l: ' ' + n for l, n in LABEL.items()})]


def format_pages(lang):
    """The page as the game shows it: fmtgame.write()'s own steps (ascii_up, wrap_px, a gap between paragraphs)."""
    body = []
    for para in FORMAT[lang]:
        body += [fmtgame.wrap_px(fmtgame.ascii_up(para, lang)), [fmtgame.GAP]]
    body.pop()
    return fmtgame.pages(body)


def rows():
    """[(what, lang, string, px, bar px, bar)] - every label / record string against the bar it is drawn in."""
    out = []
    for l in LANGS:
        out.append(('label', l, LABEL[l], complist.px(LABEL[l]), CAL_PX, 'calendar label'))
    out.append(('label (exe\'s own)', 'de', LABEL_NATIVE_DE, complist.px(LABEL_NATIVE_DE), CAL_PX, 'calendar label'))
    for l in LANGS:
        out.append(('record name', l, REC_NAME[l], complist.px(REC_NAME[l]), REC_PX, 'season record, column 1'))
    out.append(('record name (exe\'s own)', 'de', REC_NAME_NATIVE_DE, complist.px(REC_NAME_NATIVE_DE), REC_PX,
                'season record, column 1'))
    for l in LANGS:
        out.append(('record line', l, REC_LINE[l], complist.px(rec_worst(REC_LINE[l])), REC_PX,
                    'season record, column 2'))
    return out


def check(orig=None):
    """Every assert of these texts; returns the number of checks. orig = the dir of the four original exes (the
    record line must be each exe's own string): skipped when absent."""
    n = 0
    for what, l, s, w, bar, where in rows():
        t = rec_worst(s)
        assert w <= bar, (what, l, s, w, bar)
        assert all(c in complist.FONT for c in t), (what, l, s, sorted(set(t) - complist.FONT))
        assert t == t.upper() and t == t.strip() and len(t) <= TITLE_MAX, (what, l, s)
        n += 1
    for l in LANGS:                                         # the label as a contest name: the title field, the match
        assert len(LABEL[l]) <= TITLE_MAX and complist.px(LABEL[l]) <= TITLE_PX and '  ' not in LABEL[l]   # screen bar
        complist.cal_label(LABEL[l], f'frtext {l}')
        for k in '%0', '%1', '%2':
            assert REC_LINE[l].count(k) == 1, (l, k)
        n += 2
    if orig and all(os.path.exists(os.path.join(orig, e)) for e in EXE.values()):
        for l in LANGS:
            d = open(os.path.join(orig, EXE[l]), 'rb').read()
            src = next((o for o, f in typofix.FIXES.get(l, ()) if f == REC_LINE[l].encode()), REC_LINE[l].encode())
            assert d.count(src + b'\0') == 1, f'{l}: the record line is not the exe\'s own string (typofix: as patched)'
            for s in ((LABEL[l], REC_NAME[l]) if l != 'de' else (LABEL_NATIVE_DE,)):
                assert b'\0' + s.encode() + b'\0' in d, f'{l}: {s} is not the exe\'s own word'
            n += 1
    for l in LANGS:                                         # the FORMAT page
        paras = FORMAT[l]
        assert len(paras) == len(FORMAT['en']), l
        pg = format_pages(l)
        text = 0
        for page in pg:
            assert 0 < len(page) <= fmtpage.LINES, (l, len(page))
            assert page[0] and page[-1], (l, 'a blank line at a page edge')
            for line in page:
                assert fmtgame.px(line) <= fmtgame.PX_MAX and len(line) < fmtpage.LINE_W, (l, line)
                assert all(c in complist.FONT for c in line), (l, line, sorted(set(line) - complist.FONT))
                assert not any(c in line for c in complist.DE_UMLAUT), (l, line)
                text += len(line) + 1
        assert text <= fmtpage.TXTMAX, (l, text)
        fee = fmtgame.ascii_up(paras[FEE_PARA], l)
        for v in sorted({x for hv in FEES.values() for x in hv}):
            assert f' {v} ' in fee.replace('(', ' ').replace(')', ' ').replace(',', ' ').replace(':', ' ') \
                .replace('.', ' '), (l, v)
        n += 1
    for l, title in LABEL.items():                          # the page's key = the contest's name
        assert len(title) <= fmtpage.NAME - 1, (l, title)
    for w, cid, titles, texts in format_items((0, 4, 5)):
        assert cid is None and titles in (LABEL, {l: ' ' + t for l, t in LABEL.items()}) and set(texts) == set(LANGS)
        assert all(len(t) <= fmtpage.NAME - 1 for t in titles.values()), titles
    return n


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    orig = os.path.join(os.path.dirname(here), 'orig')
    n = check(orig)
    print(f'{"what":26}{"lang":5}{"string":34}{"px":>4} {"bar":>4}  where')
    for what, l, s, w, bar, where in rows():
        print(f'{what:26}{l:5}{s:34}{w:>4} {bar:>4}  {where}')
    for l in LANGS:
        pg = format_pages(l)
        print(f'FORMAT {l}: {len(FORMAT[l])} paragraphs, {len(pg)} pages, {sum(len(p) for p in pg)} lines, widest '
              f'{max(fmtgame.px(x) for p in pg for x in p)} px of {fmtgame.PX_MAX}')
    if '-v' in sys.argv:
        for l in LANGS:
            for i, page in enumerate(format_pages(l)):
                print(f'--- {l} page {i + 1}')
                print('\n'.join(page))
    print(f'frtext: {n} checks OK' + ('' if os.path.exists(os.path.join(orig, EXE["it"])) else ' (no orig/: exe strings not checked)'))


if __name__ == '__main__':
    main()
