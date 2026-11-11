"""Les championnats suivis et leurs règles de fin de saison.

Les codes sont ceux de football-data.co.uk. Les règles décrivent la saison
2026-27 de façon simplifiée : le nombre de places européennes peut varier
d'une année à l'autre selon l'indice UEFA.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Championnat:
    code: str
    nom: str
    pays: str
    haut: tuple[str, int]          # (libellé, nombre de places) en haut du classement
    relegues: int                  # descentes directes
    barrage: bool                  # la place juste au-dessus des relégués joue un barrage
    barrage_aide: str = ""
    division_inferieure: str = "la division inférieure"
    departage: str = "la différence de buts"


LDC = ("Ligue des champions", 4)

CHAMPIONNATS = {
    "F1": Championnat("F1", "Ligue 1", "France", LDC, relegues=2, barrage=True,
                      barrage_aide="match aller-retour contre le 3ᵉ de Ligue 2",
                      division_inferieure="Ligue 2"),
    "E0": Championnat("E0", "Premier League", "Angleterre", LDC, relegues=3, barrage=False,
                      division_inferieure="Championship"),
    "SP1": Championnat("SP1", "Liga", "Espagne", LDC, relegues=3, barrage=False,
                       division_inferieure="Segunda División",
                       departage="les confrontations directes"),
    "D1": Championnat("D1", "Bundesliga", "Allemagne", LDC, relegues=2, barrage=True,
                      barrage_aide="match aller-retour contre le 3ᵉ de 2. Bundesliga",
                      division_inferieure="2. Bundesliga"),
    "I1": Championnat("I1", "Serie A", "Italie", LDC, relegues=3, barrage=False,
                      division_inferieure="Serie B",
                      departage="les confrontations directes"),
    "F2": Championnat("F2", "Ligue 2", "France", ("Montée directe", 2), relegues=2, barrage=True,
                      barrage_aide="match aller-retour contre le 3ᵉ de National",
                      division_inferieure="National"),
}
PAR_DEFAUT = "F1"
