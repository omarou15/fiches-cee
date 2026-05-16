# CEE Open Toolkit pour installateurs

Ce depot est un toolkit open source generique pour preparer, controler et
documenter des dossiers CEE a partir des fiches officielles structurees.

Exemple BAR-TH-179 :

```bash
python scripts/infer_case.py --input inference_engine/examples/synthetic_minimal_case_bar_th_179.json --code BAR-TH-179 --output outputs/demo/inferred_project.json
python scripts/generate_document_pack.py --company document_engine/examples/synthetic_company_profile.json --inferred outputs/demo/inferred_project.json --mode draft --output outputs/demo_pack
```

Le mode `draft` genere des brouillons avec hypotheses visibles.
Le mode `strict` bloque si le projet contient des points bloquants.

Chaque utilisateur doit conserver ses donnees reelles dans `private/`,
`outputs/`, `clients/` ou `dossiers/`, jamais dans le depot public.
