"""Calcule la force (note Elo) de chaque club avant chacun de ses matchs.

Après chaque match, le vainqueur prend des points au vaincu : d'autant plus que
le résultat était inattendu, et d'autant plus que la victoire est large. Une
victoire d'un but (ou un nul) compte pour 1, de deux buts pour 1,5, de trois
buts pour 2, etc. (POIDS_ECART). Réglage : reglage_force.py.
"""

import numpy as np
import pandas as pd

from .collecte_resultats import DOSSIER_DATA, FICHIER

K = 20
AVANTAGE_TERRAIN = 40
NOTE_INITIALE = 1500
NOTE_PROMU = 1400
RETOUR_MOYENNE = 0.0
POIDS_ECART = 0.5  # points de K en plus par but d'écart au-delà du premier
SCORE_REEL = {"H": 1.0, "D": 0.5, "A": 0.0}


def score_attendu(note_dom, note_ext, avantage_terrain=AVANTAGE_TERRAIN):
    """Score attendu de l'équipe à domicile, entre 0 et 1."""
    ecart = note_dom + avantage_terrain - note_ext
    return 1 / (1 + 10 ** (-ecart / 400))


def facteur_ecart(ecart_buts, poids_ecart=POIDS_ECART):
    """Multiplicateur de la correction Elo selon l'écart de buts (1 pour un nul ou un but d'écart)."""
    return 1 + poids_ecart * np.maximum(np.abs(ecart_buts) - 1, 0)


def notes_debut_saison(notes, clubs_saison, clubs_saison_precedente,
                       note_promu=NOTE_PROMU, retour_moyenne=RETOUR_MOYENNE):
    """Prépare les notes au début d'une saison."""
    nouvelles_notes = {}
    for club in clubs_saison:
        if clubs_saison_precedente is None:
            # Première saison du fichier : tout le monde part du même point
            nouvelles_notes[club] = NOTE_INITIALE
        elif club in clubs_saison_precedente:
            # Club déjà présent : sa note se rapproche de la moyenne
            nouvelles_notes[club] = notes[club] + retour_moyenne * (NOTE_INITIALE - notes[club])
        else:
            # Club absent la saison précédente : c'est un promu
            nouvelles_notes[club] = note_promu
    return nouvelles_notes


def charger_matchs(championnat="F1"):
    """Lit les résultats d'un championnat, triés par saison puis par date."""
    matchs = pd.read_csv(FICHIER, parse_dates=["Date"])
    matchs = matchs[matchs["Championnat"] == championnat].drop(columns="Championnat")
    return matchs.sort_values(["Saison", "Date"], kind="stable").reset_index(drop=True)


def calculer_forces(matchs, k=K, avantage_terrain=AVANTAGE_TERRAIN,
                    note_promu=NOTE_PROMU, retour_moyenne=RETOUR_MOYENNE, poids_ecart=POIDS_ECART):
    """Renvoie les matchs avec les notes d'avant-match, et les notes finales."""
    matchs = matchs.copy()
    notes = {}
    clubs_saison_precedente = None
    force_dom, force_ext, promu_dom, promu_ext, attendus = [], [], [], [], []

    for saison, matchs_saison in matchs.groupby("Saison", sort=True):
        clubs_saison = set(matchs_saison["HomeTeam"]) | set(matchs_saison["AwayTeam"])
        notes = notes_debut_saison(notes, clubs_saison, clubs_saison_precedente,
                                   note_promu, retour_moyenne)

        for match in matchs_saison.itertuples():
            dom, ext = match.HomeTeam, match.AwayTeam

            # Notes avant le match : ce sont elles que le modèle utilisera
            force_dom.append(notes[dom])
            force_ext.append(notes[ext])
            if clubs_saison_precedente is None:
                promu_dom.append(float("nan"))
                promu_ext.append(float("nan"))
            else:
                promu_dom.append(int(dom not in clubs_saison_precedente))
                promu_ext.append(int(ext not in clubs_saison_precedente))

            # Mise à jour après le match
            attendu = score_attendu(notes[dom], notes[ext], avantage_terrain)
            attendus.append(attendu)
            correction = (k * facteur_ecart(match.FTHG - match.FTAG, poids_ecart)
                          * (SCORE_REEL[match.FTR] - attendu))
            notes[dom] += correction
            notes[ext] -= correction

        clubs_saison_precedente = clubs_saison

    matchs["force_dom"] = force_dom
    matchs["force_ext"] = force_ext
    matchs["promu_dom"] = promu_dom
    matchs["promu_ext"] = promu_ext
    matchs["score_attendu"] = attendus
    return matchs, notes


def evolution_recente(matchs_saison, notes, nb=5):
    """Variation de la note de chaque club sur ses `nb` derniers matchs de la saison."""
    variations = {}
    for club, note in notes.items():
        siens = matchs_saison[(matchs_saison["HomeTeam"] == club) | (matchs_saison["AwayTeam"] == club)]
        siens = siens.sort_values("Date").tail(nb)
        if siens.empty:
            variations[club] = 0.0
            continue
        premier = siens.iloc[0]
        avant = premier["force_dom"] if premier["HomeTeam"] == club else premier["force_ext"]
        variations[club] = note - avant
    return pd.Series(variations)


def main(championnat="F1"):
    matchs, notes = calculer_forces(charger_matchs(championnat))
    matchs.to_csv(DOSSIER_DATA / "matchs_force.csv", index=False)

    print("Notes actuelles :")
    for club, note in sorted(notes.items(), key=lambda x: -x[1]):
        print(f"  {club:<12} {note:.0f}")


if __name__ == "__main__":
    main()