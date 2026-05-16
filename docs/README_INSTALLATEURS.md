# CEE Open Toolkit pour installateurs

Ce depot est un toolkit open source generique pour preparer, controler et
documenter des dossiers CEE a partir des fiches officielles structurees.

Exemple BAR-TH-179 :

```bash
python scripts/infer_case.py --input inference_engine/examples/synthetic_minimal_case_bar_th_179.json --code BAR-TH-179 --output outputs/demo/inferred_project.json
python scripts/generate_document_pack.py --company document_engine/examples/synthetic_company_profile.json --inferred outputs/demo/inferred_project.json --mode draft --output outputs/demo_pack
```

Dans ce mode, l'utilisateur fournit seulement client, adresse, visite, photos et
documents disponibles. Le moteur infere ou estime le reste et marque ce qui doit
etre valide.

Exemple depuis une operation deja structuree :

```bash
python scripts/generate_document_pack.py --code BAR-TH-179 --company document_engine/examples/synthetic_company_profile.json --operation document_engine/examples/synthetic_operation_bar_th_179.json --output outputs/demo_bar_th_179
```

Pour une autre fiche, creer d'abord un squelette local :

```bash
python scripts/init_operation_input.py --code BAR-TH-101 --output private/operation_input.json
python scripts/generate_document_pack.py --company private/company_profile.json --operation private/operation_input.json --output outputs/dossier_bar_th_101
```

Le mode `draft` genere des brouillons avec hypotheses visibles.
Le mode `strict` bloque si le projet contient des points bloquants.

Chaque utilisateur doit conserver ses donnees reelles dans `private/`,
`outputs/`, `clients/` ou `dossiers/`, jamais dans le depot public.
