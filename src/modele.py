"""Prédit le résultat d'un match (H, D ou A) à partir des variables d'avant-match."""

from itertools import product

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

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
TIRAGES_BOOTSTRAP = 2000


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


def pertes_brier(proba, resultats):
    """Score de Brier de chaque match : somme sur H, D, A de (probabilité - réalité)²."""
    realite = pd.get_dummies(resultats).reindex(columns=RESULTATS, fill_value=0).astype(float)
    return ((proba - realite.to_numpy()) ** 2).sum(axis=1)


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


def proba_frequences(entrainement, matchs):
    """Référence 1 : les fréquences de H, D et A sur l'entraînement, pour chaque match."""
    frequences = entrainement["FTR"].value_counts(normalize=True).reindex(RESULTATS)
    return pd.DataFrame([frequences.to_numpy()] * len(matchs), columns=RESULTATS, index=matchs.index)


def proba_logistique_forces(entrainement, matchs):
    """Référence 2 : régression logistique multinomiale sur force_dom et force_ext."""
    modele = LogisticRegression().fit(entrainement[FORCES], entrainement["FTR"])
    return probabilites(modele, matchs, FORCES)


def proba_boosting(colonnes, parametres):
    """Fonction de prédiction du gradient boosting, pour des colonnes et paramètres fixés."""
    def predire(entrainement, matchs):
        modele = creer_modele(**parametres).fit(entrainement[colonnes], entrainement["FTR"])
        return probabilites(modele, matchs, colonnes)
    return predire


def evaluer(predire, matchs):
    """Log-loss de validation, puis pertes par match (log-loss, Brier) sur la saison test."""
    validation = []
    for saisons_app, saisons_val in PLIS_VALIDATION:
        val = selection(matchs, saisons_val)
        proba = predire(selection(matchs, saisons_app), val)
        validation.append(pertes_log(proba, val["FTR"]).mean())
    test = selection(matchs, [SAISON_TEST])
    proba = predire(selection(matchs, SAISONS_ENTRAINEMENT), test)
    return np.mean(validation), pertes_log(proba, test["FTR"]), pertes_brier(proba, test["FTR"])


def intervalle_bootstrap(ecarts, graine=0):
    """Intervalle à 95 % de l'écart moyen, par rééchantillonnage des matchs test."""
    generateur = np.random.default_rng(graine)
    tirages = generateur.integers(0, len(ecarts), size=(TIRAGES_BOOTSTRAP, len(ecarts)))
    moyennes = ecarts.to_numpy()[tirages].mean(axis=1)
    return np.percentile(moyennes, [2.5, 97.5])


def main():
    matchs = charger_donnees()
    entrainement = selection(matchs, SAISONS_ENTRAINEMENT)
    test = selection(matchs, [SAISON_TEST])
    print(f"Entraînement : {len(entrainement)} matchs, test : {len(test)} matchs")

    score_validation, parametres = regler_modele(matchs, VARIABLES_MODELE)
    print(f"Paramètres retenus (modèle complet) : {parametres}")
    _, parametres_forces = regler_modele(matchs, FORCES)
    print(f"Paramètres retenus (boosting sur les forces) : {parametres_forces}")

    candidats = {
        "Modèle complet (boosting, 16 variables)": proba_boosting(VARIABLES_MODELE, parametres),
        "Réf. 1 : fréquences moyennes": proba_frequences,
        "Réf. 2 : logistique sur les forces": proba_logistique_forces,
        "Complément : boosting sur les forces": proba_boosting(FORCES, parametres_forces),
    }
    evaluations = {nom: evaluer(predire, matchs) for nom, predire in candidats.items()}

    print(f"\n{'':42}{'validation':>12}{'log-loss':>10}{'Brier':>8}")
    for nom, (validation, log_test, brier_test) in evaluations.items():
        print(f"{nom:42}{validation:12.4f}{log_test.mean():10.4f}{brier_test.mean():8.4f}")

    # Écarts appariés match par match : négatif = le modèle complet fait mieux
    _, log_modele, brier_modele = evaluations["Modèle complet (boosting, 16 variables)"]
    print("\nÉcart modèle complet - référence sur la saison test [intervalle à 95 %] :")
    for nom, (_, log_ref, brier_ref) in list(evaluations.items())[1:]:
        ecart_log, ecart_brier = log_modele - log_ref, brier_modele - brier_ref
        bas_log, haut_log = intervalle_bootstrap(ecart_log)
        bas_brier, haut_brier = intervalle_bootstrap(ecart_brier)
        print(f"  {nom:40} log-loss {ecart_log.mean():+.4f} [{bas_log:+.4f} ; {haut_log:+.4f}]"
              f"   Brier {ecart_brier.mean():+.4f} [{bas_brier:+.4f} ; {haut_brier:+.4f}]")


if __name__ == "__main__":
    main()
