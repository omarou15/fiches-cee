# ATTESTATION SUR L'HONNEUR

Document de travail conforme à la structure annexe 7. À contrôler sur le modèle officiel applicable avant signature.

Règles de forme à respecter pour la version finale : caractères noirs sur fond clair, police Times New Roman droite, taille minimale 8 points, pagination "Page X / Y".

Page 1 / Y

## Partie Demandeur - En-tête

- *Raison sociale du demandeur : {{ company.legal_name }}
- *Numéro SIREN du demandeur : {{ company.siren }}
- Marque commerciale / logo : {{ company.logo_path }}
- Adresse : {{ company.address }}
- Contact : {{ company.email }} - {{ company.phone }}

Ces éléments doivent être renseignés de façon dactylographiée avant signature par le bénéficiaire et le professionnel.

## Titre et introduction

**ATTESTATION SUR L'HONNEUR**

Le contenu normé de l'introduction doit être repris sans modification depuis l'annexe 7 et l'annexe 7-1 de l'arrêté du 4 septembre 2014 modifié.

## Partie A1 - Opération standardisée BAR-TH-179

Fiche d'opération standardisée : {{ operation.cee_code }}

Critères techniques déclarés pour la partie A de l'attestation :

- *Type d'opération : mise en place d'une ou plusieurs pompes à chaleur collectives de type air/eau.
- *Usage de la PAC : {{ technical.usage }}
- *PAC utilisée uniquement pour l'eau chaude sanitaire : non.
- *Marque et référence : {{ technical.pac_brand }} {{ technical.pac_reference }}
- *Puissance thermique nominale Prated à -10 °C : {{ technical.pac_power_kw_prated_minus_10 }} kW
- *Efficacité énergétique saisonnière Etas : {{ technical.etas_percent }} %
- *Type d'application : {{ technical.application_temperature }}
- *Zone climatique : {{ site.climate_zone }}
- *Nombre d'appartements chauffés par la ou les PAC : {{ site.apartments_count }}
- *Facteur correctif R : {{ technical.r_factor }}
- *Montant CEE calculé : {{ calculation.total_kwh_cumac }} kWh cumac
- *Non-cumul BAR-TH-169 : à confirmer par le bénéficiaire et le demandeur.

En cas de plusieurs fiches dans une même attestation, numéroter les parties A1, A2, A3, etc.

## Partie B - Bénéficiaire

- *Nom ou raison sociale : {{ client.name }}
- *Adresse du site des travaux : {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- SIRET si personne morale : {{ client.siret }}
- *Téléphone : {{ client.phone }}
- *Email : {{ client.email }}
- Case à cocher : [ ] personne physique  [ ] personne morale
- Si syndicat de copropriétaires : le syndic atteste être le représentant légal du syndicat.

Engagements du bénéficiaire, à reprendre sans modification depuis l'annexe 7-1 :

- réalité des travaux ;
- exactitude des informations communiquées ;
- fourniture exclusive des justificatifs à un seul demandeur ;
- absence de double demande de certificats d'économies d'énergie ;
- acceptation d'un contrôle éventuel par le ministère chargé de l'énergie ou tout organisme désigné.

Date de signature bénéficiaire, après travaux : [À COMPLÉTER]

Signature bénéficiaire :

## Partie C - Professionnel

- *Raison sociale : {{ company.legal_name }}
- *SIRET : {{ company.siret }}
- *Téléphone : {{ company.phone }}
- *Email : {{ company.email }}
- *Qualification RGE / professionnelle : {{ technical.professional_qualification }}
- Référence du certificat : [À COMPLÉTER]
- Organisme qualificateur : [À COMPLÉTER]
- Date de validité : [À COMPLÉTER]
- Case à cocher : [ ] entreprise réalisatrice  [ ] maîtrise d'œuvre
- Sous-traitant le cas échéant : [À COMPLÉTER]

Engagements du professionnel, à reprendre sans modification depuis l'annexe 7-1 :

- mise en œuvre conforme à la fiche d'opération standardisée ;
- transmission exclusive des documents justificatifs ;
- absence de double déclaration ;
- exactitude des données techniques déclarées.

Date de signature professionnel, après travaux : [À COMPLÉTER]

Signature professionnel : {{ company.signatory.signature_path }}

## Partie finale - Mentions légales

Mention CNIL du ministère chargé de l'énergie : à reprendre sans modification depuis l'annexe 7-1.

Mention CNIL du demandeur : [À PERSONNALISER PAR LE DEMANDEUR AVANT SIGNATURE]

Sanctions pénales : toute fausse déclaration expose son auteur aux sanctions prévues par l'article 441-7 du code pénal, soit un an d'emprisonnement et 15 000 € d'amende.

Règle des astérisques : les champs précédés d'un astérisque (*) sont obligatoires. Le demandeur peut ajouter un astérisque devant des champs supplémentaires des parties A, B ou C. Aucune autre modification du contenu ou de l'organisation de l'attestation n'est autorisée.
