"""Calendrier des matchs à venir, jusqu'à la fin de la saison (API publique d'ESPN, sans clé).

football-data.co.uk n'annonce que la prochaine journée, quelques jours avant, et rien pendant
les trêves. Ce calendrier complète : il donne la date de tous les matchs qui restent, donc
la prochaine journée même pendant une trêve et les prochains matchs de chaque club.

Lancement : uv run simulateur-foot calendrier
"""

import time

import pandas as pd
import requests

from .collecte_resultats import DOSSIER_DATA, FICHIER, SAISONS
from .joueurs import LIGUES_ESPN, _club

FICHIER_CALENDRIER = DOSSIER_DATA / "calendrier.csv"
API = "https://site.api.espn.com/apis/site/v2/sports/soccer/{ligue}/scoreboard"
COLONNES = ["Championnat", "Date", "Heure", "HomeTeam", "AwayTeam"]
FUSEAU = "Europe/Paris"
DUREE_JOURNEE = 4  # jours : une journée s'étale au plus du vendredi au lundi


def lire_evenements(evenements, clubs):
    """Matchs pas encore joués d'une réponse ESPN, avec les noms de clubs de football-data.co.uk.

    Renvoie (lignes, noms de clubs non reconnus).
    """
    lignes, inconnus = [], set()
    for evenement in evenements:
        rencontre = evenement["competitions"][0]
        if rencontre["status"]["type"]["state"] != "pre":
            continue
        noms = {equipe["homeAway"]: equipe["team"]["displayName"] for equipe in rencontre["competitors"]}
        dom, ext = _club(noms["home"], clubs), _club(noms["away"], clubs)
        inconnus |= {nom for nom, club in [(noms["home"], dom), (noms["away"], ext)] if club is None}
        if dom is None or ext is None:
            continue
        quand = pd.Timestamp(evenement["date"]).tz_convert(FUSEAU)
        lignes.append({"Date": quand.strftime("%Y-%m-%d"), "Heure": quand.strftime("%H:%M"),
                       "HomeTeam": dom, "AwayTeam": ext})
    return lignes, sorted(inconnus)


def telecharger():
    """Enregistre les matchs à venir des six championnats ; renvoie (nombre de matchs, clubs non reconnus)."""
    resultats = pd.read_csv(FICHIER)
    saison = resultats[resultats["Saison"] == int(SAISONS[-1])]
    annee = pd.Timestamp.now().year
    tout, inconnus = [], []
    with requests.Session() as session:
        session.headers["User-Agent"] = "simulateur-foot"
        for code, ligue in LIGUES_ESPN.items():
            de_la_ligue = saison[saison["Championnat"] == code]
            clubs = sorted(set(de_la_ligue["HomeTeam"]) | set(de_la_ligue["AwayTeam"]))
            evenements = []
            for an in (annee, annee + 1):  # la saison est à cheval sur deux années civiles
                reponse = session.get(API.format(ligue=ligue), params={"dates": an, "limit": 1000}, timeout=30)
                reponse.raise_for_status()
                evenements += reponse.json().get("events", [])
                time.sleep(0.5)
            lignes, absents = lire_evenements(evenements, clubs)
            tout += [{"Championnat": code, **ligne} for ligne in lignes]
            inconnus += [f"{code}/{nom}" for nom in absents]
    calendrier = pd.DataFrame(tout, columns=COLONNES).drop_duplicates(["Championnat", "HomeTeam", "AwayTeam"])
    DOSSIER_DATA.mkdir(exist_ok=True)
    calendrier.sort_values(["Championnat", "Date", "Heure", "HomeTeam"], kind="stable").to_csv(
        FICHIER_CALENDRIER, index=False)
    return len(calendrier), inconnus


def charger(championnat, matchs_saison):
    """Matchs à venir d'un championnat, du plus proche au plus lointain (vide sans fichier).

    Les affiches déjà jouées sont retirées : le fichier peut dater de quelques jours.
    """
    if not FICHIER_CALENDRIER.exists():
        return pd.DataFrame(columns=COLONNES)
    calendrier = pd.read_csv(FICHIER_CALENDRIER, parse_dates=["Date"])
    calendrier = calendrier[calendrier["Championnat"] == championnat]
    jouees = set(zip(matchs_saison["HomeTeam"], matchs_saison["AwayTeam"]))
    a_venir = [(d, e) not in jouees for d, e in zip(calendrier["HomeTeam"], calendrier["AwayTeam"])]
    calendrier = calendrier[pd.Series(a_venir, index=calendrier.index, dtype=bool)]
    return calendrier.sort_values(["Date", "Heure"], kind="stable").reset_index(drop=True)


def prochaine_journee(championnat, matchs_saison, aujourd_hui=None):
    """Les matchs de la prochaine journée : ceux des DUREE_JOURNEE jours qui suivent le prochain match."""
    calendrier = charger(championnat, matchs_saison)
    aujourd_hui = pd.Timestamp(aujourd_hui or pd.Timestamp.now()).normalize()
    calendrier = calendrier[calendrier["Date"] >= aujourd_hui]
    if calendrier.empty:
        return calendrier
    limite = calendrier["Date"].min() + pd.Timedelta(days=DUREE_JOURNEE)
    return calendrier[calendrier["Date"] < limite].reset_index(drop=True)


def prochains_matchs_club(calendrier, club, nb=5):
    """Les `nb` prochains matchs d'un club dans un calendrier déjà chargé."""
    siens = calendrier[(calendrier["HomeTeam"] == club) | (calendrier["AwayTeam"] == club)]
    return siens.head(nb).reset_index(drop=True)


def main():
    nombre, inconnus = telecharger()
    print(f"{nombre} matchs à venir enregistrés dans {FICHIER_CALENDRIER}")
    if inconnus:
        print(f"Clubs non reconnus (à ajouter dans joueurs.CLUBS_ESPN) : {', '.join(inconnus)}")


if __name__ == "__main__":
    main()
