"""Suivi des pronostics : ce que le modèle annonçait avant chaque match, puis ce qui s'est passé.

La saison test de RAPPORT.md est une saison passée. Ici, on garde chaque semaine les chances
annoncées pour les matchs à venir (et celles des bookmakers), avant qu'ils soient joués :
c'est la seule mesure où le modèle ne peut pas avoir « vu » le résultat.

Un pronostic déjà enregistré n'est jamais réécrit : on garde la première annonce.

Lancement : uv run simulateur-foot pronostics (enregistre, puis affiche le bilan)
"""

import numpy as np
import pandas as pd

from .championnats import CHAMPIONNATS
from .collecte_resultats import DOSSIER_DATA, FICHIER, charger_prochains_matchs
from .modele import RESULTATS
from .prediction import SAISON_EN_COURS, chances_bookmakers, charger_forces, entrainer, probabilites

FICHIER_PRONOSTICS = DOSSIER_DATA / "pronostics.csv"
CLES = ["Championnat", "Saison", "HomeTeam", "AwayTeam"]
MARCHE = [f"marche_{r}" for r in RESULTATS]
COLONNES = CLES + ["Date", "enregistre_le"] + RESULTATS + MARCHE


def charger():
    if not FICHIER_PRONOSTICS.exists():
        return pd.DataFrame(columns=COLONNES)
    return pd.read_csv(FICHIER_PRONOSTICS, parse_dates=["Date", "enregistre_le"])


def pronostics_du_jour(code, aujourd_hui=None):
    """Chances du modèle (notes du jour) et des bookmakers pour les matchs annoncés d'un championnat."""
    matchs, notes = charger_forces(code)
    prochains = charger_prochains_matchs(code, matchs[matchs["Saison"] == SAISON_EN_COURS])
    prochains = prochains[prochains["HomeTeam"].isin(notes.keys()) & prochains["AwayTeam"].isin(notes.keys())]
    prochains = prochains.reset_index(drop=True)
    if prochains.empty:
        return pd.DataFrame(columns=COLONNES)
    modele = probabilites(entrainer(matchs), prochains["HomeTeam"].map(notes).to_numpy(),
                          prochains["AwayTeam"].map(notes).to_numpy())
    marche = chances_bookmakers(prochains["CoteH"], prochains["CoteD"], prochains["CoteA"])
    lignes = prochains[["Championnat", "HomeTeam", "AwayTeam", "Date"]].copy()
    lignes["Saison"] = SAISON_EN_COURS
    lignes["enregistre_le"] = pd.Timestamp(aujourd_hui or pd.Timestamp.now()).normalize()
    lignes[RESULTATS] = modele.round(4).to_numpy()
    lignes[MARCHE] = marche.round(4).to_numpy()
    return lignes[COLONNES]


def enregistrer(aujourd_hui=None):
    """Ajoute au fichier les pronostics des matchs annoncés qui n'y sont pas encore ; renvoie leur nombre."""
    anciens = charger()
    nouveaux = pd.concat([pronostics_du_jour(code, aujourd_hui) for code in CHAMPIONNATS], ignore_index=True)
    deja = set(map(tuple, anciens[CLES].astype(str).to_numpy()))
    inedits = nouveaux[[tuple(ligne) not in deja for ligne in nouveaux[CLES].astype(str).to_numpy()]]
    if len(inedits):
        tout = inedits if anciens.empty else pd.concat([anciens, inedits], ignore_index=True)
        DOSSIER_DATA.mkdir(exist_ok=True)
        tout.sort_values(["Date", "Championnat", "HomeTeam"], kind="stable").to_csv(
            FICHIER_PRONOSTICS, index=False, date_format="%Y-%m-%d")
    return len(inedits)


def avec_resultats(pronostics=None, resultats=None):
    """Les pronostics dont le match a été joué, avec son résultat (FTR)."""
    pronostics = charger() if pronostics is None else pronostics
    resultats = pd.read_csv(FICHIER) if resultats is None else resultats
    joues = pronostics.merge(resultats[CLES + ["FTR"]], on=CLES, how="inner")
    return joues.dropna(subset=["FTR"]).reset_index(drop=True)


def bilan(joues, championnat=None):
    """Nombre de matchs suivis, bons pronostics et log-loss du modèle et des bookmakers.

    Renvoie None tant qu'aucun match suivi n'a été joué. Les bookmakers ne sont comptés que
    sur les matchs qui avaient des cotes.
    """
    if championnat is not None:
        joues = joues[joues["Championnat"] == championnat]
    if joues.empty:
        return None
    reel = pd.Index(RESULTATS).get_indexer(joues["FTR"])

    def mesures(proba):
        garde = ~np.isnan(proba).any(axis=1)
        if not garde.any():
            return None
        p, r = proba[garde], reel[garde]
        return {"matchs": int(garde.sum()), "precision": float((p.argmax(axis=1) == r).mean()),
                "log_loss": float(-np.log(np.clip(p[np.arange(len(r)), r], 1e-12, None)).mean())}

    return {"matchs": len(joues), "depuis": joues["Date"].min(),
            "modele": mesures(joues[RESULTATS].to_numpy(dtype=float)),
            "bookmakers": mesures(joues[MARCHE].to_numpy(dtype=float))}


def main():
    print(f"{enregistrer()} nouveaux pronostics enregistrés dans {FICHIER_PRONOSTICS}")
    resultat = bilan(avec_resultats())
    if resultat is None:
        print("Aucun match suivi n'a encore été joué.")
        return
    print(f"Matchs suivis et joués : {resultat['matchs']} (depuis le {resultat['depuis']:%d/%m/%Y})")
    for nom in ["modele", "bookmakers"]:
        if resultat[nom]:
            print(f"  {nom:<11} {resultat[nom]['precision']:.1%} de bons pronostics, "
                  f"log-loss {resultat[nom]['log_loss']:.3f} ({resultat[nom]['matchs']} matchs)")


if __name__ == "__main__":
    main()
