"""Onglet « Fiche club »."""

import html

import altair as alt
import pandas as pd
import streamlit as st

from simulateur_foot.force_clubs import NOTE_INITIALE
from simulateur_foot.interface.commun import (
    FORME,
    chiffre_cle,
    donnees_joueurs,
    ecusson,
    explication,
    fin_de_saison,
    forces_du_jour,
    forme_recente,
    joueurs_projetes,
    pourcent,
    rang,
)
from simulateur_foot.logos import chemin_club
from simulateur_foot.simulation import matchs_restants


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    affiches_annoncees, c, code, matchs, notes, rangs_actuels, regles, saison, table_actuelle, version = (
        ctx.affiches_annoncees, ctx.c, ctx.code, ctx.matchs, ctx.notes, ctx.rangs_actuels, ctx.regles,
        ctx.saison, ctx.table_actuelle, ctx.version)

    explication("Tout ce que le simulateur sait d'un club, sur une seule page : sa note et sa forme, ses "
                "chances en fin de saison, ses derniers matchs et ses meilleurs joueurs.",
                titre="La fiche d'un club")
    clubs_saison = list(table_actuelle.index)
    club = st.selectbox("Club", sorted(clubs_saison), index=sorted(clubs_saison).index(clubs_saison[0]),
                        key=f"club_fiche_{code}")
    forces_club = forces_du_jour(code, version).loc[club]
    synthese_club, _, _, _ = fin_de_saison(code, version, 10_000, 0, True, affiches_annoncees)
    bilan_club = synthese_club.loc[club]
    lettres = "".join(f'<i class="{r}" title="{FORME[r]}">{r}</i>' for r in forme_recente(code, version, club))
    variation = forces_club["variation"]
    tendance = (f'<span class="hausse">▲ {variation:+.0f}</span>' if variation > 0.5 else
                f'<span class="baisse">▼ {variation:+.0f}</span>' if variation < -0.5 else "stable")
    st.html(f"""
<div class="fiche">
  {ecusson(chemin_club(code, club), alt=club)}
  <div>
    <h2>{html.escape(club)}</h2>
    <div class="infos">{rang(rangs_actuels[club])} · <b>{int(bilan_club["points"])} points</b> en
      {int(bilan_club["joues"])} matchs · différence de buts {int(bilan_club["diff_buts"]):+d}<br>
      Note <b>{forces_club["note"]:.0f}</b> ({rang(list(notes.index).index(club) + 1)} du championnat) ·
      sur 5 matchs : {tendance}</div>
  </div>
  <div class="cote-droit"><span>Forme récente</span><div class="forme">{lettres}</div></div>
</div>""")

    f1, f2, f3, f4 = st.columns(4)
    chiffre_cle(f1, "Points en fin de saison", f"{bilan_club['points_finaux']:.0f}",
                f"entre {bilan_club['bas']:.0f} et {bilan_club['haut_points']:.0f} (8 saisons sur 10)")
    chiffre_cle(f2, "Champion", pourcent(bilan_club["titre"]), f"place moyenne : {bilan_club['rang_moyen']:.1f}")
    chiffre_cle(f3, regles.haut[0], pourcent(bilan_club["haut"]), f"{regles.haut[1]} premières places")
    chiffre_cle(f4, "Relégation", pourcent(bilan_club["relegation"]),
                f"{regles.relegues} dernières places" + (f" · barrage {pourcent(bilan_club['barrage'])}"
                                                        if regles.barrage else ""))

    club_gauche, club_droite = st.columns(2, gap="large")
    with club_gauche:
        st.subheader("Ses derniers matchs")
        siens = saison[(saison["HomeTeam"] == club) | (saison["AwayTeam"] == club)].sort_values("Date")
        lignes_matchs = []
        for m in siens.tail(6).iloc[::-1].itertuples():
            a_domicile = m.HomeTeam == club
            adversaire = m.AwayTeam if a_domicile else m.HomeTeam
            pour, contre = (m.FTHG, m.FTAG) if a_domicile else (m.FTAG, m.FTHG)
            lettre = "N" if pour == contre else "V" if pour > contre else "D"
            lignes_matchs.append(
                f'<div><span class="date">{m.Date:%d/%m}</span><i class="{lettre}" title="{FORME[lettre]}">{lettre}</i>'
                f'{ecusson(chemin_club(code, adversaire), alt=adversaire) or "<span></span>"}'
                f'<span>{html.escape(adversaire)} <span class="lieu">· {"domicile" if a_domicile else "extérieur"}'
                f'</span></span><b>{int(pour)}–{int(contre)}</b></div>')
        st.html(f'<div class="matchs-club">{"".join(lignes_matchs)}</div>')
        nb_a_jouer = int(len(matchs_restants(saison).query("HomeTeam == @club or AwayTeam == @club")))
        st.caption(f"Il lui reste {nb_a_jouer} matchs. Note moyenne de ses adversaires à venir : "
                   f"{forces_club['calendrier']:.0f} (1500 = club moyen ; plus c'est haut, plus c'est dur).")

    with club_droite:
        st.subheader("Ses meilleurs joueurs")
        version_joueurs_club = donnees_joueurs()
        siens_joueurs = pd.DataFrame()
        if version_joueurs_club is not None:
            tous_joueurs, _ = joueurs_projetes(code, version, version_joueurs_club)
            siens_joueurs = tous_joueurs[tous_joueurs["club"] == club]
        if siens_joueurs.empty:
            st.caption("Aucun joueur de ce club parmi les 50 meilleurs buteurs ou passeurs du championnat.")
        else:
            siens_joueurs = siens_joueurs.sort_values(["decisives", "buts"], ascending=False).head(8)
            st.dataframe(
                siens_joueurs[["joueur", "matchs", "buts", "buts_prevus", "passes", "passes_prevus"]],
                hide_index=True, width="stretch",
                column_config={
                    "joueur": st.column_config.TextColumn("Joueur", pinned=True),
                    "matchs": st.column_config.NumberColumn("Matchs", format="%d"),
                    "buts": st.column_config.NumberColumn("Buts", format="%d"),
                    "buts_prevus": st.column_config.NumberColumn(
                        "Buts prévus", format="%.0f", help="Total attendu en fin de saison"),
                    "passes": st.column_config.NumberColumn("Passes", format="%d"),
                    "passes_prevus": st.column_config.NumberColumn(
                        "Passes prévues", format="%.0f", help="Total attendu en fin de saison"),
                })
            st.caption("Seuls les joueurs classés parmi les 50 meilleurs buteurs ou passeurs du championnat "
                       "apparaissent (données ESPN).")

    st.subheader("Sa note depuis 2021")
    parcours = pd.concat([
        matchs[matchs["HomeTeam"] == club].assign(note=lambda d: d["force_dom"], adversaire=lambda d: d["AwayTeam"]),
        matchs[matchs["AwayTeam"] == club].assign(note=lambda d: d["force_ext"], adversaire=lambda d: d["HomeTeam"]),
    ]).sort_values("Date")
    parcours["score"] = (parcours["HomeTeam"] + " " + parcours["FTHG"].astype(int).astype(str) + "–"
                         + parcours["FTAG"].astype(int).astype(str) + " " + parcours["AwayTeam"])
    courbe = alt.Chart(parcours).mark_line(interpolate="step-after", color=c["accent"], strokeWidth=2).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%Y", tickCount="year")),
        y=alt.Y("note:Q", title="Note Elo", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("Date:T", format="%d/%m/%Y"), alt.Tooltip("score:N", title="Match"),
                 alt.Tooltip("note:Q", format=".0f", title="Note avant le match")])
    repere = alt.Chart(pd.DataFrame({"y": [NOTE_INITIALE]})).mark_rule(
        strokeDash=[4, 4], color=c["D"]).encode(y="y:Q")
    st.altair_chart((repere + courbe).properties(height=260), width="stretch")
