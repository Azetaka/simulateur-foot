"""Meilleurs buteurs et passeurs de chaque championnat, avec leur projection de fin de saison.

Les statistiques viennent de l'API publique d'ESPN (gratuite, sans clé) : pour chaque
championnat, les 50 meilleurs buteurs et les 50 meilleurs passeurs de la saison en cours.

La projection suppose que le joueur garde la même part des matchs de son club. Son rythme
(buts ou passes par match joué) est ramené vers la moyenne des joueurs du classement, car
un départ canon se prolonge rarement, puis ajusté à la difficulté des matchs restants de
son club (buts attendus du modèle de score). Le reste de la saison est tiré au sort des
milliers de fois (loi de Poisson, avec un rythme lui-même incertain) ; la fourchette couvre
8 saisons simulées sur 10.

Lancement : uv run simulateur-foot joueurs
"""

import time

import numpy as np
import pandas as pd
import requests

from .collecte_resultats import DOSSIER_DATA
from .logos import ALIAS, _simplifie
from .scores import buts_attendus
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
MATCHS_PRUDENCE = 10  # poids de la moyenne dans le rythme d'un joueur, en matchs


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


def clubs_non_reconnus(joueurs, clubs, code):
    """Noms de clubs ESPN sans correspondance dans le championnat : leurs joueurs sont ignorés.

    Si la liste n'est pas vide, ajouter le nom dans CLUBS_ESPN.
    """
    noms = joueurs.loc[joueurs["Championnat"] == code, "club_espn"].unique()
    return sorted(nom for nom in noms if _club(nom, list(clubs)) is None)


def facteur_calendrier(matchs_saison, restants, notes, modele_scores):
    """Pour chaque club : ses buts attendus par match sur les matchs restants, rapportés à
    ceux des matchs déjà joués. Au-dessus de 1, le calendrier qui reste est plus facile.

    `matchs_saison` porte les notes d'avant-match (force_dom, force_ext) ; `notes` sont celles du jour.
    """
    joues_dom, joues_ext = buts_attendus(modele_scores, matchs_saison["force_dom"], matchs_saison["force_ext"])
    passes = pd.concat([pd.Series(joues_dom, index=matchs_saison["HomeTeam"].to_numpy()),
                        pd.Series(joues_ext, index=matchs_saison["AwayTeam"].to_numpy())])
    if restants.empty:
        return pd.Series(1.0, index=passes.index.unique())
    a_venir_dom, a_venir_ext = buts_attendus(modele_scores, restants["HomeTeam"].map(notes),
                                             restants["AwayTeam"].map(notes))
    a_venir = pd.concat([pd.Series(a_venir_dom, index=restants["HomeTeam"].to_numpy()),
                         pd.Series(a_venir_ext, index=restants["AwayTeam"].to_numpy())])
    return (a_venir.groupby(level=0).mean() / passes.groupby(level=0).mean()).fillna(1.0)


def rythme_corrige(total, matchs, rythme_moyen, matchs_prudence=MATCHS_PRUDENCE):
    """Rythme par match ramené vers la moyenne des joueurs du classement.

    Un joueur à 9 buts en 10 matchs ne gardera sans doute pas ce rythme : on fait comme s'il
    avait joué `matchs_prudence` matchs de plus au rythme moyen. Plus il a joué, moins la
    correction pèse.
    """
    return (total + matchs_prudence * rythme_moyen) / (matchs + matchs_prudence)


def _fourchette(total, matchs, rythme_moyen, matchs_a_jouer, generateur):
    """Fourchette 10 %-90 % de ce que chaque joueur ajoutera d'ici la fin de saison.

    Son rythme est incertain : on le tire dans une loi gamma centrée sur le rythme corrigé,
    large tant que le joueur a peu joué. Puis on tire ses buts (ou passes) des matchs à
    venir selon ce rythme (loi de Poisson).
    """
    forme = (total + MATCHS_PRUDENCE * rythme_moyen)[:, None]
    echelle = (1 / (matchs + MATCHS_PRUDENCE))[:, None]
    taux = generateur.gamma(forme, echelle, size=(len(total), NB_TIRAGES))
    ajouts = generateur.poisson(taux * matchs_a_jouer[:, None])
    return np.percentile(ajouts, [10, 90], axis=1)


def projeter(joueurs, saison, code, graine=0, calendrier=None):
    """Les joueurs d'un championnat avec leur projection de fin de saison.

    `saison` : les matchs déjà joués de la saison en cours dans ce championnat.
    `calendrier` : facteur par club (facteur_calendrier), 1 partout si absent.
    Un joueur garde la même part des matchs de son club que jusqu'ici ; son rythme est
    ramené vers la moyenne (rythme_corrige) et ajusté à la difficulté des matchs restants.
    """
    table = classement(saison)
    restants = matchs_restants(saison)
    par_club = restants["HomeTeam"].value_counts().add(restants["AwayTeam"].value_counts(), fill_value=0)
    clubs = list(table.index)
    joueurs = joueurs[joueurs["Championnat"] == code].copy()
    joueurs["club"] = joueurs["club_espn"].map(lambda nom: _club(nom, clubs))
    joueurs = joueurs[joueurs["club"].notna() & (joueurs["matchs"] > 0)].copy()

    part = (joueurs["matchs"] / joueurs["club"].map(table["joues"])).clip(upper=1)
    joueurs["facteur_calendrier"] = 1.0 if calendrier is None else joueurs["club"].map(calendrier).fillna(1.0)
    a_jouer = (joueurs["club"].map(par_club).fillna(0) * part).to_numpy()
    joueurs["matchs_prevus"] = joueurs["matchs"] + a_jouer
    # Matchs à venir « équivalents » : plus nombreux si le calendrier restant est plus facile
    equivalents = a_jouer * joueurs["facteur_calendrier"].to_numpy()
    generateur = np.random.default_rng(graine)
    for stat in ["buts", "passes"]:
        total, matchs = joueurs[stat].to_numpy(dtype=float), joueurs["matchs"].to_numpy(dtype=float)
        rythme_moyen = total.sum() / matchs.sum() if len(joueurs) else 0.0
        joueurs[f"{stat}_rythme"] = rythme_corrige(total, matchs, rythme_moyen)
        joueurs[f"{stat}_prevus"] = total + equivalents * joueurs[f"{stat}_rythme"]
        if len(joueurs):
            bas, haut = _fourchette(total, matchs, rythme_moyen, equivalents, generateur)
        else:
            bas = haut = np.array([])
        joueurs[f"{stat}_bas"] = total + bas
        joueurs[f"{stat}_haut"] = total + haut
    joueurs["decisives"] = joueurs["buts"] + joueurs["passes"]
    joueurs["decisives_prevues"] = joueurs["buts_prevus"] + joueurs["passes_prevus"]
    return joueurs.reset_index(drop=True)


def main():
    joueurs = telecharger()
    print(f"{len(joueurs)} joueurs enregistrés dans {FICHIER_JOUEURS}")
