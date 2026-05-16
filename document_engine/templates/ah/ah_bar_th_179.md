# Attestation sur l'honneur - brouillon {{ operation.cee_code }}

## Beneficiaire

- Nom: {{ client.name }}
- Adresse: {{ client.address }}
- Site: {{ site.address }}, {{ site.postal_code }} {{ site.city }}

## Professionnel

- Entreprise: {{ company.legal_name }}
- SIRET: {{ company.siret }}
- Signataire: {{ company.signatory.name }}, {{ company.signatory.title }}

## Operation

- Fiche CEE: {{ operation.cee_code }}
- Date d'engagement: {{ operation.engagement_date }}
- Description: {{ operation.description }}
- Usage: {{ technical.usage }}
- PAC: {{ technical.pac_brand }} {{ technical.pac_reference }}
- Puissance Prated a -10 deg C: {{ technical.pac_power_kw_prated_minus_10 }} kW
- Etas: {{ technical.etas_percent }} %
- Zone climatique: {{ site.climate_zone }}
- Nombre d'appartements chauffes: {{ site.apartments_count }}
- Total CEE calcule: {{ calculation.total_kwh_cumac }} kWh cumac

## Signature

Cette attestation est un brouillon. Elle doit etre controlee, completee et signee par les parties habilitees.

Signature beneficiaire:

Signature professionnel: {{ company.signatory.signature_path }}
