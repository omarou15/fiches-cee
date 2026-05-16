# Devis travaux CEE - {{ operation.cee_code }}

Logo: {{ company.logo_path }}

## Entreprise

- Nom commercial: {{ company.name }}
- Raison sociale: {{ company.legal_name }}
- SIRET: {{ company.siret }}
- TVA: {{ company.vat_number }}
- Adresse: {{ company.address }}
- Telephone: {{ company.phone }}
- Email: {{ company.email }}

## Client et operation

- Client: {{ client.name }}
- Contact: {{ client.contact_name }}
- Adresse client: {{ client.address }}
- Site operation: {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Fiche CEE: {{ operation.cee_code }}
- Intitule fiche: {{ fiche.title }}
- Description operation: {{ operation.description }}

## Devis

- Numero: {{ quote.number }}
- Date: {{ quote.date }}
- Validite: {{ quote.valid_until }}
- Statut: {{ quote.status }}

{{ quote.lines_markdown }}

Total HT: {{ quote.total_ht_formatted }}

Total TTC: {{ quote.total_ttc_formatted }}

## Mentions CEE a valider

Ce devis est rattache a la fiche {{ operation.cee_code }}. Les caracteristiques techniques, les preuves exigees et les montants CEE doivent etre verifies avec la fiche officielle avant signature.

## Signature

Bon pour accord, date et signature du client:

Signature entreprise: {{ company.signatory.signature_path }}
