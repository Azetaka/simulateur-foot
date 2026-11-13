"""Statistiques des joueurs : correspondance des clubs ESPN et projection de fin de saison (sans réseau)."""

import numpy as np
import pandas as pd
import pytest

from simulateur_foot import joueurs
from simulateur_foot.championnats import CHAMPIONNATS
from simulateur_foot.prediction import SAISON_EN_COURS, charger_forces
from simulateur_foot.scores import entrainer_scores
from simulateur_foot.simulation import classement, matchs_restants


@pytest.fixture(scope="module")
def ligue1():
    matchs, notes = charger_forces("F1")
    return matchs, notes, matchs[matchs["Saison"] == SAISON_EN_COURS]


def fiche(club, matchs, buts, passes=0, nom="Joueur", championnat="F1"):
    return {"Championnat": championnat, "id": nom, "joueur": nom, "club_espn": club,
            "matchs": matchs, "buts": buts, "passes": passes}


def test_clubs_espn_reconnus():
    clubs = ["Paris SG", "Paris FC", "St Etienne", "Rennes", "Lens", "Marseille"]
    assert joueurs._club("Paris Saint-Germain", clubs) == "Paris SG"
    assert joueurs._club("Paris FC", clubs) == "Paris FC"
    assert joueurs._club("Stade Rennais", clubs) == "Rennes"
    assert joueurs._club("Lens", clubs) == "Lens"
    assert joueurs._club("Club Inconnu", clubs) is None


def test_clubs_non_reconnus_signales():
    donnees = pd.DataFrame([fiche("Lens", 5, 2), fiche("Club Inconnu", 5, 1), fiche("Lens", 3, 1, championnat="E0")])
    assert joueurs.clubs_non_reconnus(donnees, ["Lens", "Lille"], "F1") == ["Club Inconnu"]


@pytest.mark.parametrize("code", list(CHAMPIONNATS))
def test_tous_les_clubs_du_fichier_sont_reconnus(code):
    """Avec le fichier local (s'il existe), aucun club ESPN de la saison ne reste sans correspondance."""
    if not joueurs.FICHIER_JOUEURS.exists():
        pytest.skip("data/joueurs.csv absent")
    matchs, _ = charger_forces(code)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    clubs = set(saison["HomeTeam"]) | set(saison["AwayTeam"])
    assert joueurs.clubs_non_reconnus(joueurs.charger(), clubs, code) == []


def test_rythme_ramene_vers_la_moyenne():
    # Peu de matchs : forte correction. Beaucoup de matchs : le rythme observé domine.
    assert joueurs.rythme_corrige(9, 10, 0.3) == pytest.approx((9 + 10 * 0.3) / 20)
    assert 0.3 < joueurs.rythme_corrige(9, 10, 0.3) < 0.9
    assert joueurs.rythme_corrige(90, 100, 0.3) > joueurs.rythme_corrige(9, 10, 0.3)
    assert joueurs.rythme_corrige(0, 10, 0.3) > 0  # un joueur muet n'est pas condamné à zéro


def test_projection_coherente(ligue1):
    _, _, saison = ligue1
    table = classement(saison)
    club_a, club_b = table.index[0], table.index[1]
    joues = int(table.loc[club_a, "joues"])
    donnees = pd.DataFrame([fiche(club_a, joues, 9, 3, "Canon"), fiche(club_b, 2, 1, 0, "Discret"),
                            fiche("Club Inconnu", 5, 5, 5, "Fantôme"), fiche(club_a, 0, 0, 0, "Jamais joué")])
    resultat = joueurs.projeter(donnees, saison, "F1").set_index("joueur")

    assert list(resultat.index) == ["Canon", "Discret"]  # club inconnu et joueur sans match écartés
    for stat in ["buts", "passes"]:
        assert (resultat[f"{stat}_bas"] >= resultat[stat]).all()  # on ne perd pas de buts
        assert (resultat[f"{stat}_bas"] <= resultat[f"{stat}_prevus"] + 1e-9).all()
        assert (resultat[f"{stat}_prevus"] <= resultat[f"{stat}_haut"] + 1e-9).all()
    # Le rythme retenu est plus prudent que le rythme observé du meilleur buteur
    assert resultat.loc["Canon", "buts_rythme"] < 9 / joues
    # Un titulaire ne joue pas plus de matchs que son club
    total = joues + len(matchs_restants(saison).query("HomeTeam == @club_a or AwayTeam == @club_a"))
    assert resultat.loc["Canon", "matchs_prevus"] == pytest.approx(total)


def test_calendrier_facile_augmente_la_projection(ligue1):
    _, _, saison = ligue1
    club = classement(saison).index[0]
    donnees = pd.DataFrame([fiche(club, 8, 6, 2, "Joueur")])
    neutre = joueurs.projeter(donnees, saison, "F1")
    facile = joueurs.projeter(donnees, saison, "F1", calendrier=pd.Series({club: 1.2}))
    dur = joueurs.projeter(donnees, saison, "F1", calendrier=pd.Series({club: 0.8}))
    assert dur["buts_prevus"][0] < neutre["buts_prevus"][0] < facile["buts_prevus"][0]


def test_facteur_calendrier(ligue1):
    matchs, notes, saison = ligue1
    facteurs = joueurs.facteur_calendrier(saison, matchs_restants(saison), notes, entrainer_scores(matchs))
    assert set(facteurs.index) == set(saison["HomeTeam"]) | set(saison["AwayTeam"])
    assert facteurs.between(0.6, 1.6).all()  # un calendrier change le rythme, il ne le bouleverse pas
    # Saison terminée : plus de matchs à venir, facteur neutre
    termine = joueurs.facteur_calendrier(saison, saison.iloc[:0][["HomeTeam", "AwayTeam"]], notes,
                                         entrainer_scores(matchs))
    assert np.allclose(termine, 1.0)


def test_telechargement_lit_la_reponse_espn(monkeypatch, tmp_path):
    """Réponse ESPN simulée : un joueur présent dans les deux classements n'est compté qu'une fois."""
    def joueur(identifiant, nom, club, matchs, buts, passes):
        return {"athlete": {"id": identifiant, "displayName": nom, "team": {"displayName": club},
                            "statistics": [{"name": "appearances", "value": matchs},
                                           {"name": "totalGoals", "value": buts},
                                           {"name": "goalAssists", "value": passes}]}}

    class Reponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"stats": [{"leaders": [joueur("1", "A", "Lens", 10, 7, 2)]},
                              {"leaders": [joueur("1", "A", "Lens", 10, 7, 2), joueur("2", "B", "Lille", 9, 1, 5)]}]}

    class Session:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *erreur):
            return False

        def get(self, *args, **kwargs):
            return Reponse()

    monkeypatch.setattr(joueurs.requests, "Session", Session)
    monkeypatch.setattr(joueurs.time, "sleep", lambda secondes: None)
    monkeypatch.setattr(joueurs, "FICHIER_JOUEURS", tmp_path / "joueurs.csv")
    resultat = joueurs.telecharger()
    assert len(resultat) == 2 * len(joueurs.LIGUES_ESPN)  # deux joueurs par championnat, sans doublon
    assert set(resultat["joueur"]) == {"A", "B"}
    assert joueurs.charger()["buts"].sum() == 8 * len(joueurs.LIGUES_ESPN)
