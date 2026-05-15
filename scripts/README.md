# Scripts cibles

Ce dossier est reserve au futur pipeline reproductible.

## Pipeline recommande

1. `extract_pdf.py`
   - extrait le texte des PDF ;
   - conserve les numeros de pages si possible ;
   - signale les PDF vides ou mal lus.

2. `extract_office.py`
   - extrait DOC, DOCX, XLS et XLSX ;
   - convertit les tableaux en CSV/Markdown/JSON.

3. `normalize_fiche.py`
   - regroupe fiche principale, partie A, annexes et feuilles recapitulatives ;
   - produit un JSON par code fiche.
   - applique les enrichissements de `data/curated/` quand ils existent.

4. `build_indexes.py`
   - construit les index globaux ;
   - cree les chunks RAG ;
   - prepare les metadonnees MCP.

5. `validate_json.py`
   - valide les sorties avec `schemas/` ;
   - produit `data/indexes/extraction_report.json`.

6. `search_fiches.py`
   - recherche un code exact ou une requete plein texte dans les fiches et chunks.

## Commandes

Generer les donnees derivees :

```bash
python scripts/build_indexes.py
```

Valider les JSON et chunks :

```bash
python scripts/validate_json.py
```

Chercher une fiche ou un sujet :

```bash
python scripts/search_fiches.py "BAR-TH-179"
python scripts/search_fiches.py "PAC collective"
python scripts/search_fiches.py "PAC collective" --sector residentiel --family TH
python scripts/search_fiches.py "dimensionnement pompe à chaleur" --priority-energyco --markdown
```

## Regle

Tout script doit etre idempotent : relancer le pipeline ne doit pas casser les sorties existantes ni modifier les sources officielles.
