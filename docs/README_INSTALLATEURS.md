# CEE Open Toolkit pour installateurs

Ce depot est un toolkit open source generique pour preparer, controler et
documenter des dossiers CEE a partir des fiches officielles structurees.

Exemple BAR-TH-179 :

```bash
python scripts/generate_document_pack.py --code BAR-TH-179 --company document_engine/examples/synthetic_company_profile.json --operation document_engine/examples/synthetic_operation_bar_th_179.json --output outputs/demo_bar_th_179
```

Le mode `draft` genere des brouillons avec hypotheses visibles.
Le mode `strict` bloque si le projet contient des points bloquants.

Chaque utilisateur doit conserver ses donnees reelles dans `private/`,
`outputs/`, `clients/` ou `dossiers/`, jamais dans le depot public.
