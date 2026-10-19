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
}
