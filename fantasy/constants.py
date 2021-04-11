from datetime import time

from django.db import models


class Series(models.TextChoices):
    DEMO = ('D', 'Demo')
    TORPIDS = ('T', 'Torpids')
    EIGHTS = ('E', 'Eights')


class Genders(models.TextChoices):
    MENS = ('M', "Men's")
    WOMENS = ('W', "Women's")


class timings:
    MARKET_OPENS = time(20, 00)


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

