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

4. `build_indexes.py`
   - construit les index globaux ;
   - cree les chunks RAG ;
   - prepare les metadonnees MCP.

5. `validate_json.py`
   - valide les sorties avec `schemas/` ;
   - produit `data/indexes/extraction_report.json`.

## Regle

Tout script doit etre idempotent : relancer le pipeline ne doit pas casser les sorties existantes ni modifier les sources officielles.
