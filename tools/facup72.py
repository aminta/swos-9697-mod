"""FA Cup 1871-72, the first edition: the 15 clubs and their 1871-72 players (session 26).

Sources (fetched 2026-10-01): en.wikipedia "1872 FA Cup final" (both XIs), "1871-72 Barnes F.C. season" (line-ups of Barnes,
Civil Service, Hampstead Heathens, Crystal Palace), "1871-72 Queen's Park F.C. season" (semi-final XI), "England v Scotland
representative football matches (1870-1872)" (players and their clubs), forum.hitchintownfc.club topic 2506 (Hitchin v
Crystal Palace and Hitchin v Royal Engineers, both teams), cpfc.co.uk (Peter Manning: Chenery, Chappell, Ottaway, Morten),
thefa.com (semi-final XI of Wanderers), stevesfootballstats.uk (scorers: Young, Pelham, Kenrick, Thompson...).
Templates, kits and skills of the players they share: SWOS 2020 DLC "British Football Pioneers (England)" by
Francescomanetti82 and Gorzo. British Newspaper Archive search snippets (OCR, 2026-10-01): Reading Mercury and Windsor &
Eton Express 18 Nov 1871 (Maidenhead v Marlow, both XIs), The Sportsman 15 Nov 1871 and Bell's Life 18 Nov 1871 (Clapham
Rovers v Upton Park, both XIs), Bell's Life 21 Oct 1871 (Wanderers v Harrow Chequers), Field 9 Mar 1872 and the 1871-72
England v Scotland reports (club of each player). '?' = no source found (Reigate Priory except Clutton, Donington School).
Positions of the 1871 players are reconstructed (line-ups were printed without positions).

Each club: (name, captain/secretary as the 'coach', Pioneers template club, target average price, kit or None (template's),
            {'G': [...], 'D': [...], 'M': [...], 'A': [...]})  - starters first, 1870s line-ups: 1 G, 2 backs, 1-2 half-backs,
            the rest forwards. Order = the real first-round draw, the bye (Hampstead Heathens) last.
"""
CLUBS = [
    ('BARNES', 'Percy Weston', 'BARNES', 21, None, {
        'G': ['A. Adams', 'C. Ommanney'],
        'D': ['W. K. Bruce', 'F. C. Clarkson', 'W. R. Collins'],
        'M': ['H. E. Solly', 'R. W. Willis', 'J. Graham'],
        'A': ['Percy Weston', 'E. T. Weston', 'V. Weston', 'A. R. Dunnage', 'E. C. Highton', 'A. C. Highton',
              'Charles Morice', 'C. Warren']}),
    ('CIVIL SERVICE', 'J. H. Giffard', 'CIVIL SERVICE', 17, None, {
        'G': ['James Kirkpatrick', '?'],
        'D': ['J. H. Giffard', 'A. H. Bateman', 'William Butler'],
        'M': ['H. C. Houndle', 'C. W. A. Trollope', 'Evelyn Freeth'],
        'A': ['J. Wearne', 'W. H. White', 'William Lindsay', 'Charles Baillie-Hamilton', 'William Bailey',
              'Gilbert Primrose', 'Henry Primrose', 'Arnold Kirke Smith']}),
    ('HITCHIN', 'Cecil Reid', 'WINDSOR HOME', 17, None, {
        'G': ['W. Hill', '?'],
        'D': ['Cecil Reid', 'William Tindall Lucas', 'Francis Shillitoe'],
        'M': ['G. D. Baker', 'H. E. Baker'],
        'A': ['C. A. Baker', 'W. G. Hazelrigg', 'T. C. Mainwaring', 'G. Jackson', 'Ernest Woodgate', 'F. H. Lucas',
              'H. Mainwaring', 'H. O. Crow', 'T. McKenzie']}),
    ('CRYSTAL PALACE', 'Douglas Allport', 'CRYSTAL PALACE', 22, None, {
        'G': ['Alexander Morten', 'J. Turner'],
        'D': ['Douglas Allport', 'W. M. Allport', 'A. J. Heath'],
        'M': ['John Cockerell', 'Frederick Chappell'],
        'A': ['Charles Chenery', 'Cuthbert Ottaway', 'W. Bouch', 'C. E. Smith', 'F. B. Soden', 'H. Dawkes', 'W. C. Foster',
              'T. F. Spreckley', 'A. Lloyd']}),
    ('MAIDENHEAD', 'W. Goulden', 'WINDSOR HOME', 17, None, {
        'G': ['F. Nicholson', '?'],
        'D': ['Vardy', 'T. N. Carter', 'W. Goulden'],
        'M': ['A. Austen-Leigh', 'C. Richardson'],
        'A': ['G. Young', 'J. W. Monnington', 'Lloyd', 'F. Price', 'Hebbes', '?', '?', '?', '?']}),
    ('GREAT MARLOW', 'A. C. Faulkner', 'MARLOW', 16, None, {
        'G': ['Nicholson', '?'],
        'D': ['A. C. Faulkner', 'J. Stockbridge', 'T. Kedge'],
        'M': ['S. Wright', 'J. D. Crossman'],
        'A': ['Cuthbert Ottaway', 'Clay', 'Tindall', 'J. Batting', 'Beven', '?', '?', '?', '?']}),
    ('UPTON PARK', 'C. Warner', 'UPTON PARK', 18, None, {
        'G': ['W. B. Gardner', '?'],
        'D': ['C. Warner', 'W. Freeth', 'Alfred Stair'],
        'M': ['M. Jutsum', 'H. Compton'],
        'A': ['E. Curwen', 'F. Wilton', 'T. Kitson', 'A. M. Jones', 'F. Barnett', 'C. Wilson', '?', '?', '?']}),
    ('CLAPHAM ROVERS', 'R. H. Birkett', 'CLAPHAM ROVERS', 20, None, {
        'G': ['R. H. Birkett', 'E. Field'],
        'D': ['Jarvis Kenrick', 'Robert Ogilvie', 'Robert Walker'],
        'M': ['E. W. Dent', 'C. Holden', 'Thomas Baker'],
        'A': ['Alexander Nash', 'J. Nash', 'P. St. Quintin', 'A. Thompson', 'C. C. Tayloe', 'C. F. Wace',
              'C. C. Bergmann', 'M. Mumford']}),
    ("QUEEN'S PARK", 'Robert Gardner', "QUEEN'S PARK FC", 28, [0, 5, 5, 1, 2], {
        'G': ['Robert Gardner', '?'],
        'D': ['William Ker', 'Joseph Taylor', 'R. Edmiston'],
        'M': ['James Thomson', 'James Smith', 'J. Hepburn'],
        'A': ['Robert Smith', 'Robert Leckie', 'Alexander Rhind', 'William MacKinnon', 'James Weir', 'David Wotherspoon',
              'J. Walker', '?']}),
    ('DONINGTON SCHOOL', '?', 'WORLABYE HOUSE', 12, None, {
        'G': ['?', '?'], 'D': ['?', '?', '?'], 'M': ['?', '?'],
        'A': ['?', '?', '?', '?', '?', '?', '?', '?', '?']}),
    ('ROYAL ENGINEERS', 'William Merriman', 'ROYAL ENGINEERS', 27, None, {
        'G': ['William Merriman', '?'],
        'D': ['Francis Marindin', 'George Addison', 'G. Barker'],
        'M': ['Alfred Goodwyn', 'Hoskyns'],
        'A': ['Hugh Mitchell', 'Edmund Creswell', 'Henry Renny-Tailyour', 'Henry Rich', 'Herbert Muirhead',
              'Edmond Cotter', 'Adam Bogle', 'H. Clarke', 'W. Ord']}),
    ('REIGATE PRIORY', '?', 'WINDSOR HOME', 15, None, {
        'G': ['?', '?'], 'D': ['R. W. Clutton', '?', '?'], 'M': ['?', '?'],
        'A': ['?', '?', '?', '?', '?', '?', '?', '?', '?']}),
    ('WANDERERS', 'Charles W. Alcock', 'WANDERERS', 28, None, {
        'G': ['Reginald Welch', '?'],
        'D': ['Edgar Lubbock', 'Percy Currey'],
        'M': ['Albert Thompson', 'Arthur Kinnaird'],
        'A': ['Charles W. Alcock', 'Edward Bowen', 'Alexander Bonsor', 'Morton Betts', 'William Crake', 'Thomas Hooman',
              'Walpole Vidal', 'Charles Wollaston', 'Thomas Pelham', 'Quintin Hogg']}),
    ('HARROW CHEQUERS', 'R. E. Crawford', 'OLD HARROVIANS', 19, None, {
        'G': ['Reginald Welch', '?'],
        'D': ['Fitzgerald Crawford', 'G. G. Kennedy', 'Alfred Thornton'],
        'M': ['R. E. Crawford', 'C. Masson'],
        'A': ['Morton Betts', 'William Crake', 'Edward Elliot', 'J. H. Morgan', '?', '?', '?', '?', '?']}),
    ('HAMPSTEAD HEATH.', 'J. P. Tatham', 'HAMPSTEAD HEATH', 18, None, {
        'G': ['J. Marshall', '?'],
        'D': ['R. Barker', 'H. W. Beauchamp', 'C. B. Dimond'],
        'M': ['A. M. S. Erskine', 'H. Latham'],
        'A': ['J. P. Tatham', 'S. R. Tatham', 'A. Leach', 'H. P. Leach', 'G. P. Leach', 'R. B. Michell', 'A. Bird',
              'Henry Lake', '?']}),
]

# Pioneers DLC spellings of the same people (their records keep skills and faces)
ALIAS = {'JOSEPH TAYLOR': 'JOSPEH TAYLOR', 'ALEXANDER RHIND': 'ALEX RHIND', 'C. OMMANNEY': 'CHARLIE OMMANEY',
         'A. ADAMS': 'ANTOINE ADAMS'}
