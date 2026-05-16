# Attestation sur l'honneur - brouillon generique {{ operation.cee_code }}

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
- Intitule fiche: {{ fiche.title }}
- Version fiche: {{ fiche.version }}
- Date d'effet fiche: {{ fiche.effective_date }}
- Date d'engagement: {{ operation.engagement_date }}
- Description: {{ operation.description }}
- Total CEE calcule: {{ calculation.total_kwh_cumac }} kWh cumac

## Donnees techniques declarees

- Usage: {{ technical.usage }}
- Equipement / systeme: {{ technical.equipment_description }}
- Marque: {{ technical.brand }}
- Reference: {{ technical.reference }}
- Performance: {{ technical.performance_value }}

## Signature

Cette attestation est un brouillon generique. Elle doit etre remplacee ou completee avec le modele officiel applicable, puis controlee et signee par les parties habilitees.

Signature beneficiaire:

Signature professionnel: {{ company.signatory.signature_path }}
