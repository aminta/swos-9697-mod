"""DDR 1988-89 (historic nation, Davide 2026-10-05/08): DDR-Oberliga 1988-89 + FDGB-Pokal 1988-89.

Sources (2026-10-08): de.wikipedia 'DDR-Fußball-Oberliga 1988/89' (final table, champions' squad) and
'FDGB-Pokal 1988/89' (bracket); weltfussball.de squads 1988/1989 (team pages, 'Kader') and Oberliga 1988/89
appearance statistics ('Statistik: Einsätze', ordered by minutes played). Player skills: SWOS 2020 teamdb
'1990_91 - Team Updates' by Peppecapello (its TEAM.010 = the 14 NOFV-Oberliga clubs 1990-91) for the players it
has, otherwise c1c2-style calibration.

Rules: Oberliga 14 clubs, 26 rounds, 2 points for a win. FDGB-Pokal from the 2nd main round (8 Oct 1988, 32 clubs:
the 14 Oberliga clubs + 18 DDR-Liga / district cup clubs), single matches, extra time and penalties, real bracket
(fixed pairings round by round), final BFC Dynamo - FC Karl-Marx-Stadt 1-0 (Berlin, 1 May 1989).

Squads: per club the players in order (Oberliga: most minutes first; lower clubs: weltfussball squad list, which is
by role), role G/D/M/A. build picks 2 goalkeepers + 14 outfield players (keeping the order).
"""

# key: (SWOS name <= 16 chars, coach, 'Name:R;...')
OBERLIGA = [   # final table order 1988-89
    ('dresden', 'DYNAMO DRESDEN', 'Eduard Geyer',
     'Frank Lieberam:D;Ronny Teuber:G;Matthias Sammer:M;Ulf Kirsten:A;Torsten Gütschow:A;Jörg Stübner:M;'
     'Matthias Döschner:M;Andreas Trautmann:D;Ralf Hauptmann:M;Uwe Kirchner:D;Hans-Uwe Pilz:M;Ralf Minge:A;'
     'Steffen Büttner:D;Andreas Diebitz:D;Uwe Jähnig:A;Matthias Maucksch:M;Bernd Fritzsche:D;Thomas Köhler:G'),
    ('bfc', 'BFC DYNAMO', 'Jürgen Bogs',
     'Bodo Rudwaleit:G;Andreas Thom:A;Frank Rohde:D;Thomas Doll:A;Eike Küttner:M;Marco Köller:D;Rainer Ernst:A;'
     'Burkhard Reich:D;Hendrik Herzog:D;Frank Pastor:A;Waldemar Ksienzyk:D;Bernd Schulz:M;Jörg Fügner:M;'
     'Jens-Uwe Zöphel:M;Michael Schulz:M;Christian Backs:M;Dirk Anders:M;Oskar Kosche:G'),
    ('kms', 'KARL-MARX-STADT', 'Hans Meyer',
     'Jens Schmidt:G;Ulf Mehlhorn:M;Detlef Müller:D;Steffen Ziffert:D;Hans Richter:A;Sven Köhler:M;'
     'Thomas Laudeley:D;Steffen Heidrich:M;Rico Steinmann:M;Jörg Illing:D;Lutz Wienhold:M;Udo Fankhänel:D;'
     'Peter Keller:M;Dirk Barsikow:D;Gerd Seifert:A;Torsten Bittermann:D;Stefan Persigehl:A;Holger Hiemann:G'),
    ('rostock', 'HANSA ROSTOCK', 'Werner Voigt',
     'Jens Kunath:G;Bernd Wunderlich:A;Gernot Alms:D;Heiko März:D;Jens Wahl:M;Juri Schlünz:M;Volker Röhrich:A;'
     'Hilmar Weilandt:M;Andreas Babendererde:M;Axel Kruse:A;Axel Schulz:M;Artur Ullrich:D;Frank Wriedt:D;'
     'Rainer Jarohs:A;Henri Fuchs:A;Axel Rietentiet:D;Claude Kluth:A;Marco Kostmann:G'),
    ('lok', 'LOK LEIPZIG', 'Hans-Ulrich Thomale',
     'René Müller:G;Matthias Lindner:D;Heiko Scholz:M;Damian Halata:A;Frank Baum:D;Olaf Marschall:A;'
     'Uwe Bredow:M;Ronald Kreer:D;Torsten Kracht:D;Matthias Liebers:M;Bernd Hobsch:A;Uwe Zötzsche:D;'
     'Matthias Zimmerling:A;Frank Edmond:D;André Barylla:D;Jürgen Rische:A;Stefan Marx:M;Maik Kischko:G'),
    ('magdeburg', '1.FC MAGDEBURG', 'Joachim Streich',
     'Heiko Bonan:M;Dirk Heyne:G;Peter Köhler:M;Markus Wuckel:A;Dirk Stahmann:D;Dirk Schuster:D;'
     'Frank Siersleben:M;Detlef Schößler:D;Stefan Minkwitz:M;Frank Cebulla:D;Thomas Kluge:D;'
     'Wolfgang Steinbach:M;Jens Landrath:M;Andreas Brinkmann:A;Uwe Rösler:A;Heiko Laeßig:A;Sandy Enge:D;'
     'Frank Pietruska:G'),
    ('aue', 'WISMUT AUE', 'Ulrich Schulze',
     'Jörg Weißflog:G;Volker Schmidt:D;André Köhler:D;Andreas Langer:M;Harald Mothes:A;Thomas Weiß:A;'
     'Klaus Bittner:A;Bernhard Konik:D;Roland Balck:D;Uwe Bauer:D;Steffen Krauß:M;Steffen Lorenz:D;'
     'Heiko Münch:D;John Bemme:A;Jens Meier:A;Steffen Kubatzky:M;Ralph Vogel:A;Bernd Stettinius:G'),
    ('jena', 'CARL ZEISS JENA', 'Lothar Kurbjuweit',
     'Perry Bräutigam:G;Thomas Ludwig:D;Jürgen Raab:M;Mario Röser:M;Ralf Sträßer:A;Heiko Peschke:D;'
     'Jens-Uwe Penzel:D;Heiko Weber:A;Stefan Böger:M;Stefan Meixner:M;Michael Stolz:D;Henry Lesser:A;'
     'Robby Zimmermann:A;Ronald Szepanski:D;Mathias Pittelkow:M;Oliver Merkel:M;Steffen Zipfel:M;'
     'Holger Hünsche:G'),
    ('halle', 'HFC CHEMIE', 'Karl Trautmann',
     'Giesbert Penneke:D;Uwe Lorenz:D;Steffen Karl:D;Uwe Machold:M;Jens Adler:G;Dariusz Wosz:M;Lutz Schülbe:A;'
     'Andreas Wagenhaus:D;Jan Rziha:M;Lutz Schnürer:A;René Tretschok:M;Dirk Wüllbier:D;Frank Wiermann:A;'
     'Torsten Häußler:M;Martin Trocha:A;Dietmar Schütze:A;Karsten Härtel:G'),
    ('cottbus', 'ENERGIE COTTBUS', 'Fritz Bohla',
     'Frank Vogel:D;Jens Melzig:D;Detlef Irrgang:A;Holger Fandrich:M;Olaf Besser:A;Maik Pohland:D;'
     'Peter Hackbusch:M;Petrik Sander:A;Jörg Burow:M;Ingolf Schneider:M;Jens Flügel:M;Jörg Klimpel:G;'
     'Hans-Georg Opitz:G;Jörg Schwanke:M;Tim Thamerus:A;Michael Schneider:M;Frank Lehmann:M'),
    ('brandenburg', 'ST. BRANDENBURG', 'Peter Kohl',
     'Detlef Zimmer:G;Sylvio Demuth:D;Christoph Ringk:D;Eberhard Janotta:M;Jens Pahlke:D;Frank Jeske:A;'
     'Jan Voß:M;Ingolf Pfahl:D;Uwe Schulz:M;Timo Lange:M;Roland Gumtz:M;Andreas Lindner:M;'
     'Falk Zschiedrich:D;Steffen Freund:M;Jens Pfahl:M;Uwe Hessel:D;Christian Knoop:D;Hubert Gebhardt:G'),
    ('erfurt', 'ROT-WEISS ERFURT', 'Wilfried Gröbner',
     'Frank Dünger:D;Jürgen Heun:A;Frank Kräuter:M;Holger Bühner:D;Rainer Hoffmeister:G;Armin Romstedt:A;'
     'Uwe Weidemann:M;Uwe Abel:M;Thomas Vogel:A;Carsten Sänger:D;Holger Demme:A;Heiko Wick:M;'
     'Steffen Dünger:D;Mario Deppe:D;Dirk Ettrichrätz:M;Olaf Berschuk:D;Uwe Backhaus:D;Gerd Sachs:G'),
    ('zwickau', 'SACHSENR.ZWICKAU', 'Udo Schmuck',
     'Uwe Pohl:D;Torsten Viertel:D;Marcel Babik:D;Reinhard Rother:A;Ralf Wagner:M;Peter Göldner:M;'
     'Jens Mitzscherling:A;Olaf Schreiber:M;Andreas Mittag:D;Andreas Bielau:A;Fred Steinborn:M;'
     'Thomas Leonhardt:A;Mario Neumann:G;Jens Trötschel:G;Heiko Richter:M;Jens Heineccius:A;'
     'Steffen Hartkopf:D;Thomas Schmiecher:D'),
    ('union', 'UNION BERLIN', 'Karsten Heine',
     'Olaf Seier:M;René Adamczewski:M;Olaf Reinhold:A;Norbert Trieloff:D;Lutz Hendel:M;André Sirocks:M;'
     'Peter Schoknecht:M;Steffen Enge:A;Axel Wittke:M;Frank Placzek:D;Olaf Hirsch:A;René Deffke:A;'
     'Mario Maek:D;Thomas Grether:M;Henryk Lihsa:G;Detlef Hartmann:G;Ulf-Volker Probst:D;'
     'André Hofschneider:M'),
]

# FDGB-Pokal 2nd main round: the other 18 clubs ('?' = no name known: invented filler names, logged by build)
LOWER = [
    ('halle2', 'HFC CHEMIE II', '',
     'Thomas Weiß:G;Thomas Bartosik:D;Jörg Nowotny:D;Frank Ruprecht:D;Andreas Schmidt:D;Roy Hildebrandt:M;'
     'Torsten Neubert:M;Torsten Raspe:M;Silvio Rößiger:M;Maik Rumpel:A;Frank Wiermann:A'),
    ('babelsberg', 'MOT. BABELSBERG', 'Horst Stahlberg',
     'André Hennig:G;Andreas Hintze:M;Norbert Rudolph:M;Ingo Nachtigall:D;Lutz Kerper:M;Carsten Pannek:A;'
     'Frank Edeling:D;Uwe Patz:D;Marcus Petsch:D;Christian Borowski:A;Winfried Kräuter:D;Jörg Fabian:D;'
     'Marco Döring:A;Carsten Bosecker:D;Uwe Kirchner:A;Ingolf Matthes:A;Jörg Müller:M;Kai Grabscheit:G'),
    ('neustrelitz', 'TSG NEUSTRELITZ', '',
     'Lange:G;Knaust:D;Detlef Roeder:D;Bernd Rudolph:D;Ungel:D;Warnke:D;Benthin:M;Hart:M;Köhler:M;Roloff:M;'
     'Seeboth:M;Brehme:A;Koppe:A'),
    ('neubrandenburg', 'POST NEUBRANDBG', 'Andreas Göhlich',
     'Heinz Dahms:G;Detlev Rudolph:D;Lutz Schwerinski:A;Thomas Lüth:D;Axel Werner:A;André Jütting:M;'
     'Marco Zallmann:D;Jörg Lentz:M;Rolf Sager:M;Mario Hunger:A;Karsten Imort:D;Oliver Reschke:D;'
     'Wilfried Aepinius:A;Manfred Knaust:A;Dirk Epcke:D;Michael Fuchs:M;Ulf Graef:G'),
    ('weida', 'FORTSCHR. WEIDA', 'Lutz Lindemann',
     'Thomas Runkewitz:G;Bernd Hofmann:D;Sven Müller:D;Frank Pohland:D;Peter Schmidt:D;Wilde:D;'
     'Frank Delling:M;Michael Hache:M;Stefan Pfeifer:M;Thoralf Engling:A;Steffen Haubold:A;Thomas Leutloff:A;'
     'Jürgen Tucholka:A'),
    ('brieske', 'BRIESKE-SENFTENB', 'Peter Prell',
     'Andreas Leuthäuser:A;Ralf Hansch:D;Norbert Schuppan:D;Falk Schmidtke:M;Uwe Scholz:A;Andreas Wolf:D;'
     'Detlef Oppermann:D;Andreas Kretzer:M;Marco Schmidt:D;Steffen Rietschel:M;Thomas Breschke:A;'
     'Frank Leitzke:G;Maik Stehr:D;Holger Gewiß:A;Hagen Wellschmidt:M;Andreas Fleißner:D;Michael Zerna:M;'
     'Detlef Scholze:G'),
    ('weimar', 'MOTOR WEIMAR', 'Siegfried Vollrath',
     'Wolfgang Benkert:G;Bernd Fröhling:G;Jens Große:D;Peter Habi:D;Uwe Heinzelmann:D;Andreas Karczmarczyk:D;'
     'Horst Linde:D;Thomas Meister:D;Torsten Gerlach:M;Torsten Pöhland:M;Jörg Simon:M;Andreas Winter:M;'
     'Jörg Hornik:A;Andreas Machowski:A;Mike Welwarsky:A;Kai Wengefeld:A'),
    ('ludwigsfelde', 'MOT.LUDWIGSFELDE', 'Eckhard Düwiger',
     'Andreas Hawa:G;Dirk-Uwe Lormis:G;Fred Krohn:D;Dirk Lehmann:D;Eckhard Märzke:D;Jörg Niederhübner:D;'
     'André Pollow:D;Heiko Brestrich:M;Jens Deichen:M;Heiko Lahn:M;Bernd Maier:M;Frank Müller:M;'
     'Jörg Dämmrich:A;Ronny Dau:A;Steffen Piehl:A;Stephan Rother:A'),
    ('bischofswerda', 'BISCHOFSWERDA', 'Siegfried Gumz',
     'René Groß:G;Fred Sickert:G;Fred Bank:D;Jörg Bär:D;Enrico Hollmann:D;Mario Kleditzsch:D;Falk Kunze:D;'
     'Gerrit Beckert:M;Tino Gnauck:M;Tino Gottlöber:M;Andreas Gräulich:M;Tom Stohn:M;Mathias Gries:A;'
     'Heiko Löpelt:A;Dirk Losert:A;André Merkel:A'),
    ('schwerin', 'DYNAMO SCHWERIN', 'Manfred Radtke',
     'Andreas Reinke:G;Ingo Rentzsch:G;Frank Beutling:D;Sven Buchsteiner:D;Mario Drews:D;Herbert Eggert:D;'
     'Peter Herzberg:D;Steffen Benthin:M;Jens Bochert:M;Andreas Finster:M;Frank Hollnagel:M;Rolf Hollnagel:M;'
     'Steffen Baumgart:A;Dietmar Hirsch:A;André Kort:A;Frank Prange:A'),
    ('eisenh', 'EISENHUTTENSTADT', 'Klaus-Dieter Helbig',
     'Harald Leppin:G;Olaf Backasch:D;Olaf Bitzka:D;Andre Brüll:D;Manfred Hirsch:D;Tom Kühling:D;'
     'Jörg Bartz:M;Ingo Jäschke:M;Uwe Käthner:M;Harry Rath:M;René Röder:M;Frank Bartz:A;Benito Koch:A;'
     'Dirk Konzer:A;Frank Lindemann:A;?:G'),
    ('gera', 'WISMUT GERA', 'Wolfgang Haustein',
     'Dirk Gottschalk:G;Jens Hallbauer:G;Steffen Gerth:D;René Günther:D;Heiko Häußler:D;Steffen Hintz:D;'
     'Ralf Kraft:D;Andreas Barcal:M;René Feetz:M;Uwe Hermannstädter:M;Peter Kunzmann:M;Thomas Lauke:M;'
     'Karsten Böttcher:A;Olaf Distelmeier:A;Sylvio Hoffmann:A;Jörg Höllert:A'),
    ('greifswald', 'KKW GREIFSWALD', 'Wolfgang Moschke',
     'Axel Hauschild:G;Thomas Meier:G;Mayk Bullerjahn:D;Stefan Kriesen:D;Andreas Mähl:D;Norbert Töllner:D;'
     'Volker Vaupel:D;Rainer Bertram:M;Jens Dowe:M;Maik Ehlert:M;Holger Jung:M;Ralf Kleiminger:M;'
     'Peter Bartz:A;Sven Berkenhagen:A;Axel Fuchs:A;Jens Schlicke:A'),
    ('rotation', 'ROTATION BERLIN', 'Jürgen Piepenburg',
     'Wolfgang Gehrke:G;Ralf Greuel:D;Jörg Herrmann:D;Jens Metzke:D;Sven Orbanke:D;Udo Richter:D;'
     'Sven Förster:M;Matthias Henning:M;Ingo Kimmritz:M;Oliver Klotz:M;Uwe Martins:M;Thoralf Arndt:A;'
     'Frank Gese:A;Thomas Randt:A;Mario Schwarz:A;?:G'),
    ('thale', 'STAHL THALE', 'Olaf Keller',
     'Thomas Große:G;Andreas Schneider:G;Bernd Fuchs:D;Andreas Hahne:D;Manfred Henschel:D;Bernd Teichmann:D;'
     'Peter Teichmann:D;Olaf Adamczak:M;Andreas Fischer:M;Mike Gothe:M;Dirk Hantke:M;Siegfried Keller:M;'
     'Jens Günther:A;Andreas Hesselbarth:A;Rainer Kunde:A;Heiko Losse:A'),
    ('stendal', 'LOK STENDAL', 'Detlef Raßbach',
     'Ralf Daug:G;Thomas Taraba:G;Torsten Aurich:D;Dirk Paulig:D;Wolfgang Reuter:D;Dirk Roswandowicz:D;'
     'Hartmut Sommer:D;Bernd Boche:M;Holger Döbbel:M;Jürgen Ebeling:M;Ralf Girke:M;Markus Hoffmann:M;'
     'Guido Euen:A;Dirksen Höft:A;Dirk Junghanns:A;Ronny Schmidt:A'),
    ('schoenebeck', 'MOT. SCHONEBECK', 'Günter Reinke',
     'Markus Henkel:G;Olaf Schuster:G;Dirk Ahlfänger:D;Jörg Dobritz:D;Torsten Fröhling:D;Jörg Haase:D;'
     'Dirk Ketzer:D;Andreas Bedau:M;Heiko Dannat:M;René Dörfel:M;Jens Lange:M;Bert Müller:M;'
     'Rüdiger Bartsch:A;Günter Klomhuß:A;Michael Steffen:A;Jens Wittke:A'),
    ('fuerstenwalde', 'DYN.FURSTENWALDE', 'Peter Ränke',
     'Thomas Hoffmann:G;Gerd Pröger:G;Uwe Ehrenforth:D;Uwe Horn:D;Bernd Kulke:D;Frank Morgen:D;Henry Sack:D;'
     'Dirk Ohlbrecht:M;Lars Petzold:M;Michael Stiebeler:M;Bernd Stiegel:M;Guido Thaler:M;Bernd Jopek:A;'
     'Peter Kaehlitz:A;Bernd Lüdtke:A;Henry Ortmann:A'),
]

# FDGB-Pokal 1988-89, 2nd main round (home club first), in an order where consecutive winners meet in the round of
# 16 (Schönebeck-BFC, Union-Fürstenwalde, Greifswald-Erfurt, Schwerin-Neubrandenburg, Ludwigsfelde-Rotation,
# KMS-Dresden, Stendal-Jena, Aue-Cottbus); real winners marked by the comment. Later rounds: see POKAL_LATER.
POKAL_R2 = [
    ('schoenebeck', 'rostock'),        # 1-0
    ('babelsberg', 'bfc'),             # 0-8
    ('neustrelitz', 'union'),          # 2-4
    ('fuerstenwalde', 'zwickau'),      # 2-0
    ('greifswald', 'brandenburg'),     # 2-1
    ('gera', 'erfurt'),                # 0-3
    ('schwerin', 'magdeburg'),         # 3-1 aet
    ('neubrandenburg', 'halle'),       # 5-3 aet
    ('ludwigsfelde', 'bischofswerda'), # 1-0
    ('rotation', 'thale'),             # 1-1 aet, 5-4 pens
    ('halle2', 'kms'),                 # 0-6
    ('weimar', 'dresden'),             # 1-2
    ('stendal', 'lok'),                # 1-0
    ('brieske', 'jena'),               # 1-2 aet
    ('eisenh', 'aue'),                 # 0-5
    ('weida', 'cottbus'),              # 0-2
]
# Round of 16 (real home club first): Schönebeck-BFC 2-6 aet, Union-Fürstenwalde 4-1, Greifswald-Erfurt 1-3,
# Schwerin-Neubrandenburg 1-0, Ludwigsfelde-Rotation 1-0, KMS-Dresden 2-1 aet, Stendal-Jena 0-2, Aue-Cottbus 3-0.
# Quarter-finals: Union-BFC 0-2, Aue-Jena 3-1 aet, KMS-Ludwigsfelde 4-1, Schwerin-Erfurt 0-3.
# Semi-finals: BFC-Erfurt 6-1, Aue-KMS 1-2. Final (Berlin): BFC-KMS 1-0.

# --- TEAM.092 ---------------------------------------------------------------------------------------------------------
import os
import random
import struct

FILE = 92                       # country / team file number (free: 92..99): the 14 Oberliga clubs
FILE2 = 93                      # the 18 lower clubs of the FDGB-Pokal (no league: the country's team count must match its league)
BASE = 1786                     # global numbers 1786..1799 (92) and 1800..1817 (93)
BASE2 = BASE + 14
TEAM_SIZE = 684
GER = 13                        # nationality byte (Peppecapello's DDR players)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'orig', 'swos2020', 'x_1990_91', 'TEAM.010')

# template record in Peppecapello's 1990-91 TEAM.010 (slots, roles, kit, base skills) and target average price byte
# (p+32; his 1990-91 clubs average 12-21): champions and title contenders highest, DDR-Liga clubs lowest.
TEMPLATE = {'dresden': 1, 'bfc': 10, 'kms': 4, 'rostock': 0, 'lok': 6, 'magdeburg': 9, 'aue': 11, 'jena': 5,
            'halle': 3, 'cottbus': 12, 'brandenburg': 7, 'erfurt': 2, 'zwickau': 13, 'union': 8}
TARGET = {'dresden': 21, 'bfc': 20, 'kms': 17, 'rostock': 17, 'lok': 18, 'magdeburg': 16, 'aue': 15, 'jena': 16,
          'halle': 15, 'cottbus': 14, 'brandenburg': 14, 'erfurt': 14, 'zwickau': 12, 'union': 12}
LOWER_TEMPLATES = (8, 11, 13)   # Eisenhüttenstadt, Sachsen Leipzig, Vorwärts Frankfurt (weakest 1990-91 clubs)
LOWER_TARGET = 9
# kits [type, shirt, shirt 2, shorts, socks] for clubs not in the 1990-91 file (else the template's): by colour
# analogy with Peppecapello's kits (Aue violet ~ BFC wine, Zwickau and Union red/white ~ Erfurt)
KITS = {'aue': 10, 'zwickau': 2, 'union': 2}

FIRST = 'Andreas Thomas Frank Jens Uwe Ralf Steffen Dirk Matthias Torsten Olaf Heiko Michael Jörg'.split()
LAST = 'Müller Schulz Lehmann Krüger Hoffmann Wagner Becker Richter Wolf Neumann Schwarz Zimmermann Braun Hartmann'.split()


def _players(spec):
    return [tuple(x.rsplit(':', 1)) for x in spec.split(';')]


def build():
    """TEAM.092: the 14 Oberliga clubs (ordinals 0..13, final-table order) and the 18 lower Pokal clubs (14..31)."""
    import c1c2
    d = open(SRC, 'rb').read()
    src = [d[2 + k * TEAM_SIZE:2 + (k + 1) * TEAM_SIZE] for k in range(struct.unpack('>H', d[:2])[0])]
    known = {}
    for r in src:
        for j in range(16):
            p = r[76 + j * 38:76 + (j + 1) * 38]
            known.setdefault(p[3:26].split(b'\0')[0].decode('latin1'), p)
    rng = random.Random(1989)
    used, recs, fillers, reused = set(), [], [], []
    clubs = [(k, n, c, s, TEMPLATE[k], TARGET[k]) for k, n, c, s in OBERLIGA]
    clubs += [(k, n, c, s, LOWER_TEMPLATES[i % 3], LOWER_TARGET) for i, (k, n, c, s) in enumerate(LOWER)]
    for i, (key, name, coach, spec, tk, target) in enumerate(clubs):
        t = src[tk]
        r = bytearray(t)
        lo = i >= len(OBERLIGA)
        r[0], r[1] = (FILE2, i - len(OBERLIGA)) if lo else (FILE, i)
        struct.pack_into('>H', r, 2, BASE + i)
        r[25] = 0
        r[5:22] = name.encode('latin1').ljust(17, b'\0')[:17]
        if key in KITS:
            r[26:36] = src[KITS[key]][26:36]
        r[36:59] = c1c2.swos_name(coach).encode('latin1').ljust(23, b'\0')[:23] if coach else bytes(23)
        avg = sum(t[76 + j * 38 + 32] for j in range(16)) / 16
        step = max(-3, min(3, round((target - avg) / 2)))
        pools = {c: [] for c in 'GDMA'}
        for who, role in _players(spec):
            pools[role].append(who)
        borrow = {'G': 'G', 'D': 'DMA', 'M': 'MDA', 'A': 'AMD'}
        for j in range(16):
            p = 76 + j * 38
            cls = c1c2.CLASS[t[p + 26] >> 5]
            src_role = next((x for x in borrow[cls] if pools[x]), None)
            who = pools[src_role].pop(0) if src_role else '?'
            if who == '?':
                while True:
                    who = f'{rng.choice(FIRST)} {rng.choice(LAST)}'
                    if c1c2.swos_name(who) not in known and who not in used:
                        break
                fillers.append((name, who))
            used.add(who)
            sname = c1c2.swos_name(who)
            if sname in known and i < len(OBERLIGA):     # Oberliga player in Peppecapello's 1990-91 file: his record
                q = bytearray(known[sname])
                q[2] = t[p + 2]
                q[26] = (q[26] & 0x1f) | (t[p + 26] & 0xe0)
                r[p:p + 38] = q
                reused.append(sname)
            else:
                r[p] = GER
                r[p + 3:p + 26] = sname.encode('latin1').ljust(23, b'\0')[:23]
                c1c2.level_player(r, p, step)
        recs.append(bytes(r))
    print(f'TEAM.{FILE:03d}/{FILE2:03d}: DDR 1988-89, {len(recs)} clubs, {len(reused)} players from the 1990-91 file, '
          f'{len(fillers)} invented names: {fillers}')
    n = len(OBERLIGA)
    return {FILE: struct.pack('>H', n) + b''.join(recs[:n]), FILE2: struct.pack('>H', len(recs) - n) + b''.join(recs[n:])}


# --- exe ----------------------------------------------------------------------------------------------------------------
LEAGUE_ID = 0xC6                # free contest ids (historic C1..C3, finals C4/C5)
POKAL_ID = 0xC7
GERMANY = 14                    # league/cup dates copied from Germany's (August..May)
NAME = b'DDR 1988-89'           # country button (season menu); every language
LEAGUE_NAMES = (b'OBERLIGA 1988-89', b'OBERLIGA')
POKAL_NAMES = (b'FDGB-POKAL 1988-89', b'FDGB-POKAL')
AU_CUP_SIG = bytes((0xAD, 1, 0x2C, 0x28, 0x50))   # SWOS's Australian cup (32 clubs, 5 rounds): layout of the Pokal
POKAL_ROUNDS = (0x54, 0x54, 0x54, 0x54, 0x14)     # single matches with extra time and penalties; the final
_ORD = {k: i for i, k in enumerate([c[0] for c in OBERLIGA] + [c[0] for c in LOWER])}
# fixed pairings (historic.DRAWS): keep the order, except the quarter-finals (Union-BFC, Schwerin-Erfurt, Aue-Jena,
# KMS-Ludwigsfelde with the real home clubs; then BFC-Erfurt and Aue-KMS, final BFC-KMS)
DRAWS = [(POKAL_ID, list(range(32))), (POKAL_ID, list(range(16))), (POKAL_ID, [1, 0, 3, 2, 7, 6, 5, 4]),
         (POKAL_ID, list(range(4))), (POKAL_ID, [0, 1])]

SEASON_ASM = '''
ddr_season:                             ; replaces `call SelectTeamsFinalMenu` in the season team selector
    push dword [COMP80]
    mov dword [COMP80], EUROPE_SEASON
    call SELECT
    pop dword [COMP80]
    ret
'''


def patch(p, lang, area, cave):
    """Country 92 'DDR 1988-89': Oberliga 1988-89 (league) + FDGB-Pokal 1988-89 (cup); the season team selector gets
    a world table with the DDR button. Returns (cave end, obj1 offset of the Oberliga struct for the CLASSICS table)."""
    import countries
    import historic
    import nasmcave
    import sacups
    d2 = p.le.obj_bytes(2)
    ct, tcn, _, _ = countries.tables(p)
    comp = countries.COMP[0]
    fx2 = {f[1] for f in p.le.fixups() if f[0] == 2}
    assert ct + 4 * FILE not in fx2 and comp + 4 * FILE not in fx2
    rec = area.add(bytes((countries.CONTINENT['europe'],)) + NAME + b'\0' + NAME + b'\0')
    p.add_ptr(2, ct + 4 * FILE, 2, rec)
    p.put(2, tcn + 2 * FILE, struct.pack('<H', BASE))
    # a country's team count = base of the next country - its own base: 93 must start after our 32 clubs
    assert ct + 4 * FILE2 not in fx2 and comp + 4 * FILE2 not in fx2
    p.add_ptr(2, ct + 4 * FILE2, 2, rec)                # a club's country is never null
    p.put(2, tcn + 2 * FILE2, struct.pack('<H', BASE2))
    p.put(2, tcn + 2 * (FILE2 + 1), struct.pack('<H', BASE + len(OBERLIGA) + len(LOWER)))

    gobj, gtab = p.target(2, comp + 4 * GERMANY)
    gd = p.le.obj_bytes(gobj)
    lobj, glg = p.target(gobj, gtab)
    lg = p.le.obj_bytes(lobj)[glg:glg + 13]
    assert lg[2] == GERMANY, lg.hex()
    names = [area.add(s + b'\0') - sacups.STR_BASE for s in LEAGUE_NAMES]
    hdr = bytes((LEAGUE_ID, 0, FILE, lg[3], lg[4], 9 + 6, 0, 0, 0, 1, 2, 2, 0x35))   # 1 division, 2 games, 2 points
    body = hdr + bytes((len(OBERLIGA), 0, 0, 2, 0, 0)) + b'\0' + struct.pack('<II', *names)   # 2 relegated
    at = cave
    league = at
    p.put(1, at, body)
    at = (at + len(body) + 3) & ~3

    lo = d2.find(AU_CUP_SIG)
    assert lo >= 0 and d2.count(AU_CUP_SIG) == 1
    cup = bytearray(d2[lo:lo + 14])
    assert cup[10] == 32 and cup[7] == 0 and cup[5] == 0 and d2[lo + 14 + 5] == 0
    k = 8
    while struct.unpack_from('<i', gd, gtab + k - 4)[0] != -2:
        k += 4
    cobj, gcup = p.target(gobj, gtab + k)
    gc = p.le.obj_bytes(cobj)[gcup:gcup + 5]
    cup[0], cup[2], cup[3], cup[4] = POKAL_ID, FILE, gc[3], gc[4]
    cup += bytes(POKAL_ROUNDS) + b'\0'
    cup[5] = len(cup) - 5
    cup[7] = len(cup) + 8 - 7
    pn = [area.add(s + b'\0') - sacups.STR_BASE for s in POKAL_NAMES]
    teams = [_ORD[x] for tie in POKAL_R2 for x in tie]
    assert sorted(teams) == list(range(32))
    body = bytes(cup) + struct.pack('<II', *pn) + b''.join(bytes((FILE, t) if t < len(OBERLIGA) else (FILE2, t - len(OBERLIGA))) for t in teams)
    pokal = at
    p.put(1, at, body)
    at = (at + len(body) + 3) & ~3

    import euro8889
    at, cups = euro8889.structs(p, lang, area, at, sacups.STR_BASE)
    for cup, f in euro8889.FILES.items():               # foreign clubs of the European cups: country entries + bases
        assert ct + 4 * f not in fx2 and comp + 4 * f not in fx2
        p.add_ptr(2, ct + 4 * f, 2, rec)
        p.put(2, tcn + 2 * f, struct.pack('<H', euro8889.BASES[cup]))

    table = at                                  # [Oberliga, -2, Pokal, <cup>, -1]: slot 2 = the cup of the club (euro_slot2)
    p.add_ptr(1, at, 1, league)
    p.put(1, at + 4, struct.pack('<i', -2))
    p.add_ptr(1, at + 8, 1, pokal)
    p.add_ptr(1, at + 12, 1, cups['cc'])
    p.put(1, at + 16, struct.pack('<i', -1))
    at += 20
    p.add_ptr(2, comp + 4 * FILE, 1, table)

    # Season: the DDR is one more country of EUROPE (a single-league country goes straight to its teams). The stub swaps
    # competitionsTable[80] (Europe) for a copy + country 92 while the season selector runs.
    eobj, eoff = p.target(2, comp + 4 * 80)
    ed = p.le.obj_bytes(eobj)
    fxe = {f[1]: (f[3], f[4]) for f in p.le.fixups() if f[0] == eobj}
    k = 0
    while struct.unpack_from('<i', ed, eoff + 4 * k)[0] != -1:
        k += 1
    countries_eu = ed[eoff + 4 * k + 4:ed.index(b'\xff', eoff + 4 * k + 4)]
    europe = at
    for j in range(k):
        if eoff + 4 * j in fxe:
            p.add_ptr(1, at + 4 * j, *fxe[eoff + 4 * j])
        else:
            p.put(1, at + 4 * j, ed[eoff + 4 * j:eoff + 4 * j + 4])
    p.put(1, at + 4 * k, b'\xff' * 4 + countries_eu + bytes((FILE, 0xff)))
    at = (at + 4 * k + 4 + len(countries_eu) + 2 + 3) & ~3

    _, season_call, select = historic._calls(p)
    site, skip, comp_cn, sel, num, r = euro8889.hook_sites(p)
    emap = bytearray(14)
    for key, cup in euro8889.DDR_CUP.items():
        emap[_ORD[key]] = euro8889.CUP_INDEX[cup]
    if os.environ.get('EURO_ALWAYS') == '1':           # test build: every DDR club gets the Cup Winners' Cup
        emap = bytearray([2] * 14)
    symbols = {'COMP80': (2, comp + 4 * 80), 'EUROPE_SEASON': (1, europe), 'SELECT': (1, select),
               'A0': (2, r['A0']), 'COMPCOUNTRY': (2, comp_cn), 'SELTEAMS': (2, sel), 'NUMSEL': (2, num),
               'DDR_FILE': (0, FILE), 'SKIP_SLOT2': (1, skip), 'MAP_BYTES': (0, 'db ' + ', '.join(map(str, emap))),
               'CUP_CC': (1, cups['cc']), 'CUP_CWC': (1, cups['cwc']), 'CUP_UEFA': (1, cups['uefa'])}
    src = SEASON_ASM + (euro8889.DIAG_ASM if os.environ.get('EURO_ALWAYS') == '3' else euro8889.HOOK_ASM)
    symbols['DBG_STR'] = (2, euro8889.structs.names['uefa'])
    if os.environ.get('EURO_ALWAYS'):
        src = src.replace('    cmp byte [esi + 4], 1               ; computer-controlled\n    je .skip\n', '')
    code, fix = nasmcave.assemble(src, at, symbols)
    labels = nasmcave.labels(src, at, symbols)
    p.put(1, at, code)
    for off, tobj, toff in fix:
        p.add_ptr(1, at + off, tobj, toff)
    p.put(1, season_call + 1, struct.pack('<i', labels['ddr_season'] - (season_call + 5)))
    p.remove(1, site + 1)                                # `mov [A0], eax`: drop the fixup of its address operand
    p.put(1, site, b'\xe8' + struct.pack('<i', labels['euro_slot2'] - (site + 5)))
    at = (at + len(code) + 3) & ~3
    print(f'exe: DDR 1988-89 = country {FILE}: Oberliga id {LEAGUE_ID:#x} @ obj1+{league:#x} (dates {lg[3]:#x}/{lg[4]:#x}), '
          f'FDGB-Pokal id {POKAL_ID:#x} @ obj1+{pokal:#x}, season call obj1+{season_call:#x} -> obj1+{labels["ddr_season"]:#x}')
    return at, league
