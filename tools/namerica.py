"""New Central American club countries (Roadmap 2, 1.2): Guatemala (TEAM.087), Honduras (TEAM.088).

Clubs and final order: 1996-97 first divisions (RSSSF tablesa/allfirst9697.html, fetched 2026-10-01); Guatemala's
play-off champion Comunicaciones (beat Aurora, first in the table) is listed first. Squads and coaches are GENERATED
from common local names, as for Africa and Asia: no reliable 1996-97 rosters. Template: El Salvador (TEAM.051).
Kits are approximate. Country numbers 87 and 88 (after Saudi Arabia, 86).
"""
from africa import build as _build, countries_config as _config

COUNTRIES = {
    87: ({'en': 'GUATEMALA', 'it': 'GUATEMALA', 'fr': 'GUATEMALA', 'de': 'GUATEMALA'}, 'GUATEMALAN', 53, 51, 1764, (13, 9), [
        ('COMUNICACIONES', (0, 1, 1, 1, 1)), ('AURORA', (0, 9, 9, 5, 9)), ('MUNICIPAL', (0, 4, 4, 5, 4)),
        ('TALLY JUCA', (0, 5, 5, 1, 5)), ('SUCHITEPEQUEZ', (0, 6, 6, 1, 6)), ('AZUCAREROS', (0, 8, 8, 1, 8)),
        ('ZACAPA', (0, 4, 4, 1, 1)), ('ESCUINTLA', (0, 7, 7, 1, 7)), ('XELAJU', (0, 4, 4, 2, 4)),
        ('AMATITLAN', (0, 9, 9, 2, 9)), ('SACACHISPAS', (0, 5, 5, 5, 1)), ('IZABAL JC', (0, 8, 8, 5, 8))]),
    88: ({'en': 'HONDURAS', 'it': 'HONDURAS', 'fr': 'HONDURAS', 'de': 'HONDURAS'}, 'HONDURAN', 54, 51, 1776, (13, 9), [
        ('OLIMPIA', (0, 1, 1, 1, 1)), ('VICTORIA', (0, 5, 5, 1, 5)), ('PLATENSE', (0, 1, 1, 2, 1)),
        ('MOTAGUA', (0, 5, 5, 5, 5)), ('MARATHON', (0, 8, 8, 1, 8)), ('REAL ESPANA', (0, 9, 9, 2, 9)),
        ('UNIVERSIDAD', (0, 6, 6, 1, 6)), ('VIDA', (0, 4, 4, 1, 4)), ('REAL MAYA', (0, 7, 7, 1, 7)),
        ('INDEPENDIENTE', (0, 4, 4, 5, 4))]),
}

NAMES = {
    53: ('JOSE CARLOS JUAN LUIS MARIO JORGE EDGAR ERWIN FREDY JULIO MARVIN ROLANDO OTTO RAFAEL SERGIO HECTOR '
         'GUILLERMO ALEX OSCAR RUBEN',
         'LOPEZ GARCIA PEREZ RODRIGUEZ HERNANDEZ MORALES CASTILLO RAMIREZ FLORES REYES CRUZ ORTIZ MENDOZA '
         'ESTRADA AGUILAR VELASQUEZ MONTERROSO CIFUENTES BARRIOS SOTO'),
    54: ('CARLOS JOSE LUIS MARIO JUAN DANIEL MILTON NERY AMADO SAMUEL WILMER JULIO FRANCISCO EDGARDO RAUL '
         'NIGEL CARLO DENNIS ELVIS OSMAN',
         'MARTINEZ LOPEZ MEJIA FLORES REYES ZUNIGA SIERRA CASTRO GUEVARA SUAZO ALVAREZ NUNEZ BERNARDEZ '
         'MOLINA BONILLA TROCHEZ ZELAYA PALACIOS FIGUEROA CABALLERO'),
}

NATIONAL_CUPS = {
    87: dict(id=0xbf, teams=8, rounds=(0x54, 0x54, 0x14)),
    88: dict(id=0xc0, teams=8, rounds=(0x54, 0x54, 0x14)),
}
LEAGUE_IDS = {87: 0xbd, 88: 0xbe}


def build(src_dir):
    return _build(src_dir, COUNTRIES, NAMES)


def countries_config():
    cfg = _config(COUNTRIES, NATIONAL_CUPS, 'north_america', lambda fileno, tmpl: (0x38, 0x20))   # as El Salvador
    for n, cid in LEAGUE_IDS.items():
        cfg[n]['league']['id'] = cid
    return cfg
