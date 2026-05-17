# Tableau récapitulatif annexe 6 - Ligne opération

| Colonne annexe 6 | Valeur |
|---|---|
| Référence interne du demandeur | {{ operation.case_id }} |
| Code de la fiche d'opération standardisée | {{ operation.cee_code }} |
| Secteur | {{ fiche.sector }} |
| Identité du bénéficiaire | {{ client.name }} |
| Adresse complète du bénéficiaire / site | {{ site.address }}, {{ site.postal_code }} {{ site.city }} |
| Téléphone bénéficiaire | {{ client.phone }} |
| Email bénéficiaire | {{ client.email }} |
| SIRET bénéficiaire si personne morale | {{ client.siret }} |
| Date d'engagement | {{ operation.engagement_date }} |
| Date d'achèvement | {{ invoice.date }} |
| Montant en kWh cumac | {{ calculation.total_kwh_cumac }} |
| Identité du professionnel - raison sociale | {{ company.legal_name }} |
| SIRET du professionnel | {{ company.siret }} |
| Qualification RGE - référence | {{ technical.professional_qualification }} |
| Qualification RGE - organisme | {{ technical.rge_qualifier }} |
| Qualification RGE - validité | {{ technical.rge_valid_until }} |
| Montant de la contribution versée (€) | {{ contribution.amount }} |
| Précarité énergétique | {{ compliance.precarity_status }} |
| Coup de pouce | {{ compliance.coup_de_pouce_status }} |
| Type Coup de pouce | {{ compliance.coup_de_pouce_type }} |

Ce tableau est un brouillon Markdown de contrôle. L'export informatique final doit respecter le format EMMY / annexe 6 applicable au dépôt.
