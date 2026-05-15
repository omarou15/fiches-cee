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
- `data/indexes/extraction_report.json` : rapport qualite de l'extraction.
- `data/json/` : JSON metier par fiche.
- `data/markdown/` : Markdown lisible par fiche.
- `data/text/` : texte brut extrait.

## Pour ChatGPT 5.5

1. Commencer par `data/indexes/fiches_cee_index.json`.
2. Pour `BAR-TH-179`, lire `data/json/BAR-TH-179.json`.
3. Si un champ est vide, lire `data/markdown/BAR-TH-179.md`.
4. Si la reponse a un impact dossier, citer le PDF source.
5. Si la question depend d'une date, verifier la page officielle du ministere.

## Regle anti-hallucination

Les champs vides, `null`, `unknown` ou `needs_human_review: true` signifient que l'information n'a pas ete extraite avec assez de confiance.

Dans ce cas, l'IA doit dire explicitement que l'information n'est pas confirmee dans le JSON derive et revenir au document source.

## LibreChat / MCP

Pour un MCP Server, les outils minimaux a exposer sont :

- `search_cee(query)`
- `get_cee_fiche(code)`
- `get_cee_chunks(code)`
- `list_required_documents(code)`
- `list_energyco_priority_fiches()`

Le fichier `data/indexes/chunks_cee.jsonl` peut etre indexe dans une base vectorielle. Les champs `code`, `sector`, `family`, `document_type`, `source_file` et `page_start` doivent rester dans les metadonnees.
