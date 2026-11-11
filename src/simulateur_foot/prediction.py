"""Probabilités d'un match à partir des notes Elo : le modèle retenu dans RAPPORT.md."""

import numpy as np
import pandas as pd

from .collecte_resultats import SAISONS
from .force_clubs import calculer_forces, charger_matchs
from .modele import FORCES, RESULTATS, creer_logistique

# 2122 sert de rodage aux notes ; la dernière saison est en cours
SAISON_EN_COURS = int(SAISONS[-1])
SAISONS_APPRENTISSAGE = [int(s) for s in SAISONS[1:-1]]


def charger_forces(championnat="F1"):
    """Matchs avec les notes d'avant-match, et notes à jour de chaque club."""
    return calculer_forces(charger_matchs(championnat))


def entrainer(matchs, saisons=SAISONS_APPRENTISSAGE):
    """Régression logistique multinomiale sur force_dom et force_ext."""
    selection = matchs[matchs["Saison"].isin(saisons)]
    return creer_logistique().fit(selection[FORCES], selection["FTR"])


def probabilites(modele, notes_dom, notes_ext):
    """Probabilités A, D, H pour une ou plusieurs affiches (une ligne par match)."""
    entree = pd.DataFrame({"force_dom": notes_dom, "force_ext": notes_ext})
    proba = pd.DataFrame(modele.predict_proba(entree), columns=modele.classes_)
    return proba[RESULTATS]


def probabilites_tableau(modele, notes_dom, notes_ext):
    """Comme probabilites, mais pour des tableaux de notes de n'importe quelle forme.

    Calcul direct (standardisation, puis softmax de la régression) : bien plus
    rapide que predict_proba quand on l'appelle des millions de fois pendant la
    simulation. Renvoie un tableau (..., 3) dans l'ordre A, D, H.
    """
    echelle = modele.named_steps["standardscaler"]
    regression = modele.named_steps["logisticregression"]
    entree = (np.stack([notes_dom, notes_ext], axis=-1) - echelle.mean_) / echelle.scale_
    logits = entree @ regression.coef_.T + regression.intercept_
    logits -= logits.max(axis=-1, keepdims=True)
    proba = np.exp(logits)
    proba /= proba.sum(axis=-1, keepdims=True)
    return proba[..., [list(regression.classes_).index(r) for r in RESULTATS]]


def chances_bookmakers(cotes_h, cotes_d, cotes_a):
    """Chances implicites des cotes, colonnes A, D, H.

    1 / cote donne une chance, mais leur somme dépasse 100 % : c'est la marge
    du bookmaker. On la retire en ramenant la somme à 100 % (normalisation).
    """
    inverses = pd.DataFrame({"A": 1 / pd.Series(cotes_a, dtype=float).to_numpy(),
                             "D": 1 / pd.Series(cotes_d, dtype=float).to_numpy(),
                             "H": 1 / pd.Series(cotes_h, dtype=float).to_numpy()})
    return inverses.div(inverses.sum(axis=1), axis=0)[RESULTATS]
