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
2 Confederation Cup: 3rd and the cup winner), Ghana 1 + 1. CONCACAF / OFC: see each entry (approximations listed in
APPROX, to confirm).
"""

W = 'world-2026-27-'
PLACES = {
    W + 'bra': [{'cup': 'lib', 'places': [1, 6]}, {'cup': 'sud', 'places': [7, 12]}, {'cup': 'lib', 'via': 'cup'}],
    W + 'arg': [{'cup': 'lib', 'places': [1, 5]}, {'cup': 'sud', 'places': [6, 11]}, {'cup': 'lib', 'via': 'cup'},
                {'note': 'split'}],
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
    W + 'kor': [{'cup': 'acle', 'places': [1, 4]}, {'cup': 'acl2', 'places': [5, 5]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'uae': [{'cup': 'acle', 'places': [1, 4]}, {'cup': 'acl2', 'places': [5, 5]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'qat': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 3]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'irn': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 4]}],
    W + 'chn': [{'cup': 'acle', 'places': [1, 1]}, {'cup': 'acl2', 'places': [2, 2]}, {'cup': 'acle', 'via': 'cup'}],
    W + 'aus': [{'cup': 'acle', 'places': [1, 2]}, {'cup': 'acl2', 'places': [3, 4]}, {'note': 'final'}],
    W + 'ind': [{'cup': 'acl2', 'places': [1, 1]}],
    # CAF
    W + 'egy': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'mar': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'alg': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'tun': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'rsa': [{'cup': 'cafcl', 'places': [1, 2]}, {'cup': 'cafcc', 'places': [3, 3]}, {'cup': 'cafcc', 'via': 'cup'}],
    W + 'gha': [{'cup': 'cafcl', 'places': [1, 1]}, {'cup': 'cafcc', 'via': 'cup'}],
    # CONCACAF (Champions Cup through the league; the Central American and Caribbean leagues qualify through the
    # Central American / Caribbean Cups: no colours)
    W + 'mex': [{'cup': 'ccc', 'places': [1, 6]}, {'note': 'split'}],
    W + 'usa': [{'cup': 'ccc', 'places': [1, 4]}, {'cup': 'ccc', 'via': 'cup'}, {'note': 'final'}],
    W + 'can': [{'cup': 'ccc', 'places': [1, 1]}, {'cup': 'ccc', 'via': 'cup'}, {'note': 'final'}],
    # OFC
    W + 'nzl': [{'cup': 'ofc', 'places': [1, 2]}, {'note': 'final'}],
}
# entries not taken from a qualified-teams list (the regulation's general rule or the game's single table): to confirm
APPROX = ('kor', 'irn', 'aus', 'ind', 'gha', 'mex', 'usa', 'can', 'nzl')
