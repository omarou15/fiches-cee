# Controle d'eligibilite - {{ operation.cee_code }}

## Statut

- Dossier: {{ operation.case_id }}
- Statut eligibilite: {{ compliance.eligibility_status }}
- Fiche: {{ operation.cee_code }}

## Controles BAR-TH-179

- Batiment residentiel collectif existant: {{ site.building_type }}
- Usage chauffage ou chauffage + ECS: {{ technical.usage }}
- PAC ECS seule exclue: a verifier si usage non conforme
- Etas: {{ technical.etas_percent }} %
- Puissance PAC <= 400 kW: {{ technical.pac_power_kw_prated_minus_10 }} kW
- Qualification professionnelle: {{ technical.professional_qualification }}
- Etude de dimensionnement: {{ technical.dimensioning_study_status }}
- Facteur R: {{ technical.r_factor }}
- Calcul CEE: {{ calculation.total_kwh_cumac }} kWh cumac

## Points bloquants

{{ compliance.blocking_points_markdown }}

## Risques

{{ compliance.risks_markdown }}
