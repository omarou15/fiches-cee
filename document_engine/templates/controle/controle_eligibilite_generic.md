# Controle d'eligibilite - {{ operation.cee_code }}

## Statut

- Dossier: {{ operation.case_id }}
- Statut eligibilite: {{ compliance.eligibility_status }}
- Fiche: {{ operation.cee_code }}
- Intitule fiche: {{ fiche.title }}
- Secteur: {{ fiche.sector }}
- Famille: {{ fiche.family }}
- Date d'effet: {{ fiche.effective_date }}

## Conditions fiche a verifier

{{ fiche.eligibility_conditions_markdown }}

## Exigences techniques a verifier

{{ fiche.technical_requirements_markdown }}

## Pieces justificatives a verifier

{{ fiche.required_documents_markdown }}

## Calcul CEE

- Formule source: {{ fiche.formula_text }}
- Montant calcule operation: {{ calculation.total_kwh_cumac }} kWh cumac
- Detail operation: {{ calculation.formula_text }}

## Points bloquants

{{ compliance.blocking_points_markdown }}

## Risques

{{ compliance.risks_markdown }}
