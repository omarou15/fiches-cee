# CEE Open Toolkit

Toolkit open source pour structurer les fiches CEE officielles, inferer des
projets a partir de donnees minimales, calculer les volumes CEE et generer des
brouillons de dossiers documentaires locaux.

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

Le pipeline produit maintenant des donnees derivees exploitables :

- `data/json/` : un JSON par fiche unique ;
- `data/markdown/` : une version Markdown par fiche ;
- `data/text/` : texte extrait ;
- `data/indexes/chunks_cee.jsonl` : chunks RAG ;
- `data/indexes/formulas_cee_index.json` : formules de calcul extraites des sections 5 ;
- `data/curated/` : enrichissements metier verifies, reappliques a chaque build.

## CEE Dossier Agent

Le depot contient aussi une V1 d'agent pre-depot CEE generique sans SaaS CRM :

- `docs/CEE_DOSSIER_AGENT.md` : workflow et regles anti-hallucination ;
- `docs/CHATGPT_5_5_DOSSIER_PROMPT.md` : prompt operationnel pour ChatGPT ;
- `schemas/client_operation.schema.json` : entree client structuree ;
- `schemas/dossier_predepot.schema.json` : sortie pre-depot ;
- `schemas/document_check.schema.json` : controle documentaire ;
- `scripts/dossier_agent.py` : moteur strict BAR-TH-179 ;
- `examples/dossier_agent/` : cas anonymises de test.

Les dossiers clients reels doivent rester hors du repo public. Les sorties locales
peuvent etre generees dans `dossiers_local/`, ignore par Git.

## Inference Engine et Document Engine

Architecture generique ajoutee :

- `inference_engine/` : schemas, enrichers, pricebooks et exemple minimal fictif ;
- `inference_engine/prompts/` : prompts pour visite, photos et controle des hypotheses ;
- `document_engine/` : schemas, profil entreprise fictif, templates et generateurs ;
- `rules/` : regles metier par fiche ;
- `scripts/infer_case.py` : transforme un cas minimal en projet infere ;
- `scripts/compute_cee.py` : calcule les kWh cumac depuis un projet infere ;
- `scripts/init_operation_input.py` : cree un squelette operation pour n'importe quelle fiche ;
- `scripts/generate_document_pack.py` : genere un pack documentaire local.
- `scripts/audit_document_engine.py` : controle que le moteur documentaire rend un pack pour toutes les fiches.

Exemple :

```bash
python scripts/infer_case.py --input inference_engine/examples/synthetic_minimal_case_bar_th_179.json --code BAR-TH-179 --output outputs/demo/inferred_project.json
python scripts/generate_document_pack.py --company document_engine/examples/synthetic_company_profile.json --inferred outputs/demo/inferred_project.json --mode draft --output outputs/demo_pack

python scripts/generate_document_pack.py --code BAR-TH-179 --company document_engine/examples/synthetic_company_profile.json --operation document_engine/examples/synthetic_operation_bar_th_179.json --output outputs/demo_bar_th_179
python scripts/init_operation_input.py --code BAR-TH-101 --output private/operation_input.json
python scripts/audit_document_engine.py --all-codes --fail-on-issues
```

## Note

La page officielle du ministere classe les fiches en six secteurs : agriculture, residentiel, tertiaire, industrie, reseaux et transport.
