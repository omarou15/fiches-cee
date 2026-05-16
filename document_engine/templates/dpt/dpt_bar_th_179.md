# Dossier professionnel technique - {{ operation.cee_code }}

## Synthese operation

- Dossier: {{ operation.case_id }}
- Client: {{ client.name }}
- Site: {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Fiche CEE: {{ operation.cee_code }}
- Description: {{ operation.description }}

## Caracteristiques techniques

- Usage: {{ technical.usage }}
- PAC: {{ technical.pac_brand }} {{ technical.pac_reference }}
- Puissance Prated a -10 deg C: {{ technical.pac_power_kw_prated_minus_10 }} kW
- Etas: {{ technical.etas_percent }} %
- Nombre d'appartements: {{ site.apartments_count }}
- Zone climatique: {{ site.climate_zone }}
- Total CEE: {{ calculation.total_kwh_cumac }} kWh cumac

## Pieces disponibles

{{ documents.available_markdown }}

## Pieces manquantes

{{ documents.missing_markdown }}

## Points de vigilance

{{ compliance.risks_markdown }}
