"""Télécharge les résultats des championnats suivis et les enregistre dans data/.

Source : football-data.co.uk, mis à jour en général le lundi, après les
matchs du week-end. La même source publie en milieu de semaine les matchs
de la prochaine journée, avec les cotes des bookmakers (data/prochains_matchs.csv).
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
URL_PROCHAINS = "https://www.football-data.co.uk/fixtures.csv"
FICHIER_PROCHAINS = DOSSIER_DATA / "prochains_matchs.csv"
# Cotes moyennes du marché (Avg…), à défaut celles de Bet365 (B365…)
SOURCES_COTES = ["Avg", "B365"]


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
    try:
        telecharger_prochains_matchs()
    except Exception as erreur:  # les résultats comptent plus que le calendrier : on continue
        print(f"Prochains matchs indisponibles ({erreur.__class__.__name__}).")
    return int(nouveaux)


def telecharger_prochains_matchs():
    """Enregistre les matchs annoncés de la prochaine journée, avec leurs cotes ; renvoie leur nombre."""
    df = pd.read_csv(URL_PROCHAINS, encoding="utf-8-sig")
    df = df[df["Div"].isin(list(CHAMPIONNATS))].dropna(subset=["HomeTeam", "AwayTeam"])
    prochains = pd.DataFrame({
        "Championnat": df["Div"],
        "Date": pd.to_datetime(df["Date"], dayfirst=True),
        "Heure": df["Time"],
        "HomeTeam": df["HomeTeam"],
        "AwayTeam": df["AwayTeam"],
    })
    for issue in "HDA":
        cotes = [df[f"{source}{issue}"] for source in SOURCES_COTES if f"{source}{issue}" in df]
        prochains[f"Cote{issue}"] = pd.concat(cotes, axis=1).bfill(axis=1).iloc[:, 0] if cotes else float("nan")
    DOSSIER_DATA.mkdir(exist_ok=True)
    prochains.sort_values(["Championnat", "Date", "Heure"], kind="stable").to_csv(
        FICHIER_PROCHAINS, index=False, date_format="%Y-%m-%d")
    return len(prochains)


def charger_prochains_matchs(championnat, matchs_saison):
    """Prochains matchs d'un championnat qui n'ont pas encore été joués (vide si rien n'est annoncé)."""
    if not FICHIER_PROCHAINS.exists():
        return pd.DataFrame(columns=["Championnat", "Date", "Heure", "HomeTeam", "AwayTeam",
                                     "CoteH", "CoteD", "CoteA"])
    prochains = pd.read_csv(FICHIER_PROCHAINS, parse_dates=["Date"])
    prochains = prochains[prochains["Championnat"] == championnat]
    # Le fichier de la source peut encore lister des matchs du week-end passé
    jouees = set(zip(matchs_saison["HomeTeam"], matchs_saison["AwayTeam"]))
    a_venir = [(d, e) not in jouees for d, e in zip(prochains["HomeTeam"], prochains["AwayTeam"])]
    return prochains[a_venir].reset_index(drop=True)


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
