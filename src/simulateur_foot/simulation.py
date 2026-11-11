"""Simule la fin de la saison en cours par tirage au sort (méthode de Monte-Carlo).

Chaque match restant est tiré selon ses probabilités A, D, H. Les notes Elo
restent figées à leur valeur du jour : on simule ce que l'on sait aujourd'hui.
Le simulateur ne tire pas de scores, donc les égalités de points sont
départagées par la différence de buts actuelle, puis au hasard.
Les zones du classement (Europe, montée, barrage, relégation) viennent des
règles de chaque championnat, dans championnats.py.
"""

from itertools import permutations

import numpy as np
import pandas as pd

from .championnats import CHAMPIONNATS
from .prediction import SAISON_EN_COURS, charger_forces, entrainer, probabilites

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


def simuler(table, restants, proba, nb=NB_SIMULATIONS, graine=0):
    """Rangs finaux simulés : tableau (nb simulations × clubs), 1 = premier."""
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

    # Départage : différence de buts actuelle, puis hasard (tous deux < 1 point)
    diff = table["diff_buts"].to_numpy(dtype=float)
    cle = points + (diff - diff.min()) / (diff.max() - diff.min() + 1) * 0.5
    cle += generateur.random(points.shape) * 0.01
    rangs = (-cle).argsort(axis=1).argsort(axis=1) + 1
    return points, rangs


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


def simuler_saison(championnat="F1", nb=NB_SIMULATIONS, graine=0):
    """Enchaîne tout : notes, modèle, matchs restants, tirages, résumé."""
    matchs, notes = charger_forces(championnat)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    restants = matchs_restants(saison)
    proba = probabilites(entrainer(matchs), restants["HomeTeam"].map(notes),
                         restants["AwayTeam"].map(notes))
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
