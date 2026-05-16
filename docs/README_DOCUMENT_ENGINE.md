# Document Engine

Le `document_engine/` fournit un moteur documentaire generique pour produire un
pack CEE local en Markdown a partir de deux fichiers :

- `company_profile.json` : profil entreprise local ;
- `operation_input.json` : operation client locale.

Les exemples publics sont fictifs :

```text
document_engine/examples/synthetic_company_profile.json
document_engine/examples/synthetic_operation_bar_th_179.json
```

Le moteur supporte les 217 fiches structurees du depot. Si une fiche a des
templates specifiques, ils sont utilises. Sinon, le pack est rendu avec les
templates generiques enrichis par `data/json/{CODE}.json`. Le manifeste indique
`template_profile: specific` ou `generic`.

Les donnees reelles doivent rester hors Git, par exemple :

```text
private/company_profile.json
private/operation_input.json
private/logo.png
private/signature.png
```

## Generation

Creer un squelette local pour n'importe quelle fiche :

```bash
python scripts/init_operation_input.py \
  --code BAR-TH-101 \
  --output private/operation_input.json
```

Generer un pack depuis des fichiers locaux :

```bash
python scripts/generate_document_pack.py \
  --company private/company_profile.json \
  --operation private/operation_input.json \
  --output outputs/mon_dossier_cee
```

Exemple public BAR-TH-179 :

```bash
python scripts/generate_document_pack.py \
  --company document_engine/examples/synthetic_company_profile.json \
  --operation document_engine/examples/synthetic_operation_bar_th_179.json \
  --output outputs/demo_bar_th_179
```

Le pack genere :

```text
outputs/demo_bar_th_179/
  00_SYNTHESE/
  01_ADMIN/
  02_CEE/
  03_TECHNIQUE/
  04_CONTROLE_INTERNE/
  dossier_manifest.json
```

## Templates

Les templates Markdown utilisent des placeholders simples :

```text
{{ company.name }}
{{ company.logo_path }}
{{ client.name }}
{{ site.address }}
{{ operation.cee_code }}
{{ quote.number }}
{{ invoice.number }}
{{ technical.etas_percent }}
{{ technical.pac_power_kw_prated_minus_10 }}
{{ calculation.total_kwh_cumac }}
```

Un utilisateur peut personnaliser le logo, les couleurs, les lignes de devis,
les numeros de documents et les mentions dans ses fichiers locaux.

## Avec ChatGPT

Donner a ChatGPT :

1. la fiche structuree `data/json/BAR-TH-179.json` ;
2. les regles `rules/BAR-TH-179.rules.json` ;
3. le profil local `private/company_profile.json` ;
4. l'operation locale `private/operation_input.json`.

ChatGPT doit generer ou verifier le pack sans inventer les donnees manquantes.
Si une piece ou une valeur critique manque, elle doit rester visible dans
`pieces_manquantes.md`, `checklist_cee.md` et `dossier_manifest.json`.

## Conversions futures

La V1 produit du Markdown. Les conversions DOCX/PDF pourront etre ajoutees
ensuite via Pandoc si disponible, ou via `python-docx` pour une sortie DOCX.

## Audit toutes fiches

```bash
python scripts/audit_document_engine.py --all-codes --fail-on-issues
```

Cet audit rend un pack temporaire pour chaque fiche et verifie que tous les
documents attendus existent sans placeholder `{{ ... }}` non resolu.
