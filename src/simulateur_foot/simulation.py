"""Simule la fin de la saison en cours par tirage au sort (méthode de Monte-Carlo).

Chaque match restant est tiré selon ses probabilités A, D, H, puis son écart de
buts selon le modèle de score (scores.py). Par défaut, les notes Elo évoluent
pendant chaque saison simulée : après chaque journée tirée au sort, elles sont
mises à jour avec la même règle que pour les vrais matchs (écart de buts
compris), si bien qu'un club en série favorable devient favori des journées
suivantes. La différence de buts évolue aussi et sert à départager les
égalités de points, puis le hasard tranche. La variante à notes figées
(simuler) garde les notes et la différence de buts du jour jusqu'au bout.
Les zones du classement (Europe, montée, barrage, relégation) viennent des
règles de chaque championnat, dans championnats.py.
"""

from itertools import permutations

import numpy as np
import pandas as pd

from .championnats import CHAMPIONNATS
from .force_clubs import AVANTAGE_TERRAIN, K, POIDS_ECART, facteur_ecart, score_attendu
from .prediction import SAISON_EN_COURS, charger_forces, entrainer, probabilites, probabilites_tableau
from .scores import entrainer_scores, tirer_ecarts

POINTS = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}
NB_SIMULATIONS = 10_000


def classement(matchs_saison):
    """Classement actuel : matchs joués, points, différence de buts."""
    lignes = []
    for match in matchs_saison.itertuples():
        pts_dom, pts_ext = POINTS[match.FTR]
        ecart = match.FTHG - match.FTAG
        lignes.append((match.HomeTeam, pts_dom, ecart))
        lignes.append((match.AwayTeam, pts_ext, -ecart))
    table = pd.DataFrame(lignes, columns=["club", "points", "diff_buts"])
    table = table.groupby("club").agg(joues=("points", "size"), points=("points", "sum"),
                                       diff_buts=("diff_buts", "sum"))
    return table.sort_values(["points", "diff_buts"], ascending=False)


def points_attendus(matchs_saison, proba):
    """Points que le modèle attendait de chaque club sur les matchs déjà joués.

    proba donne, pour chaque match (même ordre que matchs_saison), les chances
    A, D, H calculées avec les notes d'avant le match : c'est le pronostic qu'on
    aurait fait la veille, pas une relecture après coup.
    """
    proba = proba.reset_index(drop=True)
    dom = 3 * proba["H"] + proba["D"]
    ext = 3 * proba["A"] + proba["D"]
    lignes = pd.concat([
        pd.DataFrame({"club": matchs_saison["HomeTeam"].to_numpy(), "attendus": dom.to_numpy()}),
        pd.DataFrame({"club": matchs_saison["AwayTeam"].to_numpy(), "attendus": ext.to_numpy()}),
    ])
    return lignes.groupby("club")["attendus"].sum()


def matchs_restants(matchs_saison):
    """Toutes les affiches aller et retour qui n'ont pas encore été jouées."""
    clubs = sorted(set(matchs_saison["HomeTeam"]) | set(matchs_saison["AwayTeam"]))
    jouees = set(zip(matchs_saison["HomeTeam"], matchs_saison["AwayTeam"]))
    restantes = [paire for paire in permutations(clubs, 2) if paire not in jouees]
    return pd.DataFrame(restantes, columns=["HomeTeam", "AwayTeam"])


def calendrier(restants, graine=0, premiers=None):
    """Numéro de journée de chaque match restant (0, 1, 2…).

    La source ne donne pas les dates des matchs à venir : on mélange les
    affiches, puis on remplit les journées dans l'ordre, sans qu'un club joue
    deux fois dans la même journée. `premiers` (paires (domicile, extérieur)
    annoncées pour la prochaine journée) sont placés en tête, donc joués d'abord.
    """
    ordre = np.random.default_rng(graine).permutation(len(restants))
    if premiers:
        annonces = np.array([paire in premiers for paire in zip(restants["HomeTeam"], restants["AwayTeam"])])
        ordre = np.concatenate([ordre[annonces[ordre]], ordre[~annonces[ordre]]])
    occupes, numero = [], np.empty(len(restants), dtype=int)
    for i in ordre:
        dom, ext = restants["HomeTeam"].iat[i], restants["AwayTeam"].iat[i]
        j = next((j for j, clubs in enumerate(occupes) if dom not in clubs and ext not in clubs), len(occupes))
        if j == len(occupes):
            occupes.append(set())
        occupes[j] |= {dom, ext}
        numero[i] = j
    return numero


def departager(table, points, generateur, diff=None):
    """Rangs à partir des points : différence de buts (celle du jour, ou simulée), puis hasard (tous deux < 1 point)."""
    if diff is None:
        diff = table["diff_buts"].to_numpy(dtype=float)
    cle = points + (diff - diff.min()) / (diff.max() - diff.min() + 1) * 0.5
    cle += generateur.random(points.shape) * 0.01
    return (-cle).argsort(axis=1).argsort(axis=1) + 1


def simuler_notes_evolutives(table, restants, notes, modele, nb=NB_SIMULATIONS, graine=0, k=K,
                             modele_scores=None, poids_ecart=POIDS_ECART, premiers=None):
    """Comme simuler, mais les notes Elo bougent après chaque journée tirée au sort.

    notes : notes du jour de chaque club ; modele : celui de prediction.entrainer ;
    modele_scores : celui de scores.entrainer_scores, qui tire l'écart de buts de
    chaque match (sans lui, toute victoire vaut un but d'écart). premiers : affiches
    annoncées pour la prochaine journée, jouées en premier.
    Renvoie points et rangs finaux, tableaux (nb simulations × clubs).
    """
    clubs = list(table.index)
    position = {club: i for i, club in enumerate(clubs)}
    dom = restants["HomeTeam"].map(position).to_numpy()
    ext = restants["AwayTeam"].map(position).to_numpy()
    journee = calendrier(restants, graine, premiers)

    generateur = np.random.default_rng(graine)
    elo = np.tile(np.array([notes[club] for club in clubs], dtype=float), (nb, 1))
    points = np.tile(table["points"].to_numpy(dtype=float), (nb, 1))
    diff = np.tile(table["diff_buts"].to_numpy(dtype=float), (nb, 1))
    for j in range(journee.max() + 1 if len(restants) else 0):
        for i in np.flatnonzero(journee == j):  # un club au plus une fois par journée
            d, e = dom[i], ext[i]
            note_dom, note_ext = elo[:, d], elo[:, e]
            if modele_scores is None:
                proba = probabilites_tableau(modele, note_dom, note_ext)
                u = generateur.random(nb)
                ecart = np.where(u < proba[:, 0], -1, np.where(u < proba[:, 0] + proba[:, 1], 0, 1))
            else:
                ecart = tirer_ecarts(modele_scores, modele, note_dom, note_ext, generateur)
            points[:, d] += np.where(ecart > 0, 3, np.where(ecart == 0, 1, 0))
            points[:, e] += np.where(ecart < 0, 3, np.where(ecart == 0, 1, 0))
            diff[:, d] += ecart
            diff[:, e] -= ecart
            # Même mise à jour Elo que pour les vrais matchs (force_clubs.calculer_forces)
            reel = np.where(ecart > 0, 1.0, np.where(ecart == 0, 0.5, 0.0))
            correction = k * facteur_ecart(ecart, poids_ecart) * (reel - score_attendu(note_dom, note_ext))
            elo[:, d] += correction
            elo[:, e] -= correction
    return points, departager(table, points, generateur, diff)


def simuler(table, restants, proba, nb=NB_SIMULATIONS, graine=0):
    """Rangs finaux simulés avec des probabilités fixes : tableau (nb simulations × clubs), 1 = premier."""
    clubs = list(table.index)
    position = {club: i for i, club in enumerate(clubs)}
    dom = restants["HomeTeam"].map(position).to_numpy()
    ext = restants["AwayTeam"].map(position).to_numpy()

    # Tirage des résultats : A si u < pA, D si u < pA + pD, sinon H
    generateur = np.random.default_rng(graine)
    seuils = proba[["A", "D"]].to_numpy().cumsum(axis=1)
    u = generateur.random((nb, len(restants)))
    exterieur, nul = u < seuils[:, 0], (u >= seuils[:, 0]) & (u < seuils[:, 1])
    pts_dom = np.where(exterieur, 0, np.where(nul, 1, 3))
    pts_ext = np.where(exterieur, 3, np.where(nul, 1, 0))

    points = np.tile(table["points"].to_numpy(dtype=float), (nb, 1))
    for i in range(len(restants)):
        points[:, dom[i]] += pts_dom[:, i]
        points[:, ext[i]] += pts_ext[:, i]

    return points, departager(table, points, generateur)


def difficulte_calendrier(restants, notes, avantage_terrain=AVANTAGE_TERRAIN):
    """Note moyenne des adversaires restants de chaque club, terrain compris.

    Un adversaire reçu compte sa note moins l'avantage du terrain, un adversaire
    chez qui l'on se déplace sa note plus cet avantage : plus le chiffre est haut,
    plus la fin de saison est difficile.
    """
    notes = pd.Series(notes)
    lignes = pd.concat([
        pd.DataFrame({"club": restants["HomeTeam"].to_numpy(),
                      "adversaire": restants["AwayTeam"].map(notes).to_numpy() - avantage_terrain}),
        pd.DataFrame({"club": restants["AwayTeam"].to_numpy(),
                      "adversaire": restants["HomeTeam"].map(notes).to_numpy() + avantage_terrain}),
    ])
    return lignes.groupby("club")["adversaire"].mean()


def resume(table, points, rangs, regles=CHAMPIONNATS["F1"]):
    """Par club : points actuels et finaux moyens, probabilités de chaque zone."""
    nb_clubs = len(table)
    limite_relegation = nb_clubs - regles.relegues
    resultat = table.copy()
    resultat["points_finaux"] = points.mean(axis=0)
    resultat["titre"] = (rangs == 1).mean(axis=0)
    resultat["haut"] = (rangs <= regles.haut[1]).mean(axis=0)
    resultat["barrage"] = (rangs == limite_relegation).mean(axis=0) if regles.barrage else 0.0
    resultat["relegation"] = (rangs > limite_relegation).mean(axis=0)
    resultat["rang_moyen"] = rangs.mean(axis=0)
    return resultat.sort_values("rang_moyen")


def simuler_saison(championnat="F1", nb=NB_SIMULATIONS, graine=0, notes_evolutives=True):
    """Enchaîne tout : notes, modèle, matchs restants, tirages, résumé."""
    matchs, notes = charger_forces(championnat)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    restants = matchs_restants(saison)
    modele = entrainer(matchs)
    if notes_evolutives:
        points, rangs = simuler_notes_evolutives(table, restants, notes, modele, nb, graine,
                                                 modele_scores=entrainer_scores(matchs))
    else:
        proba = probabilites(modele, restants["HomeTeam"].map(notes), restants["AwayTeam"].map(notes))
        points, rangs = simuler(table, restants, proba, nb, graine)
    return resume(table, points, rangs, CHAMPIONNATS[championnat]), len(restants)


def main(championnat="F1"):
    regles = CHAMPIONNATS[championnat]
    resultat, nb_restants = simuler_saison(championnat)
    print(f"{regles.nom}, saison {SAISON_EN_COURS} : {nb_restants} matchs restants, "
          f"{NB_SIMULATIONS} simulations\n")
    print(f"{'club':<16}{'pts':>5}{'final':>7}{'titre':>8}{'haut':>7}{'rel.':>7}")
    for club, ligne in resultat.iterrows():
        print(f"{club:<16}{ligne.points:>5}{ligne.points_finaux:>7.1f}{ligne.titre:>8.1%}"
              f"{ligne.haut:>7.1%}{ligne.relegation:>7.1%}")
