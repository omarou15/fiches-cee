# CEE Knowledge Engine

Ce depot est aujourd'hui une base documentaire officielle. L'objectif suivant est de le transformer en base de connaissance exploitable par un agent IA, un RAG ou un MCP Server.

## Objectif

Permettre a un agent de repondre a des questions metier CEE sans devoir relire integralement les PDF a chaque demande.

Exemples de questions cibles :

- Une operation est-elle eligible a une fiche donnee ?
- Quelles preuves sont obligatoires ?
- Quelles variables entrent dans le calcul des kWh cumac ?
- Quels points de controle peuvent bloquer un dossier ?
- Quelle fiche correspond a une operation terrain ?
- Quels documents manquent pour constituer un dossier ?

## Sources de verite

Le depot contient deux familles de sources :

- `index_fiches_uniques.csv` : index des codes fiches CEE uniques.
- `index_fiches_cee.csv` : documents associes aux fiches, incluant parties A, annexes et feuilles recapitulatives.
- `_CEE_complements/` : pages CEE importantes, coups de pouce, questions-reponses, textes generaux, operations specifiques et programmes.

Les PDF, XLSX, DOCX et pages HTML restent les sources officielles. Les futures sorties JSON/Markdown doivent etre considerees comme des donnees derivees.

## Architecture cible

```text
data/
  pdf/              # copies normalisees ou liens vers documents sources
  text/             # texte brut extrait des PDF/DOCX/HTML
  markdown/         # versions chunkables avec titres et tableaux convertis
  json/             # fiches normalisees et documents structures
  indexes/          # index globaux et rapports
  embeddings/       # index vectoriels, hors Git si volumineux

schemas/
  fiche_cee.schema.json
  document_cee.schema.json
  extraction_report.schema.json

scripts/
  extract_pdf.py
  extract_office.py
  normalize_fiche.py
  build_indexes.py
  validate_json.py
```

## Pipeline cible

1. Inventorier les documents officiels.
2. Extraire le texte de chaque PDF/DOCX/XLSX.
3. Normaliser les documents par code fiche.
4. Produire un Markdown chunkable.
5. Produire un JSON metier par fiche.
6. Valider les champs obligatoires.
7. Construire les index de recherche.
8. Exposer les outils via RAG ou MCP.

Les enrichissements metier verifies fiche par fiche sont stockes dans `data/curated/` puis reappliques par le pipeline. Une correction metier ne doit pas etre faite uniquement dans `data/json/`, car elle serait ecrasee au prochain build.

## JSON metier ideal

Une fiche CEE normalisee doit viser ces champs :

- `code`
- `sector`
- `title`
- `version`
- `effective_date`
- `scope`
- `eligibility_conditions`
- `technical_requirements`
- `required_documents`
- `attestation_fields`
- `control_points`
- `calculation`
- `variables`
- `formulas`
- `zones`
- `bonifications`
- `related_documents`
- `risks`
- `source_files`

## Outils MCP cibles

Un MCP Server CEE pourrait exposer :

- `list_cee_fiches(sector, status)`
- `get_cee_fiche(code)`
- `search_cee(query, sector, document_type)`
- `check_eligibility(code, operation_json)`
- `list_required_documents(code)`
- `compute_kwh_cumac(code, variables_json)`
- `find_control_risks(code, operation_json)`
- `compare_versions(code)`

## Couche CEE Dossier Agent

La premiere couche agentique executable est documentee dans
`docs/CEE_DOSSIER_AGENT.md`.

Elle ajoute un flux pre-depot sans SaaS CRM :

- entree client structuree par `schemas/client_operation.schema.json` ;
- controle documentaire par `schemas/document_check.schema.json` ;
- sortie pre-depot par `schemas/dossier_predepot.schema.json` ;
- moteur strict `scripts/dossier_agent.py` ;
- cas anonymises dans `examples/dossier_agent/`.

La V1 couvre volontairement `BAR-TH-179`. Les dossiers clients reels restent
hors du depot public et doivent etre geres localement ou dans la conversation
ChatGPT de l'utilisateur.

## Regles RAG

Pour eviter les reponses fragiles :

- toujours citer le fichier source ;
- toujours conserver le code fiche et la version dans les chunks ;
- ne pas melanger fiche principale, partie A et annexe sans type explicite ;
- chunker par section logique, pas par taille brute seulement ;
- transformer les tableaux en Markdown ou JSON ;
- conserver les unites ;
- conserver les dates d'application ;
- signaler quand une information vient d'un document derive.

## Limites a surveiller

- Les CEE changent souvent : une verification web officielle reste necessaire pour les questions "aujourd'hui", "dernier texte", "version applicable" ou "coup de pouce actif".
- Les PDF peuvent contenir des tableaux difficiles a extraire proprement.
- Certaines preuves sont dans les parties A ou annexes, pas dans la fiche principale.
- Certaines questions metier dependent de la date d'engagement ou d'achevement de l'operation.
- Les fichiers Q/R peuvent contenir des exceptions importantes qui contredisent une lecture trop simple des fiches.

## Priorites

1. Extraire le texte de toutes les fiches principales.
2. Extraire les parties A et documents Q/R.
3. Creer un JSON minimal par fiche.
4. Ajouter validation et rapports d'extraction.
5. Construire un premier MCP en lecture seule.
6. Ajouter les outils d'eligibilite et de calcul.

Priorite toolkit actuelle : utiliser `BAR-TH-179` comme fiche modele, puis reproduire le meme niveau de structuration sur les autres fiches chauffage/PAC/GTB/reseaux prioritaires pour les installateurs et acteurs CEE.
