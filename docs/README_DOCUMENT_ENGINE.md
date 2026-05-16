# Document Engine

Le `document_engine/` genere un pack documentaire local en Markdown a partir :

- d'un `inferred_project.json` ;
- d'un `company_profile.json` local ;
- d'un mode `draft` ou `strict`.

Le profil entreprise public fourni est fictif :

```text
document_engine/examples/synthetic_company_profile.json
```

Les profils reels doivent rester locaux et ignores par Git.

Sortie cible :

```text
outputs/demo_pack/
  00_SYNTHESE/
  01_ADMIN/
  02_CEE/
  03_TECHNIQUE/
  04_CONTROLE_INTERNE/
  dossier_manifest.json
```
