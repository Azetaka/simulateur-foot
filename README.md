# simulateur-foot

Simulateur de championnats de football : Ligue 1, Premier League, Liga, Bundesliga, Serie A et Ligue 2. Il note la force de chaque club (Elo), en tire les probabilités de chaque match (victoire à domicile, nul, victoire à l'extérieur) et simule la fin de la saison en cours pour estimer les chances de titre, de places européennes (ou de montée) et de relégation.

Le choix du modèle est expliqué dans [RAPPORT.md](RAPPORT.md), étude menée sur la Ligue 1 : une régression logistique sur les deux notes Elo fait au moins aussi bien qu'un gradient boosting à 16 variables. Le même modèle est entraîné séparément pour chaque championnat.

## Installation

```bash
uv sync
```

## Interface de test

```bash
uv run simulateur-foot interface
```

Un sélecteur en haut choisit le championnat (l'adresse garde le choix : `?championnat=E0`). Trois onglets :

- **Affiche** : probabilités d'un match entre deux clubs, tirage au sort du résultat, évolution des notes Elo et confrontations passées.
- **Fin de saison** : des milliers de saisons simulées à partir du classement actuel ; probabilités de titre, de top 4, de barrage et de relégation, et carte des rangs finaux possibles.
- **Fiabilité du modèle** : scores sur la saison test et courbe de calibration.

## Données à jour

Les résultats viennent de [football-data.co.uk](https://www.football-data.co.uk), en général mis à jour le lundi après les matchs du week-end.

- **Automatiquement** : au lancement, l'interface retélécharge la saison en cours si ses données ont plus de 12 h (quelques secondes). Sans réseau, elle continue avec les données locales et le signale.
- **À la demande** : bouton « Mettre à jour » dans l'interface, ou `uv run simulateur-foot maj`.
- **Sur GitHub** : la tâche [Mise à jour des données](.github/workflows/mise-a-jour-donnees.yml) tourne le mardi et le vendredi à 6 h UTC. Elle télécharge la saison en cours, lance les tests et commite `data/resultats.csv` sur `develop` s'il y a de nouveaux matchs. GitHub ne lance les tâches planifiées que depuis la branche par défaut : le fichier doit être présent sur `main`. Elle se lance aussi à la main depuis l'onglet Actions.

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

Seul `resultats.csv` est versionné : c'est la donnée source. Les autres fichiers de `data/` se recalculent.

## Organisation

```
src/simulateur_foot/
  championnats.py         championnats suivis et règles de fin de saison
  collecte_resultats.py   téléchargement et mise à jour des résultats
  force_clubs.py          notes Elo avant chaque match
  reglage_force.py        réglage des paramètres Elo
  variables.py            forme, repos, promus
  modele.py               comparaison des modèles
  prediction.py           modèle retenu : probabilités d'un match
  simulation.py           simulation de la fin de saison (Monte-Carlo, notes qui évoluent)
  app.py                  interface Streamlit
notebooks/                contrôles et explorations
tests/                    tests (uv run pytest)
```

## Tests

```bash
uv run pytest
```
