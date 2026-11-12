# simulateur-foot

Simulateur de championnats de football : Ligue 1, Premier League, Liga, Bundesliga, Serie A et Ligue 2. Il note la force de chaque club (Elo, pondéré par l'écart de buts), en tire les probabilités de chaque match (victoire à domicile, nul, victoire à l'extérieur) et de chaque score, et simule la fin de la saison en cours pour estimer les chances de titre, de places européennes (ou de montée) et de relégation.

Le choix du modèle est expliqué dans [RAPPORT.md](RAPPORT.md), étude menée sur la Ligue 1 : une régression logistique sur les deux notes Elo fait au moins aussi bien qu'un gradient boosting à 16 variables. Le même modèle est entraîné séparément pour chaque championnat.

## Démarrage rapide

**1. Installer uv** (une seule fois). C'est l'outil qui gère Python et les dépendances : pas besoin d'installer Python à part, uv s'en charge.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Sur Mac, `brew install uv` marche aussi. Fermez puis rouvrez le terminal après l'installation.

**2. Récupérer le projet** (une seule fois) :

```bash
git clone https://github.com/Azetaka/simulateur-foot.git
cd simulateur-foot
```

**3. Lancer l'interface** :

```bash
uv run simulateur-foot interface
```

La première fois, uv télécharge Python et les dépendances (une minute environ). L'interface s'ouvre ensuite dans le navigateur, sur http://localhost:8501. Elle va chercher seule les derniers résultats si ses données ont plus de 12 h.

- **Arrêter** : `Ctrl+C` dans le terminal.
- **Relancer plus tard** : se placer dans le dossier `simulateur-foot`, puis refaire l'étape 3.
- **Depuis le dossier parent**, sans `cd` : `uv run --project simulateur-foot simulateur-foot interface`.
- **Récupérer les dernières modifications du code** : `git pull` dans le dossier du projet.

En cas de souci :

| Message | Solution |
|---|---|
| `command not found: uv` | Le terminal n'a pas vu l'installation : fermez-le et rouvrez-le. |
| `Failed to spawn: simulateur-foot` | La commande est lancée hors du dossier du projet : faites `cd simulateur-foot` d'abord. |
| L'adresse affichée est `localhost:8502`, `8503`… | Une autre interface tourne déjà et occupe le port 8501. Arrêtez-la avec `Ctrl+C` dans son terminal, ou utilisez l'adresse affichée. |

## L'interface

Un sélecteur en haut choisit le championnat (l'adresse garde le choix : `?championnat=E0`). Chaque page commence par un encadré « Comment lire cette page ». Sept onglets :

- **Un match** : chances de victoire, de nul et de défaite entre deux clubs, scores les plus probables et grille des scores, tirage au sort d'un score (et du même match joué 100 fois), évolution des notes Elo et confrontations passées.
- **Les forces du moment** : les clubs rangés par note Elo, avec la tendance sur les 5 derniers matchs, l'écart avec le classement et la difficulté du calendrier restant.
- **Prochaine journée** : les chances du modèle face à celles des bookmakers sur les matchs annoncés.
- **La fin de saison** : des milliers de saisons simulées à partir du classement actuel ; points attendus avec leur fourchette, chances de titre, de places européennes (ou de montée), de barrage et de relégation, et carte des places finales possibles. La prochaine journée annoncée est jouée en premier.
- **Fiche club** : la note et la forme d'un club, ses chances de fin de saison, ses derniers matchs et ses meilleurs joueurs.
- **Les meilleurs joueurs** : buteurs et passeurs avec leur total prévu en fin de saison. Le rythme de chaque joueur est ramené vers la moyenne (un départ canon se prolonge rarement) et ajusté à la difficulté des matchs restants de son club.
- **Le modèle est-il fiable ?** : part de pronostics justes sur une saison que le modèle n'a pas vue, calibration des probabilités et plus grosses surprises. En tête, le suivi en direct : le bilan des pronostics enregistrés avant chaque match de la saison en cours, face aux bookmakers.

## Données à jour

Les résultats viennent de [football-data.co.uk](https://www.football-data.co.uk), en général mis à jour le lundi après les matchs du week-end.

- **Automatiquement** : au lancement, l'interface retélécharge la saison en cours si ses données ont plus de 12 h (quelques secondes). Sans réseau, elle continue avec les données locales et le signale.
- **À la demande** : bouton « Mettre à jour » dans l'interface, ou `uv run simulateur-foot maj`.
- **Prochaine journée** : la même source publie en milieu de semaine les matchs du week-end suivant avec les cotes des bookmakers (`data/prochains_matchs.csv`, mis à jour en même temps que les résultats). L'onglet « Prochaine journée » compare les chances du modèle à celles des bookmakers, marge retirée.
- **Joueurs** : les buteurs et passeurs viennent de l'API publique d'ESPN (`data/joueurs.csv`), retéléchargés au lancement de l'interface s'ils ont plus de 12 h, ou avec `uv run simulateur-foot joueurs`.
- **Sur GitHub** : la tâche [Mise à jour des données](.github/workflows/mise-a-jour-donnees.yml) tourne le mardi et le vendredi à 6 h UTC. Elle télécharge la saison en cours et la prochaine journée, enregistre les pronostics des matchs à venir, met à jour les statistiques des joueurs, lance les tests et commite les fichiers de `data/` sur `develop` s'il y a du nouveau. GitHub ne lance les tâches planifiées que depuis la branche par défaut : le fichier doit être présent sur `main`. Elle se lance aussi à la main depuis l'onglet Actions.

## Ligne de commande

L'option `-c` choisit le championnat (`F1` Ligue 1 par défaut, `E0` Premier League, `SP1` Liga, `D1` Bundesliga, `I1` Serie A, `F2` Ligue 2), par exemple `uv run simulateur-foot -c E0 simulation`.

| Commande | Rôle |
|---|---|
| `uv run simulateur-foot maj` | Met à jour la saison en cours de tous les championnats |
| `uv run simulateur-foot collecte` | Retélécharge tout depuis 2021-22 dans `data/resultats.csv` |
| `uv run simulateur-foot forces` | Affiche les notes Elo et exporte `data/matchs_force.csv` |
| `uv run simulateur-foot variables` | Exporte `data/matchs_variables.csv` (forme, repos, promus) |
| `uv run simulateur-foot reglage` | Cherche les meilleurs paramètres Elo |
| `uv run simulateur-foot modele` | Compare les modèles de prédiction (≈ 2 min) |
| `uv run simulateur-foot simulation` | Simule la fin de la saison en cours dans le terminal |
| `uv run simulateur-foot bookmakers` | Compare le modèle aux bookmakers sur la saison test (télécharge les cotes) |
| `uv run simulateur-foot pronostics` | Enregistre les pronostics des matchs à venir et affiche leur bilan |
| `uv run simulateur-foot joueurs` | Télécharge les meilleurs buteurs et passeurs |
| `uv run simulateur-foot logos` | Télécharge les écussons manquants |

`resultats.csv`, `prochains_matchs.csv`, `joueurs.csv` et `pronostics.csv` sont versionnés : ce sont les données sources, et le journal des pronostics ne peut pas être reconstitué après coup. Les autres fichiers de `data/` se recalculent.

## Organisation

```
src/simulateur_foot/
  championnats.py         championnats suivis et règles de fin de saison
  collecte_resultats.py   téléchargement et mise à jour des résultats
  force_clubs.py          notes Elo avant chaque match (pondérées par l'écart de buts)
  reglage_force.py        réglage des paramètres Elo
  variables.py            forme, repos, promus
  modele.py               comparaison des modèles
  prediction.py           modèle retenu : probabilités d'un match
  scores.py               probabilités de chaque score (Poisson, recalé sur prediction.py)
  simulation.py           simulation de la fin de saison (Monte-Carlo, scores et notes qui évoluent)
  joueurs.py              buteurs et passeurs (ESPN) et leur projection de fin de saison
  logos.py                écussons des championnats et des clubs
  bookmakers.py           modèle face aux bookmakers sur la saison test
  pronostics.py           suivi des pronostics enregistrés avant les matchs
  app.py                  interface Streamlit : en-tête et choix du championnat
  interface/commun.py     styles, petits composants et calculs mis en cache
  interface/onglets/      un module par onglet (match, forces, journee, fin_saison, club, joueurs, fiabilite)
notebooks/                contrôles et explorations
tests/                    tests (uv run pytest)
```

## Tests

```bash
uv run pytest
```

Ils tournent sans accès au réseau, et automatiquement à chaque pull request ([tests.yml](.github/workflows/tests.yml)).
