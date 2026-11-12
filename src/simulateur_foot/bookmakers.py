"""Compare le modèle retenu aux bookmakers sur la saison test, pour les six championnats.

Les cotes moyennes du marché (colonnes AvgH, AvgD, AvgA de football-data.co.uk) sont
converties en chances, marge retirée. C'est la référence la plus exigeante : les
bookmakers connaissent les blessures, les compositions et les transferts, pas le modèle.

Lancement : uv run simulateur-foot bookmakers (télécharge les cotes de la saison test)
"""

import numpy as np
import pandas as pd

from .championnats import CHAMPIONNATS
from .collecte_resultats import URL
from .modele import (RESULTATS, SAISON_TEST, SAISONS_ENTRAINEMENT, pertes_log, proba_frequences,
                     proba_logistique_forces, selection)
from .prediction import chances_bookmakers, charger_forces

COTES = ["AvgH", "AvgD", "AvgA"]


def telecharger_cotes(code, saison=SAISON_TEST):
    """Cotes moyennes du marché pour chaque match d'une saison."""
    df = pd.read_csv(URL.format(saison=saison, championnat=code), encoding="utf-8-sig", encoding_errors="replace")
    return df.dropna(subset=COTES)[["HomeTeam", "AwayTeam"] + COTES]


def precision(proba, resultats):
    """Part des matchs où l'issue jugée la plus probable est la bonne."""
    return float((proba.to_numpy().argmax(axis=1) == proba.columns.get_indexer(resultats)).mean())


def comparer(test, proba_modele, proba_reference, cotes):
    """Précision et log-loss du modèle, de la référence et des bookmakers sur les mêmes matchs.

    Seuls les matchs qui ont des cotes sont comptés, pour que la comparaison soit équitable.
    """
    avec_cotes = test[["HomeTeam", "AwayTeam", "FTR"]].reset_index(drop=True).merge(
        cotes, on=["HomeTeam", "AwayTeam"], how="left")
    garde = avec_cotes[COTES].notna().all(axis=1).to_numpy()
    marche = chances_bookmakers(avec_cotes.loc[garde, "AvgH"], avec_cotes.loc[garde, "AvgD"],
                                avec_cotes.loc[garde, "AvgA"])
    resultats = avec_cotes.loc[garde, "FTR"].reset_index(drop=True)
    lignes = {}
    for nom, proba in [("reference", proba_reference[garde]), ("modele", proba_modele[garde]), ("bookmakers", marche)]:
        proba = proba.reset_index(drop=True)
        lignes[nom] = {"precision": precision(proba, resultats),
                       "log_loss": float(pertes_log(proba, resultats).mean())}
    return {"matchs": int(garde.sum()), **lignes}


def comparer_championnat(code, cotes=None):
    matchs, _ = charger_forces(code)
    entrainement, test = selection(matchs, SAISONS_ENTRAINEMENT), selection(matchs, [SAISON_TEST])
    cotes = telecharger_cotes(code) if cotes is None else cotes
    return comparer(test, proba_logistique_forces(entrainement, test), proba_frequences(entrainement, test), cotes)


def main():
    print(f"Saison test {SAISON_TEST} : bons pronostics et log-loss (plus bas = mieux)\n")
    print(f"{'':16}{'matchs':>7}{'fréquences':>20}{'modèle':>18}{'bookmakers':>18}")
    bilans = {code: comparer_championnat(code) for code in CHAMPIONNATS}
    for code, bilan in bilans.items():
        colonnes = "".join(f"{bilan[nom]['precision']:>10.1%} {bilan[nom]['log_loss']:>7.3f}"
                           for nom in ["reference", "modele", "bookmakers"])
        print(f"{CHAMPIONNATS[code].nom:<16}{bilan['matchs']:>7}{colonnes}")
    poids = np.array([bilan["matchs"] for bilan in bilans.values()])
    moyennes = "".join(
        f"{np.average([b[nom]['precision'] for b in bilans.values()], weights=poids):>10.1%} "
        f"{np.average([b[nom]['log_loss'] for b in bilans.values()], weights=poids):>7.3f}"
        for nom in ["reference", "modele", "bookmakers"])
    print(f"{'Ensemble':<16}{poids.sum():>7}{moyennes}")


if __name__ == "__main__":
    main()
