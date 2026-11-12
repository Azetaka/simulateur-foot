"""Comparaison aux bookmakers et suivi des pronostics (sans réseau)."""

import numpy as np
import pandas as pd
import pytest

from simulateur_foot import bookmakers, collecte_resultats, pronostics
from simulateur_foot.modele import RESULTATS
from simulateur_foot.prediction import SAISON_EN_COURS, charger_forces
from simulateur_foot.simulation import matchs_restants


def proba(lignes):
    return pd.DataFrame(lignes, columns=RESULTATS)  # ordre A, D, H


def test_comparaison_aux_bookmakers():
    test = pd.DataFrame({"HomeTeam": ["A", "B", "C"], "AwayTeam": ["B", "C", "A"], "FTR": ["H", "A", "D"]})
    modele = proba([[0.2, 0.2, 0.6], [0.5, 0.3, 0.2], [0.6, 0.3, 0.1]])  # juste, juste, faux
    reference = proba([[0.3, 0.3, 0.4]] * 3)
    cotes = pd.DataFrame({"HomeTeam": ["A", "B"], "AwayTeam": ["B", "C"],  # pas de cotes pour C-A
                          "AvgH": [1.5, 4.0], "AvgD": [4.0, 3.5], "AvgA": [6.0, 1.9]})
    bilan = bookmakers.comparer(test, modele, reference, cotes)
    assert bilan["matchs"] == 2  # le match sans cotes est écarté pour tout le monde
    assert bilan["modele"]["precision"] == 1.0
    assert bilan["bookmakers"]["precision"] == 1.0
    assert bilan["reference"]["precision"] == 0.5
    assert bilan["modele"]["log_loss"] == pytest.approx(-(np.log(0.6) + np.log(0.5)) / 2)
    assert bilan["bookmakers"]["log_loss"] < bilan["reference"]["log_loss"]


@pytest.fixture
def journee_fictive(tmp_path, monkeypatch):
    """Deux affiches de Ligue 1 pas encore jouées, avec des cotes, et un fichier de pronostics vide."""
    matchs, _ = charger_forces("F1")
    restants = matchs_restants(matchs[matchs["Saison"] == SAISON_EN_COURS]).head(2)
    fichier = tmp_path / "prochains_matchs.csv"
    restants.assign(Championnat="F1", Date="2099-01-01", Heure="21:00", CoteH=2.1, CoteD=3.4,
                    CoteA=3.5).to_csv(fichier, index=False)
    monkeypatch.setattr(collecte_resultats, "FICHIER_PROCHAINS", fichier)
    monkeypatch.setattr(pronostics, "FICHIER_PRONOSTICS", tmp_path / "pronostics.csv")
    return restants


def test_pronostics_enregistres_une_seule_fois(journee_fictive):
    assert pronostics.enregistrer("2098-12-30") == 2
    premiers = pronostics.charger()
    assert len(premiers) == 2
    assert np.allclose(premiers[RESULTATS].sum(axis=1), 1, atol=1e-3)
    assert np.allclose(premiers[pronostics.MARCHE].sum(axis=1), 1, atol=1e-3)
    # Relancé plus tard : rien de nouveau, et la première annonce n'est pas réécrite
    assert pronostics.enregistrer("2098-12-31") == 0
    assert (pronostics.charger()["enregistre_le"] == pd.Timestamp("2098-12-30")).all()


def test_bilan_des_pronostics(journee_fictive):
    pronostics.enregistrer("2098-12-30")
    suivis = pronostics.charger()
    assert pronostics.bilan(pronostics.avec_resultats(suivis, pd.DataFrame(columns=pronostics.CLES + ["FTR"]))) is None

    # Les deux matchs sont joués : victoire à domicile, puis nul
    resultats = suivis[pronostics.CLES].assign(FTR=["H", "D"])
    joues = pronostics.avec_resultats(suivis, resultats)
    bilan = pronostics.bilan(joues)
    assert bilan["matchs"] == 2
    attendu = -(np.log(joues.loc[0, "H"]) + np.log(joues.loc[1, "D"])) / 2
    assert bilan["modele"]["log_loss"] == pytest.approx(attendu)
    assert bilan["bookmakers"]["matchs"] == 2
    assert 0 <= bilan["modele"]["precision"] <= 1
    assert pronostics.bilan(joues, championnat="E0") is None


def test_bilan_sans_cotes():
    joues = pd.DataFrame({"Championnat": ["F1"], "Saison": [SAISON_EN_COURS], "HomeTeam": ["A"], "AwayTeam": ["B"],
                          "Date": [pd.Timestamp("2026-01-01")], "A": [0.2], "D": [0.3], "H": [0.5],
                          "marche_A": [np.nan], "marche_D": [np.nan], "marche_H": [np.nan], "FTR": ["H"]})
    bilan = pronostics.bilan(joues)
    assert bilan["modele"]["precision"] == 1.0
    assert bilan["bookmakers"] is None


def test_prochains_matchs_d_un_championnat_sans_annonce(journee_fictive):
    """Le fichier ne contient que de la Ligue 1 : un autre championnat renvoie un tableau vide, colonnes comprises."""
    matchs, _ = charger_forces("E0")
    vide = collecte_resultats.charger_prochains_matchs("E0", matchs[matchs["Saison"] == SAISON_EN_COURS])
    assert vide.empty and "HomeTeam" in vide.columns
