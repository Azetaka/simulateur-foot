"""Construit la table des matchs avec toutes les variables d'avant-match."""

import pandas as pd

from force_clubs import DOSSIER_DATA, calculer_forces, charger_matchs

FENETRE = 5
POINTS = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}
VARIABLES = ["points_5", "buts_pour_5", "buts_contre_5",
             "tirs_cadres_pour_5", "tirs_cadres_contre_5", "repos"]


def table_par_club(matchs):
    """Une ligne par club et par match, au lieu d'une ligne par match."""
    dom = pd.DataFrame({
        "id_match": matchs.index,
        "Saison": matchs["Saison"],
        "Date": matchs["Date"],
        "club": matchs["HomeTeam"],
        "lieu": "dom",
        "points": matchs["FTR"].map(lambda r: POINTS[r][0]),
        "buts_pour": matchs["FTHG"],
        "buts_contre": matchs["FTAG"],
        "tirs_cadres_pour": matchs["HST"],
        "tirs_cadres_contre": matchs["AST"],
    })
    ext = pd.DataFrame({
        "id_match": matchs.index,
        "Saison": matchs["Saison"],
        "Date": matchs["Date"],
        "club": matchs["AwayTeam"],
        "lieu": "ext",
        "points": matchs["FTR"].map(lambda r: POINTS[r][1]),
        "buts_pour": matchs["FTAG"],
        "buts_contre": matchs["FTHG"],
        "tirs_cadres_pour": matchs["AST"],
        "tirs_cadres_contre": matchs["HST"],
    })
    return pd.concat([dom, ext]).sort_values(["club", "Date"]).reset_index(drop=True)


def ajouter_variables(par_club):
    """Moyennes sur les cinq matchs précédents de la saison, et jours de repos."""
    groupes = par_club.groupby(["club", "Saison"])
    for colonne in ["points", "buts_pour", "buts_contre", "tirs_cadres_pour", "tirs_cadres_contre"]:
        # shift(1) : on ne regarde que les matchs précédents, jamais le match lui-même
        par_club[f"{colonne}_5"] = groupes[colonne].transform(
            lambda s: s.shift(1).rolling(FENETRE, min_periods=1).mean()
        )
    par_club["repos"] = groupes["Date"].diff().dt.days
    return par_club


def main():
    matchs, _ = calculer_forces(charger_matchs())
    par_club = ajouter_variables(table_par_club(matchs))

    # Retour à une ligne par match, avec les variables des deux équipes
    for lieu in ["dom", "ext"]:
        cote = par_club[par_club["lieu"] == lieu].set_index("id_match")[VARIABLES]
        matchs = matchs.join(cote.add_suffix(f"_{lieu}"))

    matchs.to_csv(DOSSIER_DATA / "matchs_variables.csv", index=False)
    print(f"{len(matchs)} matchs, {matchs.shape[1]} colonnes")


if __name__ == "__main__":
    main()