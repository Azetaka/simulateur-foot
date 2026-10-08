# Rapport : modèle de prédiction des résultats

## En bref

Le modèle complet (gradient boosting sur les 16 variables) bat nettement la référence par fréquences, mais **pas** la régression logistique qui n'utilise que `force_dom` et `force_ext`. Sur la saison test 2526, la logistique sur les forces obtient les meilleurs scores. Les variables de forme, de repos et de promotion n'apportent rien de mesurable en plus des notes Elo. Pour le simulateur, je recommande pour l'instant la logistique sur les forces.

## Ce que j'ai fait

1. **Génération des variables** : `uv run src/variables.py` → `data/matchs_variables.csv` (1 723 matchs, 28 colonnes). Ce fichier est dans `.gitignore`, donc cette étape ne donne lieu à aucun commit : je ne l'ai pas ajouté de force.
2. **`src/modele.py`** : un `HistGradientBoostingClassifier` (scikit-learn) prédit FTR (H, D, A) à partir de `force_dom`, `force_ext`, `promu_dom`, `promu_ext` et des 12 variables de forme et de repos (`VARIABLES` de `variables.py`, côté domicile et côté extérieur).
3. **Découpage** : entraînement sur 2223, 2324 et 2425 (992 matchs), test sur 2526 (306 matchs). Les saisons 2122 et 2627 sont exclues. Les paramètres sont réglés par validation temporelle à l'intérieur de l'entraînement : on apprend sur 2223 et on valide sur 2324, puis on apprend sur 2223+2324 et on valide sur 2425. La grille compte 108 combinaisons et le critère est la log-loss moyenne. Le modèle final est ensuite réentraîné sur les trois saisons. La saison test ne sert qu'une fois, à la fin.
4. **Comparaison** sur 2526 avec deux références, mesurée par la log-loss et le score de Brier, plus un intervalle bootstrap apparié sur les écarts.

Pour tout reproduire : `uv run src/variables.py` puis `uv run src/modele.py`.

Commits sur `feature/modele` (rien n'a été poussé, `main` et `develop` n'ont pas été touchées) :

- `17530c6` Définition du modèle de classification des résultats (+ ajout de scikit-learn)
- `cce6e33` Entraînement sur 2223-2425 et test sur 2526
- `d360e9b` Comparaison aux références : fréquences et forces seules
- un dernier commit pour ce rapport

## Résultats

Plus c'est bas, mieux c'est. « Validation » est la log-loss moyenne des deux plis de validation, calculée avant de regarder la saison test.

| Modèle | Validation (log-loss) | Test 2526 log-loss | Test 2526 Brier |
|---|---|---|---|
| Modèle complet (boosting, 16 variables) | 1,0147 | 1,0280 | 0,6113 |
| Réf. 1 : fréquences moyennes (A 33,4 %, D 23,7 %, H 42,9 %) | 1,0712 | 1,0653 | 0,6437 |
| **Réf. 2 : logistique sur force_dom et force_ext** | **1,0085** | **1,0064** | **0,6006** |
| Complément : boosting sur les deux forces seulement | 1,0151 | 1,0181 | 0,6075 |

Écarts appariés du modèle complet par rapport à chaque référence (négatif = le modèle complet fait mieux), avec l'intervalle bootstrap à 95 % sur les 306 matchs :

| Comparaison | Écart de log-loss | Écart de Brier |
|---|---|---|
| contre les fréquences | −0,037 [−0,069 ; −0,005] | −0,032 [−0,055 ; −0,009] |
| contre la logistique sur les forces | +0,022 [−0,005 ; +0,045] | +0,011 [−0,006 ; +0,026] |
| contre le boosting sur les forces | +0,010 [−0,006 ; +0,026] | +0,004 [−0,007 ; +0,014] |

Ce que j'en conclus :

- Le modèle complet est **significativement meilleur que les fréquences**.
- Il est **moins bon que la logistique sur les forces**. L'intervalle frôle zéro, donc on ne peut pas affirmer qu'il est pire, mais rien n'indique qu'il soit meilleur. La validation donnait déjà le même classement avant le test : ce n'est pas un hasard propre à 2526.
- La ligne « complément » isole l'effet des variables à type de modèle égal. Même dans ce cas, ajouter les 14 variables n'améliore rien.
- Paramètres retenus : `learning_rate=0.02`, `max_depth=2`, `max_iter=50`, `min_samples_leaf=20`, soit un modèle très peu complexe. L'importance par permutation sur 2526 est forte pour `force_dom` et `force_ext`, quasi nulle pour les promus et le repos, et parfois négative pour certaines variables de forme.
- Précision (part de résultats les plus probables qui sont justes) : 49 % pour le modèle complet, 51 % pour la logistique. Le nul n'est presque jamais le résultat le plus probable (7 matchs sur 306 pour le modèle complet, aucun pour la logistique). C'est normal en football : le simulateur doit tirer au sort selon les probabilités, pas prendre le résultat le plus probable.

## Choix que j'ai faits

- **Gradient boosting sur histogrammes** : c'est le modèle de scikit-learn qui accepte nativement les valeurs manquantes, sans imputation, conformément à la consigne. Les valeurs manquantes concernent le premier match de chaque club dans la saison (forme et repos). `promu_*` manque aussi, mais seulement en 2122, qui est exclue.
- **Les 16 variables brutes, sans variable construite.** Un arbre exploite mal la différence `force_dom − force_ext`, alors que c'est elle qui compte dans l'Elo. Ajouter cette différence aiderait sans doute le boosting, mais la consigne listait les variables : je n'en ai pas ajouté.
- **Référence 2 = régression logistique multinomiale** sur les deux forces : c'est le modèle simple naturel pour une note Elo, et les deux forces n'ont aucune valeur manquante. J'ai ajouté le boosting sur les forces seules en complément, pour pouvoir comparer à modèle égal.
- **Fréquences calculées sur les saisons d'entraînement**, jamais sur la saison test.
- **Score de Brier multiclasse** = somme sur H, D et A de (probabilité − réalité)², moyennée sur les matchs. Il va de 0 à 2. Certaines définitions divisent par 3 : seule l'échelle change, pas le classement.
- **Grille de réglage étendue** : une première grille plus petite donnait sa meilleure combinaison au bord, du côté le moins complexe. Je l'ai étendue vers des modèles plus simples (`max_depth=1`, moins d'itérations, `learning_rate=0.01`). L'optimum reste le même.
- **Fichiers existants modifiés** : seulement `pyproject.toml` et `uv.lock`, à cause de `uv add scikit-learn` (indispensable). Aucun fichier source existant n'a été modifié et rien n'a été renommé. `modele.py` réutilise `DOSSIER_DATA` (de `force_clubs`) et `VARIABLES` (de `variables`).

## Doutes

- **Réglage de l'Elo et saison test.** `reglage_force.py` affiche l'erreur sur 2526 pour chaque combinaison de la grille. Si les paramètres actuels de `force_clubs.py` (K=20, avantage 40, promu 1400, retour 0) ont été choisis en regardant cette colonne, la saison test n'est plus tout à fait vierge, et cela avantage les deux modèles fondés sur les forces. Je ne sais pas comment ces valeurs ont été fixées (le code les dit « provisoires »).
- **Une seule saison test de 306 matchs** : les intervalles sont larges. Les écarts entre le modèle complet et la logistique sont de l'ordre de 0,01 à 0,02 en log-loss, soit à peu près la taille du bruit.
- **Le repos ne compte que les matchs de Ligue 1.** Les coupes et l'Europe manquent, donc `repos` mesure surtout les trêves du calendrier et pas la fatigue réelle. Ce n'est pas surprenant que son importance soit nulle. Corriger cela demanderait une nouvelle source, ce qui était hors périmètre.
- **Les promus** sont déjà pris en compte par l'Elo, qui leur donne une note de départ de 1400. La variable fait donc doublon, d'où son importance nulle.
- **Rodage court** : 2122 est la seule saison de rodage. Le premier pli de validation apprend sur 2223 avec des notes encore en train de converger, ce qui peut pénaliser le réglage.
- **Peu de données pour un boosting** (992 matchs). Un modèle linéaire avec les variables de forme ferait peut-être mieux, mais il faudrait gérer les valeurs manquantes autrement que par imputation (par exemple un modèle à part pour le premier match de chaque club). Je ne l'ai pas tenté.
- Le changement de format du championnat (20 clubs en 2223, 18 ensuite) mélange deux contextes un peu différents dans l'entraînement.
