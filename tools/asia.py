"""New Asian club countries (Roadmap 2, 1.2): South Korea (TEAM.061), China (063), Saudi Arabia (086).

Clubs and final order: 1997 K-League and Jia-A, 1996-97 Saudi Premier League (RSSSF tablesa/allfirst97.html and
allfirst9697.html, fetched 2026-10-01). Squads and coaches are GENERATED from common local names, as for Africa
(africa.py does the work): no reliable 1996-97 rosters. Templates: the J-League clubs of the original game
(TEAM.055) for Korea and China, Algeria (TEAM.042) for Saudi Arabia. Kits are approximate.
Country numbers: 61 and 63 were empty in the original tables; 86 is the first number after the continents
(80-85); the game treats 86..99 as club countries (every "national team" test is 80 <= n <= 85).
"""
from africa import build as _build, countries_config as _config

COUNTRIES = {
    61: ({'en': 'SOUTH KOREA', 'it': 'COREA DEL SUD', 'fr': 'COREE DU SUD', 'de': 'SUEDKOREA'}, 'SOUTH KOREAN', 127, 55,
         1730, (17, 12), [
        ('PUSAN DAEWOO', (0, 4, 4, 1, 4)), ('CHUNNAM DRAGONS', (0, 9, 9, 2, 9)), ('ULSAN HYUNDAI', (0, 5, 5, 1, 5)),
        ('POHANG STEELERS', (2, 4, 2, 2, 2)), ('SUWON BLUEWINGS', (0, 5, 5, 1, 4)), ('CHONBUK DINOS', (0, 8, 8, 1, 8)),
        ('TAEJON CITIZEN', (0, 6, 6, 1, 6)), ('CHUNAN ILHWA', (0, 9, 9, 2, 2)), ('ANYANG LG', (2, 4, 2, 2, 4)),
        ('PUCHON SK', (0, 3, 3, 1, 3))]),
    63: ({'en': 'CHINA', 'it': 'CINA', 'fr': 'CHINE', 'de': 'CHINA'}, 'CHINESE', 139, 55, 1740, (15, 10), [
        ('DALIAN WANDA', (0, 4, 4, 1, 4)), ('SHANGHAI SHENHUA', (0, 5, 5, 1, 5)), ('BEIJING GUOAN', (0, 8, 8, 1, 8)),
        ('VANGUARD HUANDAO', (0, 4, 4, 1, 1)), ('YANBIAN AODONG', (0, 1, 1, 5, 5)), ('JINAN TAISHAN', (0, 3, 3, 1, 3)),
        ('SICHUAN QUANXING', (0, 9, 9, 5, 9)), ('GUANGZHOU APOLLO', (0, 4, 4, 2, 4)), ('QINGDAO MANATEES', (0, 7, 7, 5, 7)),
        ('AUGUST 1ST', (0, 4, 4, 4, 4)), ('TIANJIN LIFEI', (0, 7, 7, 1, 7)), ('GD HONGYUAN', (0, 1, 1, 2, 1))]),
    86: ({'en': 'SAUDI ARABIA', 'it': 'ARABIA SAUDITA', 'fr': 'ARABIE SAOUDITE', 'de': 'SAUDI-ARABIEN'}, 'SAUDI', 131,
         42, 1752, (16, 10.5), [
        ('ITTIHAD JEDDAH', (2, 9, 2, 2, 9)), ('AL NASR', (0, 9, 9, 5, 9)), ('AL HILAL', (0, 5, 5, 1, 5)),
        ('AL SHABAB', (0, 1, 1, 1, 1)), ('AL AHLI JEDDAH', (0, 8, 8, 1, 8)), ('AL RIYADH', (0, 4, 4, 1, 4)),
        ('AL ETTIFAQ', (0, 8, 8, 4, 8)), ('AL WEHDA', (0, 4, 4, 1, 1)), ('AL NAJMA', (0, 8, 8, 1, 1)),
        ('AL TAEE', (0, 4, 4, 2, 4)), ('AL ANSAR', (0, 8, 8, 5, 8)), ('AL QADSIAH', (0, 4, 4, 5, 5))]),
}

NAMES = {
    127: ('KIM LEE PARK CHOI JUNG KANG CHO YOON JANG LIM HAN OH SEO SHIN KWON HWANG AHN SONG YOO HONG',
          'SANG-HO DONG-HYUN JAE-SUK MIN-SOO JIN-WOO SUNG-YONG KI-HOON YOUNG-MIN JUNG-WON HYUN-SOO TAE-WOOK '
          'SEUNG-HO CHANG-SIK DO-HOON KYUNG-JIN WOO-YOUNG SEOK-JU JAE-HONG IN-SOO BYUNG-CHUL'),
    139: ('LI WANG ZHANG LIU CHEN YANG ZHAO HUANG ZHOU WU XU SUN HU ZHU GAO LIN HE GUO MA LUO',
          'WEI JUN QIANG MING HAO JIAN LEI BIN TAO PENG YONG GANG HAIBO XIAOFENG JIANJUN ZHIGANG HONGBO '
          'DONGMING LIJUN WENJIE'),
    131: ('MOHAMMED ABDULLAH FAHAD KHALID SAEED SAMI NAWAF HAMAD ABDULAZIZ OMAR YOUSEF IBRAHIM SALEH NASSER '
          'TALAL OSAMA AHMED HUSSEIN MAJED',
          'AL-OTAIBI AL-QAHTANI AL-GHAMDI AL-HARBI AL-ZAHRANI AL-SHEHRI AL-DOSARI AL-MUTAIRI AL-ANAZI '
          'AL-SHAMMARI AL-SUBAIE AL-MALKI AL-JUHANI AL-OMARI AL-HARTHI AL-ASMARI'),
}

# national cups (Korean FA Cup, Chinese FA Cup, Saudi King's Cup): 8 teams, as Taiwan's cup (12 clubs)
NATIONAL_CUPS = {
    61: dict(id=0xba, teams=8, rounds=(0x54, 0x54, 0x14)),
    63: dict(id=0xbb, teams=8, rounds=(0x54, 0x54, 0x14)),
    86: dict(id=0xbc, teams=8, rounds=(0x54, 0x54, 0x14)),
}
LEAGUE_IDS = {61: 0xb7, 63: 0xb8, 86: 0xb9}

JPN, TWN, IND, KOR, CHN, KSA = 55, 67, 75, 61, 63, 86
# Asian Club Championship / Asian Cup Winners' Cup 1997-98 style: 16-team knockouts, pairs from different countries.
# First season: best clubs of each country (Japan: the game's own disguised J-League names).
CLUB_CHAMPIONSHIP = [
    (JPN, 26), (TWN, 9), (KOR, 0), (IND, 1), (CHN, 0), (KSA, 2), (KSA, 0), (JPN, 19),
    (JPN, 9), (CHN, 2), (KOR, 1), (TWN, 6), (CHN, 1), (KOR, 2), (KSA, 1), (IND, 2),
]
CUP_WINNERS_CUP = [
    (JPN, 16), (TWN, 4), (KOR, 3), (IND, 5), (CHN, 3), (KSA, 5), (KSA, 3), (JPN, 1),
    (JPN, 27), (CHN, 5), (KOR, 4), (TWN, 1), (CHN, 4), (KOR, 5), (KSA, 4), (IND, 0),
]


def build(src_dir):
    return _build(src_dir, COUNTRIES, NAMES)


def countries_config():
    months = lambda fileno, tmpl: (0x40, 0x28) if fileno == 86 else (0x10, 0x50)   # Saudi: autumn-spring; KOR/CHN: J-League
    cfg = _config(COUNTRIES, NATIONAL_CUPS, 'asia', months)
    for n, cid in LEAGUE_IDS.items():
        cfg[n]['league']['id'] = cid
    return cfg
