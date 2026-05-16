# Utiliser ce depot avec une IA

Ce depot contient les documents officiels CEE et une premiere couche de donnees derivees pour RAG, MCP ou analyse par ChatGPT, Claude et outils equivalents.

## Ordre de lecture recommande

Pour une IA :

1. Lire `data/indexes/fiches_cee_index.json`.
2. Si la question porte sur une fiche precise, lire `data/json/{CODE}.json`.
3. Si le JSON est incomplet ou marque `needs_human_review`, lire `data/markdown/{CODE}.md`.
4. Pour une justification critique, retourner au PDF source liste dans `source_files`.
5. Pour une question "aujourd'hui", "derniere version" ou "coup de pouce actif", verifier la source officielle du ministere.

## Fichiers utiles

- `data/indexes/fiches_cee_index.json` : index des fiches normalisees.
- `data/indexes/documents_cee_index.json` : documents associes aux fiches.
- `data/indexes/chunks_cee.jsonl` : chunks RAG avec metadonnees.
- `data/indexes/energyco_priority_index.json` : fiches prioritaires pour les cas Energyco.
- `data/indexes/keyword_hits_index.json` : fiches detectees par mots-cles, sans validation prioritaire Energyco.
- `data/indexes/formulas_cee_index.json` : formules de calcul extraites des sections 5 des fiches uniques.
- `data/indexes/extraction_report.json` : rapport qualite de l'extraction.
- `data/indexes/pdf_audit_unique_fiches.json` : audit des PDF principaux des fiches uniques uniquement.
- `data/indexes/formula_audit_report.json` : audit PDF -> JSON des sections 5 et des valeurs de calcul.
- `data/curated/` : enrichissements metier reproductibles appliques au build.
- `data/json/` : JSON metier par fiche.
- `data/markdown/` : Markdown lisible par fiche.
- `data/text/` : texte brut extrait.

## Pour ChatGPT 5.5

1. Commencer par `data/indexes/fiches_cee_index.json`.
2. Pour `BAR-TH-179`, lire `data/json/BAR-TH-179.json`.
3. Si un champ est vide, lire `data/markdown/BAR-TH-179.md`.
4. Si la reponse a un impact dossier, citer le PDF source.
5. Si la question depend d'une date, verifier la page officielle du ministere.

## Pour monter un dossier CEE pre-depot

1. Lire `docs/CHATGPT_5_5_DOSSIER_PROMPT.md`.
2. Transformer les informations client en `client_operation.json`.
3. Valider la structure avec `schemas/client_operation.schema.json`.
4. Pour la V1, traiter uniquement `BAR-TH-179` avec `scripts/dossier_agent.py`.
5. Generer un pack local hors repo public.
6. Si une donnee ou piece manque, poser une question precise et ne jamais inventer.

## Regle anti-hallucination

Les champs vides, `null`, `unknown` ou `needs_human_review: true` signifient que l'information n'a pas ete extraite avec assez de confiance.

Dans ce cas, l'IA doit dire explicitement que l'information n'est pas confirmee dans le JSON derive et revenir au document source.

## Audit PDF local

Le controle PDF volontairement strict porte uniquement sur les fiches uniques :

```bash
python scripts/audit_unique_fiches.py --fail-on-issues
```

Ce controle exclut les parties A, annexes, feuilles recapitulatives, complements et documents generaux.

## LibreChat / MCP

Pour un MCP Server, les outils minimaux a exposer sont :

- `search_cee(query)`
- `get_cee_fiche(code)`
- `get_cee_chunks(code)`
- `list_required_documents(code)`
- `list_energyco_priority_fiches()`

Le fichier `data/indexes/chunks_cee.jsonl` peut etre indexe dans une base vectorielle. Les champs `code`, `sector`, `family`, `document_type`, `source_file` et `page_start` doivent rester dans les metadonnees.

## Recherche locale

Exemples :

```bash
python scripts/search_fiches.py "PAC collective" --sector residentiel --family TH
python scripts/search_fiches.py "dimensionnement pompe à chaleur" --priority-energyco --markdown
python scripts/search_fiches.py "facteur R puissance chaufferie" --code BAR-TH-179
```
