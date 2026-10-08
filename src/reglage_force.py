"""Cherche les paramètres de la force des clubs qui prédisent le mieux les matchs passés."""

from itertools import product

from force_clubs import SCORE_REEL, calculer_forces, charger_matchs

GRILLE = {
    "k": [10, 15, 20, 25, 30, 40],
    "avantage_terrain": [0, 20, 40, 60],
    "note_promu": [1350, 1400, 1450],
    "retour_moyenne": [0.0, 0.15, 0.25, 0.35, 0.5],
}
SAISONS_REGLAGE = [2223, 2324, 2425]
SAISON_TEST = 2526


def erreur(matchs, saisons):
    """Écart quadratique moyen entre le score réel et le score attendu."""
    selection = matchs[matchs["Saison"].isin(saisons)]
    score_reel = selection["FTR"].map(SCORE_REEL)
    return ((score_reel - selection["score_attendu"]) ** 2).mean()


def main():
    matchs = charger_matchs()

    # Référence naïve : annoncer toujours le score moyen de l'équipe à domicile
    score_moyen = matchs[matchs["Saison"].isin(SAISONS_REGLAGE)]["FTR"].map(SCORE_REEL).mean()
    test = matchs[matchs["Saison"] == SAISON_TEST]
    erreur_naive = ((test["FTR"].map(SCORE_REEL) - score_moyen) ** 2).mean()

    # Paramètres provisoires actuels
    matchs_provisoires, _ = calculer_forces(matchs)

    # Toutes les combinaisons de la grille
    resultats = []
    for valeurs in product(*GRILLE.values()):
        parametres = dict(zip(GRILLE.keys(), valeurs))
        matchs_notes, _ = calculer_forces(matchs, **parametres)
        resultats.append((
            erreur(matchs_notes, SAISONS_REGLAGE),
            erreur(matchs_notes, [SAISON_TEST]),
            parametres,
        ))
    resultats.sort(key=lambda x: x[0])

    print(f"Combinaisons testées : {len(resultats)}")
    print(f"Erreur naïve sur la saison test       : {erreur_naive:.4f}")
    print(f"Erreur provisoire sur la saison test  : {erreur(matchs_provisoires, [SAISON_TEST]):.4f}")
    print("\nCinq meilleures combinaisons (erreur réglage | erreur test | paramètres) :")
    for erreur_reglage, erreur_test, parametres in resultats[:5]:
        print(f"  {erreur_reglage:.4f} | {erreur_test:.4f} | {parametres}")


if __name__ == "__main__":
    main()