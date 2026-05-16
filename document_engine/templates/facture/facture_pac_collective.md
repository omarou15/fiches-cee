# Facture travaux - {{ operation.cee_code }}

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
- Usage PAC: {{ technical.usage }}
- Marque et reference PAC: {{ technical.pac_brand }} {{ technical.pac_reference }}
- Puissance thermique nominale Prated a -10 deg C: {{ technical.pac_power_kw_prated_minus_10 }} kW
- Etas: {{ technical.etas_percent }} %

Document brouillon a remplacer ou valider avant depot.
