"""Meilleurs buteurs et passeurs de chaque championnat, avec leur projection de fin de saison.

Les statistiques viennent de l'API publique d'ESPN (gratuite, sans clé) : pour chaque
championnat, les 50 meilleurs buteurs et les 50 meilleurs passeurs de la saison en cours.

La projection suppose que le joueur garde son rythme : même part des matchs de son club,
mêmes buts et passes par match joué. Le reste de la saison est tiré au sort des milliers
de fois (loi de Poisson, avec un taux lui-même incertain tant que le joueur a peu joué) ;
la fourchette couvre 8 saisons simulées sur 10.

Lancement : uv run simulateur-foot joueurs
"""

import time

import numpy as np
import pandas as pd
import requests

from .championnats import CHAMPIONNATS
from .collecte_resultats import DOSSIER_DATA
from .logos import ALIAS, _simplifie
from .simulation import classement, matchs_restants

FICHIER_JOUEURS = DOSSIER_DATA / "joueurs.csv"
API = "https://site.web.api.espn.com/apis/site/v2/sports/soccer/{ligue}/statistics"
LIGUES_ESPN = {"F1": "fra.1", "E0": "eng.1", "SP1": "esp.1", "D1": "ger.1", "I1": "ita.1", "F2": "fra.2"}
# Noms ESPN que la correspondance automatique ne retrouve pas
CLUBS_ESPN = {"Paris Saint-Germain": "Paris SG", "Wolverhampton Wanderers": "Wolves",
              "Atletico Madrid": "Ath Madrid", "Athletic Club": "Ath Bilbao", "Alavés": "Alaves",
              "Inter": "Inter", "AS Roma": "Roma", "Borussia Mönchengladbach": "M'gladbach",
              "AC Milan": "Milan", "Saint-Étienne": "St Etienne", "Stade Rennais": "Rennes",
              "Brighton & Hove Albion": "Brighton", "Deportivo": "Alaves", "FC Cologne": "FC Koln",
              "Internazionale": "Inter"}
NB_TIRAGES = 20_000


def telecharger():
    """Télécharge les meilleurs buteurs et passeurs des 6 championnats vers data/joueurs.csv."""
    lignes = []
    with requests.Session() as session:
        session.headers["User-Agent"] = "simulateur-foot"
        for code, ligue in LIGUES_ESPN.items():
            reponse = session.get(API.format(ligue=ligue), timeout=20)
            reponse.raise_for_status()
            for categorie in reponse.json()["stats"]:
                for ordre in categorie["leaders"]:
                    joueur = ordre["athlete"]
                    stats = {s["name"]: s["value"] for s in joueur.get("statistics", [])}
                    lignes.append({
                        "Championnat": code, "id": joueur["id"], "joueur": joueur["displayName"],
                        "club_espn": joueur["team"]["displayName"],
                        "matchs": stats.get("appearances", 0), "buts": stats.get("totalGoals", 0),
                        "passes": stats.get("goalAssists", 0)})
            time.sleep(0.5)
    joueurs = pd.DataFrame(lignes).drop_duplicates(["Championnat", "id"])
    FICHIER_JOUEURS.parent.mkdir(parents=True, exist_ok=True)
    joueurs.to_csv(FICHIER_JOUEURS, index=False)
    return joueurs


def heures_depuis_telechargement():
    if not FICHIER_JOUEURS.exists():
        return float("inf")
    return (time.time() - FICHIER_JOUEURS.stat().st_mtime) / 3600


def charger():
    return pd.read_csv(FICHIER_JOUEURS, dtype={"id": str})


def _club(nom_espn, clubs):
    """Le nom football-data.co.uk du club ESPN, ou None s'il n'est pas dans la liste."""
    if nom_espn in CLUBS_ESPN and CLUBS_ESPN[nom_espn] in clubs:
        return CLUBS_ESPN[nom_espn]
    simplifies = {_simplifie(ALIAS.get(c, c)): c for c in clubs}
    nom = _simplifie(nom_espn)
    if nom in simplifies:
        return simplifies[nom]
    inclus = [c for k, c in simplifies.items() if len(k) >= 4 and (k in nom or nom in k)]
    return inclus[0] if len(inclus) == 1 else None


def _fourchette(total, matchs, matchs_a_jouer, generateur):
    """Fourchette 10 %-90 % de ce que chaque joueur ajoutera d'ici la fin de saison.

    Son rythme (par match joué) est incertain : on le tire dans une loi gamma centrée sur
    le rythme observé, large tant que le joueur a peu joué. Puis on tire ses buts (ou passes)
    des matchs à venir selon ce rythme (loi de Poisson).
    """
    taux = generateur.gamma((total + 0.5)[:, None], (1 / matchs)[:, None], size=(len(total), NB_TIRAGES))
    ajouts = generateur.poisson(taux * matchs_a_jouer[:, None])
    return np.percentile(ajouts, [10, 90], axis=1)


def projeter(joueurs, saison, code, graine=0):
    """Les joueurs d'un championnat avec leur projection de fin de saison.

    `saison` : les matchs déjà joués de la saison en cours dans ce championnat. Un joueur
    garde la même part des matchs de son club qu'jusqu'ici.
    """
    table = classement(saison)
    restants = matchs_restants(saison)
    par_club = restants["HomeTeam"].value_counts().add(restants["AwayTeam"].value_counts(), fill_value=0)
    clubs = list(table.index)
    joueurs = joueurs[joueurs["Championnat"] == code].copy()
    joueurs["club"] = joueurs["club_espn"].map(lambda nom: _club(nom, clubs))
    joueurs = joueurs[joueurs["club"].notna() & (joueurs["matchs"] > 0)].copy()

    part = (joueurs["matchs"] / joueurs["club"].map(table["joues"])).clip(upper=1)
    a_jouer = (joueurs["club"].map(par_club).fillna(0) * part).to_numpy()
    joueurs["matchs_prevus"] = joueurs["matchs"] + a_jouer
    generateur = np.random.default_rng(graine)
    for stat in ["buts", "passes"]:
        joueurs[f"{stat}_prevus"] = joueurs[stat] + a_jouer * joueurs[stat] / joueurs["matchs"]
        bas, haut = _fourchette(joueurs[stat].to_numpy(), joueurs["matchs"].to_numpy(), a_jouer, generateur)
        joueurs[f"{stat}_bas"] = joueurs[stat] + bas
        joueurs[f"{stat}_haut"] = joueurs[stat] + haut
    joueurs["decisives"] = joueurs["buts"] + joueurs["passes"]
    joueurs["decisives_prevues"] = joueurs["buts_prevus"] + joueurs["passes_prevus"]
    return joueurs.reset_index(drop=True)


def main():
    joueurs = telecharger()
    print(f"{len(joueurs)} joueurs enregistrés dans {FICHIER_JOUEURS}")
