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
    c, chances_marche, chances_modele, inconnus, prochains = (
        ctx.c, ctx.chances_marche, ctx.chances_modele, ctx.inconnus, ctx.prochains)

    explication("Les matchs annoncés de la prochaine journée, avec deux pronostics côte à côte : celui "
                "du modèle, tiré des seules notes Elo du jour, et celui des bookmakers, tiré de leurs "
                "cotes moyennes. Les bookmakers savent ce que le modèle ignore : blessures, suspensions, "
                "rotation de l'effectif. Quand les deux divergent nettement, c'est souvent là que le "
                "modèle manque une information.")
    if prochains.empty:
        st.info("Aucun match annoncé pour l'instant. La source publie la prochaine journée en général "
                "en milieu de semaine : le bouton « Mettre à jour » va la chercher.")
    else:
        ecarts = (chances_modele - chances_marche).abs()
        meme_favori = (chances_modele.idxmax(axis=1) == chances_marche.idxmax(axis=1))
        desaccord = ecarts.max(axis=1).idxmax()
        j1, j2, j3 = st.columns(3)
        chiffre_cle(j1, "Matchs annoncés", len(prochains),
                    f"du {prochains['Date'].min():%d/%m} au {prochains['Date'].max():%d/%m}")
        chiffre_cle(j2, "Même favori", f"{meme_favori.sum()} sur {len(prochains)}",
                    "Le modèle et les bookmakers désignent le même résultat le plus probable")
        chiffre_cle(j3, "Plus gros désaccord",
                    f"{prochains.loc[desaccord, 'HomeTeam']} – {prochains.loc[desaccord, 'AwayTeam']}",
                    f"{ecarts.loc[desaccord].max() * 100:.0f} points d'écart sur une issue")

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
            issue = ecarts.loc[i].idxmax()
            nom_issue = {"H": f"la victoire de {m['HomeTeam']}", "D": "le nul",
                         "A": f"la victoire de {m['AwayTeam']}"}[issue]
            sens = "plus" if chances_modele.loc[i, issue] > chances_marche.loc[i, issue] else "moins"
            ecart = ecarts.loc[i, issue] * 100
            pied = (f'Accord : <b>{ecart:.0f} points</b> d\'écart au plus' if ecart < 5 else
                    f'<span class="{"fort" if ecart >= 12 else ""}">Le modèle croit {sens} à {nom_issue}</span> : '
                    f'<b>{pourcent(chances_modele.loc[i, issue])}</b> contre '
                    f'<b>{pourcent(chances_marche.loc[i, issue])}</b> pour les bookmakers')
            cartes.append(f"""<div class="duel">
              <div class="duel-tete"><div class="clubs">{m['HomeTeam']}<span>–</span>{m['AwayTeam']}</div>
                <div class="quand">{JOURS[m['Date'].dayofweek]} {m['Date']:%d/%m}{heure}</div></div>
              <div class="duel-ligne"><span class="source">Modèle</span>
                <div class="mini-barre">{mini_barre(chances_modele.loc[i])}</div></div>
              <div class="duel-ligne"><span class="source">Bookmakers</span>
                <div class="mini-barre">{mini_barre(chances_marche.loc[i])}</div></div>
              <div class="duel-pied">{pied}</div></div>""")
        st.html(f'<div class="journee">{"".join(cartes)}</div>')
        st.caption("Chances des bookmakers : inverse des cotes moyennes du marché (à défaut, celles de "
                   "Bet365), ramenées à 100 % pour retirer leur marge. Désaccord en rouge à partir de "
                   "12 points d'écart."
                   + (f" {inconnus} match(s) écarté(s) : club absent des résultats de la saison." if inconnus else ""))

        with st.expander("Voir les chiffres"):
            st.dataframe(
                prochains[["Date", "Heure", "HomeTeam", "AwayTeam"]].assign(
                    **{f"modele_{r}": chances_modele[r] * 100 for r in "HDA"},
                    **{f"marche_{r}": chances_marche[r] * 100 for r in "HDA"}),
                hide_index=True, width="stretch",
                column_config={
                    "Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    "HomeTeam": "Domicile", "AwayTeam": "Extérieur",
                    **{f"modele_{r}": st.column_config.NumberColumn(f"Modèle {t}", format="%.0f %%")
                       for r, t in [("H", "1"), ("D", "N"), ("A", "2")]},
                    **{f"marche_{r}": st.column_config.NumberColumn(f"Bookmakers {t}", format="%.0f %%")
                       for r, t in [("H", "1"), ("D", "N"), ("A", "2")]},
                })
