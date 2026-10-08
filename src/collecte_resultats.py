"""Télécharge les résultats de Ligue 1 saison par saison et les enregistre dans data/."""

from pathlib import Path

import pandas as pd

SAISONS = ["2122", "2223", "2324", "2425", "2526", "2627"]
URL = "https://www.football-data.co.uk/mmz4281/{saison}/F1.csv"
COLONNES = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HS", "AS", "HST", "AST"]
DOSSIER_DATA = Path(__file__).resolve().parents[1] / "data"

def telecharger_saison(saison):
    """Renvoie les matchs d'une saison, avec les colonnes utiles."""
    df = pd.read_csv(URL.format(saison=saison))
    df = df.dropna(subset=["HomeTeam"])
    df = df.reindex(columns=COLONNES)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["Saison"] = saison
    return df

def main():
    liste = []
    for saison in SAISONS:
        df = telecharger_saison(saison)
        print(f"Saison {saison} : {len(df)} matchs")
        liste.append(df)

    matchs = pd.concat(liste, ignore_index=True)
    DOSSIER_DATA.mkdir(exist_ok=True)
    matchs.to_csv(DOSSIER_DATA / "resultats_ligue1.csv", index=False)
    print(f"Total : {len(matchs)} matchs enregistrés")

if __name__ == "__main__":
    main()