# Cadre de contribution CEE - Annexe 8

**CE DOCUMENT DOIT ÊTRE ÉTABLI AVANT OU AU MAXIMUM 14 JOURS APRÈS LA SIGNATURE DU DEVIS PAR LE BÉNÉFICIAIRE, ET TOUJOURS AVANT LE DÉBUT DES TRAVAUX.**

## Identification du demandeur

- Raison sociale : {{ company.legal_name }}
- SIREN : {{ company.siren }}
- Adresse : {{ company.address }}
- Contact : {{ company.email }} - {{ company.phone }}

## Identification du bénéficiaire

- Nom ou raison sociale : {{ client.name }}
- Adresse du site : {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Téléphone : {{ client.phone }}
- Email : {{ client.email }}

## Nature de la contribution

- Fiche d'opération standardisée : {{ operation.cee_code }}
- Description de l'opération : {{ operation.description }}
- Nature de la contribution proposée : {{ contribution.type }}
- Montant prévisionnel de la prime CEE : {{ contribution.amount }}
- Volume CEE estimé : {{ calculation.total_kwh_cumac }} kWh cumac
- Conditions de versement : {{ contribution.conditions }}

## Engagements du demandeur

Le demandeur s'engage à verser la contribution décrite ci-dessus sous réserve de la recevabilité du dossier CEE et du respect des conditions réglementaires applicables.

La présente contribution est accordée dans le cadre du dispositif des certificats d'économies d'énergie prévu aux articles L. 221-1 et suivants du code de l'énergie.

## Mentions légales

Les données personnelles communiquées sont utilisées pour l'instruction, le contrôle et l'archivage du dossier CEE.

Date d'établissement du cadre de contribution : {{ contribution.date }}

Signature du demandeur : {{ company.signatory.signature_path }}

