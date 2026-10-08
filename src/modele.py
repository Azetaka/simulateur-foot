"""Prédit le résultat d'un match (H, D ou A) à partir des variables d'avant-match."""

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


def main():
    matchs = charger_donnees()
    print(f"{len(matchs)} matchs, {len(VARIABLES_MODELE)} variables")
    print("Valeurs manquantes par variable :")
    print(matchs[VARIABLES_MODELE].isna().sum().to_string())


if __name__ == "__main__":
    main()
