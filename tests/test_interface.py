"""L'interface s'affiche sans erreur pour chaque championnat (sans accès au réseau)."""

import pytest
from streamlit.testing.v1 import AppTest

from simulateur_foot.championnats import CHAMPIONNATS


@pytest.mark.parametrize("code", list(CHAMPIONNATS))
def test_interface_sans_erreur(code):
    app = AppTest.from_file("../src/simulateur_foot/app.py", default_timeout=120)
    app.session_state["verification"] = None  # pas de mise à jour automatique pendant les tests
    app.query_params["championnat"] = code
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 3
