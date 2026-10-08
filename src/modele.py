"""Prédit le résultat d'un match (H, D ou A) à partir des variables d'avant-match."""

from itertools import product

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from force_clubs import DOSSIER_DATA
from variables import VARIABLES

FORCES = ["force_dom", "force_ext"]
PROMUS = ["promu_dom", "promu_ext"]
# Les six variables de forme et de repos, pour chacune des deux équipes
FORME = [f"{variable}_{lieu}" for lieu in ["dom", "ext"] for variable in VARIABLES]
VARIABLES_MODELE = FORCES + PROMUS + FORME
RESULTATS = ["A", "D", "H"]  # ordre alphabétique, celui des classes de scikit-learn

# 2122 sert de rodage aux notes Elo (tout le monde part à 1500), 2627 est en cours
SAISONS_ENTRAINEMENT = [2223, 2324, 2425]
SAISON_TEST = 2526
# Validation temporelle : on ne valide jamais sur une saison antérieure à l'entraînement
PLIS_VALIDATION = [([2223], [2324]), ([2223, 2324], [2425])]
GRILLE = {
    "learning_rate": [0.01, 0.02, 0.05],
    "max_depth": [1, 2, 3],
    "max_iter": [25, 50, 100, 200],
    "min_samples_leaf": [20, 50, 100],
}


def charger_donnees():
    """Lit la table des matchs produite par variables.py."""
    return pd.read_csv(DOSSIER_DATA / "matchs_variables.csv", parse_dates=["Date"])


def creer_modele(**parametres):
    """Gradient boosting sur histogrammes.

    Ce modèle accepte les valeurs manquantes sans imputation : à chaque
    coupure, les matchs sans valeur (premier match de la saison, pas de
    match précédent) sont envoyés du côté qui réduit le plus l'erreur.
    """
    return HistGradientBoostingClassifier(random_state=0, **parametres)


def probabilites(modele, matchs, colonnes):
    """Probabilités prédites, colonnes dans l'ordre de RESULTATS."""
    proba = modele.predict_proba(matchs[colonnes])
    return pd.DataFrame(proba, columns=modele.classes_, index=matchs.index)[RESULTATS]


def pertes_log(proba, resultats):
    """Log-loss de chaque match : moins le logarithme de la probabilité du résultat réel."""
    p_reel = proba.to_numpy()[np.arange(len(proba)), proba.columns.get_indexer(resultats)]
    return pd.Series(-np.log(p_reel), index=proba.index)


def selection(matchs, saisons):
    """Matchs des saisons demandées."""
    return matchs[matchs["Saison"].isin(saisons)]


def regler_modele(matchs, colonnes):
    """Choisit les paramètres de la grille par validation temporelle (log-loss moyenne)."""
    resultats = []
    for valeurs in product(*GRILLE.values()):
        parametres = dict(zip(GRILLE.keys(), valeurs))
        scores = []
        for saisons_app, saisons_val in PLIS_VALIDATION:
            app, val = selection(matchs, saisons_app), selection(matchs, saisons_val)
            modele = creer_modele(**parametres).fit(app[colonnes], app["FTR"])
            scores.append(pertes_log(probabilites(modele, val, colonnes), val["FTR"]).mean())
        resultats.append((np.mean(scores), parametres))
    return min(resultats, key=lambda x: x[0])


def main():
    matchs = charger_donnees()
    entrainement = selection(matchs, SAISONS_ENTRAINEMENT)
    test = selection(matchs, [SAISON_TEST])
    print(f"Entraînement : {len(entrainement)} matchs, test : {len(test)} matchs")

    score_validation, parametres = regler_modele(matchs, VARIABLES_MODELE)
    print(f"Paramètres retenus : {parametres} (log-loss de validation {score_validation:.4f})")

    modele = creer_modele(**parametres).fit(entrainement[VARIABLES_MODELE], entrainement["FTR"])
    proba = probabilites(modele, test, VARIABLES_MODELE)
    print(f"Log-loss sur la saison test : {pertes_log(proba, test['FTR']).mean():.4f}")


if __name__ == "__main__":
    main()
