"""Télécharge les résultats des championnats suivis et les enregistre dans data/.

Source : football-data.co.uk, mis à jour en général le lundi, après les
matchs du week-end.
"""

import time
from pathlib import Path

import pandas as pd

from .championnats import CHAMPIONNATS

SAISONS = ["2122", "2223", "2324", "2425", "2526", "2627"]
URL = "https://football-data.co.uk/mmz4281/{saison}/{championnat}.csv"
COLONNES = ["Championnat", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HS", "AS", "HST", "AST"]
DOSSIER_DATA = Path(__file__).resolve().parents[2] / "data"
FICHIER = DOSSIER_DATA / "resultats.csv"


def telecharger_saison(saison, championnat="F1"):
    """Renvoie les matchs d'une saison d'un championnat, avec les colonnes utiles."""
    df = pd.read_csv(URL.format(saison=saison, championnat=championnat), encoding="latin-1")
    df = df.dropna(subset=["HomeTeam", "FTR"])
    df = df.reindex(columns=COLONNES[1:])
    df.insert(0, "Championnat", championnat)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Saison"] = int(saison)
    return df


def enregistrer(matchs):
    DOSSIER_DATA.mkdir(exist_ok=True)
    # Tri stable : l'ordre des matchs d'un même jour reste celui de la source
    matchs = matchs.sort_values(["Championnat", "Saison", "Date"], kind="stable")
    entiers = ["FTHG", "FTAG", "HS", "AS", "HST", "AST"]
    matchs[entiers] = matchs[entiers].astype("Int64")
    matchs.to_csv(FICHIER, index=False, date_format="%Y-%m-%d")


def main():
    """Télécharge tout : chaque championnat, chaque saison."""
    liste = []
    for code, championnat in CHAMPIONNATS.items():
        for saison in SAISONS:
            df = telecharger_saison(saison, code)
            print(f"{championnat.nom:<15} {saison} : {len(df)} matchs")
            liste.append(df)
    matchs = pd.concat(liste, ignore_index=True)
    enregistrer(matchs)
    print(f"Total : {len(matchs)} matchs enregistrés")


def mettre_a_jour():
    """Ne retélécharge que la saison en cours, beaucoup plus rapide que main().

    Renvoie le nombre de nouveaux matchs.
    """
    if not FICHIER.exists():
        main()
        return None
    anciens = pd.read_csv(FICHIER, parse_dates=["Date"])
    saison = int(SAISONS[-1])
    frais = pd.concat([telecharger_saison(SAISONS[-1], code) for code in CHAMPIONNATS],
                      ignore_index=True)
    gardes = anciens[anciens["Saison"] != saison]
    nouveaux = len(frais) - (anciens["Saison"] == saison).sum()
    enregistrer(pd.concat([gardes, frais], ignore_index=True))
    return int(nouveaux)


def heures_depuis_mise_a_jour():
    """Âge du fichier de résultats, en heures (infini s'il n'existe pas)."""
    if not FICHIER.exists():
        return float("inf")
    return (time.time() - FICHIER.stat().st_mtime) / 3600


def main_mise_a_jour():
    nouveaux = mettre_a_jour()
    matchs = pd.read_csv(FICHIER, parse_dates=["Date"])
    en_cours = matchs[matchs["Saison"] == int(SAISONS[-1])]
    print(f"{nouveaux} nouveaux matchs." if nouveaux is not None else "Fichier créé.")
    for code, groupe in en_cours.groupby("Championnat"):
        print(f"  {CHAMPIONNATS[code].nom:<15} {len(groupe):>4} matchs, dernier le {groupe['Date'].max():%d/%m/%Y}")


if __name__ == "__main__":
    main()
