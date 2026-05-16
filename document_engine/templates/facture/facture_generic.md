# Facture travaux CEE - {{ operation.cee_code }}

Logo: {{ company.logo_path }}

## Entreprise

- {{ company.legal_name }}
- SIRET: {{ company.siret }}
- TVA: {{ company.vat_number }}
- Adresse: {{ company.address }}
- Email: {{ company.email }}

## Client

- Client: {{ client.name }}
- Adresse: {{ client.address }}
- Site operation: {{ site.address }}, {{ site.postal_code }} {{ site.city }}

## Facture

- Numero: {{ invoice.number }}
- Date: {{ invoice.date }}
- Echeance: {{ invoice.due_date }}
- Statut: {{ invoice.status }}

{{ invoice.lines_markdown }}

Total HT: {{ invoice.total_ht_formatted }}

Total TTC: {{ invoice.total_ttc_formatted }}

## Reference CEE

- Fiche: {{ operation.cee_code }}
- Intitule fiche: {{ fiche.title }}
- Total CEE calcule: {{ calculation.total_kwh_cumac }} kWh cumac

Document brouillon a valider avant tout usage reglementaire.
