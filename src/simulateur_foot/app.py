"""Interface de test du simulateur : choix du championnat, un match, la fin de saison, la fiabilité.

Lancement : uv run simulateur-foot interface
"""

import html

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from simulateur_foot.championnats import CHAMPIONNATS, PAR_DEFAUT
from simulateur_foot.collecte_resultats import (FICHIER, FICHIER_PROCHAINS, charger_prochains_matchs,
                                                heures_depuis_mise_a_jour, mettre_a_jour)
from simulateur_foot import joueurs as stats_joueurs
from simulateur_foot.logos import chemin_championnat, chemin_club, url as logos_url
from simulateur_foot.force_clubs import AVANTAGE_TERRAIN, NOTE_INITIALE, NOTE_PROMU
from simulateur_foot.modele import (RESULTATS, SAISON_TEST, SAISONS_ENTRAINEMENT, evaluer,
                                    proba_frequences, proba_logistique_forces, selection)
from simulateur_foot.prediction import (SAISON_EN_COURS, SAISONS_APPRENTISSAGE, chances_bookmakers,
                                        charger_forces, entrainer, probabilites)
from simulateur_foot.simulation import (classement, matchs_restants, points_attendus, resume, simuler,
                                        simuler_notes_evolutives)

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
  @media (max-width: 1100px) {
    [data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 2.5rem; }
    .entete { grid-template-columns: 1fr; gap: 1rem; }
  }
  @media (max-width: 640px) {
    .jr { grid-template-columns: 1.4rem 1.8rem 1fr; }
    .jr .piste { grid-column: 1 / -1; }
    .jr .bulle { left: .5rem; width: calc(100% - 1rem); }
    .bandeau h1 { font-size: 2.3rem; }
    .bandeau .ecusson-ligue { display: none; }
    .entete { grid-template-columns: 1fr; gap: 1rem; }
    .etapes { grid-template-columns: 1fr; }
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
def fin_de_saison(code, version, nb, graine, evolutives=True):
    matchs, notes = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    table = classement(saison)
    restants = matchs_restants(saison)
    if evolutives:
        points, rangs = simuler_notes_evolutives(table, restants, notes, modele_retenu(code, version),
                                                 nb, graine)
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
    return synthese.join(fourchette), rangs, list(table.index), len(restants)


@st.cache_data
def joueurs_projetes(code, version, version_joueurs):
    """Meilleurs buteurs et passeurs du championnat, avec leur projection de fin de saison."""
    matchs, _ = donnees(code, version)
    saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
    return stats_joueurs.projeter(stats_joueurs.charger(), saison, code)


def donnees_joueurs():
    """Date du fichier des joueurs, après l'avoir mis à jour s'il a plus de 12 h (None si absent)."""
    if stats_joueurs.heures_depuis_telechargement() > SEUIL_HEURES:
        try:
            stats_joueurs.telecharger()
        except Exception:  # pas de réseau, ESPN indisponible : on garde le fichier local s'il existe
            pass
    return stats_joueurs.FICHIER_JOUEURS.stat().st_mtime if stats_joueurs.FICHIER_JOUEURS.exists() else None


@st.cache_data
def prochaine_journee(code, version, version_prochains):
    """Matchs annoncés, chances du modèle (notes du jour) et des bookmakers (cotes moyennes)."""
    matchs, notes = donnees(code, version)
    prochains = charger_prochains_matchs(code, matchs[matchs["Saison"] == SAISON_EN_COURS])
    connus = prochains["HomeTeam"].isin(notes.index) & prochains["AwayTeam"].isin(notes.index)
    prochains = prochains[connus].reset_index(drop=True)
    if prochains.empty:  # rien d'annoncé : le modèle refuse un tableau vide
        vide = pd.DataFrame(columns=RESULTATS, dtype=float)
        return prochains, vide, vide, int((~connus).sum())
    modele = probabilites(modele_retenu(code, version), prochains["HomeTeam"].map(notes).to_numpy(),
                          prochains["AwayTeam"].map(notes).to_numpy())
    marche = chances_bookmakers(prochains["CoteH"], prochains["CoteD"], prochains["CoteA"])
    return prochains, modele, marche, int((~connus).sum())


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


# ---------- En-tête ----------

st.set_page_config(page_title="Simulateur foot", page_icon="⚽", layout="wide")
mode = "dark" if st.context.theme.type == "dark" else "light"
c = THEMES[mode]
css = CSS
for cle, valeur in c.items():
    if isinstance(valeur, str):
        css = css.replace(f"__{cle}__", valeur)
st.html(css)

# Une fois par session : si les résultats ont plus de 12 h, on va chercher les nouveaux
if "verification" not in st.session_state:
    st.session_state.verification = None
    if heures_depuis_mise_a_jour() > SEUIL_HEURES:
        with st.spinner("Recherche des derniers résultats…"):
            st.session_state.verification = actualiser()

codes = list(CHAMPIONNATS)
# L'adresse n'est lue qu'au premier passage. Ensuite, le choix vit dans st.session_state.
# Un `default` relu à chaque passage changerait l'identité du widget et ferait perdre un clic sur deux.
if "championnat" not in st.session_state:
    code_url = st.query_params.get("championnat", PAR_DEFAUT)
    st.session_state.championnat = code_url if code_url in codes else PAR_DEFAUT
elif st.session_state.championnat is None:  # un clic sur le championnat déjà choisi le désélectionne
    st.session_state.championnat = st.session_state.get("dernier_championnat", PAR_DEFAUT)
barre_championnat, barre_donnees, barre_bouton = st.columns([5, 4, 1.1], vertical_alignment="center")
code = barre_championnat.segmented_control(
    "Championnat", codes, key="championnat",
    format_func=lambda x: CHAMPIONNATS[x].nom, label_visibility="collapsed") or PAR_DEFAUT
st.query_params["championnat"] = st.session_state.dernier_championnat = code
regles = CHAMPIONNATS[code]
version = version_donnees()

matchs, notes = donnees(code, version)
saison = matchs[matchs["Saison"] == SAISON_EN_COURS]
table_actuelle = classement(saison)
rangs_actuels = {club: i + 1 for i, club in enumerate(table_actuelle.index)}

st.html(f"""
<div class="entete">
<div class="bandeau"><div class="texte">
  <div class="sur-titre">Simulateur foot · {regles.pays} · saison {nom_saison(SAISON_EN_COURS)} ·
  résultats au {saison["Date"].max():%d/%m/%Y}</div>
  <h1>{regles.nom}</h1>
  <p>Cet outil estime les chances de chaque club, match par match puis sur toute la saison,
  à partir des résultats du championnat depuis 2021.</p>
</div>{ecusson(chemin_championnat(code), "ecusson-ligue", regles.nom)}</div>
<div class="etapes">
  <div class="etape"><b><span class="num">1</span>Une note par club</b>
    <span>Chaque club a une note Elo : il gagne des points quand il bat un adversaire, il en perd
    quand il s'incline. Plus la surprise est grande, plus la note bouge. 1500 = club moyen.</span></div>
  <div class="etape"><b><span class="num">2</span>Des probabilités par match</b>
    <span>L'écart de notes entre les deux clubs, plus un bonus pour l'équipe qui reçoit, donne
    les chances de victoire, de nul et de défaite.</span></div>
  <div class="etape"><b><span class="num">3</span>Des milliers de saisons</b>
    <span>On joue au hasard tous les matchs restants, selon ces chances, des milliers de fois.
    On compte ensuite combien de fois chaque club finit champion, en haut du tableau ou relégué.</span></div>
</div>
</div>
""")

heures = heures_depuis_mise_a_jour()
age = "il y a moins d'une heure" if heures < 1 else (
    f"il y a {heures:.0f} h" if heures < 48 else f"il y a {heures / 24:.0f} jours")
barre_donnees.caption(f"Résultats téléchargés depuis football-data.co.uk {age}. La source est mise à "
                      f"jour en général le lundi ; l'outil va chercher les nouveaux résultats tout seul "
                      f"au lancement quand ses données ont plus de {SEUIL_HEURES} h.")
if barre_bouton.button("Mettre à jour", width="stretch"):
    with st.spinner("Téléchargement de la saison en cours…"):
        st.session_state.verification = actualiser()
    st.rerun()
if st.session_state.verification:
    etat, message = st.session_state.verification
    (st.success if etat == "ok" else st.warning)(message)
    st.session_state.verification = None

onglet_match, onglet_journee, onglet_saison, onglet_joueurs, onglet_fiabilite = st.tabs(
    ["Un match", "Prochaine journée", "La fin de saison", "Les meilleurs joueurs", "Le modèle est-il fiable ?"])

# ---------- Un match ----------

with onglet_match:
    explication("Choisissez deux clubs : le simulateur donne les chances de chaque issue si ce match "
                "se jouait aujourd'hui. Ce sont des chances, pas une certitude : un club donné "
                "gagnant à 60 % perd ou fait nul 4 fois sur 10. Le bouton « Jouer le match » "
                "le montre en le tirant au sort.")

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

        if "tirage" not in st.session_state:
            st.session_state.tirage = None
        if st.button("Jouer le match", type="primary"):
            st.session_state.tirage = int(np.random.default_rng().integers(1_000_000))
        if st.session_state.tirage is not None:
            generateur = np.random.default_rng(st.session_state.tirage)
            issues = generateur.choice(RESULTATS, size=100, p=proba[RESULTATS].to_numpy())
            issue = issues[0]
            texte = {"H": f"Victoire de {dom}", "D": "Match nul", "A": f"Victoire de {ext}"}[issue]
            st.html(f'<div class="resultat"><span class="pastille" style="background:{c[issue]};'
                    f'width:1.1rem;height:1.1rem;margin:0"></span>{texte}</div>')
            comptes = {r: int((issues == r).sum()) for r in ["H", "D", "A"]}
            cases = "".join(f'<div style="background:{c[r]}"></div>' for r in ["H", "D", "A"]
                            for _ in range(comptes[r]))
            st.markdown(f"**Et si on le jouait 100 fois ?** {dom} gagne {comptes['H']} fois, "
                        f"{comptes['D']} nuls, {ext} gagne {comptes['A']} fois. Relancez : "
                        "les chiffres bougent un peu, mais restent proches des chances annoncées.")
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

# ---------- Prochaine journée ----------

with onglet_journee:
    explication("Les matchs annoncés de la prochaine journée, avec deux pronostics côte à côte : celui "
                "du modèle, tiré des seules notes Elo du jour, et celui des bookmakers, tiré de leurs "
                "cotes moyennes. Les bookmakers savent ce que le modèle ignore : blessures, suspensions, "
                "rotation de l'effectif. Quand les deux divergent nettement, c'est souvent là que le "
                "modèle manque une information.")
    version_prochains = FICHIER_PROCHAINS.stat().st_mtime if FICHIER_PROCHAINS.exists() else 0
    prochains, chances_modele, chances_marche, inconnus = prochaine_journee(code, version, version_prochains)

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

# ---------- La fin de saison ----------

with onglet_saison:
    explication("Le simulateur part du classement actuel et joue au hasard tous les matchs qui restent, "
                "selon les chances de chaque affiche. Il recommence des milliers de fois. Si un club "
                "finit champion dans 6 500 saisons simulées sur 10 000, ses chances de titre sont "
                "de 65 %. Après chaque journée tirée au sort, les notes des clubs sont mises à "
                "jour comme après un vrai match : un club qui enchaîne les victoires devient favori "
                "des journées suivantes, comme dans la réalité.")

    r1, r2, k1, k2, k3 = st.columns([1.5, .8, 1, 1, 1], vertical_alignment="bottom")
    nb = r1.select_slider("Nombre de saisons simulées", [1_000, 5_000, 10_000, 50_000], value=10_000,
                          format_func=lambda n: f"{n:,}".replace(",", " "))
    graine = r2.number_input("Graine du hasard", min_value=0, value=0, step=1,
                             help="Même graine = mêmes tirages : pratique pour comparer deux réglages.")
    evolutives = r1.toggle(
        "Les notes évoluent pendant la saison simulée", value=True,
        help="Désactivé, chaque club garde sa note du jour jusqu'à la fin : les séries ne se "
             "prolongent pas et la simulation est trop sûre d'elle. Pratique pour comparer.")
    synthese, rangs, ordre_clubs, nb_restants = fin_de_saison(code, version, nb, graine, evolutives)
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
        tableau[["logo", "club", "rang", "joues", "points", "prevus", "ecart", "diff_buts", "points_finaux"] + probas],
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
            "vrais matchs. Le calendrier des matchs restants n'est pas connu : l'ordre des affiches "
            "est tiré au hasard, en journées où chaque club joue au plus une fois. Avec les notes "
            "figées (interrupteur en haut), la simulation est plus sûre d'elle.\n"
            "- Le simulateur tire l'**issue** de chaque match (victoire, nul, défaite), pas le score. "
            "À égalité de points, les clubs sont départagés par leur différence de buts actuelle, "
            f"puis au hasard. En {regles.nom}, le vrai règlement départage d'abord par "
            f"{regles.departage}.\n"
            f"- Un club qui n'était pas dans le championnat la saison précédente démarre à "
            f"{NOTE_PROMU} points, qu'il monte de {regles.division_inferieure} ou descende de "
            "l'étage au-dessus : les notes de deux divisions ne se comparent pas encore.\n"
            f"- Les zones ({regles.haut[0].lower()}, barrage, relégation) suivent les règles 2026-27, "
            "simplifiées : le nombre de places européennes peut varier selon l'indice UEFA.\n"
            "- Blessures, transferts et changements d'entraîneur ne sont pas pris en compte.")

# ---------- Le modèle est-il fiable ? ----------

with onglet_joueurs:
    explication("Les 50 meilleurs buteurs et les 50 meilleurs passeurs du championnat, avec leur total "
                "prévu à la fin de saison. Le calcul suppose que chaque joueur garde son rythme : la même "
                "part des matchs de son club, et les mêmes buts (ou passes) par match joué. On tire "
                "ensuite des milliers de fins de saison au hasard. Le trait couvre 8 saisons simulées "
                "sur 10 : très large tant que le joueur a peu joué, car un bon début de saison "
                "n'annonce pas toujours la suite.", titre="Comment lire la prévision")
    version_joueurs = donnees_joueurs()
    if version_joueurs is None:
        st.warning("Les statistiques des joueurs n'ont pas pu être téléchargées (pas de réseau ?). "
                   "Réessayez avec `uv run simulateur-foot joueurs`.")
    else:
        tous = joueurs_projetes(code, version, version_joueurs)
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
      <dt>Rythme</dt><dd>{rythme} {singulier} / match</dd>
      <dt>Fin de saison</dt><dd class="fort">≈ {prevu} {unite}</dd>
      <dt>Fourchette</dt><dd>{bas} à {haut}</dd>
    </dl>
  </div>
</div>""")
        st.html('<div class="legende-classement"><span><i></i>Total actuel</span>'
                '<span><i class="clair"></i>Prévu en fin de saison</span>'
                '<span><i class="trait"></i>Fourchette probable (8 saisons sur 10)</span></div>'
                f'<div class="classement">{"".join(lignes)}</div>')


with onglet_fiabilite:
    scores, proba_test, test = fiabilite(code, version)
    reel = test["FTR"]
    explication(
        f"Pour savoir si les chances annoncées sont crédibles, on a fait un examen à l'aveugle : le modèle "
        f"a appris sur les saisons {', '.join(nom_saison(s) for s in SAISONS_ENTRAINEMENT)}, puis il a "
        f"prédit les {len(test)} matchs de la saison {nom_saison(SAISON_TEST)} sans les avoir vus. "
        "On compare ici ses prédictions à ce qui s'est vraiment passé. Le simulateur utilise ensuite "
        f"le même modèle, réentraîné en ajoutant {nom_saison(SAISON_TEST)}.")

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
