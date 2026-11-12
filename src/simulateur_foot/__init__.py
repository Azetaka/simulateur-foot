"""Simulateur de championnats de football : force des clubs, prédiction des matchs, simulation de saison."""

import argparse
import inspect
import subprocess
import sys
from pathlib import Path

ETAPES = {
    "collecte": ("collecte_resultats", "Télécharge tous les championnats, toutes les saisons"),
    "maj": ("collecte_resultats", "Met à jour la saison en cours (rapide)"),
    "forces": ("force_clubs", "Calcule les notes Elo et exporte data/matchs_force.csv"),
    "variables": ("variables", "Exporte data/matchs_variables.csv (forme, repos, promus)"),
    "reglage": ("reglage_force", "Cherche les meilleurs paramètres Elo"),
    "modele": ("modele", "Compare les modèles de prédiction (≈ 2 min)"),
    "simulation": ("simulation", "Simule la fin de la saison en cours"),
    "bookmakers": ("bookmakers", "Compare le modèle aux bookmakers sur la saison test"),
    "pronostics": ("pronostics", "Enregistre les pronostics des matchs à venir et affiche leur bilan"),
    "joueurs": ("joueurs", "Télécharge les meilleurs buteurs et passeurs (ESPN)"),
    "logos": ("logos", "Télécharge les écussons des championnats et des clubs"),
}
FONCTIONS = {"maj": "main_mise_a_jour"}


def main() -> None:
    from .championnats import CHAMPIONNATS, PAR_DEFAUT

    parser = argparse.ArgumentParser(prog="simulateur-foot", description=__doc__)
    parser.add_argument("-c", "--championnat", default=PAR_DEFAUT, choices=list(CHAMPIONNATS),
                        help="Code du championnat (F1 = Ligue 1, E0 = Premier League…)")
    commandes = parser.add_subparsers(dest="commande", required=True)
    for nom, (_, aide) in ETAPES.items():
        commandes.add_parser(nom, help=aide)
    commandes.add_parser("interface", help="Ouvre l'interface de test dans le navigateur")
    arguments = parser.parse_args()
    commande = arguments.commande

    if commande == "interface":
        # Lancé depuis la racine du dépôt pour que Streamlit trouve .streamlit/config.toml
        racine = Path(__file__).resolve().parents[2]
        app = Path(__file__).with_name("app.py")
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)], cwd=racine))

    module = __import__(f"simulateur_foot.{ETAPES[commande][0]}", fromlist=["main"])
    fonction = getattr(module, FONCTIONS.get(commande, "main"))
    if "championnat" in inspect.signature(fonction).parameters:
        fonction(championnat=arguments.championnat)
    else:
        fonction()
