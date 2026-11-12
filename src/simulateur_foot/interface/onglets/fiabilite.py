"""Onglet « Le modèle est-il fiable ? »."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from simulateur_foot import pronostics as suivi_pronostics
from simulateur_foot.interface.commun import (
    NOMS_ISSUES,
    bilan_pronostics,
    chiffre_cle,
    decimal,
    explication,
    fiabilite,
    nom_saison,
    pourcent,
)
from simulateur_foot.modele import RESULTATS, SAISON_TEST, SAISONS_ENTRAINEMENT


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    c, code, regles, version = (
        ctx.c, ctx.code, ctx.regles, ctx.version)

    scores, proba_test, test = fiabilite(code, version)
    reel = test["FTR"]
    explication(
        f"Pour savoir si les chances annoncées sont crédibles, on a fait un examen à l'aveugle : le modèle "
        f"a appris sur les saisons {', '.join(nom_saison(s) for s in SAISONS_ENTRAINEMENT)}, puis il a "
        f"prédit les {len(test)} matchs de la saison {nom_saison(SAISON_TEST)} sans les avoir vus. "
        "On compare ici ses prédictions à ce qui s'est vraiment passé. Le simulateur utilise ensuite "
        f"le même modèle, réentraîné en ajoutant {nom_saison(SAISON_TEST)}.")

    st.subheader("Et cette saison ? Le suivi en direct")
    fichier_suivi = suivi_pronostics.FICHIER_PRONOSTICS
    bilan_ligue, bilan_tous = bilan_pronostics(code, version, fichier_suivi.stat().st_mtime) \
        if fichier_suivi.exists() else (None, None)
    if bilan_tous is None:
        st.caption("Chaque semaine, les chances annoncées pour les matchs à venir sont enregistrées avant "
                   "qu'ils soient joués (`uv run simulateur-foot pronostics`). Le bilan apparaîtra ici dès "
                   "que les premiers matchs suivis auront été joués.")
    else:
        st.markdown(f"Depuis le {bilan_tous['depuis']:%d/%m/%Y}, les chances annoncées pour chaque match sont "
                    "enregistrées **avant** qu'il soit joué, avec celles des bookmakers. Voici le bilan sur "
                    "les matchs joués depuis : contrairement à l'examen ci-dessous, le modèle ne peut pas "
                    "avoir vu ces résultats.")
        s1, s2, s3, s4 = st.columns(4)
        for colonne, titre, bilan in [(s1, regles.nom, bilan_ligue), (s3, "Les six championnats", bilan_tous)]:
            voisine = s2 if colonne is s1 else s4
            if bilan is None:
                chiffre_cle(colonne, f"{titre} · modèle", "–", "aucun match suivi pour l'instant")
                chiffre_cle(voisine, f"{titre} · bookmakers", "–", "")
                continue
            modele, marche = bilan["modele"], bilan["bookmakers"]
            chiffre_cle(colonne, f"{titre} · modèle", pourcent(modele["precision"]),
                        f"de bons pronostics sur {modele['matchs']} matchs")
            chiffre_cle(voisine, f"{titre} · bookmakers", pourcent(marche["precision"]) if marche else "–",
                        f"sur {marche['matchs']} matchs avec cotes" if marche else "pas de cotes")
        st.caption("Sur quelques dizaines de matchs, ces pourcentages bougent beaucoup d'une semaine à "
                   "l'autre : ils ne deviennent parlants qu'au fil de la saison.")

    fiab_gauche, fiab_droite = st.columns(2, gap="large")
    precision = (proba_test.idxmax(axis=1) == reel).mean()
    domicile = (reel == "H").mean()
    with fiab_gauche:
        st.subheader("Le favori du modèle gagne-t-il ?")
        st.markdown(f"Si l'on pariait à chaque match sur l'issue que le modèle juge la plus probable, on "
                    f"aurait raison **{pourcent(precision)}** du temps. C'est mieux que de toujours miser "
                    f"sur le club qui reçoit ({pourcent(domicile)}) ou de choisir au hasard (33 %).")
        comparaison = pd.DataFrame({
            "methode": ["Le modèle", "Toujours le club qui reçoit", "Au hasard"],
            "taux": [precision, domicile, 1 / 3],
            "role": ["modele", "reference", "reference"],
        })
        barres = alt.Chart(comparaison).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("methode:N", sort=list(comparaison["methode"]), title=None,
                    scale=alt.Scale(paddingInner=0.35), axis=alt.Axis(labelLimit=220)),
            x=alt.X("taux:Q", title="Part de pronostics justes", axis=alt.Axis(format=".0%"),
                    scale=alt.Scale(domain=[0, 0.6])),
            color=alt.Color("role:N", scale=alt.Scale(domain=["modele", "reference"],
                                                      range=[c["H"], c["D"]]), legend=None),
            tooltip=[alt.Tooltip("methode:N", title="Méthode"),
                     alt.Tooltip("taux:Q", format=".1%", title="Pronostics justes")],
        )
        etiquettes = barres.mark_text(align="left", dx=6, color=c["encre"], fontWeight=600).encode(
            text=alt.Text("taux:Q", format=".0%"), color=alt.value(c["encre"]))
        st.altair_chart((barres + etiquettes).properties(height=150), width="stretch")

    with fiab_droite:
        st.subheader("Quand il annonce 40 %, est-ce que ça arrive 4 fois sur 10 ?")
        st.markdown("C'est la vraie question pour un simulateur : les pourcentages doivent être honnêtes. "
                    "On range les matchs selon la chance annoncée, puis on regarde combien de fois l'issue "
                    "s'est vraiment produite. Un modèle parfait aurait tous ses points sur la diagonale "
                    "pointillée ; au-dessus, il sous-estime ; en dessous, il surestime.")
        lignes = []
        for issue in RESULTATS:
            tranches = pd.qcut(proba_test[issue], 5, duplicates="drop")
            groupe = pd.DataFrame({"annonce": proba_test[issue], "arrive": reel == issue}).groupby(tranches, observed=True)
            for _, g in groupe:
                lignes.append((NOMS_ISSUES[issue], g["annonce"].mean(), g["arrive"].mean(), len(g)))
        calibration = pd.DataFrame(lignes, columns=["issue", "annonce", "arrive", "matchs"])
        echelle = alt.Scale(domain=[NOMS_ISSUES[r] for r in ["H", "D", "A"]], range=[c[r] for r in ["H", "D", "A"]])
        diagonale = alt.Chart(pd.DataFrame({"x": [0, 0.8]})).mark_line(
            strokeDash=[4, 4], strokeWidth=1, color=c["D"]).encode(x="x:Q", y="x:Q")
        courbes = alt.Chart(calibration).encode(
            x=alt.X("annonce:Q", title="Chance annoncée par le modèle", axis=alt.Axis(format=".0%"),
                    scale=alt.Scale(domain=[0, 0.8])),
            y=alt.Y("arrive:Q", title="Ce qui est vraiment arrivé", axis=alt.Axis(format=".0%"),
                    scale=alt.Scale(domain=[0, 0.8])),
            color=alt.Color("issue:N", scale=echelle, title=None, legend=alt.Legend(orient="top")),
            order="annonce:Q",
            tooltip=[alt.Tooltip("issue:N", title="Issue"),
                     alt.Tooltip("annonce:Q", format=".0%", title="Annoncé"),
                     alt.Tooltip("arrive:Q", format=".0%", title="Arrivé"),
                     alt.Tooltip("matchs:Q", title="Matchs")],
        )
        st.altair_chart((diagonale + courbes.mark_line(strokeWidth=2) + courbes.mark_circle(size=90, opacity=1))
                        .properties(height=380), width="stretch")
        st.caption("Chaque point regroupe un cinquième des matchs de la saison test. Le modèle n'annonce "
                   f"jamais plus de {pourcent(proba_test['D'].max())} de chances de match nul : il "
                   "repère mal les matchs serrés, une limite connue des modèles fondés sur la seule note.")

    with fiab_gauche:
        st.subheader(f"Les plus grosses surprises de {nom_saison(SAISON_TEST)}")
        st.markdown("Les matchs dont le résultat semblait le moins probable au modèle. Ce sont eux qui "
                    "rappellent qu'une chance de 15 % finit toujours par arriver.")
        chance_reelle = proba_test.to_numpy()[np.arange(len(test)), proba_test.columns.get_indexer(reel)]
        surprises = test.assign(chance=chance_reelle * 100).nsmallest(8, "chance")
        st.dataframe(
            surprises.assign(Score=surprises["FTHG"].astype(int).astype(str) + " – " + surprises["FTAG"].astype(int).astype(str),
                             Issue=surprises["FTR"].map(NOMS_ISSUES))
            [["Date", "HomeTeam", "Score", "AwayTeam", "Issue", "chance"]]
            .rename(columns={"HomeTeam": "Domicile", "AwayTeam": "Extérieur"}),
            hide_index=True, width="stretch",
            column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                           "chance": st.column_config.NumberColumn("Chance annoncée", format="%.0f %%")})

    with st.expander("Pour les curieux : les scores techniques"):
        (log_m, brier_m), (log_r, brier_r) = scores["modele"], scores["frequences"]
        s1, s2 = st.columns(2)
        s1.metric("Log-loss", decimal(log_m), f"{decimal(log_m - log_r, signe=True)} par rapport à la référence",
                  delta_color="inverse")
        s2.metric("Score de Brier", decimal(brier_m), f"{decimal(brier_m - brier_r, signe=True)} par rapport à la référence",
                  delta_color="inverse")
        st.markdown(
            "Ces deux scores mesurent l'écart entre les chances annoncées et la réalité ; **plus ils sont "
            "bas, mieux c'est**. La log-loss punit sévèrement une grosse erreur d'assurance (annoncer 5 % "
            "pour un résultat qui arrive). La référence annonce les mêmes chances pour tous les matchs : "
            "les fréquences moyennes de victoire à domicile, de nul et de victoire à l'extérieur. "
            "La comparaison avec un modèle plus riche (forme, repos, promus) est détaillée dans "
            "`RAPPORT.md` et se relance avec `uv run simulateur-foot modele`.")
