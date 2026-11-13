"""Interface du simulateur : choix du championnat, puis un onglet par vue.

Ce fichier pose l'en-tête et prépare les données du championnat choisi ; chaque onglet vit dans
interface/onglets/ et les éléments partagés (styles, composants, calculs en cache) dans interface/commun.py.

Lancement : uv run simulateur-foot interface
"""

from types import SimpleNamespace

import streamlit as st

from simulateur_foot import collecte_resultats
from simulateur_foot.championnats import CHAMPIONNATS, PAR_DEFAUT
from simulateur_foot.collecte_resultats import heures_depuis_mise_a_jour
from simulateur_foot.interface.commun import (
    CSS,
    SEUIL_HEURES,
    THEMES,
    actualiser,
    donnees,
    ecusson,
    nom_saison,
    prochaine_journee,
    version_donnees,
)
from simulateur_foot.interface.onglets import (
    club,
    fiabilite,
    fin_saison,
    forces,
    joueurs,
    journee,
    match,
)
from simulateur_foot.logos import chemin_championnat
from simulateur_foot.prediction import SAISON_EN_COURS
from simulateur_foot.simulation import classement

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
    quand il s'incline. Plus la surprise est grande, et plus la victoire est large, plus la note bouge.
    1500 = club moyen.</span></div>
  <div class="etape"><b><span class="num">2</span>Des probabilités par match</b>
    <span>L'écart de notes entre les deux clubs, plus un bonus pour l'équipe qui reçoit, donne
    les chances de victoire, de nul et de défaite, puis celles de chaque score.</span></div>
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

fichier_prochains = collecte_resultats.FICHIER_PROCHAINS  # lu sur le module : les tests le remplacent
version_prochains = fichier_prochains.stat().st_mtime if fichier_prochains.exists() else 0
prochains, chances_modele, inconnus = prochaine_journee(code, version, version_prochains)
affiches_annoncees = tuple(sorted(zip(prochains["HomeTeam"], prochains["AwayTeam"])))

(onglet_match, onglet_forces, onglet_journee, onglet_saison, onglet_club, onglet_joueurs,
 onglet_fiabilite) = st.tabs(
    ["Un match", "Les forces du moment", "Prochaine journée", "La fin de saison", "Fiche club",
     "Les meilleurs joueurs", "Le modèle est-il fiable ?"])


# Ce que les onglets reçoivent : le championnat choisi et ses données
ctx = SimpleNamespace(
    affiches_annoncees=affiches_annoncees, c=c, chances_modele=chances_modele, code=code, inconnus=inconnus, matchs=matchs, notes=notes,
    prochains=prochains, rangs_actuels=rangs_actuels, regles=regles, saison=saison,
    table_actuelle=table_actuelle, version=version)

for onglet, module in [(onglet_match, match), (onglet_forces, forces), (onglet_journee, journee),
                       (onglet_saison, fin_saison), (onglet_club, club), (onglet_joueurs, joueurs),
                       (onglet_fiabilite, fiabilite)]:
    with onglet:
        module.afficher(ctx)
