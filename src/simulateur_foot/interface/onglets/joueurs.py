"""Onglet « Les meilleurs joueurs »."""

import html

import streamlit as st

from simulateur_foot.interface.commun import (
    donnees_joueurs,
    ecusson,
    explication,
    joueurs_projetes,
    nom_saison,
)
from simulateur_foot.logos import chemin_club
from simulateur_foot.prediction import SAISON_EN_COURS


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    code, saison, version = (
        ctx.code, ctx.saison, ctx.version)

    explication("Les 50 meilleurs buteurs et les 50 meilleurs passeurs du championnat, avec leur total "
                "prévu à la fin de saison. Le calcul suppose que chaque joueur garde la même part des "
                "matchs de son club. Son rythme est ramené vers la moyenne, car un départ canon se "
                "prolonge rarement tel quel, puis ajusté selon que les matchs restants de son club sont "
                "plus faciles ou plus durs que ceux déjà joués. On tire ensuite des milliers de fins de "
                "saison au hasard : le trait couvre 8 saisons simulées sur 10.",
                titre="Comment lire la prévision")
    version_joueurs = donnees_joueurs()
    if version_joueurs is None:
        st.warning("Les statistiques des joueurs n'ont pas pu être téléchargées (pas de réseau ?). "
                   "Réessayez avec `uv run simulateur-foot joueurs`.")
    else:
        tous, clubs_inconnus = joueurs_projetes(code, version, version_joueurs)
        if clubs_inconnus:
            st.warning("Clubs non reconnus dans les données ESPN, leurs joueurs manquent : "
                       f"{', '.join(clubs_inconnus)}. À ajouter dans CLUBS_ESPN (joueurs.py).")
        j1, j2 = st.columns([2, 1], vertical_alignment="bottom")
        choix = j1.segmented_control("Classement", ["Buteurs", "Passeurs"], default="Buteurs",
                                     label_visibility="collapsed") or "Buteurs"
        nb_joueurs = j2.select_slider("Joueurs affichés", [10, 15, 25, 50], value=15)
        stat, unite = ("buts", "buts") if choix == "Buteurs" else ("passes", "passes décisives")
        top = tous.sort_values([stat, f"{stat}_prevus"], ascending=False).head(nb_joueurs)
        top = top[top[stat] > 0].copy()
        st.caption(f"Saison {nom_saison(SAISON_EN_COURS)}, résultats au {saison['Date'].max():%d/%m/%Y}. "
                   f"Données : ESPN. La barre pleine montre le total actuel, la barre claire le total prévu en fin "
                   f"de saison, le trait noir la fourchette. Passez la souris sur un joueur pour le détail.")

        singulier = "but" if stat == "buts" else "passe décisive"
        maxi = float(top[f"{stat}_haut"].max()) * 1.12
        pct = lambda valeur: f"{max(valeur, 0) / maxi * 100:.2f}"
        lignes = []
        for i, j in enumerate(top.itertuples(index=False), start=1):
            actuel, prevu = int(getattr(j, stat)), round(getattr(j, f"{stat}_prevus"))
            bas, haut = round(getattr(j, f"{stat}_bas")), round(getattr(j, f"{stat}_haut"))
            rythme = f"{actuel / j.matchs:.2f}".replace(".", ",")
            retenu = f"{getattr(j, f'{stat}_rythme'):.2f}".replace(".", ",")
            calendrier = ("plus facile" if j.facteur_calendrier > 1.03 else
                          "plus dur" if j.facteur_calendrier < 0.97 else "équivalent")
            largeur = f"{(getattr(j, f'{stat}_haut') - getattr(j, f'{stat}_bas')) / maxi * 100:.2f}"
            logo = ecusson(chemin_club(code, j.club), alt=j.club)
            nom, club = html.escape(j.joueur), html.escape(j.club)
            lignes.append(f"""
<div class="jr">
  <div class="rang">{i}</div>{logo}
  <div class="ident"><b>{nom}</b><span>{club}</span></div>
  <div class="piste">
    <div class="prevu" style="width:{pct(getattr(j, f"{stat}_prevus"))}%"></div>
    <div class="actuel" style="width:{pct(getattr(j, stat))}%"></div>
    <div class="fourch" style="left:{pct(getattr(j, f"{stat}_bas"))}%;width:{largeur}%"></div>
    <span class="val" style="left:{pct(getattr(j, f"{stat}_haut"))}%">{prevu}</span>
  </div>
  <div class="bulle">
    <div class="tete">{logo}<div><b>{nom}</b><span>{club}</span></div></div>
    <dl>
      <dt>Aujourd'hui</dt><dd>{actuel} {unite}</dd>
      <dt>Matchs joués</dt><dd>{int(j.matchs)}</dd>
      <dt>Rythme actuel</dt><dd>{rythme} {singulier} / match</dd>
      <dt>Rythme retenu</dt><dd>{retenu} / match</dd>
      <dt>Matchs restants</dt><dd>{calendrier}</dd>
      <dt>Fin de saison</dt><dd class="fort">≈ {prevu} {unite}</dd>
      <dt>Fourchette</dt><dd>{bas} à {haut}</dd>
    </dl>
  </div>
</div>""")
        st.html('<div class="legende-classement"><span><i></i>Total actuel</span>'
                '<span><i class="clair"></i>Prévu en fin de saison</span>'
                '<span><i class="trait"></i>Fourchette probable (8 saisons sur 10)</span></div>'
                f'<div class="classement">{"".join(lignes)}</div>')
