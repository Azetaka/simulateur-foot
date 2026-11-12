"""Réglages communs aux tests."""

import pytest

from simulateur_foot import calendrier_saison


@pytest.fixture(autouse=True)
def sans_calendrier(tmp_path, monkeypatch):
    """Par défaut, pas de calendrier : la prochaine journée ne dépend que de ce que chaque test fournit.

    Les tests du calendrier remplacent à leur tour ce fichier par le leur.
    """
    monkeypatch.setattr(calendrier_saison, "FICHIER_CALENDRIER", tmp_path / "calendrier_absent.csv")
