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
