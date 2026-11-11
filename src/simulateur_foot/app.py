"""Interface de test du simulateur : affiche, fin de saison, fiabilité du modèle.

Lancement : uv run simulateur-foot interface
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from simulateur_foot.force_clubs import AVANTAGE_TERRAIN
from simulateur_foot.modele import (RESULTATS, SAISON_TEST, SAISONS_ENTRAINEMENT, evaluer,
                                    pertes_brier, pertes_log, proba_frequences,
                                    proba_logistique_forces, selection)
from simulateur_foot.prediction import (SAISON_EN_COURS, SAISONS_APPRENTISSAGE, charger_forces,
                                        entrainer, probabilites)
from simulateur_foot.simulation import classement, matchs_restants, resume, simuler

# Couleurs des données (palette validée daltonisme) : domicile, nul, extérieur
COULEURS = {
    "light": {"H": "#2a78d6", "D": "#8b8a85", "A": "#1baf7a", "seq": ["#ece8df", "#9ec5f4", "#2a78d6", "#104281"], "fond": "#F6F4EF"},
    "dark": {"H": "#3987e5", "D": "#8f8e88", "A": "#199e70", "seq": ["#1c1f1a", "#184f95", "#3987e5", "#9ec5f4"], "fond": "#11130F"},
}
NOMS_ISSUES = {"H": "Domicile", "D": "Nul", "A": "Extérieur"}


def nom_saison(saison):
    """2627 → 2026-27."""
    texte = str(saison)
    return f"20{texte[:2]}-{texte[2:]}"


def decimal(x, signe=False):
    """Nombre à trois décimales, virgule à la française."""
    return (f"{x:+.3f}" if signe else f"{x:.3f}").replace(".", ",")


def pourcent(x):
    return f"{x:.0%}".replace("%", " %")


# ---------- Données (mises en cache) ----------

@st.cache_data
def donnees():
    matchs, notes = charger_forces()
    return matchs, pd.Series(notes).sort_values(ascending=False)


@st.cache_resource
def modele_retenu():
    matchs, _ = donnees()
    return entrainer(matchs)


@st.cache_data
def fin_de_saison(nb, graine):
    matchs, notes = donnees()
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    restants = matchs_restants(saison)
    proba = probabilites(modele_retenu(), restants["HomeTeam"].map(notes).to_numpy(),
                         restants["AwayTeam"].map(notes).to_numpy())
    points, rangs = simuler(table, restants, proba, nb, graine)
    return resume(table, points, rangs), rangs, list(table.index), len(restants)


@st.cache_data
def fiabilite():
    matchs, _ = donnees()
    resultats = {}
    for nom, predire in [("Logistique sur les notes Elo", proba_logistique_forces),
                         ("Référence : fréquences moyennes", proba_frequences)]:
        validation, log_test, brier_test = evaluer(predire, matchs)
        resultats[nom] = (validation, log_test.mean(), brier_test.mean())
    test = selection(matchs, [SAISON_TEST])
    proba = proba_logistique_forces(selection(matchs, SAISONS_ENTRAINEMENT), test)
    return resultats, proba, test["FTR"]


# ---------- Mise en page ----------

st.set_page_config(page_title="Simulateur Ligue 1", page_icon="⚽", layout="wide")
mode = "dark" if st.context.theme.type == "dark" else "light"
couleurs = COULEURS[mode]

st.html(f"""
<style>
  .bandeau {{ display:flex; align-items:baseline; gap:.8rem; flex-wrap:wrap;
              border-bottom:3px solid var(--st-primary-color, #D7361E); padding-bottom:.4rem; }}
  .bandeau h1 {{ font-family:'Barlow Condensed',sans-serif; font-size:2.6rem; line-height:1;
                 margin:0; padding:0; letter-spacing:.01em; text-transform:uppercase; }}
  .bandeau span {{ opacity:.7; font-size:.95rem; }}
  .barre {{ display:flex; gap:2px; height:44px; margin:.6rem 0 .3rem; }}
  .barre div {{ border-radius:4px; display:flex; align-items:center; justify-content:center;
                color:#fff; font-weight:600; font-variant-numeric:tabular-nums; min-width:2.6rem; }}
  .legende {{ display:flex; justify-content:space-between; gap:1rem; font-size:.9rem; flex-wrap:wrap; }}
  .legende b {{ font-variant-numeric:tabular-nums; }}
  .pastille {{ display:inline-block; width:.7rem; height:.7rem; border-radius:2px; margin-right:.35rem; }}
  .score {{ font-family:'Barlow Condensed',sans-serif; font-size:2.2rem; font-weight:700; }}
</style>
""")

matchs, notes = donnees()
saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
dernier = saison["Date"].max()
st.html(f"""<div class="bandeau"><h1>Simulateur Ligue 1</h1>
<span>Saison {nom_saison(SAISON_EN_COURS)} · {len(saison)} matchs joués ·
résultats au {dernier:%d/%m/%Y}</span></div>""")

onglet_affiche, onglet_saison, onglet_fiabilite = st.tabs(
    ["Affiche", "Fin de saison", "Fiabilité du modèle"])

# ---------- Affiche ----------

with onglet_affiche:
    clubs = list(notes.index)
    col_dom, col_ext = st.columns(2)
    dom = col_dom.selectbox("Club à domicile", clubs, index=0)
    ext = col_ext.selectbox("Club à l'extérieur", [c for c in clubs if c != dom], index=0)

    proba = probabilites(modele_retenu(), [notes[dom]], [notes[ext]]).iloc[0]
    segments = "".join(
        f'<div style="flex:{proba[r]:.4f};background:{couleurs[r]}">{pourcent(proba[r])}</div>'
        for r in ["H", "D", "A"])
    legende = "".join(
        f'<div><span class="pastille" style="background:{couleurs[r]}"></span>{texte} <b>{pourcent(proba[r])}</b></div>'
        for r, texte in [("H", f"Victoire {dom}"), ("D", "Match nul"), ("A", f"Victoire {ext}")])
    st.html(f'<div class="barre">{segments}</div><div class="legende">{legende}</div>')

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Note Elo · {dom}", f"{notes[dom]:.0f}")
    m2.metric(f"Note Elo · {ext}", f"{notes[ext]:.0f}")
    m3.metric("Écart avec l'avantage du terrain", f"{notes[dom] + AVANTAGE_TERRAIN - notes[ext]:+.0f}",
              help=f"Le club à domicile reçoit {AVANTAGE_TERRAIN} points d'Elo de bonus.")

    if st.button("Jouer le match", type="primary"):
        issue = np.random.default_rng().choice(RESULTATS, p=proba[RESULTATS].to_numpy())
        texte = {"H": f"Victoire de {dom}", "D": "Match nul", "A": f"Victoire de {ext}"}[issue]
        st.html(f'<div class="score"><span class="pastille" style="background:{couleurs[issue]};'
                f'width:1.1rem;height:1.1rem"></span>{texte}</div>')
        st.caption("Tirage au sort selon les probabilités : relancez pour un autre tirage.")

    # Évolution des notes avant chaque match, pour les deux clubs
    historique = pd.concat([
        matchs.assign(club=matchs["HomeTeam"], note=matchs["force_dom"], adversaire=matchs["AwayTeam"]),
        matchs.assign(club=matchs["AwayTeam"], note=matchs["force_ext"], adversaire=matchs["HomeTeam"]),
    ])
    historique = historique[historique["club"].isin([dom, ext])]
    historique["score"] = historique["FTHG"].astype(int).astype(str) + "–" + historique["FTAG"].astype(int).astype(str)
    survol = alt.selection_point(fields=["Date"], nearest=True, on="pointerover", empty=False)
    base = alt.Chart(historique).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),
        y=alt.Y("note:Q", title="Note Elo", scale=alt.Scale(zero=False)),
        color=alt.Color("club:N", title=None,
                        scale=alt.Scale(domain=[dom, ext], range=[couleurs["H"], couleurs["A"]]),
                        legend=alt.Legend(orient="top")),
    )
    lignes = base.mark_line(strokeWidth=2, interpolate="step-after")
    points = base.mark_circle(size=70).encode(
        opacity=alt.condition(survol, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("Date:T", format="%d/%m/%Y"), "club:N",
                 alt.Tooltip("note:Q", format=".0f", title="Note avant match"),
                 "adversaire:N", alt.Tooltip("score:N", title="Score (dom–ext)")],
    ).add_params(survol)
    st.subheader("Évolution des notes Elo")
    st.altair_chart((lignes + points).properties(height=320), use_container_width=True)

    face_a_face = matchs[matchs["HomeTeam"].isin([dom, ext]) & matchs["AwayTeam"].isin([dom, ext])]
    if len(face_a_face):
        st.subheader("Confrontations depuis 2021")
        st.dataframe(
            face_a_face.sort_values("Date", ascending=False)
            .assign(Saison=face_a_face["Saison"].map(nom_saison),
                    Score=face_a_face["FTHG"].astype(int).astype(str) + " – " + face_a_face["FTAG"].astype(int).astype(str))
            [["Date", "Saison", "HomeTeam", "Score", "AwayTeam"]]
            .rename(columns={"HomeTeam": "Domicile", "AwayTeam": "Extérieur"}),
            hide_index=True, use_container_width=True,
            column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY")})

# ---------- Fin de saison ----------

with onglet_saison:
    c1, c2 = st.columns([2, 1])
    nb = c1.select_slider("Nombre de saisons simulées", [1_000, 5_000, 10_000, 50_000], value=10_000,
                         format_func=lambda n: f"{n:,}".replace(",", " "))
    graine = c2.number_input("Graine du hasard", min_value=0, value=0, step=1,
                             help="Même graine = mêmes tirages : utile pour comparer.")
    synthese, rangs, ordre_clubs, nb_restants = fin_de_saison(nb, graine)

    favori = synthese["titre"].idxmax()
    k1, k2, k3 = st.columns(3)
    k1.metric("Matchs restants", nb_restants)
    k2.metric("Favori pour le titre", favori, f'{pourcent(synthese.loc[favori, "titre"])} de chances de titre', delta_color="off", delta_arrow="off")
    menace = synthese["relegation"].idxmax()
    k3.metric("Le plus menacé", menace, f"{pourcent(synthese.loc[menace, 'relegation'])} de relégation",
              delta_color="off", delta_arrow="off")

    tableau = synthese.reset_index().rename(columns={"index": "club"})
    probas = ["titre", "ligue_champions", "barrage", "relegation"]
    tableau[probas] = tableau[probas] * 100
    tableau.insert(0, "Rang actuel", tableau["club"].map({c: i + 1 for i, c in enumerate(ordre_clubs)}))
    progression = lambda titre, aide: st.column_config.ProgressColumn(
        titre, help=aide, format="%.0f %%", min_value=0, max_value=100)
    st.dataframe(
        tableau[["club", "Rang actuel", "joues", "points", "diff_buts", "points_finaux",
                 "titre", "ligue_champions", "barrage", "relegation"]],
        hide_index=True, use_container_width=True, height=36 * (len(tableau) + 1) + 3,
        column_config={
            "club": st.column_config.TextColumn("Club", pinned=True),
            "joues": "J", "points": "Pts", "diff_buts": st.column_config.NumberColumn("Diff.", format="%+d"),
            "points_finaux": st.column_config.NumberColumn("Pts finaux (moy.)", format="%.1f"),
            "titre": progression("Titre", "1ʳᵉ place"),
            "ligue_champions": progression("Top 4", "Places qualificatives pour la Ligue des champions"),
            "barrage": progression("Barrage", f"{len(tableau) - 2}ᵉ place"),
            "relegation": progression("Relégation", "Deux dernières places"),
        })
    st.caption("Les notes Elo restent figées à leur valeur du jour. Le simulateur tire l'issue de chaque "
               "match, pas le score : les égalités de points sont départagées par la différence de buts "
               "actuelle, puis au hasard.")

    # Distribution des rangs finaux : clubs triés par rang moyen
    ordre = list(synthese.index)
    distribution = pd.DataFrame(
        [(club, rang, (rangs[:, i] == rang).mean())
         for i, club in enumerate(ordre_clubs) for rang in range(1, len(ordre_clubs) + 1)],
        columns=["club", "rang", "probabilite"])
    carte = alt.Chart(distribution).mark_rect(stroke=couleurs["fond"], strokeWidth=2, cornerRadius=2).encode(
        x=alt.X("rang:O", title="Rang final"),
        y=alt.Y("club:N", sort=ordre, title=None, axis=alt.Axis(labelOverlap=False)),
        color=alt.Color("probabilite:Q", title="Probabilité",
                        scale=alt.Scale(range=couleurs["seq"], domain=[0, 0.1, 0.3, 0.6], clamp=True,
                                        interpolate="lab"),
                        legend=alt.Legend(format=".0%", orient="top", gradientLength=220)),
        tooltip=["club:N", alt.Tooltip("rang:O", title="Rang"),
                 alt.Tooltip("probabilite:Q", format=".1%", title="Probabilité")],
    )
    st.subheader("Où chaque club peut finir")
    st.altair_chart(carte.properties(height=30 * len(ordre)), use_container_width=True)

# ---------- Fiabilité ----------

with onglet_fiabilite:
    resultats, proba_test, reel = fiabilite()
    st.markdown(f"Le modèle apprend sur {', '.join(nom_saison(s) for s in SAISONS_ENTRAINEMENT)} "
                f"et il est jugé sur **{nom_saison(SAISON_TEST)}**, qu'il n'a jamais vue. Plus la "
                "log-loss et le score de Brier sont bas, mieux c'est. Le simulateur utilise ensuite "
                f"le même modèle réentraîné sur {', '.join(nom_saison(s) for s in SAISONS_APPRENTISSAGE)}.")

    (val_m, log_m, brier_m), (val_r, log_r, brier_r) = resultats.values()
    precision = (proba_test.idxmax(axis=1) == reel).mean()
    f1, f2, f3 = st.columns(3)
    f1.metric("Log-loss sur la saison test", decimal(log_m), f"{decimal(log_m - log_r, True)} vs fréquences",
              delta_color="inverse")
    f2.metric("Score de Brier", decimal(brier_m), f"{decimal(brier_m - brier_r, True)} vs fréquences",
              delta_color="inverse")
    f3.metric("Issue la plus probable juste", pourcent(precision),
              help="Le nul n'est presque jamais l'issue la plus probable : c'est pourquoi le "
                   "simulateur tire au sort au lieu de prendre l'issue favorite.")

    # Calibration : quand le modèle annonce 40 %, l'issue arrive-t-elle 40 % du temps ?
    lignes = []
    for issue in RESULTATS:
        tranches = pd.qcut(proba_test[issue], 5, duplicates="drop")
        groupe = pd.DataFrame({"annonce": proba_test[issue], "arrive": reel == issue}).groupby(tranches, observed=True)
        for _, g in groupe:
            lignes.append((NOMS_ISSUES[issue], g["annonce"].mean(), g["arrive"].mean(), len(g)))
    calibration = pd.DataFrame(lignes, columns=["issue", "annonce", "arrive", "matchs"])
    echelle = alt.Scale(domain=[NOMS_ISSUES[r] for r in ["H", "D", "A"]],
                        range=[couleurs[r] for r in ["H", "D", "A"]])
    diagonale = alt.Chart(pd.DataFrame({"x": [0, 0.8]})).mark_line(
        strokeDash=[4, 4], strokeWidth=1, color="#8b8a85").encode(x="x:Q", y="x:Q")
    courbes = alt.Chart(calibration).encode(
        x=alt.X("annonce:Q", title="Probabilité annoncée", axis=alt.Axis(format=".0%"),
                scale=alt.Scale(domain=[0, 0.8])),
        y=alt.Y("arrive:Q", title="Fréquence observée", axis=alt.Axis(format=".0%"),
                scale=alt.Scale(domain=[0, 0.8])),
        color=alt.Color("issue:N", scale=echelle, title=None, legend=alt.Legend(orient="top")),
        tooltip=["issue:N", alt.Tooltip("annonce:Q", format=".0%", title="Annoncé"),
                 alt.Tooltip("arrive:Q", format=".0%", title="Observé"), "matchs:Q"],
    )
    st.subheader("Calibration sur la saison test")
    st.altair_chart((diagonale + courbes.mark_line(strokeWidth=2) + courbes.mark_circle(size=90))
                    .properties(height=360), use_container_width=True)
    st.caption("Chaque point regroupe un cinquième des matchs test. Plus les points suivent la "
               "diagonale, plus les probabilités sont fiables. La comparaison complète avec le "
               "modèle à 16 variables se relance avec `uv run simulateur-foot modele` (≈ 2 min).")
