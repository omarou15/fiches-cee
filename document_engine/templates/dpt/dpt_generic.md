# Dossier professionnel technique - {{ operation.cee_code }}

## Synthese operation

- Dossier: {{ operation.case_id }}
- Client: {{ client.name }}
- Site: {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Fiche CEE: {{ operation.cee_code }}
- Intitule fiche: {{ fiche.title }}
- Description: {{ operation.description }}

## Conditions d'eligibilite extraites

{{ fiche.eligibility_conditions_markdown }}

## Exigences techniques extraites

{{ fiche.technical_requirements_markdown }}

## Pieces justificatives attendues

{{ fiche.required_documents_markdown }}

## Pieces disponibles

{{ documents.available_markdown }}

## Pieces manquantes

{{ documents.missing_markdown }}

## Sources reglementaires

{{ fiche.source_files_markdown }}
