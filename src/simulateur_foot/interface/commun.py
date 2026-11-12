"""Éléments communs aux onglets de l'interface : couleurs, styles, petits composants et
données mises en cache (une fonction par calcul, rejouée seulement si les résultats changent).
"""


import numpy as np
import pandas as pd
import streamlit as st

from simulateur_foot import joueurs as stats_joueurs
from simulateur_foot import pronostics as suivi_pronostics
from simulateur_foot.championnats import CHAMPIONNATS
from simulateur_foot.collecte_resultats import (
    FICHIER,
    charger_prochains_matchs,
    mettre_a_jour,
)
from simulateur_foot.force_clubs import evolution_recente
from simulateur_foot.logos import url as logos_url
from simulateur_foot.modele import (
    RESULTATS,
    SAISON_TEST,
    SAISONS_ENTRAINEMENT,
    evaluer,
    proba_frequences,
    proba_logistique_forces,
    selection,
)
from simulateur_foot.prediction import (
    SAISON_EN_COURS,
    charger_forces,
    entrainer,
    probabilites,
)
from simulateur_foot.scores import entrainer_scores
from simulateur_foot.simulation import (
    classement,
    difficulte_calendrier,
    matchs_restants,
    points_attendus,
    resume,
    simuler,
    simuler_notes_evolutives,
)

# Jetons de couleur. Données : palette validée pour les daltoniens (domicile, nul, extérieur).
THEMES = {
    "light": {
        "H": "#2a78d6", "D": "#8b8f88", "A": "#e08a1e",
        "seq": ["#e3eede", "#9ec5f4", "#2a78d6", "#104281"],
        "fond": "#EAF2E6", "carte": "#F8FBF5", "bord": "#CBDDC3",
        "encre": "#0F1F14", "encre2": "#4A5D4F", "accent": "#1B7A3A", "accent_doux": "#D8EBD3",
    },
    "dark": {
        "H": "#3987e5", "D": "#8f948d", "A": "#f0a23a",
        "seq": ["#15271b", "#184f95", "#3987e5", "#9ec5f4"],
        "fond": "#0C1710", "carte": "#13231A", "bord": "#24392B",
        "encre": "#E8F1EA", "encre2": "#9DB2A3", "accent": "#3FBF63", "accent_doux": "#16301F",
    },
}
NOMS_ISSUES = {"H": "Victoire à domicile", "D": "Match nul", "A": "Victoire à l'extérieur"}
FORME = {"V": "Victoire", "N": "Nul", "D": "Défaite"}
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

CSS = """
<style>
  [data-testid="stMainBlockContainer"] { max-width: 1640px; padding: 1.6rem 2.5rem 3rem; }
  .entete { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.55fr); gap: 2rem;
            align-items: stretch; border-bottom: 3px solid __accent__; padding-bottom: 1rem; }
  .bandeau { display: flex; align-items: center; justify-content: space-between; gap: 1.5rem;
             border-radius: 10px; padding: 1.4rem 1.6rem 1.3rem; color: #fff;
             background: repeating-linear-gradient(90deg, #14602d 0 64px, #17702f 64px 128px);
             box-shadow: inset 0 0 0 2px rgba(255,255,255,.55); }
  .bandeau .texte { min-width: 0; }
  .bandeau .sur-titre { color: #BDE8C7; font-weight: 600; font-size: .8rem;
                        letter-spacing: .12em; text-transform: uppercase; }
  .bandeau h1 { font-family: 'Barlow Condensed', sans-serif; font-size: 3rem; line-height: 1;
                margin: .15rem 0 .4rem; padding: 0; text-transform: uppercase; color: #fff; }
  .bandeau p { margin: 0; color: #E3F3E6; font-size: 1rem; max-width: 34rem; }
  .etapes { display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; margin: 0; }
  .etape { background: __carte__; border: 1px solid __bord__; border-radius: 6px; padding: .8rem .9rem; }
  .etape b { display: block; font-family: 'Barlow Condensed', sans-serif; font-size: 1.25rem;
             color: __encre__; }
  .etape .num { color: __accent__; font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
                margin-right: .3rem; }
  .etape span { color: __encre2__; font-size: .88rem; line-height: 1.4; }
  .explication { border-left: 3px solid __accent__; background: __accent_doux__; border-radius: 0 6px 6px 0;
                 padding: .7rem 1rem; margin: .4rem 0 1rem; color: __encre__; font-size: .95rem;
                 line-height: 1.5; }
  .explication b.titre { display: block; font-size: .75rem; letter-spacing: .1em;
                         text-transform: uppercase; color: __accent__; margin-bottom: .2rem; }
  .affiche { container-type: inline-size; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 1rem;
             background: __carte__; border: 1px solid __bord__; border-radius: 8px; padding: 1.1rem 1.3rem; }
  .club { display: flex; flex-direction: column; gap: .25rem; }
  .club.droite { align-items: flex-end; text-align: right; }
  .club .lieu { font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: __encre2__; }
  .ecusson { width: 1.9rem; height: 1.9rem; object-fit: contain; flex: none; }
  /* Hauteur calée sur le nom ; largeur libre (bornée) pour les écussons larges ou étroits */
  .club .ecusson { height: clamp(2.2rem, 8cqi, 3.1rem); width: auto; max-width: 4.4rem; }
  .bandeau .ecusson-ligue { flex: none; width: 5.5rem; height: 5.5rem; object-fit: contain; padding: .6rem;
                            background: rgba(255,255,255,.95); border-radius: 50%; }
  .club .nom { font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
               font-size: clamp(1.3rem, 5cqi, 2.3rem); white-space: nowrap;
               line-height: 1; color: __encre__; display: flex; align-items: center; gap: .5rem; }
  .club .infos { color: __encre2__; font-size: .9rem; font-variant-numeric: tabular-nums; }
  .club .infos b { color: __encre__; }
  .contre { font-family: 'Barlow Condensed', sans-serif; font-size: 1.4rem; color: __encre2__; }
  .forme { display: flex; gap: 3px; margin-top: .15rem; }
  .forme i { font-style: normal; width: 1.35rem; height: 1.35rem; border-radius: 3px; font-size: .72rem;
             font-weight: 600; display: flex; align-items: center; justify-content: center;
             border: 1px solid __bord__; color: __encre__; }
  .forme i.V { background: __encre__; color: __fond__; border-color: __encre__; }
  .forme i.N { background: transparent; }
  .forme i.D { background: transparent; color: __encre2__; border-style: dashed; }
  .barre { display: flex; gap: 2px; height: 46px; margin: 1rem 0 .4rem; }
  .barre div { border-radius: 4px; display: flex; align-items: center; justify-content: center;
               color: #fff; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 2.8rem; }
  .legende { display: flex; justify-content: space-between; gap: .4rem 1rem; font-size: .92rem;
             flex-wrap: wrap; color: __encre__; }
  .legende b { font-variant-numeric: tabular-nums; }
  .pastille { display: inline-block; width: .75rem; height: .75rem; border-radius: 2px;
              margin-right: .4rem; vertical-align: -1px; }
  .resultat { font-family: 'Barlow Condensed', sans-serif; font-size: 2rem; font-weight: 700;
              color: __encre__; display: flex; align-items: center; gap: .6rem; }
  .gaufre { display: grid; grid-template-columns: repeat(20, 1fr); gap: 3px; max-width: 560px;
            margin: .5rem 0 .4rem; }
  .gaufre div { aspect-ratio: 1; border-radius: 2px; }
  .legende-graphique { display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; font-size: .85rem;
                       color: __encre2__; margin: -.2rem 0 .3rem; }
  .legende-graphique span { display: inline-flex; align-items: center; gap: .45rem; }
  .legende-graphique i { display: inline-block; flex: none; box-sizing: border-box; }
  .colonne-titre { font-family: 'Barlow Condensed', sans-serif; font-size: 1.05rem; font-weight: 600;
                   letter-spacing: .08em; text-transform: uppercase; color: __encre2__;
                   border-bottom: 1px solid __bord__; padding-bottom: .3rem; margin: .2rem 0 .6rem; }
  .journee { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(430px, 100%), 1fr));
             gap: .8rem; margin: .4rem 0 .8rem; }
  .duel { background: __carte__; border: 1px solid __bord__; border-radius: 8px; padding: .8rem 1rem .75rem; }
  .duel-tete { display: flex; justify-content: space-between; align-items: baseline; gap: .6rem;
               margin-bottom: .45rem; }
  .duel-tete .clubs { font-family: 'Barlow Condensed', sans-serif; font-size: 1.4rem; font-weight: 700;
                      color: __encre__; line-height: 1.1; }
  .duel-tete .clubs span { color: __encre2__; font-weight: 400; margin: 0 .3rem; }
  .duel-tete .quand { color: __encre2__; font-size: .82rem; white-space: nowrap; }
  .duel-ligne { display: grid; grid-template-columns: 6.6rem 1fr; align-items: center; gap: .6rem;
                margin: .3rem 0; }
  .duel-ligne .source { font-size: .74rem; letter-spacing: .07em; text-transform: uppercase;
                        color: __encre2__; }
  .mini-barre { display: flex; gap: 2px; height: 24px; }
  .mini-barre div { border-radius: 3px; display: flex; align-items: center; justify-content: center;
                    color: #fff; font-size: .8rem; font-weight: 600; font-variant-numeric: tabular-nums;
                    min-width: 0; overflow: hidden; white-space: nowrap; }
  .duel-pied { font-size: .86rem; color: __encre2__; margin-top: .5rem; border-top: 1px solid __bord__;
               padding-top: .45rem; }
  .duel-pied b { color: __encre__; }
  .duel-pied .fort { color: __accent__; font-weight: 600; }
  .chiffre-cle { background: __carte__; border: 1px solid __bord__; border-radius: 6px;
                 padding: .8rem 1rem; height: 100%; }
  .chiffre-cle .valeur .ecusson { height: 2rem; width: auto; max-width: 2.8rem; margin-right: .5rem;
                                  vertical-align: -.3rem; }
  .chiffre-cle .valeur { font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
                         font-size: 2.2rem; line-height: 1.05; color: __encre__; }
  .chiffre-cle .libelle { font-size: .8rem; letter-spacing: .06em; text-transform: uppercase;
                          color: __encre2__; }
  .chiffre-cle .detail { font-size: .88rem; color: __encre2__; margin-top: .2rem; }
  .fiche { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 1.2rem;
           background: __carte__; border: 1px solid __bord__; border-radius: 10px; padding: 1.1rem 1.4rem;
           margin-bottom: .8rem; }
  .fiche .ecusson { width: 5rem; height: 5rem; }
  .fiche h2 { font-family: 'Barlow Condensed', sans-serif; font-size: 2.6rem; line-height: 1; margin: 0;
              padding: 0; text-transform: uppercase; color: __encre__; }
  .fiche .infos { color: __encre2__; font-size: .95rem; margin-top: .3rem; font-variant-numeric: tabular-nums; }
  .fiche .infos b { color: __encre__; }
  .fiche .hausse { color: __accent__; font-weight: 600; }
  .fiche .baisse { color: __encre2__; font-weight: 600; }
  .fiche .cote-droit { display: flex; flex-direction: column; align-items: flex-end; gap: .3rem; }
  .fiche .cote-droit span { font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: __encre2__; }
  .matchs-club { display: flex; flex-direction: column; gap: .3rem; margin: .3rem 0 1rem; }
  .matchs-club div { display: grid; grid-template-columns: 4.6rem 1.6rem 1.8rem 1fr auto; align-items: center;
                     gap: .6rem; padding: .35rem .6rem; background: __carte__; border: 1px solid __bord__;
                     border-radius: 6px; color: __encre__; font-size: .93rem; }
  .matchs-club .date, .matchs-club .lieu { color: __encre2__; font-size: .82rem; }
  .matchs-club .ecusson { width: 1.6rem; height: 1.6rem; }
  .matchs-club b { font-variant-numeric: tabular-nums; }
  .matchs-club i { font-style: normal; width: 1.5rem; height: 1.5rem; border-radius: 3px; font-size: .75rem;
                   font-weight: 600; display: flex; align-items: center; justify-content: center;
                   border: 1px solid __bord__; }
  .matchs-club i.V { background: __encre__; color: __fond__; border-color: __encre__; }
  .matchs-club i.D { color: __encre2__; border-style: dashed; }
  .classement { margin: .6rem 0 1.2rem; }
  .jr { position: relative; display: grid; grid-template-columns: 1.6rem 2.2rem minmax(7rem, 13rem) 1fr;
        align-items: center; gap: .7rem; padding: .35rem .5rem; border-radius: 8px; }
  .jr:hover { background: __accent_doux__; z-index: 5; }
  .jr .rang { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 1.3rem;
              color: __encre2__; text-align: center; }
  .jr:nth-child(-n+3) .rang { color: __accent__; }
  .jr .ecusson { width: 2.2rem; height: 2.2rem; }
  .jr .ident { display: flex; flex-direction: column; line-height: 1.15; min-width: 0; }
  .jr .ident b { color: __encre__; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .jr .ident span { color: __encre2__; font-size: .8rem; }
  .piste { position: relative; height: 1.6rem; }
  .piste .prevu, .piste .actuel { position: absolute; left: 0; top: .15rem; height: 1.3rem; border-radius: 0 6px 6px 0; }
  .piste .prevu { background: __accent__; opacity: .25; }
  .piste .actuel { background: __accent__; }
  .piste .fourch { position: absolute; top: calc(.8rem - 1px); height: 2px; background: __encre__; opacity: .8; }
  .piste .fourch::before, .piste .fourch::after { content: ""; position: absolute; top: -4px; width: 2px;
                                                   height: 10px; background: __encre__; }
  .piste .fourch::before { left: 0; } .piste .fourch::after { right: 0; }
  .piste .val { position: absolute; top: 50%; transform: translateY(-50%); margin-left: .6rem;
                font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 1.3rem; color: __encre__; }
  .jr .bulle { display: none; position: absolute; left: 4rem; top: calc(100% - .2rem); z-index: 20; width: 17rem;
               background: __carte__; border: 1px solid __bord__; border-radius: 10px; padding: .8rem .95rem;
               box-shadow: 0 10px 28px rgba(0,0,0,.25); pointer-events: none; }
  .jr:hover .bulle { display: block; }
  .bulle .tete { display: flex; align-items: center; gap: .6rem; padding-bottom: .55rem; margin-bottom: .5rem;
                 border-bottom: 1px solid __bord__; }
  .bulle .tete .ecusson { width: 2.4rem; height: 2.4rem; }
  .bulle .tete b { display: block; font-family: 'Barlow Condensed', sans-serif; font-size: 1.35rem;
                   line-height: 1; color: __encre__; }
  .bulle .tete span { color: __encre2__; font-size: .82rem; }
  .bulle dl { display: grid; grid-template-columns: auto 1fr; gap: .25rem .9rem; margin: 0; font-size: .88rem; }
  .bulle dt { color: __encre2__; }
  .bulle dd { margin: 0; text-align: right; font-weight: 600; color: __encre__; font-variant-numeric: tabular-nums; }
  .bulle dd.fort { color: __accent__; font-size: 1rem; }
  .legende-classement { display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; font-size: .85rem; color: __encre2__;
                        margin: .2rem 0 .4rem; }
  .legende-classement i { display: inline-block; width: 1.6rem; height: .7rem; border-radius: 3px;
                          margin-right: .4rem; background: __accent__; vertical-align: middle; }
  .legende-classement i.clair { opacity: .25; }
  .legende-classement i.trait { height: 2px; background: __encre__; }
  .sous-titre { font-family: 'Barlow Condensed', sans-serif; font-size: 1.05rem; font-weight: 600;
                letter-spacing: .08em; text-transform: uppercase; color: __encre2__; margin: 1rem 0 .3rem; }
  .scores-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin: .2rem 0 .5rem; }
  .chip { display: inline-flex; align-items: baseline; gap: .45rem; background: __carte__; border: 1px solid __bord__;
          border-radius: 6px; padding: .3rem .65rem; font-variant-numeric: tabular-nums; }
  .chip b { font-family: 'Barlow Condensed', sans-serif; font-size: 1.35rem; color: __encre__; }
  .chip span { color: __encre2__; font-size: .85rem; }
  .chip.fort { border-color: __accent__; background: __accent_doux__; }
  .resultat .score { font-size: 2.6rem; letter-spacing: .02em; }
  .resultat .score small { font-size: 1.2rem; font-weight: 600; color: __encre2__; margin: 0 .5rem; }
  .issue { color: __encre2__; margin: -.2rem 0 .6rem; }
  .fr { grid-template-columns: 1.6rem 2.2rem minmax(8rem, 17rem) 1fr 4.4rem; }
  .fr .ident span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .piste .repere { position: absolute; top: 0; height: 1.6rem; border-left: 2px dashed __encre2__; opacity: .8; }
  .delta { justify-self: end; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 1.15rem;
           padding: .1rem .45rem; border-radius: 4px; border: 1px solid __bord__; color: __encre2__;
           min-width: 3.4rem; text-align: center; font-variant-numeric: tabular-nums; }
  .delta.haut { color: #fff; background: __accent__; border-color: __accent__; }
  .delta.bas { color: __encre__; border-style: dashed; }
  .legende-classement i.repere-leg { width: 0; height: .9rem; border-left: 2px dashed __encre2__; background: none;
                                     border-radius: 0; }
  @media (max-width: 1100px) {
    [data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 2.5rem; }
    .entete { grid-template-columns: 1fr; gap: 1rem; }
  }
  @media (max-width: 640px) {
    .fiche { grid-template-columns: auto 1fr; }
    .fiche .cote-droit { grid-column: 1 / -1; align-items: flex-start; }
    .jr { grid-template-columns: 1.4rem 1.8rem 1fr; }
    .jr .piste { grid-column: 1 / -1; }
    .jr .bulle { left: .5rem; width: calc(100% - 1rem); }
    .bandeau h1 { font-size: 2.3rem; }
    .bandeau .ecusson-ligue { display: none; }
    .entete { grid-template-columns: 1fr; gap: 1rem; }
    .etapes { grid-template-columns: 1fr; gap: .4rem; }
    .etape { padding: .45rem .8rem; }
    .etape b { font-size: 1.1rem; }
    .etape span { display: none; }
    .fr { grid-template-columns: 1.4rem 1.8rem 1fr 3.6rem; }
    .fr .piste { grid-column: 1 / -1; }
    .fr .delta { grid-column: 4; grid-row: 1; }
    .affiche { grid-template-columns: 1fr; gap: .7rem; }
    .club.droite { align-items: flex-start; text-align: left; }
    .contre { display: none; }
    .club .nom { font-size: 1.9rem; }
    .club .ecusson { height: 2.6rem; max-width: 3.6rem; }
  }
</style>
"""


# ---------- Mise en forme des nombres ----------

def nom_saison(saison):
    """2627 → 2026-27."""
    texte = str(saison)
    return f"20{texte[:2]}-{texte[2:]}"


def decimal(x, chiffres=3, signe=False):
    """Nombre à virgule, à la française."""
    return f"{x:{'+' if signe else ''}.{chiffres}f}".replace(".", ",")


def pourcent(x):
    return f"{x:.0%}".replace("%", " %")


def rang(n):
    """1 → 1ᵉʳ, 6 → 6ᵉ."""
    return f"{n}ᵉʳ" if n == 1 else f"{n}ᵉ"


# ---------- Petits composants ----------

def explication(texte, titre="Comment lire cette page"):
    st.html(f'<div class="explication"><b class="titre">{titre}</b>{texte}</div>')


PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"  # image vide


def image(chemin):
    """L'adresse de l'écusson sur le serveur de fichiers statiques (image vide s'il est absent)."""
    return logos_url(chemin) if chemin.exists() else PIXEL


def ecusson(chemin, classe="ecusson", alt=""):
    return f'<img class="{classe}" src="{logos_url(chemin)}" alt="{alt}">' if chemin.exists() else ""


def chiffre_cle(colonne, libelle, valeur, detail=""):
    colonne.html(f'<div class="chiffre-cle"><div class="libelle">{libelle}</div>'
                 f'<div class="valeur">{valeur}</div><div class="detail">{detail}</div></div>')


# ---------- Données (mises en cache) ----------
# Chaque fonction reçoit le code du championnat et la « version » du fichier de
# résultats (sa date de modification) : une mise à jour vide le cache d'elle-même.

SEUIL_HEURES = 12  # au-delà, la saison en cours est retéléchargée au lancement


def version_donnees():
    return FICHIER.stat().st_mtime


@st.cache_data
def donnees(code, version):
    matchs, notes = charger_forces(code)
    return matchs, pd.Series(notes).sort_values(ascending=False)


@st.cache_resource
def modele_retenu(code, version):
    matchs, _ = donnees(code, version)
    return entrainer(matchs)


@st.cache_resource
def modele_scores_retenu(code, version):
    matchs, _ = donnees(code, version)
    return entrainer_scores(matchs)


@st.cache_data
def forces_du_jour(code, version):
    """Chaque club avec sa note, sa variation sur 5 matchs, son rang au classement et son calendrier restant."""
    matchs, notes = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    forces = pd.DataFrame({"note": notes})
    forces["variation"] = evolution_recente(saison, notes)
    forces["rang"] = pd.Series({club: i + 1 for i, club in enumerate(table.index)})
    forces["joues"] = table["joues"]
    forces["calendrier"] = difficulte_calendrier(matchs_restants(saison), notes)
    return forces.sort_values("note", ascending=False)


@st.cache_data
def forme_recente(code, version, club, nb=5):
    """Les derniers résultats du club cette saison, du plus ancien au plus récent (V, N, D)."""
    matchs, _ = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    siens = saison[(saison["HomeTeam"] == club) | (saison["AwayTeam"] == club)].sort_values("Date")
    lettres = []
    for m in siens.tail(nb).itertuples():
        if m.FTR == "D":
            lettres.append("N")
        else:
            gagne = (m.FTR == "H") == (m.HomeTeam == club)
            lettres.append("V" if gagne else "D")
    return lettres


@st.cache_data
def fin_de_saison(code, version, nb, graine, evolutives=True, premiers=()):
    """premiers : affiches annoncées pour la prochaine journée, jouées en premier dans chaque simulation."""
    matchs, notes = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    restants = matchs_restants(saison)
    if evolutives:
        points, rangs = simuler_notes_evolutives(table, restants, notes, modele_retenu(code, version),
                                                 nb, graine, modele_scores=modele_scores_retenu(code, version),
                                                 premiers=set(premiers))
    else:
        proba = probabilites(modele_retenu(code, version), restants["HomeTeam"].map(notes).to_numpy(),
                             restants["AwayTeam"].map(notes).to_numpy())
        points, rangs = simuler(table, restants, proba, nb, graine)
    synthese = resume(table, points, rangs, CHAMPIONNATS[code])
    bas, haut = np.percentile(points, [10, 90], axis=0)
    fourchette = pd.DataFrame({"bas": bas, "haut_points": haut}, index=table.index)
    # Pronostic d'avant-match de chaque match déjà joué : notes Elo du jour du match
    proba_jouees = probabilites(modele_retenu(code, version), saison["force_dom"].to_numpy(),
                                saison["force_ext"].to_numpy())
    fourchette["prevus"] = points_attendus(saison, proba_jouees)
    # Arrondi au dixième, + 0.0 pour éviter d'afficher « -0.0 »
    fourchette["ecart"] = (table["points"] - fourchette["prevus"]).round(1) + 0.0
    fourchette["calendrier"] = difficulte_calendrier(restants, notes)
    return synthese.join(fourchette), rangs, list(table.index), len(restants)


@st.cache_data
def joueurs_projetes(code, version, version_joueurs):
    """Meilleurs buteurs et passeurs du championnat, leur projection, et les clubs ESPN non reconnus."""
    matchs, notes = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    tous = stats_joueurs.charger()
    calendrier = stats_joueurs.facteur_calendrier(saison, matchs_restants(saison), notes,
                                                  modele_scores_retenu(code, version))
    inconnus = stats_joueurs.clubs_non_reconnus(tous, set(saison["HomeTeam"]) | set(saison["AwayTeam"]), code)
    return stats_joueurs.projeter(tous, saison, code, calendrier=calendrier), inconnus


def donnees_joueurs():
    """Date du fichier des joueurs, après l'avoir mis à jour s'il a plus de 12 h (None si absent).

    Comme pour les résultats, la mise à jour automatique n'a lieu qu'une fois par session ;
    les tests la désactivent en fixant st.session_state.maj_joueurs à False.
    """
    if st.session_state.get("maj_joueurs", True):
        st.session_state.maj_joueurs = False
        if stats_joueurs.heures_depuis_telechargement() > SEUIL_HEURES:
            try:
                stats_joueurs.telecharger()
            except Exception:  # pas de réseau, ESPN indisponible : on garde le fichier local s'il existe
                pass
    return stats_joueurs.FICHIER_JOUEURS.stat().st_mtime if stats_joueurs.FICHIER_JOUEURS.exists() else None


@st.cache_data
def prochaine_journee(code, version, version_prochains):
    """Matchs annoncés et chances du modèle avec les notes du jour ; nombre de matchs écartés."""
    matchs, notes = donnees(code, version)
    prochains = charger_prochains_matchs(code, matchs[matchs["Saison"] == SAISON_EN_COURS])
    connus = prochains["HomeTeam"].isin(notes.index) & prochains["AwayTeam"].isin(notes.index)
    prochains = prochains[connus].reset_index(drop=True)
    if prochains.empty:  # rien d'annoncé : le modèle refuse un tableau vide
        vide = pd.DataFrame(columns=RESULTATS, dtype=float)
        return prochains, vide, int((~connus).sum())
    modele = probabilites(modele_retenu(code, version), prochains["HomeTeam"].map(notes).to_numpy(),
                          prochains["AwayTeam"].map(notes).to_numpy())
    return prochains, modele, int((~connus).sum())


@st.cache_data
def bilan_pronostics(code, version, version_pronostics):
    """Bilan des pronostics enregistrés avant les matchs : (ce championnat, les six réunis)."""
    joues = suivi_pronostics.avec_resultats()
    return suivi_pronostics.bilan(joues, code), suivi_pronostics.bilan(joues)


@st.cache_data
def fiabilite(code, version):
    matchs, _ = donnees(code, version)
    scores = {}
    for nom, predire in [("modele", proba_logistique_forces), ("frequences", proba_frequences)]:
        _, log_test, brier_test = evaluer(predire, matchs)
        scores[nom] = (log_test.mean(), brier_test.mean())
    test = selection(matchs, [SAISON_TEST])
    proba = proba_logistique_forces(selection(matchs, SAISONS_ENTRAINEMENT), test)
    return scores, proba, test


def actualiser():
    """Retélécharge la saison en cours ; renvoie un message pour l'utilisateur."""
    try:
        nouveaux = mettre_a_jour()
    except Exception as erreur:  # pas de réseau, site indisponible…
        return "erreur", f"Mise à jour impossible ({erreur.__class__.__name__}) : les données locales sont utilisées."
    if not nouveaux:
        return "ok", "Données vérifiées : aucun nouveau match depuis la dernière mise à jour."
    return "ok", f"Données mises à jour : {nouveaux} nouveaux matchs."
