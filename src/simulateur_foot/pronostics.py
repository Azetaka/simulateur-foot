"""Suivi des pronostics : ce que le modèle annonçait avant chaque match, puis ce qui s'est passé.

La saison test de RAPPORT.md est une saison passée. Ici, on garde chaque semaine les chances
annoncées pour les matchs à venir, avant qu'ils soient joués :
c'est la seule mesure où le modèle ne peut pas avoir « vu » le résultat.

Un pronostic déjà enregistré n'est jamais réécrit : on garde la première annonce.

Lancement : uv run simulateur-foot pronostics (enregistre, puis affiche le bilan)
"""

import numpy as np
import pandas as pd

from .championnats import CHAMPIONNATS
from .collecte_resultats import DOSSIER_DATA, FICHIER, charger_prochains_matchs
from .modele import RESULTATS
from .prediction import (
    SAISON_EN_COURS,
    charger_forces,
    entrainer,
    probabilites,
)

FICHIER_PRONOSTICS = DOSSIER_DATA / "pronostics.csv"
CLES = ["Championnat", "Saison", "HomeTeam", "AwayTeam"]
COLONNES = CLES + ["Date", "enregistre_le"] + RESULTATS


def charger():
    if not FICHIER_PRONOSTICS.exists():
        return pd.DataFrame(columns=COLONNES)
    return pd.read_csv(FICHIER_PRONOSTICS, parse_dates=["Date", "enregistre_le"])


def pronostics_du_jour(code, aujourd_hui=None):
    """Chances du modèle, avec les notes du jour, pour les matchs annoncés d'un championnat."""
    matchs, notes = charger_forces(code)
    prochains = charger_prochains_matchs(code, matchs[matchs["Saison"] == SAISON_EN_COURS])
    prochains = prochains[prochains["HomeTeam"].isin(notes.keys()) & prochains["AwayTeam"].isin(notes.keys())]
    prochains = prochains.reset_index(drop=True)
    if prochains.empty:
        return pd.DataFrame(columns=COLONNES)
    modele = probabilites(entrainer(matchs), prochains["HomeTeam"].map(notes).to_numpy(),
                          prochains["AwayTeam"].map(notes).to_numpy())
    lignes = prochains[["Championnat", "HomeTeam", "AwayTeam", "Date"]].copy()
    lignes["Saison"] = SAISON_EN_COURS
    lignes["enregistre_le"] = pd.Timestamp(aujourd_hui or pd.Timestamp.now()).normalize()
    lignes[RESULTATS] = modele.round(4).to_numpy()
    return lignes[COLONNES]


def enregistrer(aujourd_hui=None):
    """Ajoute au fichier les pronostics des matchs annoncés qui n'y sont pas encore ; renvoie leur nombre."""
    anciens = charger()
    nouveaux = pd.concat([pronostics_du_jour(code, aujourd_hui) for code in CHAMPIONNATS], ignore_index=True)

    def cle(table):  # une chaîne par match ; liste construite à la main car agg échoue sur un tableau vide
        return ["|".join(ligne) for ligne in table[CLES].astype(str).to_numpy()]

    inedits = nouveaux[~pd.Series(cle(nouveaux), index=nouveaux.index).isin(cle(anciens))]
    if len(inedits):
        tout = inedits if anciens.empty else pd.concat([anciens, inedits], ignore_index=True)
        DOSSIER_DATA.mkdir(exist_ok=True)
        tout[COLONNES].sort_values(["Date", "Championnat", "HomeTeam"], kind="stable").to_csv(
            FICHIER_PRONOSTICS, index=False, date_format="%Y-%m-%d")
    return len(inedits)


def avec_resultats(pronostics=None, resultats=None):
    """Les pronostics dont le match a été joué, avec son résultat (FTR)."""
    pronostics = charger() if pronostics is None else pronostics
    resultats = pd.read_csv(FICHIER) if resultats is None else resultats
    joues = pronostics.merge(resultats[CLES + ["FTR"]], on=CLES, how="inner")
    return joues.dropna(subset=["FTR"]).reset_index(drop=True)


def bilan(joues, championnat=None):
    """Nombre de matchs suivis, part de bons pronostics et log-loss du modèle.

    Renvoie None tant qu'aucun match suivi n'a été joué.
    """
    if championnat is not None:
        joues = joues[joues["Championnat"] == championnat]
    if joues.empty:
        return None
    reel = pd.Index(RESULTATS).get_indexer(joues["FTR"])
    proba = joues[RESULTATS].to_numpy(dtype=float)
    return {"matchs": len(joues), "depuis": joues["Date"].min(),
            "precision": float((proba.argmax(axis=1) == reel).mean()),
            "log_loss": float(-np.log(np.clip(proba[np.arange(len(reel)), reel], 1e-12, None)).mean())}


def main():
    print(f"{enregistrer()} nouveaux pronostics enregistrés dans {FICHIER_PRONOSTICS}")
    resultat = bilan(avec_resultats())
    if resultat is None:
        print("Aucun match suivi n'a encore été joué.")
        return
    print(f"Matchs suivis et joués : {resultat['matchs']} (depuis le {resultat['depuis']:%d/%m/%Y}) : "
          f"{resultat['precision']:.1%} de bons pronostics, log-loss {resultat['log_loss']:.3f}")


if __name__ == "__main__":
    main()
