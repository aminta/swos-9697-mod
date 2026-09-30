"""Real 1996-97 squads of the Serie C1/C2 clubs added to TEAM.020 (source: it.wikipedia club season pages,
"<club> 1996-1997", rosa section; fetched 2026-09-30). Players with known league appearances come first
in their role; the rest keep the page order. Roles: P goalkeeper, D defender, C midfielder, A forward.
Foreign players: name -> (SWOS nationality, black face).
"""

ROSTERS = {
    # --- Serie C1 ---
    'TREVISO': ('Giuseppe Pillon',
                'Mauro Bacchin, Massimo Cecchinato, Tiziano Ramon',
                'Massimiliano Dal Compare, Simone Groppi, Stefano Lombardi, Giuseppe Margiotta, Francesco Maino, Ezio Rossi',
                'Diego Bonavina, Andrea Boscolo, Alessandro De Poli, Gianluca Leoni, Filippo Novello, Daniele Pasa, Giovanni Soncin',
                'Loris Pradella, Alessandro Costa, Flavio Fiorio, Dario Tollardo'),
    'BRESCELLO': ("Giancarlo D'Astoli",
                  'Marco Boghetto, Roberto Di Gennaro',
                  'Omar Campana, Davide Corti, Rocco Crippa, Cristian Petiziol, Umberto Salamone, Luca Salvalaggio, '
                  'Daniel Terrera, Gianluca Zattarin',
                  'Francesco Bertolotti, Massimiliano Ferrigno, Arnaldo Franzini, Giuseppe Lanotte, Michele Malpeli, '
                  'Joseph Manzini, Corrado Oldoni, Antonio Terracciano',
                  'Andrea Tedeschi, Emiliano Centanni, Federico Cossato, Christian Guatteo, Antonio Martorella'),
    'CARPI': ('Luigi De Canio',
              'Antonio Piazza, Francesco Ripa',
              'Enrico Sala, Ciro Caruso, Raniero Di Cunzolo, Stefano Lorenzi, Simone Mazzocchi, Stefano Pellegrini, '
              'Teodoro Piccinno, Matteo Pivotto',
              'Federico Lunardon, Mario Alfieri, Michele Andrisani, Roberto Antonioli, Luis Fernando Centi, '
              'Alessio Di Giuseppe, Luca Landonio, Willi Pittana, Ivo Pulga, Massimo Tramontano',
              'Cristiano Masitto, Giovanni Arioli, Marco Cavicchia, Roberto Corradi, Claudio Gallicchio, '
              'Massimiliano Longhi, Raffaele Paolino'),
    'SARONNO': ('Mario Beretta',
                'Paolo Locatelli, Gianluca Spinelli, Gabriele Spinetta',
                'Paolo Bravo, Giacomo Gattuso, Marco Grossi, Claudio Macchi, Morris Molinari, Alfredo Ottolina, '
                'Antonio Ricci, Damiano Sironi',
                'Pierluigi Cattaneo, Igor Marziano, Alessandro Marzio, Marco Osio, Mirko Pagliarini, Umberto Pini, '
                'Sabino Sardella, Carlo Stabile, Alvise Zago',
                'Luca Lugnan, Davide Faiella, Pierpaolo Tomassini'),
    'PRATO': ('Giorgio Veneri',
              'Marco Ambrosio, Alessandro Brunetti',
              'Massimo Oddo, Davide Barni, Roberto Bucchioni, Ivanoe Lanzara, Claudio Mascheretti, Mario Masini, '
              'Giovanni Serao',
              'Marcello Albino, Antonio Armento, Francesco Campolattano, Alessandro Doga, Massimo Gallaccio, '
              'Roberto Marta, Nathan Schiavon, Mario Stancanelli, Simone Tognon',
              'Nunzio Falco, Denis Godeas, Giovanni Abate, Alberto Bernardi, Francesco De Francesco'),
    'NOCERINA': ('Marco Maestripieri',
                 'Gennaro Iezzo, Vincenzo Criscuolo',
                 "Domenico Colletto, Salvatore D'Angelo, Angelo Deruggiero, Marco De Simone, Giovanni Di Rocco, "
                 'Marcello Esposito, Vincenzo Perillo',
                 'Fabio Liverani, Fabrizio Fabris, Alessandro Toti, Lorenzo Battaglia, Antonio Bucciarelli, Angelo Cianciotta, '
                 'Emiliano De Juliis, Loris Del Nevo, Franco Marchegiani, Salvatore Marra, '
                 'Gennaro Merolla, Luigi Molino, Andrea Pallanch, Carmelo Puglisi',
                 'Salvatore Buoncammino, Walter Lapini, Francesco Tribuna, Ernesto Verolino, Alvaro Zian'),
    'CASARANO': ('Dino Bitetto',
                 'Nello Cusin, Alessandro Leopizzi, Massimiliano Mugnai',
                 'Andrea Citterio, Antonio Calabro, Flavio Leo, Nicola Losacco, Salvatore Nobile, Teodoro Piccinno, '
                 'Luca Pierotti, Pietro Sportillo, Danilo Vitali',
                 "Stefano Tagliani, Stefano Archetti, Roberto Chiappara, Roberto D'Aversa, Antonio Foschini, "
                 'Vito Grieco, Vincenzo Lambertini, Giuliano Nichil, Giovanni Pittalis, Raffaele Quaranta, '
                 'Renato Voglino, Claudio Zaminga',
                 'Ciro De Cesare, Fabrizio Miccoli, Antonio Bernardi, Luigi Corvo, Massimo Manca, Roberto Pasca'),
    'JUVE STABIA': ('Viviano Guida',
                    'Francesco Bifera, Ciro Ambra',
                    'Gennaro Monaco, Giovanni Di Meglio, Vincenzo Feola, Roberto Amodio, Mariano De Francesco, '
                    'Vincenzo Saladino, Maurizio Caccavale',
                    "Attilio Nicodemo, Felice Foglia, Edmondo De Amicis, Luigi D'Alessio, Alessandro Manca, "
                    'Gaetano Perrella, Donato Amato, Massimo Lovato',
                    'Raffaele Costantino, Gennaro Sarnelli, Dirk Vollmar'),
    # --- Serie C2 ---
    'LUMEZZANE': ('Giovanni Trainini',
                  'Alessandro Bianchessi, Alessandro Bolpagni',
                  'Damiano Sonzogni, Manuel Belleri, Stefano Botti, Cristiano Dona, Marco Zaninelli, Claudio Zola',
                  'Mauro Antonioli, Cristian Boscolo, Francesco Faini, Michele Sella, Giorgio Zamuner',
                  'Simone Inzaghi, Massimiliano Maffioletti, Claudio Salvi, Corrado Cortesi, Stefano Preti'),
    'LECCO': ('Elio Gustinetti',
              'Liam Ardigo, Maurizio Monguzzi',
              'Andrea Capecchi, Cristiano Giaretta, Egidio Mazzina, Lorenzo Marconi, Claudio Maretti, '
              'Pasquale Sensibile, Denis Zanardo',
              'Fabio Castellazzi, Gioacchino Adamo, Riccardo Allegretti, Alberto Colombo, Oscar Damiani, '
              'Antonio Orlando',
              'Luca Campistri, Alberto Bertolini, Roberto Bonazzi, Marco Limetti'),
    'LIVORNO': ('Paolo Stringara',
                'Fabrizio Boccafogli, Francesco Palmieri',
                'Alessandro Castagna, Luca Marcato, Franco Micco, Gianpaolo Morabito, Marco Ogliari, Andrea Persia, '
                'Gabriele Rummolo, Maurizio Vincioni',
                'Marcello Carli, Davide Cordone, Gianni Cuc, Walter Cuccu, Mauro Nardini, Matteo Niccolai, '
                'Marco Merlo, Manuel Vivani',
                'Enio Bonaldi, Santo Gianguzzo, Alessandro Lupo, Gianbattista Olivari, Claudio Ramacciotti, Roberto Ria'),
    'BATTIPAGLIESE': ('Roberto Chiancone',
                      'Federico Infanti, Giovanni Schettino',
                      'Giovanni Schettini, Marco Ambrogioni, Federico Cavola, Raniero Di Cunzolo, Osvaldo Ferullo, '
                      'Giovanni Langella, Luigi Lonoce',
                      'Salvatore Russo, Antonino Cardinale, Marco Di Capua, Alessandro Di Giovannantonio, '
                      'Michele Di Mingo, Vincenzo Manzo, Francesco Pesacane, Massimiliano Rossi, Francesco Tataranni',
                      "Massimiliano D'Angelo, Luigi Di Baia, Domenico D'Anto, Andrea Deflorio, Francesco Madonna, "
                      'Michele Marino'),
    'TURRIS': ('Salvatore Esposito',
               'Luigi Sassanelli, Gennaro Esposito, Francesco Giudizioso',
               "Giuseppe Antonaccio, Giovanni Bagnara, Fabrizio Baldini, Luca Barbini, Salvatore Cangiano, "
               "Vittorio De Carlo, Antonio Dell'Oglio, Giuseppe Di Meo, Domenico Izzo, Raffaele Miglio, "
               'Matteo Siniscalco',
               'Vincenzo Bevo, Nicola Di Criscio, Giuseppe Granozi, Giovanni Iovino, Aniello Lama, Antonio Maschio, '
               'Luca Scarano, Pietro Tarantino, Gaetano Voza',
               'Raimondo Acampora, Giuseppe Barrucci, Tommaso De Carolis, Paolo Russo'),
    'BENEVENTO': ('Massimo Silva',
                  'Andrea Armellini, David Dei, Luigi Imparato, Bernardo Sala',
                  'Massimo De Solda, Alessandro Battisti, Di Meola, Giovanni Langella, Osvaldo Mancini, '
                  'Stefano Mastroianni, Michele Moscetta, Giuseppe Orsini, Giuseppe Petitto, Nazareno Pignotti',
                  "Davide Bombardini, Roberto D'Ermilio, Domenico De Simone, Alessandro De Solda, Andrea Fiorini, "
                  'Graziano Iscaro, Pietro Maiellaro, Giuseppe Sampino',
                  'Sossio Aruta, Roberto De Palma, Francesco Libro'),
    'CATANZARO': ('Rino Lavezzini',
                  'Marco Bizzarri, Vincenzo Nunziata',
                  'Fabrizio Cipriani, Francesco Esposito, Lorenzo Fiorentini, Renato Mancini, Carlo Pascucci, '
                  'Paolo Petrullo, Marco Pisano',
                  'Leonardo Vanzetto, Francesco De Luca, Dino Di Julio, Riccardo Illario, Giacomo Lazzini, Mauro Picasso',
                  'Michele De Min, Giovanni Baratto, Massimo Campo, Gianfranco Criniti, Francesco Libro, '
                  'Cristian Polidori'),
    'TRIESTINA': ('Giorgio Roselli',
                  'Graziano Vinti, Paolo Bianchet',     # Bianchet: goalkeeper, 6 apps (unionetriestina.it)
                  'Pierre Aubameyang, Paolo Benetti, Gianmaria Berretti, Gianluca Birtig, Luigi Corino, '
                  'Gualtiero Grandini, Giuseppe Scattini, Alessandro Ubaldi, Gianfranco Zanotto',
                  'Ezio Brevi, Giuliano Camporese, Alen Carli, Denis Drioli, Giuseppe Mosca, Massimo Pavanel, '
                  'Gianni Pivetta, Andrea Polmonari, Luciano Stazi',
                  'Massimo Marsich, William Aldrovandi, Marco Di Costanzo, Mirco Gubellini, Guy Roger Nzamba, '
                  'Gianfranco Serioli, Marco Spilli, Alex Taribello'),
    'RIMINI': ('Carlo Florimbi',
               'Alessandro Misefori, Antonello Ciprietti',
               'Carlo Cornacchia, Cosimo De Blasio, Davide Baronio, Francesco Danza, Giuseppe Leo, William Pianu',
               "Fabrizio Mastini, Gabriele Mazzotti, Gianluca Rosone, Leonardo Malaguti, Massimiliano D'Urso, "
               "Massimiliano Maddaloni, Mauro Buratti, Roberto D'Ermilio, Simone Tognon",
               'Filippo Coppola, Ignazio Damato, Massimo Mezzini, Stefano Nicoletti'),
    'FROSINONE': ('Carlo Orlandi',
                  'Stefano Ambrosi, Massimo Assante',
                  'Vincenzo Prochilo, Marco Bagaglini, Massimo Carli, Gianluca Lagati, Alessandro Marucci, '
                  'Fabio Sanguedolce, Ciro Scognamiglio, Carlo Tebi',
                  'Antonio Colagiovanni, Carlo Cotroneo, Cristiano Di Loreto, Marco Francabandiera, '
                  'Cristiano Gagliarducci, Stefano Papiri, Fabrizio Perrotti, Maurizio Promutico, Carlo Valentini, '
                  'Tommaso Zara',
                  'Massimo Anselmi, Salvatore Campilongo, Tiziano Levanti, Claudio Pelosi, Antonio Rebesco, Gianni Testa'),
    'SANDONA': ('Valentino Leonarduzzi',
                'Daniele Cerretti, Claudio Furlan',
                'Gianfranco Cinetto, Luigi Russo, Alberto Burato, Davide Zanon',
                'Willy Baiana, Enrico Bonaldo, Giulio Giacomin, Walter Pasqualini, Massimiliano Striuli, '
                'Marco Tomaselli, Nicola Trangoni, Giorgio Zanutta',
                'Fabio Bazzani, Gabriele Dei Rossi, Simone Facchini, Marco Samaritani, Matteo Vianello'),
    'PRO PATRIA': ('Carlo Garavaglia',
                   'Paolo Locatelli, Luca Righi',
                   'Roberto Bandirali, Fabio Barbieri, Ivan Brambilla, Cisco Guida, Marco Mazziotti, Luca Paganini, '
                   'Roberto Pellizzari, Silvio Toniolo, Andrea Tubaldo',
                   'Valentino Angeloni, Massimiliano Brizzi, Walter Curti, Dino Giannascoli, Gianluca Peron, '
                   'Claudio Rusconi, Sabino Sardella',
                   'Tommaso Rocchi, Daniele Guerzoni, Claudio Lunini, Ferdinando Piro'),
    'CATANIA': ('Giovanni Mei',
                'Patrizio Fimiani, Giovanni Giorgianni',
                'Alessandro Cicchetti, Gennaro Grillo, Antonino Di Dio, Tommaso Napoli, Roberto Ricca, Jose Sparti, '
                'Fabio Ercoli, Marcello Pizzimenti, Antonio Sarcinella',
                "Gaetano Cala Campana, Umberto Brutto, Maurizio Anastasi, Massimo D'Aviri, Orazio Russo, "
                'Maickel Ferrier, Davide Faieta, Giuseppe Marino, Pasquale Marino, Maurizio Pellegrino',
                "Rosario Bonanno, Mirco Corrente, Lorenzo Intrieri, Tiziano D'Isidoro, Nino Naccari, Franco Pannitteri"),
    'PRO SESTO': ('Gianfranco Motta',
                  'Sandro Merlo, Enricomaria Malatesta',
                  'Cristian Adami, Tommy Beltrame, Matia Brambilla, Cristian Campi, Stefano Di Gioia, Andrea Merenda',
                  'Matteo Ambrosoni, Alessio Balducci, Cristian Brocchi, Massimiliano Caliari, Jacopo Colombo, '
                  'Hugo Daniel Donato, Daniele Gardini, Marco Lopriore, Federico Meda, Jehad Muntasser, '
                  'Michele Pennacchio, Davide Tedoldi',
                  'Matteo Beretta, Davide Di Nicola, Emiliano Malaccari, Aniello Nino'),
    'CITTADELLA': ('Ezio Glerean',
                   'Andrea Campagnolo, Adriano Zancope',
                   'Terry Cavazzana, Christian Greco, Christian Ottofaro, Ugo Sarracino, Paolo Simeoni, Alberto Simonetto',
                   'Walter Antonello, Sandro Berto, Nicola Bressi, Fabio Filippi, Gianni Migliorini, Matteo Pagani, '
                   'Paolo Pupita, Riccardo Rimondini',
                   'Filippo Bordin, Christian Colitti, Nicola Rostellato, Paolo Zirafa'),
}

FOREIGN = {'PIERRE AUBAMEYANG': (109, True), 'GUY ROGER NZAMBA': (109, True), 'DIRK VOLLMAR': (13, False),
           'HUGO DANIEL DONATO': (68, False)}

# target average player price (SWOS price index) from the 1996-97 final standings; existing clubs (original
# SWOS data): C1 14.3-20.2, C2 Pisa 17.2, Taranto 14.8, Ternana 14.4; Serie B average 17.9.
# Skills and prices of the template squad are shifted by whole skill steps (1 step = 2 price units) towards it.
TARGET = {
    'TREVISO': 19, 'BRESCELLO': 18.5, 'CARPI': 18, 'SARONNO': 18, 'PRATO': 17.5, 'NOCERINA': 17.5,
    'CASARANO': 17, 'JUVE STABIA': 17,
    'LUMEZZANE': 15, 'BATTIPAGLIESE': 15, 'LECCO': 14.5, 'TURRIS': 14.5, 'LIVORNO': 14.5, 'TRIESTINA': 14,
    'BENEVENTO': 14, 'CATANZARO': 14, 'RIMINI': 13.5, 'PRO PATRIA': 13.5, 'PRO SESTO': 13.5, 'CITTADELLA': 13.5,
    'CATANIA': 13.5, 'SANDONA': 13, 'FROSINONE': 12.5,
}

# --- existing clubs (session 14b): same treatment, kits and names kept from the original TEAM.020 ---
EXISTING = {
    'ACIREALE': ('Rosario Foti',
                 'Stefano Razzetti, Corrado Vaccaro',
                 'Andrea Suriano, Giuseppe Bonanno, Michele Cataldi, Agatino Chiavaro, Roberto Civolani, Mattia Esposito, '
                 'Elio Migliaccio, Gianluca Rencricca',
                 'Maurizio Anastasi, Vladimiro Caramel, Vito Lasalandra, Gianni Margheriti, Santo Torre',
                 'Donato Terrevoli, Angeloantonio Cianciotta, Giuseppe Delle Donne, Sandro Mazzoni, Gianfranco Serioli, '
                 'Salmon Zalla'),
    'ANCONA': ('Giuseppe Petrelli',
               'Alessandro Cesaretti, David Dei',
               'Simone Altobelli, Andrea Camplone, Gianpaolo Castorina, Simone Farabegoli, Francesco Nocera, '
               'Gianfranco Parlato, Diego Pellegrini, Stefano Ricci',
               'Davide Tentoni, Luigi Bugiardini, Marco Carrara, Andrea Casonato, Massimo De Amicis, Michele Fini, '
               'Augusto Gabriele, Giacomo Modica, Cristian Trapella',
               'Stefano Albanesi, Mario Bonfiglio, Alberto Briaschi, Massimiliano Fanesi, Fabio Lucidi, Adriano Meacci, '
               'Alessandro Morello, Rocco Pagano, Lorenzo Scarafoni'),
    'ASCOLI': ('Enrico Nicolini',        # ordered by league appearances
               'Roberto Menghini, Francesco Musarra',
               'Stefano Fontana, William Viali, Andrea Sussi, Giovanni Orfei, Marco Piccioni, Massimo Savio, Dario Rossi, '
               'Simone Schicchi',
               'Paolo Sacchetti, David Fiorentini, Stefano Mobili, Maurizio Cammarieri, Roberto Romualdi, Mauro Salvagno, '
               'Marco Chirico, Enzo Tasso, Manuel Milana, Manolo Manoni, Giorgio La Vista, Luca Minopoli',
               'Roberto Manca, Antonio Rizzolo, Stefano Pompini, Antonio Di Meo'),
    'AVELLINO': ('Giuliano Zoratti',
                 'Salvatore Soviero, Marco Giannitti',
                 'Angelo Ametrano, Luca Bocchino, Domenico Colletto, Davide Ferrari, Gennaro Grillo, Antonio Minadeo, '
                 'Salvo Parisi, Ruggero Radice, Mario Solimeno, Alessandro Turone, Giuseppe Vecchio, Francesco Zampella',
                 "Francesco Bianco, Alfonso Camorani, Antonio Cresta, Fiorenzo D'Ainzara, Emiliano De Juliis, "
                 'Pasqualino Di Serafino, Sandro Federico, Angelo Ferraro, Emanuele Germano, Salvatore Giorgio, '
                 'Cisco Guida, Marco Lo Pinto, Michele Menolascina, Lorenzo Scoponi',
                 'Salvatore Campilongo, Domenico Cannalonga, Andrea Cecchini, Edmondo Farias, Salvatore Fresta, '
                 'Stefano Guidoni, Antonino Marcatti, Gioacchino Prisciandaro'),
    'COMO': ('Alessandro Scanziani',
             'Claudio Bozzini, Michele Nicoletti',
             'Gabriele Baraldi, Gian Mario Consonni, Corrado Ferracuti, Paolo Mozzini, Vincenzo Pandullo, '
             'Carlo Sassarini, Luca Ungari',
             'Gianluca Zambrotta, Attilio Bonomi, Tarcisio Catanese, Fabrizio Catelli, Mattia Collauto, '
             'Stefano De Agostini, Roberto Galia, Ruben Garlini, Luca Lomi, Daniele Papis, Michele Pedroli, '
             'Stefano Saresini, Rodolfo Vanoli',
             'Luca Cecconi, Cristian Bertani, Alfredo Francani, Cristian Morgandi, Fabio Vignaroli'),
    'FIDELIS ANDRIA': ('Giuseppe Papadopulo',
                       'Cristiano Lupatelli, Nicola Dibitonto, Luca Siringo',
                       'Andrea Arcuti, Germano Fragliasso, Antonio Landi, Giuseppe Luceri, Pietro Mariani, '
                       'Antonio Sarcinella, Alessandro Scarponi, Mario Solimeno',
                       'Oberdan Biagioni, Roberto Cappellacci, Cristian Ciaramella, Danilo Coppola, '
                       'Antonio De Leonardis, Nicola De Santis, Giammarco Frezza, Pasquale Logiudice, Giuseppe Minaudo, '
                       'Renato Olive, Alessandro Sturba',
                       'Genny Del Prete, Luca Falanga, Mario Lemme, Vincenzo Palumbo, Francesco Passiatore, '
                       'Vincenzo Santoruvo'),
    'MODENA': ('Pierluigi Frosio',
               'Alessio Bandieri',
               'Riki Di Bin, Andrea Di Cintio, Ciro Di Nicolantonio, Roberto Galletti, Alessandro Gola, Luigi Sottana',
               'Luca Amoruso, Andrea Bottazzi, Gianluca Gaudenzi, Roberto Magnani, Gabriele Bocchi, Massimo Pellegrini, '
               'Cristiano Scazzola',
               'Corrado Grabbi, Simone Cavalli, Salvatore Tarascio, Paolo Mandelli, Andrea Zucco'),
    'MONZA': ('Giorgio Rumignani',       # Massimo Oddo (loan, also Prato) kept at Prato
              'Christian Abbiati, Giuseppe Gatta',
              'Francesco Bega, Alessio Delpiano, Gianluca Falsini, Claudio Finetti, Francesco Rossi, Giuseppe Zappella',
              "Filippo Antonelli, Antonino Asta, Riccardo Bracaloni, Federico Crovari, Roberto D'Aversa, "
              'Omar Milanetto, Fulvio Saini',
              'Emanuele Cancellato, Simone Erba, Alberto Gallo, Orazio Millesi, Michele Pietranera, Marco Veronese'),
    'PISTOIESE': ('Enrico Catuzzi',
                  'Paolo Di Sarno, Luca Gentili, Davide Quironi',
                  'Nicola Legrottaglie, Stefano Pioli, Cristian Zenoni, Alessio Ballanti, Gianluca Gibellini, '
                  'Pietro Girillo, Alberto Mantelli, Filippo Medri, Antonio Niccolai',
                  'Damiano Zenoni, Antonio Bellavista, Sergio Campolo, Francesco Cimmarusti, Fabio Consagra, '
                  'Rocco Cotroneo, Jimmy Fialdini, Carmelo Imbriani, Marco Napolioni, Mauro Nardini, Daniele Russo, '
                  'Vito Sardone',
                  'Francesco Caruso, Massimo Ciocci, Daniele Beltrammi, Gabriele Graziani, Gabriele Lombino, '
                  'Eddy Perensin, Simone Quercioli, Massimiliano Vadacca'),
    'SPAL': ('Salvatore Bianchetti',
             'Oriano Boschin',
             'Andrea Borsa, Giovanni Bucaro, Giovanni Fasce, Giuseppe Fornaciari, Alessandro Furlanetto, '
             'Vincenzo Pandullo, Yuri Pellegrini, Dario Rossi, Cristian Stellini',
             'Andrea Bianchi, Edoardo Braiati, Loris Del Nevo, Alessandro Ferronato, Alfonso Greco, Marco Libassi, '
             'Eugenio Sgarbossa, Andrea Sussi',
             'Roberto Putelli, Fabrizio Fermanelli, Fabio Frazzica, Salvatore Giorgio, Mirco Gubellini, '
             'Giancarlo Romairone, Giovanni Sorce, Gabriele Zagati'),
    'PISA': ('Luciano Filippi',
             'Antonio Corradi, Alessio Schiaffino',
             'Emiliano Niccolini, Jacopo Balestri, Alessandro Baroni, Daniele Marsan, Gianluca Presicci, '
             'Ildebrando Stafico',
             'Paolo Andreotti, Massimo Andreotti, Guglielmo Baldini, Giacomo Biagi, Simone Felici, Paolo Benedetti, '
             'Gianni Cristiani, Massimo Belluomini, Pasquale Minuti, Alessandro Piovesan',
             'Gianluca Savoldi, Federico Balestri, Gerry Cavallo, Alessandro Andreini'),
    'TARANTO': ('Pietro Ruisi',
                'Francesco Galati, Aniello Mancon, Vincenzo Marinacci, Ivano Rotoli',
                'Diego Ficarra, Gennaro Grillo, Vito Incrivaglia, Vincenzo Maiuri, Stefano Mundala, Giuseppe Stante, '
                'Danilo Vitali',
                'Piero Caputo, Michele Cazzaro, Roberto Chiappara, Fabio Di Lauro, Sandro Federico, Antonio Foschini, '
                'Roberto Gemmi, Francesco Latartara, Michele Menolascina, Giorgio Olivari, Tommaso Pernisco, '
                'Luca Perrotta, Giovanni Renna, Carmelo Russo, Francesco Santoro',
                'Sossio Aruta, Loriano Cipriani, Fabio Di Domenico, Vincenzo Di Maio, Antonino Sparacio, Fabio Simonetti'),
    'TERNANA': ('Luigi Delneri',
                'Oscar Verderame, Giuseppe Benatelli, Francesco Rapetti',
                'Giacomo Filippi, Daniele Marsan, Mauro Mayer, Marco Mengucci, Riccardo Onorato, Ciro Scognamiglio, '
                'Cristian Silvestri, Cristian Stellini',
                'Daniele Bellotto, Bruno Baldari, Patrizio Billio, Roberto Borrello, Andrea Caverzan, '
                'Fabio Manganiello, Roberto Marta, Giacomo Modica, Mirko Monetta, Vasco Morelli',
                'Giovanni Rossi, Diego Grassi, Claudio Pelosi, Giancarlo Romairone, Diego Zanin'),
}
ROSTERS.update(EXISTING)
TARGET.update({
    'FIDELIS ANDRIA': 19, 'ANCONA': 18.5, 'AVELLINO': 18.5, 'ASCOLI': 18.5, 'MONZA': 18, 'ACIREALE': 17,
    'COMO': 16.5, 'MODENA': 16, 'PISTOIESE': 15.5, 'SPAL': 15.5,
    'TERNANA': 15, 'PISA': 13.5, 'TARANTO': 12,
})
