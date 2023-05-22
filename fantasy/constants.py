from datetime import time
import enum

from django.db import models


class Locations(enum.Enum):
    DEMO = 'DEMO'
    OXFORD = 'OXF'
    CAMBRIDGE = 'CAM'


class Series(models.TextChoices):
    DEMO = ('D', 'Demo')
    TORPIDS = ('T', 'Torpids')
    EIGHTS = ('E', 'Eights')
    LENTS = ('L', 'Lents')
    MAYS = ('M', 'Mays')


GENDERS_OVERALL = 'O'


class Genders(models.TextChoices):
    MEN = ('M', 'Men')
    WOMEN = ('W', 'Women')


class timings:
    MARKET_OPENS = time(20, 00)
    GAME_ADVANCE = time(19, 45)  # Only used in Rules page


class money:
    INITIAL_BALANCE = 1000
    PRICE_MAX = 300
    PRICE_MIN = 20


class Clubs(models.TextChoices):
    BALL = ('ball', 'Balliol')
    BRAS = ('bras', 'Brasenose')
    CHRI = ('chri', 'Christ Church')
    CORP = ('corp', 'Corpus Christi')
    EXET = ('exet', 'Exeter')
    GRTE = ('grte', 'Green Templeton')
    HERT = ('hert', 'Hertford')
    JESU = ('jesu', 'Jesus')
    KEBL = ('kebl', 'Keble')
    LADY = ('lady', 'Lady Margaret Hall')
    LINA = ('lina', 'Linacre')
    LINC = ('linc', 'Lincoln')
    MAGD = ('magd', 'Magdalen')
    MANS = ('mans', 'Mansfield')
    MERT = ('mert', 'Merton')
    NEWC = ('newc', 'New College')
    ORIE = ('orie', 'Oriel')
    OSLE = ('osle', 'Osler House')
    PEMB = ('pemb', 'Pembroke')
    QUEE = ('quee', "Queen's")
    REGE = ('rege', "Regent's Park")
    SOME = ('some', 'Somerville')
    SANN = ('sann', "St Anne's")
    SANT = ('sant', "St Antony's")
    SBEN = ('sben', "St Benet's")
    SCAT = ('scat', "St Catherine's")
    SEDM = ('sedm', 'St Edmund Hall')
    SHIL = ('shil', "St Hilda's")
    SHUG = ('shug', "St Hugh's")
    SJOH = ('sjoh', "St John's")
    SPET = ('spet', "St Peter's")
    TRIN = ('trin', 'Trinity')
    UNIV = ('univ', 'University')
    WADH = ('wadh', 'Wadham')
    WOLF = ('wolf', 'Wolfson')
    WORC = ('worc', 'Worcester')
    ADDE = ('adde', 'Addenbrookes')
    ANGL = ('angl', 'Anglia Ruskin')
    CAIU = ('caiu', 'Caius')
    CHRC = ('chrc', "Christ's")
    CHUR = ('chur', 'Churchill')
    CLAR = ('clar', 'Clare')
    CLAH = ('clah', 'Clare Hall')
    COCC = ('cocc', 'Corpus Christi')
    DARW = ('darw', 'Darwin')
    DOWN = ('down', 'Downing')
    EMMA = ('emma', 'Emmanuel')
    FATT = ('fatt', 'First & Third')
    FITZ = ('fitz', 'Fitzwilliam')
    GIRT = ('girt', 'Girton')
    HOME = ('home', 'Homerton')
    HUGH = ('hugh', 'Hughes Hall')
    JESC = ('jesc', 'Jesus')
    KING = ('king', "King's")
    LADC = ('ladc', 'Lady Margaret')
    LUCY = ('lucy', 'Lucy Cavendish')
    MAGC = ('magc', 'Magdalene')
    MURR = ('murr', 'Murray Edwards')
    NEWN = ('newn', 'Newnham')
    PEMC = ('pemc', 'Pembroke')
    PETE = ('pete', 'Peterhouse')
    QUEC = ('quec', "Queens'")
    ROBI = ('robi', 'Robinson')
    SCAC = ('scac', "St Catherine's")
    SEDC = ('sedc', "St Edmund's")
    SELW = ('selw', 'Selwyn')
    SIDN = ('sidn', 'Sidney Sussex')
    TRIH = ('trih', 'Trinity Hall')
    WOLC = ('wolc', 'Wolfson')

