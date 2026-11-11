# simulateur-foot

Simulateur de Ligue 1. Il note la force de chaque club (Elo), en tire les probabilités de chaque match (victoire à domicile, nul, victoire à l'extérieur) et simule la fin de la saison en cours pour estimer les chances de titre, de Ligue des champions et de relégation.

Le choix du modèle est expliqué dans [RAPPORT.md](RAPPORT.md) : une régression logistique sur les deux notes Elo fait au moins aussi bien qu'un gradient boosting à 16 variables.

## Installation

```bash
uv sync
```

## Interface de test

```bash
uv run simulateur-foot interface
```

Trois onglets :

- **Affiche** : probabilités d'un match entre deux clubs, tirage au sort du résultat, évolution des notes Elo et confrontations passées.
- **Fin de saison** : des milliers de saisons simulées à partir du classement actuel ; probabilités de titre, de top 4, de barrage et de relégation, et carte des rangs finaux possibles.
- **Fiabilité du modèle** : scores sur la saison test et courbe de calibration.

## Ligne de commande

| Commande | Rôle |
|---|---|
| `uv run simulateur-foot collecte` | Télécharge les résultats depuis football-data.co.uk dans `data/resultats_ligue1.csv` |
| `uv run simulateur-foot forces` | Affiche les notes Elo et exporte `data/matchs_force.csv` |
| `uv run simulateur-foot variables` | Exporte `data/matchs_variables.csv` (forme, repos, promus) |
| `uv run simulateur-foot reglage` | Cherche les meilleurs paramètres Elo |
| `uv run simulateur-foot modele` | Compare les modèles de prédiction (≈ 2 min) |
| `uv run simulateur-foot simulation` | Simule la fin de la saison en cours dans le terminal |

Seul `resultats_ligue1.csv` est versionné : c'est la donnée source. Les autres fichiers de `data/` se recalculent.

## Organisation

```
src/simulateur_foot/
  collecte_resultats.py   téléchargement des résultats
  force_clubs.py          notes Elo avant chaque match
  reglage_force.py        réglage des paramètres Elo
  variables.py            forme, repos, promus
  modele.py               comparaison des modèles
  prediction.py           modèle retenu : probabilités d'un match
  simulation.py           simulation de la fin de saison (Monte-Carlo)
  app.py                  interface Streamlit
notebooks/                contrôles et explorations
tests/                    tests (uv run pytest)
```

## Tests

```bash
uv run pytest
```
