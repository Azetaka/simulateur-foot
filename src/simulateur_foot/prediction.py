"""Probabilités d'un match à partir des notes Elo : le modèle retenu dans RAPPORT.md."""

import pandas as pd

from .collecte_resultats import SAISONS
from .force_clubs import calculer_forces, charger_matchs
from .modele import FORCES, RESULTATS, creer_logistique

# 2122 sert de rodage aux notes ; la dernière saison est en cours
SAISON_EN_COURS = int(SAISONS[-1])
SAISONS_APPRENTISSAGE = [int(s) for s in SAISONS[1:-1]]


def charger_forces():
    """Matchs avec les notes d'avant-match, et notes à jour de chaque club."""
    return calculer_forces(charger_matchs())


def entrainer(matchs, saisons=SAISONS_APPRENTISSAGE):
    """Régression logistique multinomiale sur force_dom et force_ext."""
    selection = matchs[matchs["Saison"].isin(saisons)]
    return creer_logistique().fit(selection[FORCES], selection["FTR"])


def probabilites(modele, notes_dom, notes_ext):
    """Probabilités A, D, H pour une ou plusieurs affiches (une ligne par match)."""
    entree = pd.DataFrame({"force_dom": notes_dom, "force_ext": notes_ext})
    proba = pd.DataFrame(modele.predict_proba(entree), columns=modele.classes_)
    return proba[RESULTATS]
