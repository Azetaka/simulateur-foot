"""Onglet « Prochaine journée »."""

import streamlit as st

from simulateur_foot.interface.commun import (
    JOURS,
    NOMS_ISSUES,
    chiffre_cle,
    explication,
    pourcent,
)


def afficher(ctx):
    """Affiche l'onglet ; ctx porte le championnat choisi et ses données (voir app.py)."""
    c, chances_modele, inconnus, prochains = ctx.c, ctx.chances_modele, ctx.inconnus, ctx.prochains

    explication("Les matchs de la prochaine journée, avec les chances de chaque issue selon le modèle : "
                "elles viennent des seules notes Elo du jour et du bonus du club qui reçoit. Le modèle "
                "ignore les blessures, les suspensions et la rotation de l'effectif : un favori à 60 % "
                "perd ou fait nul 4 fois sur 10.")
    if prochains.empty:
        st.info("Aucun match annoncé pour l'instant : le bouton « Mettre à jour » va chercher le calendrier.")
        return

    net = chances_modele.max(axis=1).idxmax()
    favori = prochains.loc[net, "HomeTeam" if chances_modele.loc[net].idxmax() == "H" else "AwayTeam"]
    serre = chances_modele.max(axis=1).idxmin()
    j1, j2, j3 = st.columns(3)
    chiffre_cle(j1, "Matchs annoncés", len(prochains),
                f"du {prochains['Date'].min():%d/%m} au {prochains['Date'].max():%d/%m}")
    chiffre_cle(j2, "Favori le plus net", favori, f"{pourcent(chances_modele.loc[net].max())} de chances de victoire")
    chiffre_cle(j3, "Match le plus ouvert",
                f"{prochains.loc[serre, 'HomeTeam']} – {prochains.loc[serre, 'AwayTeam']}",
                f"issue la plus probable à {pourcent(chances_modele.loc[serre].max())} seulement")

    st.html(f"""<div class="legende-graphique" style="margin-top:1rem">
      <span><i style="width:12px;height:12px;border-radius:2px;background:{c['H']}"></i>Victoire à domicile</span>
      <span><i style="width:12px;height:12px;border-radius:2px;background:{c['D']}"></i>Match nul</span>
      <span><i style="width:12px;height:12px;border-radius:2px;background:{c['A']}"></i>Victoire à l'extérieur</span>
    </div>""")

    def mini_barre(chances):
        return "".join(
            f'<div style="flex:{chances[r]:.4f};background:{c[r]}" title="{NOMS_ISSUES[r]} : '
            f'{pourcent(chances[r])}">{pourcent(chances[r]) if chances[r] >= 0.16 else ""}</div>'
            for r in ["H", "D", "A"])

    cartes = []
    for i, m in prochains.iterrows():
        heure = f" · {m['Heure']}" if isinstance(m["Heure"], str) else ""
        issue = chances_modele.loc[i].idxmax()
        pronostic = {"H": f"Victoire de {m['HomeTeam']}", "D": "Match nul",
                     "A": f"Victoire de {m['AwayTeam']}"}[issue]
        cartes.append(f"""<div class="duel">
          <div class="duel-tete"><div class="clubs">{m['HomeTeam']}<span>–</span>{m['AwayTeam']}</div>
            <div class="quand">{JOURS[m['Date'].dayofweek]} {m['Date']:%d/%m}{heure}</div></div>
          <div class="duel-ligne"><div class="mini-barre">{mini_barre(chances_modele.loc[i])}</div></div>
          <div class="duel-pied">Issue la plus probable : <b>{pronostic}</b>
            ({pourcent(chances_modele.loc[i, issue])})</div></div>""")
    st.html(f'<div class="journee">{"".join(cartes)}</div>')
    if inconnus:
        st.caption(f"{inconnus} match(s) écarté(s) : club absent des résultats de la saison.")

    with st.expander("Voir les chiffres"):
        st.dataframe(
            prochains[["Date", "Heure", "HomeTeam", "AwayTeam"]].assign(
                **{f"modele_{r}": chances_modele[r] * 100 for r in "HDA"}),
            hide_index=True, width="stretch",
            column_config={
                "Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "HomeTeam": "Domicile", "AwayTeam": "Extérieur",
                **{f"modele_{r}": st.column_config.NumberColumn(titre, format="%.0f %%")
                   for r, titre in [("H", "Victoire domicile"), ("D", "Nul"), ("A", "Victoire extérieur")]},
            })
