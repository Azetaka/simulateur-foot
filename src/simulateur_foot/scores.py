"""Probabilités de chaque score d'un match, à partir des notes Elo.

Deux régressions de Poisson, apprises sur les deux notes, donnent les buts attendus
du club qui reçoit et de celui qui se déplace ; le croisement des deux lois donne une
grille de probabilités, un score par case. Pour l'issue du match (victoire, nul,
défaite), ce modèle ne fait pas mieux que la logistique de prediction.py (RAPPORT.md) :
la grille est donc recalée, région par région, sur les chances A, D, H de la
logistique. Les deux modèles racontent ainsi la même histoire, et la simulation peut
tirer des écarts de buts cohérents avec les issues.
"""

import numpy as np
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .modele import FORCES
from .prediction import SAISONS_APPRENTISSAGE, probabilites_tableau

MAX_BUTS = 7  # au-delà, la probabilité est négligeable ; la grille est renormalisée
BUTS = np.arange(MAX_BUTS + 1)
FACTORIELLES = np.cumprod(np.concatenate([[1], np.arange(1, MAX_BUTS + 1)]))
ECARTS = np.arange(-MAX_BUTS, MAX_BUTS + 1)  # écart de buts, du club qui reçoit
_DOM, _EXT = np.indices((MAX_BUTS + 1, MAX_BUTS + 1))
REGIONS = {"A": _DOM < _EXT, "D": _DOM == _EXT, "H": _DOM > _EXT}


def entrainer_scores(matchs, saisons=SAISONS_APPRENTISSAGE):
    """Deux régressions de Poisson (buts du club qui reçoit, buts du club qui se déplace)."""
    selection = matchs[matchs["Saison"].isin(saisons)]
    return tuple(
        make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=300))
        .fit(selection[FORCES], selection[colonne].astype(float))
        for colonne in ["FTHG", "FTAG"])


def buts_attendus(modele_scores, notes_dom, notes_ext):
    """Buts moyens du club qui reçoit et de celui qui se déplace ; tableaux de la forme des notes."""
    entree = np.stack([np.asarray(notes_dom, dtype=float), np.asarray(notes_ext, dtype=float)], axis=-1)
    moyennes = []
    for modele in modele_scores:
        echelle = modele.named_steps["standardscaler"]
        regression = modele.named_steps["poissonregressor"]
        centre = (entree - echelle.mean_) / echelle.scale_
        moyennes.append(np.exp(centre @ regression.coef_ + regression.intercept_))
    return moyennes[0], moyennes[1]


def _poisson(moyenne):
    """Probabilité de marquer 0, 1… MAX_BUTS buts : tableau (..., MAX_BUTS + 1)."""
    moyenne = np.asarray(moyenne, dtype=float)[..., None]
    return np.exp(-moyenne) * moyenne ** BUTS / FACTORIELLES


def recaler(grille, proba):
    """Ramène chaque région de la grille (A, D, H) à la probabilité donnée par la logistique.

    grille : (..., buts dom, buts ext) ; proba : (..., 3) dans l'ordre A, D, H.
    """
    resultat = np.zeros_like(grille)
    for i, masque in enumerate(REGIONS.values()):
        masse = np.where(masque, grille, 0).sum(axis=(-2, -1), keepdims=True)
        resultat += np.where(masque, grille * proba[..., i, None, None] / masse, 0)
    return resultat


def grille_scores(modele_scores, modele, notes_dom, notes_ext):
    """Probabilité de chaque score : tableau (..., buts du club qui reçoit, buts de l'autre)."""
    mu_dom, mu_ext = buts_attendus(modele_scores, notes_dom, notes_ext)
    grille = _poisson(mu_dom)[..., :, None] * _poisson(mu_ext)[..., None, :]
    return recaler(grille, probabilites_tableau(modele, notes_dom, notes_ext))


def distribution_ecarts(grille):
    """Probabilité de chaque écart de buts (ECARTS), depuis la grille : tableau (..., 2 × MAX_BUTS + 1)."""
    return np.stack([np.trace(grille, offset=-ecart, axis1=-2, axis2=-1) for ecart in ECARTS], axis=-1)


def tirer_ecarts(modele_scores, modele, notes_dom, notes_ext, generateur):
    """Écart de buts tiré au sort pour chaque affiche ; son signe suit les chances A, D, H."""
    seuils = distribution_ecarts(grille_scores(modele_scores, modele, notes_dom, notes_ext)).cumsum(axis=-1)
    u = generateur.random(np.shape(notes_dom) + (1,))
    return ECARTS[np.minimum((u > seuils).sum(axis=-1), len(ECARTS) - 1)]


def tirer_scores(grille, generateur, nb=1):
    """`nb` scores tirés au sort dans une grille (MAX_BUTS + 1) × (MAX_BUTS + 1) : (buts dom, buts ext)."""
    cases = generateur.choice(grille.size, size=nb, p=grille.ravel() / grille.sum())
    return np.divmod(cases, MAX_BUTS + 1)
