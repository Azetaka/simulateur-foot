"""Suivi des pronostics et calendrier de la saison (sans réseau)."""

import numpy as np
import pandas as pd
import pytest

from simulateur_foot import calendrier_saison, collecte_resultats, pronostics
from simulateur_foot.modele import RESULTATS
from simulateur_foot.prediction import SAISON_EN_COURS, charger_forces
from simulateur_foot.simulation import matchs_restants

# ---------- Suivi des pronostics ----------


@pytest.fixture
def journee_fictive(tmp_path, monkeypatch):
    """Deux affiches de Ligue 1 pas encore jouées, et un fichier de pronostics vide."""
    matchs, _ = charger_forces("F1")
    restants = matchs_restants(matchs[matchs["Saison"] == SAISON_EN_COURS]).head(2)
    fichier = tmp_path / "prochains_matchs.csv"
    restants.assign(Championnat="F1", Date="2099-01-01", Heure="21:00").to_csv(fichier, index=False)
    monkeypatch.setattr(collecte_resultats, "FICHIER_PROCHAINS", fichier)
    monkeypatch.setattr(pronostics, "FICHIER_PRONOSTICS", tmp_path / "pronostics.csv")
    return restants


def test_pronostics_enregistres_une_seule_fois(journee_fictive):
    assert pronostics.enregistrer("2098-12-30") == 2
    premiers = pronostics.charger()
    assert len(premiers) == 2
    assert list(premiers.columns) == pronostics.COLONNES
    assert np.allclose(premiers[RESULTATS].sum(axis=1), 1, atol=1e-3)
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
    assert bilan["log_loss"] == pytest.approx(attendu)
    assert 0 <= bilan["precision"] <= 1
    assert pronostics.bilan(joues, championnat="E0") is None


def test_precision_du_bilan():
    joues = pd.DataFrame({"Championnat": ["F1", "F1"], "Saison": [SAISON_EN_COURS] * 2, "HomeTeam": ["A", "C"],
                          "AwayTeam": ["B", "D"], "Date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                          "A": [0.2, 0.5], "D": [0.3, 0.3], "H": [0.5, 0.2], "FTR": ["H", "H"]})
    bilan = pronostics.bilan(joues)  # le premier favori gagne, pas le second
    assert bilan["precision"] == 0.5
    assert bilan["depuis"] == pd.Timestamp("2026-01-01")


def test_prochains_matchs_d_un_championnat_sans_annonce(journee_fictive):
    """Le fichier ne contient que de la Ligue 1 : un autre championnat renvoie un tableau vide, colonnes comprises."""
    matchs, _ = charger_forces("E0")
    vide = collecte_resultats.charger_prochains_matchs("E0", matchs[matchs["Saison"] == SAISON_EN_COURS])
    assert vide.empty and "HomeTeam" in vide.columns


# ---------- Calendrier de la saison ----------


def evenement(date, domicile, exterieur, etat="pre"):
    return {"date": date, "competitions": [{"status": {"type": {"state": etat}}, "competitors": [
        {"homeAway": "home", "team": {"displayName": domicile}},
        {"homeAway": "away", "team": {"displayName": exterieur}}]}]}


def test_lecture_du_calendrier_espn():
    clubs = ["Paris SG", "Lens", "Lille", "Rennes"]
    lignes, inconnus = calendrier_saison.lire_evenements([
        evenement("2026-11-21T20:05Z", "Paris Saint-Germain", "Lens"),
        evenement("2026-11-08T14:00Z", "Lille", "Lens", etat="post"),  # déjà joué : écarté
        evenement("2026-11-22T23:30Z", "Stade Rennais", "Lille"),  # 00:30 à Paris : le lendemain
        evenement("2026-11-22T14:00Z", "Club Inconnu", "Lille"),
    ], clubs)
    assert lignes == [{"Date": "2026-11-21", "Heure": "21:05", "HomeTeam": "Paris SG", "AwayTeam": "Lens"},
                      {"Date": "2026-11-23", "Heure": "00:30", "HomeTeam": "Rennes", "AwayTeam": "Lille"}]
    assert inconnus == ["Club Inconnu"]


@pytest.fixture
def calendrier_fictif(tmp_path, monkeypatch):
    """Ligue 1 : quatre affiches pas encore jouées sur deux journées ; aucun match annoncé par football-data."""
    matchs, _ = charger_forces("F1")
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    restants = matchs_restants(saison).head(4)
    fichier = tmp_path / "calendrier.csv"
    restants.assign(Championnat="F1", Date=["2099-01-02", "2099-01-03", "2099-01-09", "2099-01-10"],
                    Heure="21:00")[calendrier_saison.COLONNES].to_csv(fichier, index=False)
    monkeypatch.setattr(calendrier_saison, "FICHIER_CALENDRIER", fichier)
    monkeypatch.setattr(collecte_resultats, "FICHIER_PROCHAINS", tmp_path / "absent.csv")
    monkeypatch.setattr(pronostics, "FICHIER_PRONOSTICS", tmp_path / "pronostics.csv")
    return saison, restants.reset_index(drop=True)


def test_prochaine_journee_du_calendrier(calendrier_fictif):
    saison, restants = calendrier_fictif
    assert len(calendrier_saison.charger("F1", saison)) == 4
    journee = calendrier_saison.prochaine_journee("F1", saison, aujourd_hui="2098-12-30")
    assert list(journee["HomeTeam"]) == list(restants["HomeTeam"][:2])  # la seconde journée attend
    suivante = calendrier_saison.prochaine_journee("F1", saison, aujourd_hui="2099-01-05")
    assert suivante["Date"].min() == pd.Timestamp("2099-01-09")
    assert calendrier_saison.prochaine_journee("E0", saison).empty
    club = restants.loc[0, "HomeTeam"]
    siens = calendrier_saison.prochains_matchs_club(calendrier_saison.charger("F1", saison), club, nb=1)
    assert len(siens) == 1 and club in (siens.loc[0, "HomeTeam"], siens.loc[0, "AwayTeam"])


def test_sans_annonce_on_prend_le_calendrier(calendrier_fictif):
    """Trêve : football-data n'annonce rien, la prochaine journée et ses pronostics viennent du calendrier."""
    saison, restants = calendrier_fictif
    prochains = collecte_resultats.charger_prochains_matchs("F1", saison)
    assert list(prochains["HomeTeam"]) == list(restants["HomeTeam"][:2])
    assert pronostics.enregistrer("2098-12-30") == 2
    assert np.allclose(pronostics.charger()[RESULTATS].sum(axis=1), 1, atol=1e-3)
