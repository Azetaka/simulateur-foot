"""Tests des briques du simulateur, sur de petites données construites à la main."""

import numpy as np
import pandas as pd
import pytest

from simulateur_foot.force_clubs import NOTE_INITIALE, calculer_forces, score_attendu
from simulateur_foot.modele import pertes_brier, pertes_log
from simulateur_foot.simulation import classement, matchs_restants, resume, simuler
from simulateur_foot.variables import ajouter_variables, table_par_club


def matchs_exemple():
    """Une mini-saison de trois clubs, puis une deuxième avec un promu."""
    return pd.DataFrame({
        "Date": pd.to_datetime(["2023-08-01", "2023-08-08", "2023-08-15",
                                "2024-08-01", "2024-08-08"]),
        "HomeTeam": ["A", "B", "C", "A", "D"],
        "AwayTeam": ["B", "C", "A", "B", "A"],
        "FTHG": [2, 0, 1, 1, 0],
        "FTAG": [0, 0, 3, 1, 2],
        "FTR": ["H", "D", "A", "D", "A"],
        "HST": [5, 2, 3, 4, 1],
        "AST": [1, 2, 6, 4, 5],
        "Saison": [2324, 2324, 2324, 2425, 2425],
    })


def test_score_attendu_symetrique_sans_avantage():
    assert score_attendu(1500, 1500, avantage_terrain=0) == pytest.approx(0.5)
    assert score_attendu(1600, 1500, 0) + score_attendu(1500, 1600, 0) == pytest.approx(1)


def test_elo_somme_nulle_et_notes_avant_match():
    matchs, notes = calculer_forces(matchs_exemple())
    # Premier match : tout le monde part de la note initiale
    assert matchs.loc[0, ["force_dom", "force_ext"]].tolist() == [NOTE_INITIALE] * 2
    # A gagne le premier match : sa note d'avant le match suivant a monté
    assert matchs.loc[2, "force_ext"] > NOTE_INITIALE
    # D n'était pas là la saison d'avant : c'est un promu
    assert matchs.loc[4, "promu_dom"] == 1 and matchs.loc[4, "promu_ext"] == 0
    assert set(notes) == {"A", "B", "D"}


def test_forme_ne_voit_pas_le_match_lui_meme():
    par_club = ajouter_variables(table_par_club(matchs_exemple()))
    a = par_club[(par_club["club"] == "A") & (par_club["Saison"] == 2324)]
    # Premier match de la saison : aucune forme connue
    assert np.isnan(a["points_5"].iloc[0])
    # Deuxième match : seulement la victoire du premier
    assert a["points_5"].iloc[1] == 3


def test_pertes():
    proba = pd.DataFrame({"A": [0.2, 0.5], "D": [0.3, 0.25], "H": [0.5, 0.25]})
    resultats = pd.Series(["H", "A"])
    assert pertes_log(proba, resultats).tolist() == pytest.approx([-np.log(0.5)] * 2)
    assert pertes_brier(proba, resultats).iloc[0] == pytest.approx(0.04 + 0.09 + 0.25)


def test_matchs_restants_et_classement():
    saison = matchs_exemple().query("Saison == 2324")
    restants = matchs_restants(saison)
    # 3 clubs → 6 affiches aller-retour, 3 déjà jouées
    assert len(restants) == 3
    assert ("A", "B") not in set(zip(restants["HomeTeam"], restants["AwayTeam"]))
    table = classement(saison)
    assert table.loc["A", "points"] == 6 and table.loc["A", "diff_buts"] == 4


def test_simulation_respecte_les_probabilites():
    saison = matchs_exemple().query("Saison == 2324")
    table = classement(saison)
    restants = matchs_restants(saison)
    # Le club à domicile gagne toujours
    proba = pd.DataFrame({"A": [0.0] * 3, "D": [0.0] * 3, "H": [1.0] * 3})
    points, rangs = simuler(table, restants, proba, nb=50)
    attendu = table["points"] + restants["HomeTeam"].value_counts().reindex(table.index).fillna(0) * 3
    assert (points == attendu.to_numpy()).all()
    synthese = resume(table, points, rangs)
    assert synthese["titre"].sum() == pytest.approx(1)
    assert sorted(rangs[0]) == [1, 2, 3]
