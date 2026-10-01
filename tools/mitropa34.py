"""Mitropa Cup 1934: the 16 clubs with their 1934 squads (session 26).

Sources (fetched 2026-10-01):
- line-ups of every Hungarian-club tie (both teams): tempofradi.hu "A KK története - 1934, a Bologna másodszor"
  (Ferencvaros, Floridsdorfer AC, Bocskai, Ujpest, Austria Wien, Hungaria, Sparta, Kladno, Juventus, Bologna, Admira);
- it.wikipedia season pages (rosa): Bologna Sezione Calcio 1933-1934, Foot-Ball Club Juventus 1933-1934,
  Associazione Sportiva Ambrosiana-Inter 1933-1934, Associazione Calcio Napoli 1933-1934;
- cs.wikipedia "1. asociační liga 1933/1934" (soupisky: Slavia, Sparta, Kladno, Teplitzer FK, with coaches);
- en.wikipedia "1933-34 SK Rapid Wien season" (squad and Mitropa appearances, from rapidarchiv.at).
Players also in the SWOS 2020 DLC "1934 FIFA WORLD CUP (Italy)" by Insane keep that record (skills, face).
'?' marks a reconstructed name (no source found: second goalkeepers, small squads) - see RECONSTRUCTED.

Each club: (name, coach, nationality of the template, target average price, kit or None (keep the template's),
            {'G': [...], 'D': [...], 'M': [...], 'A': [...]}) - players listed starters first.
A player is 'Name' (club nationality) or ('Name', nat) for a foreigner.
"""
ITA, AUT, HUN, TCH, URU, ARG, BRA, PAR, BEL = 18, 1, 15, 6, 76, 68, 70, 74, 2

# kits: [type, shirt 1, shirt 2, shorts, socks] (0 plain, 1 halves, 2 stripes, 3 hoops; 1 white 2 black 4 red 5 blue
# 6 claret/violet 7 sky blue 8 green 9 yellow)
CLUBS = [
    ('FERENCVAROS', 'Zoltán Blum', HUN, 40, None, {
        'G': ['József Háda', '?'],
        'D': ['Bán', 'Lajos Korányi'],
        'M': ['Antal Lyka', 'János Móré', 'Gyula Lázár', 'Mihály Táncos'],
        'A': ['Károly Rátkai', 'Gyula Polgár', 'György Sárosi', 'Géza Toldi', 'Tibor Kemény',
              'Béla Székely', 'Barna', 'Ferenc Majorszky']}),
    ('FLORIDSDORFER AC', '', AUT, 33, [0, 5, 5, 1, 5], {
        'G': ['Scharl', '?'],
        'D': ['Josef Bernard', 'Schlauf', '?'],
        'M': ['Müller', 'Hoffmann', 'Radakovics', '?'],
        'A': ['Weisz', 'Chloupek', 'Graber', 'Dostal', 'Langer', 'Hanke', '?']}),
    ('SK KLADNO', 'Ferdinand Üblacker', TCH, 36, None, {
        'G': ['Karel Tichý', 'Oldřich Šesták'],
        'D': ['František Nejedlý', 'Emil Habr', 'Ludvík Koubek'],
        'M': ['Václav Bouška', 'Karel Kraus', 'Antonín Černý', 'Jiří Fišer', 'Josef Pleticha'],
        'A': ['František Kloz', 'Miroslav Procházka', 'Josef Junek', 'Karel Hromádka', 'Václav Nový',
              'Karel Podrazil']}),
    ('AMBROSIANA', 'Árpád Weisz', ITA, 40, [2, 2, 5, 1, 2], {
        'G': ['Carlo Ceresoli', '?'],
        'D': ['Giuseppe Ballerio', 'Luigi Allemandi', 'Paolo Agosteo'],
        'M': ['Armando Castellazzi', 'Renato De Manzano', ('Atilio Demaría', ARG), ('Ricardo Faccio', URU),
              'Alfredo Pitto', 'Giuseppe Viani'],
        'A': ['Giuseppe Meazza', ('Francesco Frione', URU), 'Virgilio Levratto', 'Natale Masera', 'Eligio Vecchi']}),
    ('BOLOGNA', 'Lajos Kovács', ITA, 42, None, {
        'G': ['Mario Gianni', '?'],
        'D': ['Eraldo Monzeglio', 'Felice Gasperi', 'Dino Fiorini'],
        'M': ['Mario Montesanto', ('Francesco Occhiuzzi', URU), 'Aldo Donati', 'Giordano Corsi', 'Gastone Martelli',
              'Mario Perazzolo'],
        'A': ['Bruno Maini', 'Angelo Schiavio', ('Francisco Fedullo', URU), 'Carlo Reguzzoni', ('Raffaele Sansone', URU)]}),
    ('BOCSKAI', 'Edwin Herzog', HUN, 34, [0, 9, 9, 5, 5], {
        'G': ['Alberti', '?'],
        'D': ['József Vágó', 'Janzsó', '?'],
        'M': ['István Palotás', 'Odry', 'Szaniszló', '?', '?'],
        'A': ['Imre Markos', 'Jenő Vincze', 'Pál Teleki', 'Dóczé', 'Sándor Hevesi', '?']}),
    ('SLAVIA PRAHA', 'Josef Sloup-Štaplík', TCH, 39, None, {
        'G': ['František Plánička', 'Augustin Zeman'],
        'D': ['Ladislav Ženíšek', 'Adolf Fiala', 'Antonín Vodička'],
        'M': ['Štefan Čambal', 'Rudolf Krčil', 'Bedřich Pech', 'Bohumil Joska'],
        'A': ['Antonín Puč', 'Jiří Sobotka', 'František Svoboda', 'Vlastimil Kopecký',
              'František Junek', 'Vojtěch Bradáč', 'Karel Hejma']}),
    ('RAPID WIEN', 'Edi Bauer', AUT, 39, None, {
        'G': ['Rudolf Raftl', 'Leopold Czejka'],
        'D': ['Karl Jestrab', 'Ludwig Tauschek', 'Rudolf Fiala', 'Johann Luef'],
        'M': ['Franz Wagner', 'Josef Smistik', 'Stefan Skoumal', 'Johann Ostermann', 'Alois Ohrenberger'],
        'A': ['Karl Hochreiter', 'Matthias Kaburek', 'Josef Bican', 'Franz Binder', 'Hans Pesser']}),
    ('AUSTRIA WIEN', '', AUT, 39, None, {
        'G': ['Müllner', '?'],
        'D': ['Graf', 'Kaith', 'Ludwig'],
        'M': ['Najemnik', 'Johann Mock', 'Walter Nausch', 'Karl Gall', '?'],
        'A': ['Molzer', 'Josef Stroh', 'Matthias Sindelar', 'Spechtl', 'Rudolf Viertl', 'Camillo Jerusalem']}),
    ('UJPEST', 'István Tóth Potya', HUN, 38, None, {
        'G': ['Hóri', '?'],
        'D': ['Gyula Futó', 'László Sternberg', 'Borsányi'],
        'M': ['Seres', 'György Szűcs', 'Antal Szalay', '?'],
        'A': ['Tamássy', 'Pusztai', 'Pál Jávor', 'Kocsis', 'P. Szabó', 'István Avar', 'Kis']}),
    ('JUVENTUS', 'Carlo Carcano', ITA, 42, None, {
        'G': ['Gianpiero Combi', 'Cesare Valinasso'],
        'D': ['Virginio Rosetta', 'Umberto Caligaris', 'Giovanni Varglien', 'Mario Ferrero'],
        'M': ['Luis Monti', 'Luigi Bertolini', 'Mario Varglien', 'Teobaldo Depetrini'],
        'A': ['Renato Cesarini', 'Pietro Serantoni', 'Felice Borel', 'Giovanni Ferrari', 'Raimundo Orsi',
              'Pietro Sernagiotto']}),
    ('TEPLITZER FK', '', TCH, 35, None, {
        'G': ['Čestmír Patzel', '?'],
        'D': ['Heinrich Schöpke', 'Willy Mizera', 'Alois Krückl'],
        'M': ['Vilhelm Náhlovský', 'Ervín Kovács', 'Stefan Pospichal', 'Martin Watzata'],
        'A': ['Gustav Haberstroth', 'Istvan Roth', 'Josef Müllner', 'Karl Koder', 'Tomáš Porubský',
              'Stefan Csano', 'Armin Grünfeld']}),
    ('ADMIRA WIEN', '', AUT, 41, [0, 2, 2, 1, 2], {
        'G': ['Peter Platzer', '?'],
        'D': ['Pavlicek', 'Janda', '?'],
        'M': ['Johann Urbanek', 'Hummenberger', 'Mirschitzka', '?'],
        'A': ['Siegl', 'Wilhelm Hahnemann', 'Stoiber', 'Anton Schall', 'Adolf Vogl', 'Vogl II', 'Durspekt']}),
    ('NAPOLI', 'William Garbutt', ITA, 37, None, {
        'G': ['Giuseppe Cavanna', 'Vittorio Alfieri'],
        'D': ['Luigi Castello', ('Paulo Innocenti', BRA), 'Giovanni Vincenzi', 'Enrico Colombari'],
        'M': ['Carlo Buscaglia', ('Gaetano Ragusa', BRA), ('José Gelardi', BRA), 'Umberto Visentin'],
        'A': [('Attila Sallustro', PAR), 'Antonio Vojak', 'Pietro Ferraris', 'Gino Rossetti', 'Giovanni Venditto',
              'Giovanni Giraud']}),
    ('HUNGARIA', 'Imre Senkey', HUN, 38, None, {
        'G': ['Antal Szabó', '?'],
        'D': ['Gyula Mándi', 'Kis', 'Bíró'],
        'M': ['Egri', 'Gusztáv Sebes', 'János Dudás', 'Szabó IV', '?'],
        'A': ['Fenyvesi', 'István Kardos', 'László Cseh', 'József Turay', 'Pál Titkos', 'Szabó III']}),
    ('SPARTA PRAHA', 'Ferenc Szedlacsek', TCH, 39, None, {
        'G': ['Bohumil Klenovec', 'Antonín Ledvina'],
        'D': ['Jaroslav Burgr', 'Josef Čtyřoký', 'Josef Sedláček', 'Václav Mrázek'],
        'M': ['Josef Košťálek', 'Jaroslav Bouček', 'Erich Srbek', 'Josef Silný'],
        'A': ['Václav Hruška', 'Ferdinand Faczinek', ('Raymond Braine', BEL), 'Oldřich Nejedlý',
              'Géza Kalocsay', 'František Pelcner']}),
]

# the stars of 1934 at the top of the scale (price 49, skills +1)
STARS = {'GIUSEPPE MEAZZA', 'MATTHIAS SINDELAR', 'GYORGY SAROSI', 'JOSEF BICAN', 'ANGELO SCHIAVIO',
         'FRANTISEK PLANICKA', 'CARLO REGUZZONI', 'OLDRICH NEJEDLY', 'LUIS MONTI', 'RAIMUNDO ORSI'}
