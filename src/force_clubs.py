"""Calcule la force (note Elo) de chaque club avant chacun de ses matchs."""

from pathlib import Path

import pandas as pd

K = 20
AVANTAGE_TERRAIN = 40
NOTE_INITIALE = 1500
NOTE_PROMU = 1400
RETOUR_MOYENNE = 0.0
DOSSIER_DATA = Path(__file__).resolve().parents[1] / "data"
SCORE_REEL = {"H": 1.0, "D": 0.5, "A": 0.0}


def score_attendu(note_dom, note_ext, avantage_terrain=AVANTAGE_TERRAIN):
    """Score attendu de l'équipe à domicile, entre 0 et 1."""
    ecart = note_dom + avantage_terrain - note_ext
    return 1 / (1 + 10 ** (-ecart / 400))


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


def charger_matchs():
    """Lit le fichier de résultats, trié par saison puis par date."""
    matchs = pd.read_csv(DOSSIER_DATA / "resultats_ligue1.csv", parse_dates=["Date"])
    return matchs.sort_values(["Saison", "Date"]).reset_index(drop=True)


def calculer_forces(matchs, k=K, avantage_terrain=AVANTAGE_TERRAIN,
                    note_promu=NOTE_PROMU, retour_moyenne=RETOUR_MOYENNE):
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
            correction = k * (SCORE_REEL[match.FTR] - attendu)
            notes[dom] += correction
            notes[ext] -= correction

        clubs_saison_precedente = clubs_saison

    matchs["force_dom"] = force_dom
    matchs["force_ext"] = force_ext
    matchs["promu_dom"] = promu_dom
    matchs["promu_ext"] = promu_ext
    matchs["score_attendu"] = attendus
    return matchs, notes


def main():
    matchs, notes = calculer_forces(charger_matchs())
    matchs.to_csv(DOSSIER_DATA / "matchs_force.csv", index=False)

    print("Notes actuelles :")
    for club, note in sorted(notes.items(), key=lambda x: -x[1]):
        print(f"  {club:<12} {note:.0f}")


if __name__ == "__main__":
    main()