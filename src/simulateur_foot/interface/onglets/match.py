"""Onglet « Un match »."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from simulateur_foot.force_clubs import AVANTAGE_TERRAIN, NOTE_INITIALE
from simulateur_foot.interface.commun import (
    FORME,
    NOMS_ISSUES,
    decimal,
    ecusson,
    explication,
    forme_recente,
    modele_retenu,
    modele_scores_retenu,
    nom_saison,
    pourcent,
    rang,
)
from simulateur_foot.logos import chemin_club
from simulateur_foot.prediction import probabilites
from simulateur_foot.scores import buts_attendus, grille_scores, tirer_scores


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    c, code, matchs, notes, rangs_actuels, version = (
        ctx.c, ctx.code, ctx.matchs, ctx.notes, ctx.rangs_actuels, ctx.version)

    explication("Choisissez deux clubs : le simulateur donne les chances de chaque issue si ce match "
                "se jouait aujourd'hui. Ce sont des chances, pas une certitude : un club donné "
                "gagnant à 60 % perd ou fait nul 4 fois sur 10. Le bouton « Jouer le match » "
                "le montre en tirant un score au sort.")

    gauche, droite = st.columns([5, 6], gap="large")
    clubs = list(notes.index)
    col_dom, col_ext = gauche.columns(2)
    dom = col_dom.selectbox("Club qui reçoit", clubs, index=0)
    ext = col_ext.selectbox("Club qui se déplace", [x for x in clubs if x != dom], index=0)
    proba = probabilites(modele_retenu(code, version), [notes[dom]], [notes[ext]]).iloc[0]

    with gauche:
        def fiche(club, lieu, cote, droite=False):
            forme = "".join(f'<i class="{r}" title="{FORME[r]}">{r}</i>' for r in forme_recente(code, version, club))
            return (f'<div class="club{" droite" if droite else ""}"><span class="lieu">{lieu}</span>'
                    f'<span class="nom">{ecusson(chemin_club(code, club), alt=club)}'
                    f'<span class="pastille" style="background:{c[cote]}"></span>{club}</span>'
                    f'<span class="infos">Note <b>{notes[club]:.0f}</b> · {rang(rangs_actuels[club])} du classement</span>'
                    f'<div class="forme" title="5 derniers matchs, du plus ancien au plus récent">{forme}</div></div>')

        st.html(f'<div class="affiche">{fiche(dom, "Domicile", "H")}<span class="contre">contre</span>'
                f'{fiche(ext, "Extérieur", "A", droite=True)}</div>')

        segments = "".join(
            f'<div style="flex:{proba[r]:.4f};background:{c[r]}" title="{NOMS_ISSUES[r]}">{pourcent(proba[r])}</div>'
            for r in ["H", "D", "A"])
        legende = "".join(
            f'<div><span class="pastille" style="background:{c[r]}"></span>{texte} <b>{pourcent(proba[r])}</b></div>'
            for r, texte in [("H", f"Victoire de {dom}"), ("D", "Match nul"), ("A", f"Victoire de {ext}")])
        st.html(f'<div class="barre">{segments}</div><div class="legende">{legende}</div>')

        ecart = notes[dom] + AVANTAGE_TERRAIN - notes[ext]
        favori = dom if ecart > 0 else ext
        st.caption(f"Écart de notes : {ecart:+.0f} points en faveur de {favori}, en comptant le bonus de "
                   f"{AVANTAGE_TERRAIN} points accordé au club qui reçoit. Forme : V = victoire, "
                   "N = nul, D = défaite, sur les 5 derniers matchs de la saison.")

        # Grille des scores : loi de Poisson sur les notes, recalée sur les chances ci-dessus
        grille = grille_scores(modele_scores_retenu(code, version), modele_retenu(code, version),
                               np.array([notes[dom]]), np.array([notes[ext]]))[0]
        mu_dom, mu_ext = buts_attendus(modele_scores_retenu(code, version), [notes[dom]], [notes[ext]])
        meilleurs = np.dstack(np.unravel_index(np.argsort(-grille.ravel())[:5], grille.shape))[0]
        chips = "".join(f'<div class="chip{" fort" if i == 0 else ""}"><b>{bd}–{be}</b>'
                        f'<span>{pourcent(grille[bd, be])}</span></div>' for i, (bd, be) in enumerate(meilleurs))
        st.html(f'<div class="sous-titre">Les scores les plus probables</div><div class="scores-chips">{chips}</div>')
        st.caption(f"Buts attendus : {decimal(mu_dom[0], 1)} pour {dom}, {decimal(mu_ext[0], 1)} pour {ext}. "
                   "Chaque case ci-dessous donne la chance d'un score exact ; les cases d'une même "
                   "issue (victoire, nul, défaite) totalisent les chances annoncées plus haut.")
        cellules = pd.DataFrame([(bd, be, grille[bd, be]) for bd in range(6) for be in range(6)],
                                columns=["dom", "ext", "probabilite"])
        axes = dict(x=alt.X("dom:O", title=f"Buts de {dom}", axis=alt.Axis(labelAngle=0, orient="top")),
                    y=alt.Y("ext:O", title=f"Buts de {ext}"))
        cases = alt.Chart(cellules).mark_rect(stroke=c["fond"], strokeWidth=2, cornerRadius=3).encode(
            **axes, color=alt.Color("probabilite:Q", legend=None,
                                    scale=alt.Scale(range=c["seq"], domain=[0, 0.03, 0.07, 0.12], clamp=True,
                                                    interpolate="lab")),
            tooltip=[alt.Tooltip("dom:O", title=f"Buts de {dom}"), alt.Tooltip("ext:O", title=f"Buts de {ext}"),
                     alt.Tooltip("probabilite:Q", format=".1%", title="Chance")])
        etiquettes = alt.Chart(cellules).mark_text(fontSize=12, fontWeight=600).encode(
            **axes, text=alt.Text("probabilite:Q", format=".0%"),
            color=alt.condition(alt.datum.probabilite > 0.05, alt.value(c["fond"]), alt.value(c["encre"])))
        st.altair_chart((cases + etiquettes).properties(height=250), width="stretch")

        if "tirage" not in st.session_state:
            st.session_state.tirage = None
        if st.button("Jouer le match", type="primary"):
            st.session_state.tirage = int(np.random.default_rng().integers(1_000_000))
        if st.session_state.tirage is not None:
            generateur = np.random.default_rng(st.session_state.tirage)
            buts_dom, buts_ext = tirer_scores(grille, generateur, nb=100)
            issues = np.where(buts_dom > buts_ext, "H", np.where(buts_dom == buts_ext, "D", "A"))
            issue = issues[0]
            texte = {"H": f"Victoire de {dom}", "D": "Match nul", "A": f"Victoire de {ext}"}[issue]
            st.html(f'<div class="resultat"><span class="pastille" style="background:{c[issue]};'
                    f'width:1.1rem;height:1.1rem;margin:0"></span><span class="score">{dom}<small>{buts_dom[0]} – '
                    f'{buts_ext[0]}</small>{ext}</span></div><div class="issue">{texte}</div>')
            comptes = {r: int((issues == r).sum()) for r in ["H", "D", "A"]}
            scores = pd.Series(list(zip(buts_dom, buts_ext))).value_counts()
            (sd, se), frequence = scores.index[0], int(scores.iloc[0])
            cases = "".join(f'<div style="background:{c[r]}"></div>' for r in ["H", "D", "A"]
                            for _ in range(comptes[r]))
            st.markdown(f"**Et si on le jouait 100 fois ?** {dom} gagne {comptes['H']} fois, "
                        f"{comptes['D']} nuls, {ext} gagne {comptes['A']} fois ; le score qui revient le plus "
                        f"est {sd}–{se} ({frequence} fois). Relancez : les chiffres bougent un peu, mais "
                        "restent proches des chances annoncées.")
            st.html(f'<div class="gaufre">{cases}</div>')

    with droite:
        st.subheader("Comment les notes ont évolué")
        st.markdown(f"Chaque marche correspond à un match : la note monte après une victoire, baisse "
                    f"après une défaite. La ligne pointillée marque {NOTE_INITIALE}, le niveau d'un club "
                    "moyen. Survolez la courbe pour voir le match.")
        historique = pd.concat([
            matchs.assign(club=matchs["HomeTeam"], note=matchs["force_dom"], adversaire=matchs["AwayTeam"]),
            matchs.assign(club=matchs["AwayTeam"], note=matchs["force_ext"], adversaire=matchs["HomeTeam"]),
        ])
        historique = historique[historique["club"].isin([dom, ext])]
        historique["score"] = (historique["HomeTeam"] + " " + historique["FTHG"].astype(int).astype(str) + "–"
                               + historique["FTAG"].astype(int).astype(str) + " " + historique["AwayTeam"])
        survol = alt.selection_point(fields=["Date"], nearest=True, on="pointerover", empty=False)
        base = alt.Chart(historique).encode(
            x=alt.X("Date:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),
            y=alt.Y("note:Q", title="Note Elo", scale=alt.Scale(zero=False)),
            color=alt.Color("club:N", title=None,
                            scale=alt.Scale(domain=[dom, ext], range=[c["H"], c["A"]]),
                            legend=alt.Legend(orient="top")),
        )
        moyenne = alt.Chart(pd.DataFrame({"y": [NOTE_INITIALE]})).mark_rule(
            strokeDash=[4, 4], color=c["D"]).encode(y="y:Q")
        lignes = base.mark_line(strokeWidth=2, interpolate="step-after")
        points = base.mark_circle(size=80).encode(
            opacity=alt.condition(survol, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip("Date:T", format="%d/%m/%Y"), alt.Tooltip("club:N", title="Club"),
                     alt.Tooltip("note:Q", format=".0f", title="Note avant le match"),
                     alt.Tooltip("score:N", title="Match")],
        ).add_params(survol)
        st.altair_chart((moyenne + lignes + points).properties(height=320), width="stretch")

        face_a_face = matchs[matchs["HomeTeam"].isin([dom, ext]) & matchs["AwayTeam"].isin([dom, ext])]
        if len(face_a_face):
            victoires_dom = ((face_a_face["FTR"] == "H") & (face_a_face["HomeTeam"] == dom)).sum() + \
                            ((face_a_face["FTR"] == "A") & (face_a_face["AwayTeam"] == dom)).sum()
            nuls = (face_a_face["FTR"] == "D").sum()
            st.subheader("Leurs confrontations depuis 2021")
            st.markdown(f"{len(face_a_face)} matchs : **{victoires_dom}** victoires de {dom}, **{nuls}** nuls, "
                        f"**{len(face_a_face) - victoires_dom - nuls}** victoires de {ext}.")
            st.dataframe(
                face_a_face.sort_values("Date", ascending=False)
                .assign(Saison=face_a_face["Saison"].map(nom_saison),
                        Score=face_a_face["FTHG"].astype(int).astype(str) + " – " + face_a_face["FTAG"].astype(int).astype(str))
                [["Date", "Saison", "HomeTeam", "Score", "AwayTeam"]]
                .rename(columns={"HomeTeam": "Domicile", "AwayTeam": "Extérieur"}),
                hide_index=True, width="stretch",
                column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY")})
