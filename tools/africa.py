"""New African club countries (Roadmap 2): team files TEAM.052/053/054/056/058.

Clubs and final order: 1996-97 first divisions (Egypt, Morocco, Tunisia) and 1997 (Nigeria, Cameroon), from
RSSSF (tablesa/allfirst9697.html, allfirst97.html, tablesk/kam97.html; fetched 2026-10-01) and Wikipedia
(1996-97 Egyptian Premier League, 1996-97 Tunisian Ligue 1). Kits are approximate.
Squads: real 1996-97 rosters of these clubs are not available, so player and coach names are GENERATED
from common local names (not real players). Positions, faces and skill profiles come from template clubs of
the original game (Algeria TEAM.042 for North Africa, Ghana TEAM.079 for Nigeria/Cameroon), shifted towards a
strength target that falls linearly with the final position.
"""
import random
import struct

from c1c2 import level_player

TEAM_SIZE = 684

# file number: (country name per language, adjective (EN), nationality code, template file, global base,
#               (target price top, bottom), clubs in final order: (name, kit))
# kit: (shirt type, shirt colour, stripe colour, shorts, socks); colours: 0 grey 1 white 2 black 3 orange 4 red
#      5 blue 6 maroon 7 light blue 8 green 9 yellow; types: 0 plain 1 sleeves 2 vertical 3 horizontal stripes
COUNTRIES = {
    52: ({'en': 'EGYPT', 'it': 'EGITTO', 'fr': 'EGYPTE', 'de': 'AGYPTEN'}, 'EGYPTIAN', 105, 42, 424, (17, 10), [
        ('AL AHLY', (0, 4, 4, 1, 4)), ('ZAMALEK', (3, 1, 4, 1, 1)), ('EL MANSOURA', (0, 5, 5, 1, 5)),
        ('ISMAILY', (0, 9, 9, 5, 9)), ('AL ITTIHAD', (2, 8, 1, 2, 8)), ('EL QANAH', (0, 7, 7, 1, 7)),
        ('AL MASRY', (0, 8, 8, 1, 8)), ('ITTIHAD OSMAN', (0, 1, 1, 5, 5)), ('ASWAN', (0, 3, 3, 2, 3)),
        ('BALADEYA MAHALLA', (2, 4, 1, 1, 4)), ('AL MOKAWLOON', (1, 9, 2, 2, 9)), ('SUEZ', (0, 5, 5, 5, 1)),
        ('GOMHORIA SHEBIN', (0, 1, 1, 2, 1)), ('EL KOROUM', (0, 6, 6, 1, 6)), ('AL MERREIKH', (0, 4, 4, 2, 2)),
        ('AL ALUMINIUM', (0, 0, 0, 5, 0))]),
    53: ({'en': 'MOROCCO', 'it': 'MAROCCO', 'fr': 'MAROC', 'de': 'MAROKKO'}, 'MOROCCAN', 115, 42, 440, (16, 10), [
        ('RAJA CASABLANCA', (0, 8, 8, 1, 8)), ('WYDAD CASABLANCA', (0, 4, 4, 1, 4)), ('RS SETTAT', (0, 2, 2, 2, 4)),
        ('JS MASSIRA', (0, 9, 9, 8, 9)), ('DH EL JADIDA', (3, 4, 8, 1, 4)), ('CODM MEKNES', (0, 4, 4, 8, 4)),
        ('FAR RABAT', (0, 2, 2, 1, 2)), ('MC OUJDA', (0, 1, 1, 2, 2)), ('SCC MOHAMMEDIA', (0, 4, 4, 2, 4)),
        ('KAC MARRAKECH', (0, 4, 4, 1, 1)), ('HUSA AGADIR', (2, 4, 9, 4, 4)), ('WYDAD FES', (0, 4, 4, 1, 4)),
        ('AS SALE', (0, 5, 5, 1, 5)), ('OC KHOURIBGA', (2, 8, 1, 8, 8)), ('US SIDI KACEM', (0, 9, 9, 5, 9)),
        ('MOGHREB TETOUAN', (2, 4, 1, 1, 4))]),
    54: ({'en': 'TUNISIA', 'it': 'TUNISIA', 'fr': 'TUNISIE', 'de': 'TUNESIEN'}, 'TUNISIAN', 91, 42, 456, (16, 9.5), [
        ('ETOILE DU SAHEL', (0, 4, 4, 1, 4)), ('ESPERANCE TUNIS', (2, 4, 9, 2, 4)), ('CS SFAXIEN', (2, 2, 1, 2, 2)),
        ('CA BIZERTIN', (2, 2, 9, 2, 9)), ('CLUB AFRICAIN', (0, 4, 4, 1, 4)), ('OLYMPIQUE BEJA', (2, 4, 1, 1, 4)),
        ('AS MARSA', (0, 9, 9, 5, 9)), ('STADE TUNISIEN', (2, 8, 4, 1, 8)), ('JS KAIROUAN', (0, 1, 1, 7, 7)),
        ('OLYMPIQUE DU KEF', (0, 1, 1, 1, 1)), ('ES ZARZIS', (0, 9, 9, 2, 9)), ('CO TRANSPORTS', (0, 1, 1, 5, 5)),
        ('OC KERKENNAH', (0, 7, 7, 1, 7)), ('STADE SOUSSIEN', (0, 8, 8, 1, 8))]),
    56: ({'en': 'NIGERIA', 'it': 'NIGERIA', 'fr': 'NIGERIA', 'de': 'NIGERIA'}, 'NIGERIAN', 107, 79, 1924, (14, 9), [
        ('EAGLE CEMENT', (0, 7, 7, 1, 7)), ('JASPER UNITED', (0, 9, 9, 8, 9)), ('SHOOTING STARS', (0, 5, 5, 1, 5)),
        ('JULIUS BERGER', (0, 5, 5, 1, 1)), ('UDOJI UNITED', (0, 8, 8, 1, 8)), ('GOMBE UNITED', (0, 4, 4, 1, 4)),
        ('IWUANYANWU NAT.', (0, 4, 4, 1, 4)), ('EL KANEMI', (0, 1, 1, 2, 1)), ('KANO PILLARS', (0, 9, 9, 5, 9)),
        ('ENUGU RANGERS', (0, 4, 4, 1, 1)), ('SHARKS', (0, 7, 7, 2, 7)), ('KATSINA UNITED', (0, 8, 8, 1, 8)),
        ('BENDEL INSURANCE', (0, 5, 5, 5, 5)), ('BCC LIONS', (0, 9, 9, 8, 9)), ('PLATEAU UNITED', (0, 1, 1, 2, 4)),
        ('ENYIMBA', (0, 8, 8, 1, 8)), ('TORNADOES', (0, 3, 3, 2, 3)), ('NIGERDOCK', (0, 5, 5, 1, 9))]),
    58: ({'en': 'CAMEROON', 'it': 'CAMERUN', 'fr': 'CAMEROUN', 'de': 'KAMERUN'}, 'CAMEROONIAN', 94, 79, 1942,
         (13.5, 8.5), [
        ('COTONSPORT', (0, 8, 8, 1, 8)), ('STADE BANDJOUN', (0, 4, 4, 1, 4)), ('UNION DOUALA', (0, 8, 8, 4, 8)),
        ('LEOPARD DOUALA', (0, 9, 9, 2, 9)), ('OLYMPIC MVOLYE', (0, 5, 5, 1, 5)), ('PWD BAMENDA', (0, 1, 1, 5, 5)),
        ('TONNERRE YAOUNDE', (0, 1, 1, 2, 1)), ('CANON YAOUNDE', (2, 8, 4, 1, 4)), ('FOVU BAHAM', (0, 9, 9, 8, 9)),
        ('UNISPORT BAFANG', (0, 4, 4, 8, 4)), ('DYNAMO DOUALA', (0, 5, 5, 1, 4)), ('KUMBO STRIKERS', (0, 3, 3, 1, 3)),
        ('RACING BAFOUSSAM', (0, 8, 8, 9, 8)), ('PANTHERE', (0, 2, 2, 2, 9)), ('AVENIR DOUALA', (0, 7, 7, 1, 7)),
        ('VICTORIA UNITED', (0, 4, 4, 1, 1)), ('PREVOYANCE YDE', (0, 1, 1, 8, 8)), ('U. ABONG-MBANG', (0, 9, 9, 4, 9))]),
}

_ARAB_FIRST = ('AHMED MOHAMED MAHMOUD MOSTAFA HASSAN HOSSAM HANY IBRAHIM KHALED TAREK AYMAN WALID SAMIR ASHRAF '
               'MAGDY SAYED ESSAM YASSER OSAMA HAMADA SHERIF NADER TAMER REDA ADEL EMAD AMR FATHY GAMAL')
NAMES = {
    105: (_ARAB_FIRST,
          'HASSAN EL_SAYED ABDALLAH SALEM RAMADAN FAWZY SOLIMAN MANSOUR GOMAA RAGAB ZAKI SHAWKY HEGAZY FARAG '
          'MORSY NASSER KAMEL HELMY YOUSSEF AMER BAKR EL_GOHARY EL_KASS SABRY OTHMAN EID SHEHATA GHANEM '
          'FAHMY ABOU_ZEID SALAH HAFEZ EL_MASRY'),
    115: ('ABDELLATIF MUSTAPHA SAID NOUREDDINE YOUSSEF RACHID AZIZ HASSAN KHALID MOHAMED ABDELKRIM DRISS '
          'LAHCEN JAMAL HICHAM ABDELILAH TARIK ABDERRAHIM SALAHEDDINE ADIL BRAHIM KAMAL OMAR NABIL REDOUANE',
          'BENNANI EL_OUAFI BOUSSAID TAHIRI ALAOUI BERRADA LAMRANI CHAKIR ZOUHAIR AMRANI FILALI SEBBAR '
          'EL_HAMDAOUI BOUZID OUAKILI RAMI BENJELLOUN KADIRI EL_MOUTAOUAKIL SAIDI JEBBARI HAMMOUCHI MESSAOUDI '
          'NACIRI BOUAZZA EL_KHATTABI'),
    91: ('MOHAMED SAMI KAMEL ADEL KHALED NABIL TAREK SLIM RIADH HATEM MOUNIR FAOUZI LOTFI SKANDER IMED '
         'ZOUHAIER MEHDI ANIS CHOKRI HASSEN FETHI NIZAR WALID RADHI BECHIR',
         'BEN_SALAH TRABELSI JAZIRI BEN_AMOR GHARBI BOUAZIZI BEN_YOUSSEF HAMMAMI CHERIF MZOUGHI SASSI BEJAOUI '
         'KHEMIRI DRIDI BEN_SLIMANE ZITOUNI MANSOURI JELASSI BOUGHANMI ABIDI KHALFALLAH RIAHI SOUISSI KAABI'),
    107: ('SUNDAY EMMANUEL CHINEDU OLUSEGUN IKECHUKWU TUNDE BABATUNDE NDUKA FRIDAY AUGUSTINE CHIDI UCHE '
          'GODWIN PATRICK BELLO MUSA IBRAHIM YAKUBU SAMSON KELECHI VICTOR DANIEL FELIX OBINNA ADEWALE',
          'OKAFOR ADEBAYO OKONKWO EZE NWOSU OGUNDIPE ADEYEMI IBEH OBI ODUYA AKINWALE UMAR LAWAL EKWUEME '
          'OKORO NWANKWO AFOLABI OGBONNA ABUBAKAR OLADIPO IHEANACHO ANYANWU DANLADI OSUJI EKPO ADAMU'),
    94: ('JEAN PIERRE SAMUEL PAUL ANDRE JOSEPH FRANCOIS EMMANUEL ALAIN JACQUES ROGER MARC BERNARD ETIENNE '
         'GEORGES DANIEL ERIC SERGE THOMAS AUGUSTIN PASCAL CHRISTIAN RENE PATRICE',
         'NDJOCK ETAME MBARGA ATANGANA NGONO ESSOMBA TCHAMI FOTSO KAMGA NDONGO ABENA OWONA MANGA EKOTTO '
         'NKONO BELLA ONANA ESSAMA TAGNE NJOYA MOUKOKO EBANDA NGUEMO FOUDA DJOMO TOKO'),
}


# national cups (Egypt Cup, Coupe du Trone, Coupe de Tunisie, FA Cup, Coupe du Cameroun): clones of the Algerian cup,
# ids after the last original cup (0xB1); rounds 0x54 = two legs?, 0x94 = two legs, 0x14 = final, as in the original cups
NATIONAL_CUPS = {
    52: dict(id=0xb2, teams=16, rounds=(0x54, 0x54, 0x94, 0x14)),
    53: dict(id=0xb3, teams=16, rounds=(0x54, 0x54, 0x94, 0x14)),
    54: dict(id=0xb4, teams=8, rounds=(0x54, 0x54, 0x14)),             # 14 clubs: 8-team cup like Taiwan (12 clubs)
    56: dict(id=0xb5, teams=16, rounds=(0x54, 0x54, 0x94, 0x14)),
    58: dict(id=0xb6, teams=16, rounds=(0x54, 0x54, 0x94, 0x14)),
}


def gen_name(rng, nat, used, maxlen=22, names=None):
    first, last = ([w.replace('_', ' ') for w in s.split()] for s in (names or NAMES)[nat])   # '_' joins two words
    while True:
        n = f'{rng.choice(first)} {rng.choice(last)}'
        if len(n) <= maxlen and n not in used:
            used.add(n)
            return n


def build(src_dir, countries=None, names=None):
    """{file number: TEAM.0nn bytes} for all new countries (asia.py passes its own tables)."""
    out = {}
    for fileno, (_, _, nat, tmpl, base, (top, bottom), clubs) in (countries or COUNTRIES).items():
        rng = random.Random(1997 * 1000 + fileno)
        d = open(f'{src_dir}/TEAM.{tmpl:03d}', 'rb').read()
        templates = [d[2 + i * TEAM_SIZE:2 + (i + 1) * TEAM_SIZE] for i in range(struct.unpack('>H', d[:2])[0])]
        used = set()
        recs = []
        for pos, (name, kit) in enumerate(clubs):
            assert len(name) <= 16, name
            target = top - (top - bottom) * pos / (len(clubs) - 1)
            t = templates[pos % len(templates)]
            r = bytearray(t)
            r[0], r[1] = fileno, pos
            struct.pack_into('>H', r, 2, base + pos)
            r[5:22] = name.encode().ljust(17, b'\0')
            r[25] = 0
            r[26:31] = bytes(kit)
            r[31:36] = bytes((0, 1, 1, 1, 1)) if kit[1] != 1 else bytes((0, 2, 2, 2, 2))   # away: white, or black
            r[36:59] = gen_name(rng, nat, used, names=names).encode().ljust(23, b'\0')
            avg = sum(t[76 + k * 38 + 32] for k in range(16)) / 16
            step = max(-3, min(3, round((target - avg) / 2)))
            for k in range(16):
                p = 76 + k * 38
                r[p] = nat
                r[p + 3:p + 26] = gen_name(rng, nat, used, names=names).encode().ljust(23, b'\0')
                level_player(r, p, step)
            recs.append(bytes(r))
        out[fileno] = struct.pack('>H', len(recs)) + b''.join(recs)
    return out


def countries_config(countries=None, cups=None, continent='africa', months=None):
    """Entries for countries.COUNTRIES (registration in the exe). months(fileno, tmpl) -> (start, end) bytes."""
    cfg = {}
    months = months or (lambda fileno, tmpl: (0x40 if tmpl == 42 else 0x38, 0x28))
    for fileno, (names, adj, _, tmpl, base, _, clubs) in (countries or COUNTRIES).items():
        cfg[fileno] = dict(continent=continent, name={**{k: v.encode() for k, v in names.items()}},
                           adj={'en': adj.encode(), **{k: v.encode() for k, v in names.items() if k != 'en'}},
                           base=base,
                           league=dict(start=months(fileno, tmpl)[0], end=months(fileno, tmpl)[1], games=2,
                                       divisions=[(len(clubs), 0, 0, 0, 0, 0)], names=None,
                                       cup=(cups or NATIONAL_CUPS)[fileno]))
    return cfg
