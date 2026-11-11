"""Simulateur de Ligue 1 : force des clubs, prédiction des matchs, simulation de saison."""

import argparse
import subprocess
import sys
from pathlib import Path

ETAPES = {
    "collecte": ("collecte_resultats", "Télécharge les résultats de Ligue 1 dans data/"),
    "forces": ("force_clubs", "Calcule les notes Elo et exporte data/matchs_force.csv"),
    "variables": ("variables", "Exporte data/matchs_variables.csv (forme, repos, promus)"),
    "reglage": ("reglage_force", "Cherche les meilleurs paramètres Elo"),
    "modele": ("modele", "Compare les modèles de prédiction (≈ 2 min)"),
    "simulation": ("simulation", "Simule la fin de la saison en cours"),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulateur-foot", description=__doc__)
    commandes = parser.add_subparsers(dest="commande", required=True)
    for nom, (_, aide) in ETAPES.items():
        commandes.add_parser(nom, help=aide)
    commandes.add_parser("interface", help="Ouvre l'interface de test dans le navigateur")
    commande = parser.parse_args().commande

    if commande == "interface":
        # Lancé depuis la racine du dépôt pour que Streamlit trouve .streamlit/config.toml
        racine = Path(__file__).resolve().parents[2]
        app = Path(__file__).with_name("app.py")
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)], cwd=racine))

    module = __import__(f"simulateur_foot.{ETAPES[commande][0]}", fromlist=["main"])
    module.main()
