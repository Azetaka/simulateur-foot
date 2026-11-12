"""L'interface s'affiche sans erreur pour chaque championnat (sans accès au réseau)."""

import pytest
from streamlit.testing.v1 import AppTest

from simulateur_foot.championnats import CHAMPIONNATS


@pytest.mark.parametrize("code", list(CHAMPIONNATS))
def test_interface_sans_erreur(code):
    app = AppTest.from_file("../src/simulateur_foot/app.py", default_timeout=120)
    app.session_state["verification"] = None  # pas de mise à jour automatique pendant les tests
    app.session_state["maj_joueurs"] = False
    app.query_params["championnat"] = code
    app.run()
    assert not app.exception
    # Trois tableaux, plus celui de la prochaine journée quand des matchs sont annoncés,
    # plus celui des joueurs de la fiche club quand le club en a parmi les meilleurs
    assert len(app.dataframe) in (3, 4, 5)
    assert len(app.tabs) == 7


def test_prochaine_journee_avec_des_matchs_annonces(tmp_path, monkeypatch):
    """Journée fictive : deux affiches pas encore jouées, avec des cotes."""
    from simulateur_foot import collecte_resultats
    from simulateur_foot.prediction import SAISON_EN_COURS, charger_forces
    from simulateur_foot.simulation import matchs_restants

    matchs, _ = charger_forces("F1")
    restants = matchs_restants(matchs[matchs["Saison"] == SAISON_EN_COURS]).head(2)
    fichier = tmp_path / "prochains_matchs.csv"
    restants.assign(Championnat="F1", Date="2099-01-01", Heure="21:00", CoteH=2.1, CoteD=3.4,
                    CoteA=3.5).to_csv(fichier, index=False)
    monkeypatch.setattr(collecte_resultats, "FICHIER_PROCHAINS", fichier)

    app = AppTest.from_file("../src/simulateur_foot/app.py", default_timeout=120)
    app.session_state["verification"] = None
    app.session_state["maj_joueurs"] = False
    app.query_params["championnat"] = "F1"
    app.run()
    assert not app.exception
    assert len(app.dataframe) in (4, 5)  # dont le tableau « Voir les chiffres » de la prochaine journée
