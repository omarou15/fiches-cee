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
   - extrait les formules de calcul depuis la section 5 des fiches ;
   - cree les chunks RAG ;
   - prepare les metadonnees MCP.

5. `validate_json.py`
   - valide les sorties avec `schemas/` ;
   - produit `data/indexes/extraction_report.json`.

6. `audit_unique_fiches.py`
   - ouvre uniquement les PDF principaux de `index_fiches_uniques.csv` ;
   - verifie lisibilite, texte extrait, presence du code fiche et fichiers generes ;
   - produit `data/indexes/pdf_audit_unique_fiches.json`.

7. `audit_formula_extraction.py`
   - ouvre les PDF principaux des fiches uniques ;
   - compare la section 5 officielle avec `calculation.formula_section_text` ;
   - verifie que toutes les valeurs numeriques de la section 5 sont presentes dans `calculation.extracted_values`.

8. `search_fiches.py`
   - recherche un code exact ou une requete plein texte dans les fiches et chunks.

9. `dossier_agent.py`
   - genere un pack CEE pre-depot local a partir d'un `client_operation.json` ;
   - couvre strictement `BAR-TH-179` en V1 ;
   - marque toute donnee absente comme question bloquante au lieu de l'inventer.

10. `infer_case.py`
   - transforme un cas minimal fictif ou local en `inferred_project.json` ;
   - chaque valeur inferee porte statut, confiance, source et validation humaine.

11. `compute_cee.py`
   - calcule les kWh cumac depuis un projet infere.

12. `generate_document_pack.py`
   - genere un pack documentaire local en mode `draft` ou `strict`.

## Commandes

Generer les donnees derivees :

```bash
python scripts/build_indexes.py
```

Valider les JSON et chunks :

```bash
python scripts/validate_json.py
```

Auditer les 217 fiches principales uniquement :

```bash
python scripts/audit_unique_fiches.py --fail-on-issues
```

Auditer les formules et valeurs de calcul :

```bash
python scripts/audit_formula_extraction.py --fail-on-issues
```

Chercher une fiche ou un sujet :

```bash
python scripts/search_fiches.py "BAR-TH-179"
python scripts/search_fiches.py "PAC collective"
python scripts/search_fiches.py "PAC collective" --sector residentiel --family TH
python scripts/search_fiches.py "dimensionnement pompe à chaleur" --common-use-cases --markdown
```

Generer un pack pre-depot BAR-TH-179 local :

```bash
python scripts/dossier_agent.py examples/dossier_agent/bar_th_179_complete.json --output dossiers_local/demo_bar_th_179
```

Inferer un cas minimal puis generer un pack documentaire generique :

```bash
python scripts/infer_case.py --input inference_engine/examples/synthetic_minimal_case_bar_th_179.json --code BAR-TH-179 --output outputs/demo/inferred_project.json
python scripts/generate_document_pack.py --company document_engine/examples/synthetic_company_profile.json --inferred outputs/demo/inferred_project.json --mode draft --output outputs/demo_pack
```

Generer directement un pack documentaire depuis une operation structuree :

```bash
python scripts/generate_document_pack.py --code BAR-TH-179 --company document_engine/examples/synthetic_company_profile.json --operation document_engine/examples/synthetic_operation_bar_th_179.json --output outputs/demo_bar_th_179
```

## Regle

Tout script doit etre idempotent : relancer le pipeline ne doit pas casser les sorties existantes ni modifier les sources officielles.
