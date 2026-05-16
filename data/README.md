# Donnees derivees

Ce dossier recevra les sorties generees a partir des documents officiels.

Structure cible :

```text
data/
  curated/
  text/
  markdown/
  json/
  indexes/
  embeddings/
```

Les documents originaux restent dans les dossiers sectoriels et dans `_CEE_complements`. Les fichiers de `data/` sont des extractions ou normalisations et doivent toujours pointer vers leurs sources.

`data/curated/` contient les enrichissements métier validés fiche par fiche. Ces fichiers sont appliqués par `scripts/build_indexes.py` afin que les JSON enrichis restent reproductibles.

`data/indexes/formulas_cee_index.json` regroupe les formules de calcul extraites des sections 5 des fiches uniques : texte officiel de la section, formule synthetisee, variables detectees, expressions directes et statut d'extraction.

`data/indexes/formula_audit_report.json` controle les formules en rouvrant les PDF principaux : la section 5 du PDF doit correspondre au JSON, et chaque valeur numerique detectee dans la section 5 doit exister dans `calculation.extracted_values`.
