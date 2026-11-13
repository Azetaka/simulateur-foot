"""Onglet « Les forces du moment »."""

import html

import streamlit as st

from simulateur_foot.force_clubs import NOTE_INITIALE, NOTE_PROMU
from simulateur_foot.interface.commun import (
    chiffre_cle,
    ecusson,
    explication,
    forces_du_jour,
    rang,
)
from simulateur_foot.logos import chemin_club


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    code, version = (
        ctx.code, ctx.version)

    explication("Les clubs rangés par leur note Elo d'aujourd'hui, celle qui sert à tous les calculs. Le "
                "classement récompense les points déjà pris ; la note, elle, juge la force actuelle : qui a "
                "battu qui, par quel écart, et contre quelle opposition. Quand les deux divergent, c'est un club "
                "en avance ou en retard sur son niveau réel. La variation à droite donne la tendance sur les "
                "5 derniers matchs.", titre="Comment lire ce classement")
    forces = forces_du_jour(code, version)
    plus_fort, en_forme, en_peine = forces.index[0], forces["variation"].idxmax(), forces["variation"].idxmin()
    f1, f2, f3 = st.columns(3)
    chiffre_cle(f1, "Le plus fort aujourd'hui", ecusson(chemin_club(code, plus_fort)) + plus_fort,
                f"Note {forces.loc[plus_fort, 'note']:.0f} · {rang(int(forces.loc[plus_fort, 'rang']))} du classement")
    chiffre_cle(f2, "En pleine forme", ecusson(chemin_club(code, en_forme)) + en_forme,
                f"{forces.loc[en_forme, 'variation']:+.0f} points sur ses 5 derniers matchs")
    chiffre_cle(f3, "En difficulté", ecusson(chemin_club(code, en_peine)) + en_peine,
                f"{forces.loc[en_peine, 'variation']:+.0f} points sur ses 5 derniers matchs")

    bas, haut = forces["note"].min() - 30, forces["note"].max() + 30
    pct = lambda valeur: f"{(valeur - bas) / (haut - bas) * 100:.2f}"
    lignes = []
    for i, (club, ligne) in enumerate(forces.iterrows(), start=1):
        avance = int(ligne.rang) - i  # positif : mieux noté que classé
        commentaire = (" · mieux que son classement" if avance >= 2 else
                       " · moins bien que son classement" if avance <= -2 else "")
        classe = "haut" if ligne.variation >= 10 else "bas" if ligne.variation <= -10 else ""
        logo = ecusson(chemin_club(code, club), alt=club)
        lignes.append(f"""
<div class="jr fr">
  <div class="rang">{i}</div>{logo}
  <div class="ident"><b>{html.escape(club)}</b><span>{rang(int(ligne.rang))} du classement{commentaire}</span></div>
  <div class="piste">
    <div class="repere" style="left:{pct(NOTE_INITIALE)}%" title="{NOTE_INITIALE} : club moyen"></div>
    <div class="actuel" style="width:{pct(ligne.note)}%"></div>
    <span class="val" style="left:{pct(ligne.note)}%">{ligne.note:.0f}</span>
  </div>
  <div class="delta {classe}" title="Variation de la note sur les 5 derniers matchs">{ligne.variation:+.0f}</div>
  <div class="bulle">
    <div class="tete">{logo}<div><b>{html.escape(club)}</b><span>{rang(i)} à la note, {rang(int(ligne.rang))} au classement</span></div></div>
    <dl>
      <dt>Note Elo</dt><dd class="fort">{ligne.note:.0f}</dd>
      <dt>5 derniers matchs</dt><dd>{ligne.variation:+.0f} points</dd>
      <dt>Matchs joués</dt><dd>{int(ligne.joues)}</dd>
      <dt>Adversaires restants</dt><dd>{ligne.calendrier:.0f} en moyenne</dd>
    </dl>
  </div>
</div>""")
    st.html('<div class="legende-classement"><span><i></i>Note Elo aujourd\'hui</span>'
            f'<span><i class="repere-leg"></i>{NOTE_INITIALE}, un club moyen</span>'
            '<span>Variation sur 5 matchs : <b>plein</b> en hausse de 10 points ou plus, '
            '<b>pointillé</b> en baisse de 10 ou plus</span></div>'
            f'<div class="classement">{"".join(lignes)}</div>')
    dur, facile = forces["calendrier"].idxmax(), forces["calendrier"].idxmin()
    st.caption(f"Un club qui n'était pas dans le championnat la saison passée démarre à {NOTE_PROMU}. "
               f"Survolez un club pour le détail. Calendrier restant le plus dur : {dur} (adversaires notés "
               f"{forces.loc[dur, 'calendrier']:.0f} en moyenne, terrain compris), le plus abordable : {facile} "
               f"({forces.loc[facile, 'calendrier']:.0f}).")
