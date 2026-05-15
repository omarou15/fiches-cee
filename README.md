# Fiches CEE officielles

Archive des fiches d'operations standardisees CEE telechargees depuis la page officielle du ministere le 15 mai 2026.

Source officielle :
https://www.ecologie.gouv.fr/politiques-publiques/operations-standardisees-deconomies-denergie

## Contenu

Les fichiers sont classes par secteur :

Attention : le nombre de fichiers n'est pas le nombre de fiches uniques. Le depot contient les fiches principales, mais aussi les documents associes publies par le ministere : parties A, annexes, feuilles recapitulatives et fichiers ZIP.

| Secteur | Dossier | Documents | Fiches uniques |
| --- | --- | ---: |
| Agriculture | `Agriculture_AGRI` | 89 | 28 |
| Residentiel | `Residentiel_BAR` | 170 | 56 |
| Tertiaire | `Tertiaire_BAT` | 164 | 54 |
| Industrie | `Industrie_IND` | 93 | 31 |
| Reseaux | `Reseaux_RES` | 18 | 6 |
| Transport | `Transport_TRA` | 212 | 42 |

Total : 746 documents sectoriels pour 217 fiches uniques.

Le dossier `_Documents_generaux` contient aussi :

- l'arrete consolide du 22 decembre 2014 ;
- le catalogue actualise des fiches ;
- la repartition des departements par zone climatique.

## Index

Le fichier `manifest_fiches_cee.csv` liste chaque document telecharge avec :

- le secteur ;
- le libelle officiel ;
- le chemin local du fichier lors du telechargement ;
- l'URL source ;
- le statut du telechargement.

Le fichier `index_fiches_cee.csv` contient les memes documents avec des chemins relatifs au depot GitHub. C'est l'index le plus pratique a donner a ChatGPT ou a utiliser dans un futur MCP Server.

Le fichier `index_fiches_uniques.csv` liste une seule ligne par code fiche CEE unique, avec le nombre de documents associes.

## Complements CEE

Le dossier `_CEE_complements` contient les elements importants des autres pages CEE de la rubrique officielle "Energies" : coups de pouce, dispositif general, questions-reponses, operations specifiques, programmes, SARE, lettres d'information et statistiques 2026.

Ce dossier est volontairement selectif : il ne contient pas toutes les archives historiques, seulement les documents utiles et les pages de reference.

## Vers un CEE Knowledge Engine

Le depot contient maintenant une couche de conception pour transformer cette archive en base de connaissance exploitable par IA :

- `docs/CEE_KNOWLEDGE_ENGINE.md` : architecture RAG/MCP cible ;
- `docs/DATA_CONVENTIONS.md` : conventions de nommage, chunks, metadonnees et champs critiques ;
- `schemas/` : schemas JSON pour les fiches, documents et rapports d'extraction ;
- `scripts/README.md` : pipeline reproductible recommande ;
- `data/README.md` : structure cible des donnees derivees.

## Note

La page officielle du ministere classe les fiches en six secteurs : agriculture, residentiel, tertiaire, industrie, reseaux et transport.
