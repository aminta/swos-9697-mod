"""World 2026-27: the other confederations' club-cup places of each top flight (zones.py colours, fmtgame.py lines), by
pack id; a pack's own "continental_places" overrides its entry.

Entry: [{"cup": key, "places": [first, last]}, ...] (zones.CONFED keys: lib / sud, ccc, acle / acl2, cafcl / cafcc,
ofc) + optional {"cup": key, "via": "cup"} (the national cup winner's place) and {"note": kind} for the leagues whose
real places are not table positions (fmtgame.CONFED_NOTES: 'split' Apertura / Clausura champions then the annual
table, 'final' the champion of a final / play-offs): the game plays one table there, coloured as its annual table.

Sources, CONMEBOL (the 2026 editions, the same per-association rules for 2027): the Copa Libertadores 2026 and Copa
Sudamericana 2026 qualified teams (en.wikipedia.org/wiki/2026_Copa_Libertadores, /2026_Copa_Sudamericana): berths per
association (Argentina 6, Brazil 7, the others 4 in the Libertadores; Argentina and Brazil 6, the others 4 in the
Sudamericana) and their domestic routes. The holders' extra places are not shown (decided by the cups).
AFC: the 2026-27 ACL Elite / ACL Two qualified teams (wiki 2026-27_AFC_Champions_League_Elite / _Two): the league
routes per association (the preliminary-stage places as ACL Elite; places moved down by holders or ineligible clubs
counted back). CAF: the standard allocation of the top 12 associations (2 Champions League: champion and runner-up;
2 Confederation Cup: 3rd and the cup winner), Ghana 1 + 1. CONCACAF: the 2027 Champions Cup qualified clubs (concacaf.com:
Liga MX 6, MLS 5, CPL 2, Canadian Championship, U.S. Open Cup; the Central American / Caribbean leagues through the
Central American / Caribbean Cups). OFC: New Zealand's 2 places (a developed association). DECLARED: see below.
"""

W = 'world-2026-27-'
PLACES = {
    W + 'bra': [{'cup': 'lib', 'places': [1, 6]}, {'cup': 'sud', 'places': [7, 12]}, {'cup': 'lib', 'via': 'cup'}],
    W + 'arg': [{'cup': 'lib', 'places': [1, 5]}, {'cup': 'sud', 'places': [6, 11]}, {'cup': 'lib', 'via': 'cup'},
                {'note': 'annual'}],                                 # (the annual table: STAT > CLASSIFICA GENERALE)
    W + 'bol': [{'cup': 'lib', 'places': [1, 3]}, {'cup': 'sud', 'places': [4, 7]}, {'cup': 'lib', 'via': 'cup'}],
    W + 'chi': [{'cup': 'lib', 'places': [1, 3]}, {'cup': 'sud', 'places': [4, 7]}, {'cup': 'lib', 'via': 'cup'}],
    W + 'col': [{'cup': 'lib', 'places': [1, 4]}, {'cup': 'sud', 'places': [5, 7]}, {'cup': 'sud', 'via': 'cup'},
                {'note': 'split'}],
    W + 'ecu': [{'cup': 'lib', 'places': [1, 3]}, {'cup': 'sud', 'places': [4, 5]}, {'cup': 'sud', 'places': [7, 8]},
                {'cup': 'lib', 'via': 'cup'}],
    W + 'par': [{'cup': 'lib', 'places': [1, 3]}, {'cup': 'sud', 'places': [4, 7]}, {'cup': 'lib', 'via': 'cup'},
                {'note': 'split'}],
    W + 'per': [{'cup': 'lib', 'places': [1, 4]}, {'cup': 'sud', 'places': [5, 8]}],
    W + 'uru': [{'cup': 'lib', 'places': [1, 4]}, {'cup': 'sud', 'places': [5, 8]}, {'note': 'final'}],
    W + 'ven': [{'cup': 'lib', 'places': [1, 4]}, {'cup': 'sud', 'places': [5, 8]}, {'note': 'final'}],
    # AFC (2026-27 routes)
    W + 'jpn': [{'cup': 'acle', 'places': [1, 3]}, {'cup': 'acl2', 'via': 'cup'}],
    W + 'ksa': [{'cup': 'acle', 'places': [1, 5]}, {'cup': 'acl2', 'places': [6, 6]}],
    W + 'kor': [{'cup': 'acle', 'places': [1, 3]}, {'cup': 'acl2', 'places': [4, 4]}, {'cup': 'acle', 'via': 'cup'}],   # 3 + 1 play-off (2026-27: champion = cup winner, Gimcheon ineligible)
    W + 'uae': [{'cup': 'acle', 'places': [1, 4]}, {'cup': 'acl2', 'places': [5, 5]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'qat': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 3]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'irn': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 3]}, {'cup': 'acl2', 'via': 'cup'}],
    W + 'chn': [{'cup': 'acle', 'places': [1, 1]}, {'cup': 'acl2', 'places': [2, 2]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'aus': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 3]}, {'note': 'final'}],   # premiers + runners-up (play-off)
    W + 'ind': [{'cup': 'acl2', 'places': [1, 1]}, {'cup': 'acl2', 'via': 'cup'}],   # ISL champion, Super Cup winner (preliminary)
    # CAF
    W + 'egy': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'mar': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'alg': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'tun': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'rsa': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'gha': [{'cup': 'cafcl', 'places': [1, 1]}, {'cup': 'cafcc', 'via': 'cup'}],
    # CONCACAF (Champions Cup through the league; the Central American and Caribbean leagues qualify through the
    # Central American / Caribbean Cups: no colours)
    W + 'mex': [],   # (Apertura / Clausura champions and runners-up + 2 aggregate: no table places - Davide 2026-10-24:
                     # the tables show the Liguilla 1st-8th, the access is told by the FORMAT text)
    W + 'usa': [{'cup': 'ccc', 'places': [1, 3]}, {'cup': 'ccc', 'via': 'cup'}, {'note': 'final'}],   # Shield + next 2; MLS Cup, the other conference's leader
    W + 'can': [{'cup': 'ccc', 'places': [1, 1]}, {'cup': 'ccc', 'via': 'cup'}, {'note': 'final'}],   # CPL Shield + league (final) winner
    # OFC
    W + 'nzl': [{'cup': 'ofc', 'places': [1, 2]}, {'note': 'final'}],   # 2 places (developed association), via the National League
}
# declared in the release notes: places by the game's single table where the real ones are not table positions
# (Apertura / Clausura champions, play-off finals, conference leaders) or from the general rule (Ghana, Iran's cup)
DECLARED = {'split': ('arg', 'col', 'par'), 'final': ('uru', 'ven', 'aus', 'usa', 'can', 'nzl'),
            'rule': ('gha', 'irn', 'ind')}
