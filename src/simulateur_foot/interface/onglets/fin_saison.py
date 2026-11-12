"""Onglet « La fin de saison »."""

import altair as alt
import pandas as pd
import streamlit as st

from simulateur_foot.force_clubs import NOTE_PROMU
from simulateur_foot.interface.commun import (
    chiffre_cle,
    decimal,
    ecusson,
    explication,
    fin_de_saison,
    image,
    pourcent,
)
from simulateur_foot.logos import chemin_club


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    affiches_annoncees, c, code, rangs_actuels, regles, version = (
        ctx.affiches_annoncees, ctx.c, ctx.code, ctx.rangs_actuels, ctx.regles, ctx.version)

    explication("Le simulateur part du classement actuel et tire au sort le score de tous les matchs qui "
                "restent, selon les chances de chaque affiche. Il recommence des milliers de fois. Si un club "
                "finit champion dans 6 500 saisons simulées sur 10 000, ses chances de titre sont "
                "de 65 %. Après chaque match tiré au sort, les notes des clubs sont mises à "
                "jour comme après un vrai match : un club qui enchaîne les victoires devient favori "
                "des journées suivantes, comme dans la réalité. La prochaine journée annoncée est jouée "
                "en premier.")

    r1, r2, k1, k2, k3 = st.columns([1.5, .8, 1, 1, 1], vertical_alignment="bottom")
    nb = r1.select_slider("Nombre de saisons simulées", [1_000, 5_000, 10_000, 50_000], value=10_000,
                          format_func=lambda n: f"{n:,}".replace(",", " "))
    graine = r2.number_input("Graine du hasard", min_value=0, value=0, step=1,
                             help="Même graine = mêmes tirages : pratique pour comparer deux réglages.")
    evolutives = r1.toggle(
        "Les notes évoluent pendant la saison simulée", value=True,
        help="Désactivé, chaque club garde sa note du jour jusqu'à la fin : les séries ne se "
             "prolongent pas et la simulation est trop sûre d'elle. Pratique pour comparer.")
    synthese, rangs, ordre_clubs, nb_restants = fin_de_saison(code, version, nb, graine, evolutives,
                                                              affiches_annoncees if evolutives else ())
    nb_clubs = len(ordre_clubs)

    favori = synthese["titre"].idxmax()
    menace = synthese["relegation"].idxmax()
    chiffre_cle(k1, "Matchs restants", nb_restants,
                f"{nb_restants // (nb_clubs // 2)} journées sur {2 * (nb_clubs - 1)}")
    chiffre_cle(k2, "Favori pour le titre", ecusson(chemin_club(code, favori), alt="") + favori,
                f"Champion dans {pourcent(synthese.loc[favori, 'titre'])} des saisons simulées")
    chiffre_cle(k3, "Le plus menacé", ecusson(chemin_club(code, menace), alt="") + menace,
                f"Relégué dans {pourcent(synthese.loc[menace, 'relegation'])} des saisons simulées")

    def ecussons_axe(ordre, taille=18):
        """Couche d'écussons dans la marge gauche, devant le nom de chaque club (axe y avec labelPadding=30)."""
        logos = pd.DataFrame({"club": ordre, "logo": [image(chemin_club(code, club)) for club in ordre]})
        return alt.Chart(logos).mark_image(width=taille, height=taille).encode(
            y=alt.Y("club:N", sort=ordre), x=alt.value(-taille / 2 - 6), url="logo:N")

    graphe_points, graphe_places = st.columns(2, gap="large")
    with graphe_points:
        st.subheader("Combien de points en fin de saison ?")
        st.markdown("Le point donne le total moyen en fin de saison, le trait couvre 8 saisons simulées "
                    "sur 10. À gauche, un repère gris à droite du losange, c'est un club qui a fait mieux "
                    "que prévu jusqu'ici.")
        st.html(f"""<div class="legende-graphique">
          <span><i style="width:3px;height:14px;background:{c['D']}"></i>Points aujourd'hui</span>
          <span><i style="width:9px;height:9px;border:2px solid {c['encre2']};transform:rotate(45deg)"></i>
            Points prévus à cette journée</span>
          <span><i style="width:11px;height:11px;border-radius:50%;background:{c['H']}"></i>
            Points en fin de saison (moyenne)</span>
          <span><i style="width:22px;height:3px;background:{c['H']};opacity:.45"></i>8 saisons sur 10</span>
        </div>""")
        projection = synthese.reset_index().rename(columns={"index": "club"})
        ordre = list(synthese.index)
        axe_y = alt.Y("club:N", sort=ordre, title=None, axis=alt.Axis(labelOverlap=False, labelPadding=30))
        infobulle = [alt.Tooltip("club:N", title="Club"), alt.Tooltip("points:Q", title="Points actuels"),
                     alt.Tooltip("prevus:Q", format=".1f", title="Points prévus à cette journée"),
                     alt.Tooltip("ecart:Q", format="+.1f", title="Écart au prévu"),
                     alt.Tooltip("points_finaux:Q", format=".0f", title="Points finaux (moyenne)"),
                     alt.Tooltip("bas:Q", format=".0f", title="Fourchette basse"),
                     alt.Tooltip("haut_points:Q", format=".0f", title="Fourchette haute")]
        fourchettes = alt.Chart(projection).mark_rule(strokeWidth=3, color=c["H"], opacity=.45).encode(
            y=axe_y, x=alt.X("bas:Q", title="Points"), x2="haut_points:Q", tooltip=infobulle)
        ecarts = alt.Chart(projection).mark_rule(strokeWidth=1.5, color=c["encre2"], opacity=.6).encode(
            y=axe_y, x="prevus:Q", x2="points:Q", tooltip=infobulle)
        prevus = alt.Chart(projection).mark_point(shape="diamond", size=70, filled=True, color=c["carte"],
                                                  stroke=c["encre2"], strokeWidth=2, opacity=1).encode(
            y=axe_y, x="prevus:Q", tooltip=infobulle)
        actuels = alt.Chart(projection).mark_tick(color=c["D"], thickness=2, size=14).encode(
            y=axe_y, x="points:Q", tooltip=infobulle)
        moyens = alt.Chart(projection).mark_circle(size=110, color=c["H"], opacity=1).encode(
            y=axe_y, x="points_finaux:Q", tooltip=infobulle)
        st.altair_chart((fourchettes + ecarts + prevus + actuels + moyens + ecussons_axe(ordre))
                        .properties(height=28 * nb_clubs), width="stretch")
        mieux, moins = synthese["ecart"].idxmax(), synthese["ecart"].idxmin()
        st.caption(
            f"Plus belle surprise : {mieux}, {decimal(synthese.loc[mieux, 'ecart'], 1, signe=True)} points "
            f"par rapport au prévu. Plus grosse déception : {moins}, "
            f"{decimal(synthese.loc[moins, 'ecart'], 1, signe=True)}. Le prévu additionne, match après match, "
            "les points qu'on pouvait attendre la veille avec les notes Elo du moment "
            "(3 × chances de victoire + 1 × chances de nul).")

    with graphe_places:
        st.subheader("Où chaque club peut finir")
        st.markdown("Une ligne par club, une colonne par place finale : plus la case est foncée, plus "
                    "la place est probable. Une ligne étalée signale une saison encore très ouverte.")
        distribution = pd.DataFrame(
            [(club, place, (rangs[:, i] == place).mean())
             for i, club in enumerate(ordre_clubs) for place in range(1, nb_clubs + 1)],
            columns=["club", "rang", "probabilite"])
        carte = alt.Chart(distribution).mark_rect(stroke=c["fond"], strokeWidth=2, cornerRadius=2).encode(
            x=alt.X("rang:O", title="Place au classement final", axis=alt.Axis(labelAngle=0, orient="top")),
            y=alt.Y("club:N", sort=ordre, title=None, axis=alt.Axis(labelOverlap=False, labelPadding=30)),
            color=alt.Color("probabilite:Q", title="Probabilité",
                            scale=alt.Scale(range=c["seq"], domain=[0, 0.1, 0.3, 0.6], clamp=True,
                                            interpolate="lab"),
                            legend=alt.Legend(format=".0%", orient="bottom", gradientLength=220)),
            tooltip=[alt.Tooltip("club:N", title="Club"), alt.Tooltip("rang:O", title="Place"),
                     alt.Tooltip("probabilite:Q", format=".1%", title="Probabilité")],
        )
        st.altair_chart((carte + ecussons_axe(ordre)).properties(height=28 * nb_clubs), width="stretch")

    st.subheader("Les chances de chaque club")
    tableau = projection.copy()
    probas = ["titre", "haut"] + (["barrage"] if regles.barrage else []) + ["relegation"]
    tableau[probas] = tableau[probas] * 100
    tableau.insert(0, "logo", tableau["club"].map(lambda club: image(chemin_club(code, club))))
    tableau.insert(2, "rang", tableau["club"].map(rangs_actuels))
    progression = lambda titre, aide: st.column_config.ProgressColumn(
        titre, help=aide, format="%.0f\u00a0%%", min_value=0, max_value=100)
    place_barrage = nb_clubs - regles.relegues
    st.dataframe(
        tableau[["logo", "club", "rang", "joues", "points", "prevus", "ecart", "diff_buts", "points_finaux",
                 "calendrier"] + probas],
        hide_index=True, width="stretch", height=36 * (len(tableau) + 1) + 3,
        column_config={
            "logo": st.column_config.ImageColumn("Logo", width="small", pinned=True),
            "club": st.column_config.TextColumn("Club", pinned=True),
            "rang": st.column_config.NumberColumn("Rang", help="Place au classement actuel"),
            "joues": st.column_config.NumberColumn("J", help="Matchs joués"),
            "points": st.column_config.NumberColumn("Pts", help="Points actuels"),
            "prevus": st.column_config.NumberColumn("Prévus", format="%.1f",
                                                    help="Points que le modèle prévoyait à cette journée"),
            "ecart": st.column_config.NumberColumn("Écart", format="%+.1f",
                                                   help="Points réels moins points prévus : positif = "
                                                        "mieux que prévu"),
            "diff_buts": st.column_config.NumberColumn("Diff.", format="%+d", help="Différence de buts"),
            "points_finaux": st.column_config.NumberColumn("Pts attendus", format="%.0f",
                                                           help="Points moyens en fin de saison"),
            "calendrier": st.column_config.NumberColumn("Calendrier", format="%.0f",
                                                        help="Note moyenne des adversaires restants, terrain "
                                                             "compris : plus c'est haut, plus la fin de saison "
                                                             "est dure"),
            "titre": progression("Champion", "1ʳᵉ place"),
            "haut": progression(regles.haut[0], f"{regles.haut[1]} premières places"),
            "barrage": progression("Barrage", f"{place_barrage}ᵉ place : {regles.barrage_aide}"),
            "relegation": progression("Relégation", f"{regles.relegues} dernières places : descente "
                                                    f"directe en {regles.division_inferieure}"),
        })
    st.caption("Clubs rangés du meilleur au moins bon classement final attendu. Les colonnes sont "
               "triables : cliquez sur un titre.")

    with st.expander("Hypothèses et limites de la simulation"):
        st.markdown(
            "- Les notes **évoluent** dans chaque saison simulée, avec la même règle Elo que pour les "
            "vrais matchs, écart de buts compris. Seule la prochaine journée annoncée est connue : "
            "elle est jouée en premier, puis l'ordre des autres affiches est tiré au hasard, en journées "
            "où chaque club joue au plus une fois. Avec les notes figées (interrupteur en haut), la "
            "simulation est plus sûre d'elle.\n"
            "- Le simulateur tire l'**issue** de chaque match (victoire, nul, défaite) selon la régression "
            "logistique, puis son **écart de buts** selon le modèle de score (loi de Poisson). "
            "À égalité de points, les clubs sont départagés par leur différence de buts simulée, "
            f"puis au hasard. En {regles.nom}, le vrai règlement départage d'abord par "
            f"{regles.departage}.\n"
            f"- Un club qui n'était pas dans le championnat la saison précédente démarre à "
            f"{NOTE_PROMU} points, qu'il monte de {regles.division_inferieure} ou descende de "
            "l'étage au-dessus : les notes de deux divisions ne se comparent pas encore.\n"
            f"- Les zones ({regles.haut[0].lower()}, barrage, relégation) suivent les règles 2026-27, "
            "simplifiées : le nombre de places européennes peut varier selon l'indice UEFA.\n"
            "- Blessures, transferts et changements d'entraîneur ne sont pas pris en compte.")
