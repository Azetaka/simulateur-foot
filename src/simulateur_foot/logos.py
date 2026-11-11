"""Écussons des championnats et des clubs, téléchargés depuis TheSportsDB.

Les images vont dans src/simulateur_foot/static/logos/ (championnats/ et clubs/<code>/). Les écussons
appartiennent à leurs clubs et ligues : ils servent ici à l'illustration de l'outil.

Lancement : uv run simulateur-foot logos
"""

import difflib
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

from simulateur_foot.collecte_resultats import FICHIER

DOSSIER = Path(__file__).resolve().parent / "static" / "logos"  # servi par Streamlit sous /app/static/logos
API = "https://www.thesportsdb.com/api/v1/json/123"  # clé de test publique de TheSportsDB
PAUSE = 3  # secondes entre deux requêtes (la clé de test est limitée)
TAILLE_MAX = 256  # côté maximal des images enregistrées, en pixels
MARGE = 0.03  # marge transparente gardée autour du dessin, en part du plus grand côté

# Identifiants TheSportsDB des championnats
LIGUES = {"F1": 4334, "E0": 4328, "SP1": 4335, "D1": 4331, "I1": 4332, "F2": 4401}
PAYS = {"F1": "France", "F2": "France", "E0": "England", "SP1": "Spain", "D1": "Germany", "I1": "Italy"}

# Noms football-data.co.uk (abrégés) -> nom à chercher
ALIAS = {
    "Reims": "Stade de Reims",
    "Ein Frankfurt": "Eintracht Frankfurt", "FC Koln": "FC Koln", "M'gladbach": "Borussia Monchengladbach",
    "Dortmund": "Borussia Dortmund", "Leverkusen": "Bayer Leverkusen", "Bayern Munich": "Bayern Munich",
    "Greuther Furth": "Greuther Furth", "Hertha": "Hertha BSC", "Holstein Kiel": "Holstein Kiel",
    "St Pauli": "St. Pauli", "Union Berlin": "Union Berlin", "Bielefeld": "Arminia Bielefeld",
    "Hoffenheim": "TSG Hoffenheim", "Freiburg": "SC Freiburg", "Stuttgart": "VfB Stuttgart",
    "Wolfsburg": "VfL Wolfsburg", "Augsburg": "FC Augsburg", "Mainz": "Mainz 05", "Bochum": "VfL Bochum",
    "Heidenheim": "1. FC Heidenheim", "Darmstadt": "Darmstadt 98", "Hamburg": "Hamburger SV",
    "Man City": "Manchester City", "Man United": "Manchester United", "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest", "Wolves": "Wolverhampton Wanderers", "Tottenham": "Tottenham Hotspur",
    "Brighton": "Brighton and Hove Albion", "Leeds": "Leeds United", "Leicester": "Leicester City",
    "Norwich": "Norwich City", "Hull": "Hull City", "Ipswich": "Ipswich Town", "Luton": "Luton Town",
    "Coventry": "Coventry City", "West Ham": "West Ham United", "Sheffield United": "Sheffield United",
    "Bournemouth": "AFC Bournemouth", "Burnley": "Burnley", "Southampton": "Southampton",
    "Paris SG": "Paris SG", "St Etienne": "Saint Etienne", "Paris FC": "Paris FC", "Nimes": "Nimes",
    "Quevilly Rouen": "Quevilly", "Pau FC": "Pau", "Red Star": "Red Star", "Boulogne": "Boulogne",
    "Ath Bilbao": "Athletic Bilbao", "Ath Madrid": "Atletico Madrid", "Sociedad": "Real Sociedad",
    "Vallecano": "Rayo Vallecano", "Espanol": "Espanyol", "Celta": "Celta Vigo", "Betis": "Real Betis",
    "La Coruna": "Deportivo La Coruna", "Santander": "Racing Santander", "Valladolid": "Real Valladolid",
    "Oviedo": "Real Oviedo", "Alaves": "Deportivo Alaves", "Almeria": "UD Almeria", "Cadiz": "Cadiz",
    "Leganes": "Leganes", "Malaga": "Malaga", "Granada": "Granada", "Valencia": "Valencia",
    "Inter": "Inter Milan", "Milan": "AC Milan", "Verona": "Hellas Verona", "Roma": "AS Roma",
    "Lazio": "Lazio", "Napoli": "Napoli", "Venezia": "Venezia", "Spezia": "Spezia", "Parma": "Parma",
    "Cremonese": "Cremonese", "Pisa": "Pisa", "Como": "Como", "Salernitana": "Salernitana",
}


# Dépôt GitHub d'écussons (clubs de la saison en cours des 5 grands championnats) : un seul
# téléchargement, sans limite de débit. TheSportsDB complète les clubs absents (anciens, Ligue 2).
DEPOT = "luukhopman/football-logos"
DOSSIERS_DEPOT = {"F1": "France - Ligue 1", "E0": "England - Premier League", "SP1": "Spain - LaLiga",
                  "D1": "Germany - Bundesliga", "I1": "Italy - Serie A"}
# Cas où la correspondance automatique se trompe ou échoue
FICHIERS_DEPOT = {"Paris SG": "Paris Saint-Germain", "Wolves": "Wolverhampton Wanderers",
                  "West Ham": "West Ham United", "Rennes": "Stade Rennais FC"}


def slug(texte):
    """Nom de fichier sûr : sans accents, en minuscules, avec des tirets."""
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texte.lower()).strip("-")


def url(chemin):
    """Adresse de l'image sous le serveur de fichiers statiques de Streamlit."""
    return "/app/static/" + chemin.relative_to(DOSSIER.parent).as_posix()


def chemin_club(code, club):
    return DOSSIER / "clubs" / code / f"{slug(club)}.png"


def chemin_championnat(code):
    return DOSSIER / "championnats" / f"{code}.png"


def _json(session, url, **params):
    """Interroge l'API ; en cas de limite de débit (429), attend et réessaie."""
    for tentative in range(6):
        time.sleep(PAUSE)
        reponse = session.get(f"{API}/{url}", params=params, timeout=20)
        if reponse.status_code != 429:
            reponse.raise_for_status()
            return reponse.json()
        time.sleep(30 * (tentative + 1))
    reponse.raise_for_status()


def _enregistrer(session, url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    reponse = session.get(url, timeout=30)
    reponse.raise_for_status()
    destination.write_bytes(reponse.content)
    recadrer(destination)


def recadrer(chemin):
    """Recadre l'écusson au plus près du dessin, avec une petite marge, et limite sa taille.

    Les sources livrent des images de formats variés (139 × 181, 512 × 512) avec plus ou moins
    de marge transparente : à taille d'affichage égale, certains écussons paraissaient minuscules.
    Renvoie True si l'image a changé.
    """
    with Image.open(chemin) as source:
        image = source.convert("RGBA")
    cadre = image.getchannel("A").point(lambda a: 255 if a > 16 else 0).getbbox()
    if cadre is None:
        return False
    dessin = image.crop(cadre)
    marge = round(max(dessin.size) * MARGE)
    ecarts = (cadre[0], cadre[1], image.width - cadre[2], image.height - cadre[3])
    if max(image.size) <= TAILLE_MAX and max(ecarts) <= marge + 2:
        return False  # déjà recadré : ne pas rogner le bord adouci à chaque passage
    resultat = Image.new("RGBA", (dessin.width + 2 * marge, dessin.height + 2 * marge))
    resultat.paste(dessin, (marge, marge))
    resultat.thumbnail((TAILLE_MAX, TAILLE_MAX), Image.Resampling.LANCZOS)
    resultat.save(chemin, optimize=True)
    return True


def recadrer_tous():
    """Applique recadrer aux écussons déjà téléchargés ; renvoie le nombre d'images modifiées."""
    return sum(recadrer(chemin) for chemin in sorted(DOSSIER.rglob("*.png")))


def telecharger_championnats(session):
    manquants = []
    for code, identifiant in LIGUES.items():
        if chemin_championnat(code).exists():
            continue
        ligue = (_json(session, "lookupleague.php", id=identifiant).get("leagues") or [{}])[0]
        url = ligue.get("strBadge") or ligue.get("strLogo")
        if url:
            _enregistrer(session, url, chemin_championnat(code))
        else:
            manquants.append(code)
    return manquants


def telecharger_clubs(session):
    """Télécharge l'écusson de chaque club. Renvoie la liste des clubs introuvables."""
    matchs = pd.read_csv(FICHIER)
    manquants = []
    for code, groupe in matchs.groupby("Championnat"):
        for club in sorted(set(groupe["HomeTeam"]) | set(groupe["AwayTeam"])):
            if chemin_club(code, club).exists():
                continue
            nom = ALIAS.get(club, club)
            equipes = _json(session, "searchteams.php", t=nom).get("teams") or []
            equipes = [e for e in equipes if e.get("strSport") == "Soccer"]
            retenues = [e for e in equipes if e.get("strCountry") == PAYS[code]] or equipes
            url = retenues[0].get("strBadge") if retenues else None
            if url:
                _enregistrer(session, url, chemin_club(code, club))
            else:
                manquants.append(f"{code}/{club}")
    return manquants


def _simplifie(texte):
    """Nom réduit à l'essentiel pour comparer : sans accents ni préfixes (FC, AS, SC…)."""
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    texte = re.sub(r"\b(fc|afc|ac|as|sc|cf|ca|ud|rc|rcd|us|ssc|vfl|vfb|fsv|tsg|sv|1|fk|1899|04|05|98)\b|\.", "", texte)
    return re.sub(r"[^a-z0-9]", "", texte)


def _fichier_depot(club, fichiers):
    """Le fichier du dépôt qui correspond à ce club, ou None si aucun ne convient sans ambiguïté."""
    if club in FICHIERS_DEPOT:
        return FICHIERS_DEPOT[club] if FICHIERS_DEPOT[club] in fichiers else None
    simplifies = {_simplifie(f): f for f in fichiers}
    nom = _simplifie(ALIAS.get(club, club))
    if nom in simplifies:
        return simplifies[nom]
    inclus = [f for k, f in simplifies.items() if len(nom) >= 5 and (nom in k or k in nom)]
    if len(inclus) == 1:
        return inclus[0]
    proches = difflib.get_close_matches(nom, list(simplifies), 1, 0.9)
    return simplifies[proches[0]] if proches else None


def telecharger_depot(session):
    """Récupère les écussons du dépôt GitHub pour les clubs encore absents."""
    matchs = pd.read_csv(FICHIER)
    for code, dossier in DOSSIERS_DEPOT.items():
        url = f"https://api.github.com/repos/{DEPOT}/contents/logos/{requests.utils.quote(dossier)}"
        reponse = session.get(url, timeout=20)
        reponse.raise_for_status()
        fichiers = {f["name"][:-4]: f["download_url"] for f in reponse.json() if f["name"].endswith(".png")}
        groupe = matchs[matchs["Championnat"] == code]
        for club in sorted(set(groupe["HomeTeam"]) | set(groupe["AwayTeam"])):
            fichier = _fichier_depot(club, list(fichiers))
            if fichier and not chemin_club(code, club).exists():
                _enregistrer(session, fichiers[fichier], chemin_club(code, club))


def telecharger():
    """Télécharge les écussons absents ; ceux déjà présents ne sont pas retéléchargés."""
    with requests.Session() as session:
        session.headers["User-Agent"] = "simulateur-foot"
        telecharger_depot(session)
        manquants = [f"championnat {c}" for c in telecharger_championnats(session)]
        manquants += telecharger_clubs(session)
    return manquants


def main():
    manquants = telecharger()
    recadres = recadrer_tous()
    print(f"Écussons enregistrés dans {DOSSIER} ({recadres} recadrés)")
    if manquants:
        print(f"{len(manquants)} introuvables (ajoutez un alias dans ALIAS) : {', '.join(manquants)}")


if __name__ == "__main__":
    main()
