# Conventions de donnees

Ce document definit les conventions a utiliser pour transformer l'archive CEE en base de connaissance.

## Identifiants

Chaque fiche est identifiee par son code officiel :

```text
BAR-TH-171
BAT-TH-116
IND-UT-137
```

Regle :

- un code fiche = une entree metier principale ;
- une fiche peut avoir plusieurs documents associes ;
- les parties A, annexes et feuilles recapitulatives ne doivent pas creer de nouveau code fiche.

## Types de documents

Valeurs recommandees pour `document_type` :

- `fiche_principale`
- `partie_a`
- `annexe`
- `feuille_recapitulative`
- `question_reponse`
- `coup_de_pouce`
- `texte_reglementaire`
- `guide`
- `programme`
- `statistique`
- `page_reference`

## Dossiers cibles

Pour les donnees derivees :

```text
data/text/BAR-TH-171.txt
data/markdown/BAR-TH-171.md
data/json/BAR-TH-171.json
```

Si plusieurs documents existent pour le meme code :

```text
data/json/BAR-TH-171.fiche_principale.json
data/json/BAR-TH-171.partie_a.json
data/json/BAR-TH-171.annexe_2026.json
```

## Dates

Toutes les dates doivent etre stockees en ISO 8601 :

```json
"effective_date": "2026-01-01"
```

Quand la date vient du nom de fichier, ajouter :

```json
"date_source": "filename"
```

Quand elle vient du contenu du document :

```json
"date_source": "document_text"
```

## Unites

Conserver les unites originales et ajouter si possible une version normalisee :

```json
{
  "name": "surface",
  "label": "Surface isolee",
  "unit": "m2",
  "value_type": "number"
}
```

## Chunks RAG

Chaque chunk doit inclure au minimum :

- `chunk_id`
- `source_file`
- `document_type`
- `code`
- `sector`
- `title`
- `section_title`
- `text`
- `page_start` si disponible
- `page_end` si disponible

## Champs critiques

Ces champs doivent etre prioritaires pour l'extraction :

- conditions d'eligibilite ;
- exigences techniques ;
- pieces justificatives ;
- modes de preuve ;
- attestation sur l'honneur ;
- formule de calcul ;
- variables ;
- dates d'application ;
- exclusions ;
- controles obligatoires ;
- risques de rejet.

## Statuts d'extraction

Valeurs recommandees :

- `not_started`
- `extracted`
- `needs_review`
- `validated`
- `failed`

## Regle de prudence

Si une information ne peut pas etre extraite avec confiance, le JSON doit contenir :

```json
{
  "confidence": "low",
  "needs_human_review": true,
  "notes": "Champ non detecte de facon fiable dans le document source."
}
```
