# Guide installateur

## 1. Introduction

Ce dépôt aide un installateur à préparer un dossier CEE complet à partir d'une fiche officielle, des données client et des informations de visite.
Il génère les documents de travail, calcule les kWh cumac quand la fiche est supportée, signale les pièces manquantes et alerte sur les risques PNCEE.
Il ne dépose pas le dossier sur EMMY.
Il ne remplace pas l'obligé, le délégataire, le mandataire ou le responsable technique qui valide le dossier final.

## 2. Prérequis

Avant de commencer :

- installer Python 3.10 ou plus récent ;
- cloner ce dépôt sur votre ordinateur ;
- installer les dépendances :

```bash
pip install -r requirements.txt
```

- créer un dossier local `private/`, ignoré par git, pour vos vraies données :

```bash
mkdir -p private
```

Ne mettez jamais de données client réelles dans les exemples publics du dépôt.

## 3. Étape 1 - Configurer son profil entreprise

Cette étape se fait une seule fois. Copiez le profil fictif fourni par le dépôt :

```bash
cp document_engine/examples/synthetic_company_profile.json private/company_profile.json
```

Ouvrez ensuite `private/company_profile.json` et remplacez les valeurs fictives par vos vraies informations.

Champs principaux à remplir :

| Champ | Explication simple |
| --- | --- |
| `name` | Nom commercial affiché sur les documents. |
| `legal_name` | Raison sociale officielle de l'entreprise. |
| `siret` | Numéro SIRET de l'entreprise. |
| `address` | Adresse complète de l'entreprise. |
| `phone` | Numéro de téléphone à afficher sur les documents. |
| `email` | Adresse email de contact. |
| `signatory.name` | Nom de la personne qui signe ou valide les documents. |
| `signatory.title` | Fonction du signataire, par exemple gérant, responsable technique ou chargé d'affaires. |

Vous pouvez aussi personnaliser le logo, le site web, les coordonnées bancaires et les couleurs, mais ce n'est pas obligatoire pour démarrer.

## 4. Étape 2 - Pour chaque nouvelle opération

### A. Générer le squelette de saisie

Pour créer un fichier de départ pour une opération BAR-TH-179 :

```bash
python scripts/init_operation_input.py --code BAR-TH-179 --output private/operation_input.json
```

Le fichier généré contient les rubriques à compléter pour le bénéficiaire, l'adresse du chantier, la visite technique, les équipements, les pièces disponibles et les informations CEE.
L'objectif est de saisir ce que vous savez réellement. Si une information manque, laissez-la vide ou indiquez qu'elle est à vérifier.

### B. Remplir `private/operation_input.json`

Pour BAR-TH-179, les informations importantes sont les suivantes :

| Champ | À quoi ça sert |
| --- | --- |
| `client.name` | Nom du bénéficiaire ou de la copropriété. |
| `client.address` | Adresse administrative du bénéficiaire si elle est différente du site. |
| `site.address` | Adresse exacte où les travaux sont réalisés. |
| `site.postal_code` | Code postal du site, utile pour déduire ou vérifier la zone climatique. |
| `climate_zone` | Zone climatique du bâtiment : H1 pour le nord et l'est, H2 pour le centre et l'ouest, H3 pour le pourtour méditerranéen. |
| `building.type` | Type de bâtiment. Pour BAR-TH-179, il doit s'agir d'un bâtiment résidentiel collectif. |
| `building.existing_building` | Indique que le bâtiment existe déjà. Les fiches CEE visent souvent les bâtiments existants. |
| `operation.usage` | Usage de la PAC : chauffage seul ou chauffage avec eau chaude sanitaire. Une PAC ECS seule n'est pas éligible sur BAR-TH-179. |
| `technical.pac_type` | Type de PAC prévue. Pour BAR-TH-179, il s'agit d'une PAC collective air/eau. |
| `technical.application_temperature` | Type d'application : basse température, moyenne température ou haute température. |
| `technical.etas_percent` | Rendement saisonnier Etas indiqué par le fabricant. C'est une valeur réglementaire critique. |
| `technical.pac_power_kw_prated_minus_10` | Puissance thermique nominale de la PAC à -10 °C, indiquée par la documentation fabricant. |
| `technical.boiler_room_power_after_works_kw` | Puissance utile totale de la chaufferie après travaux, hors équipements de secours à exclure si nécessaire. |
| `technical.backup_equipment_excluded` | Confirmation que les équipements de secours ne sont pas comptés à tort dans la puissance de chaufferie. |
| `building.apartment_count_heated_by_pac` | Nombre d'appartements chauffés par la ou les PAC installées. |
| `professional.rge_quality_sign` | Qualification ou certification du professionnel réalisant l'opération. |
| `documents.dimensioning_study` | Étude préalable de dimensionnement, signée et datée si la fiche l'exige. |
| `documents.manufacturer_datasheet` | Documentation fabricant prouvant la marque, la référence, la puissance et l'Etas. |
| `documents.quote` | Devis ou preuve d'engagement des travaux. |
| `documents.invoice` | Facture finale des travaux. |
| `documents.attestation_honneur` | Attestation sur l'honneur CEE. |
| `operation.non_cumulation` | Permet de vérifier qu'une autre fiche incompatible, par exemple BAR-TH-169, n'est pas utilisée pour la même opération. |

Ne forcez pas une valeur au hasard. Si vous ne connaissez pas une donnée, laissez-la manquante : l'outil doit la signaler comme point bloquant ou hypothèse à valider.

### C. Générer le dossier complet

Lancez d'abord l'inférence et le contrôle de l'opération :

```bash
python scripts/infer_case.py --input private/operation_input.json --code BAR-TH-179 --output private/inferred_project.json
```

Générez ensuite le pack documentaire en mode brouillon :

```bash
python scripts/generate_document_pack.py --company private/company_profile.json --inferred private/inferred_project.json --mode draft --output outputs/dossier_BAR-TH-179
```

Le mode `draft` génère les documents même si certaines données sont estimées ou à compléter.
Avant envoi, vérifiez toujours les points bloquants, les hypothèses et les risques de conformité.

## 5. Documents générés

| Fichier | Ce que c'est | À qui le remettre | Signature requise |
| --- | --- | --- | --- |
| `00_SYNTHESE/synthese_dossier.md` | Résumé global du dossier, statut, calcul et alertes. | Interne installateur. | Non. |
| `00_SYNTHESE/pieces_manquantes.md` | Liste des pièces absentes ou à corriger. | Interne, client ou syndic selon le cas. | Non. |
| `00_SYNTHESE/controle_eligibilite.md` | Contrôle des conditions principales de la fiche. | Responsable technique ou personne qui valide le dossier. | Non. |
| `01_ADMIN/devis.md` | Devis travaux généré depuis les données de l'opération. | Client ou bénéficiaire. | Oui, avant engagement. |
| `01_ADMIN/facture.md` | Facture brouillon ou finale selon les données fournies. | Client ou bénéficiaire. | Oui, selon votre procédure interne. |
| `01_ADMIN/mail_pieces_manquantes.md` | Modèle d'email pour demander les informations ou documents manquants. | Client, syndic ou équipe interne. | Non. |
| `02_CEE/attestation_honneur.md` | Attestation sur l'honneur CEE. | Bénéficiaire, professionnel et acteur CEE selon le circuit. | Oui. |
| `02_CEE/calcul_kwh_cumac.md` | Détail du calcul des kWh cumac. | Interne, mandataire, délégataire ou obligé. | Non. |
| `02_CEE/checklist_cee.md` | Liste de contrôle des pièces CEE. | Interne. | Non. |
| `03_TECHNIQUE/note_dimensionnement.md` | Note de dimensionnement technique. | Bénéficiaire, bureau d'études ou dossier technique. | Oui si votre procédure l'exige. |
| `03_TECHNIQUE/dpt.md` | Dossier ou document technique de preuve. | Interne, mandataire ou contrôle. | À vérifier selon le circuit. |
| `04_CONTROLE_INTERNE/rapport_controle_interne.md` | Rapport de contrôle avant envoi. | Interne. | Non. |
| `04_CONTROLE_INTERNE/risques_pncee.md` | Risques de rejet ou de demande de complément. | Responsable technique. | Non. |
| `dossier_manifest.json` | Liste structurée des fichiers générés. | IA, scripts ou contrôle interne. | Non. |

## 6. Si l'IA signale une question bloquante

`blocking_points` signifie qu'une information obligatoire manque ou qu'une condition critique n'est pas vérifiée.
Exemples : Etas absent, étude de dimensionnement manquante, usage non éligible, puissance nécessaire au calcul absente.

`draft_generic_no_rules` signifie que la fiche demandée n'a pas encore de règles complètes dans le dépôt.
Dans ce cas, les documents peuvent être générés comme brouillon, mais le contrôle réglementaire n'est pas suffisant pour envoyer le dossier.

Que faire :

1. Ouvrez le fichier de synthèse et la liste des pièces manquantes.
2. Retrouvez l'information dans la visite, le devis, la fiche fabricant, la facture ou l'étude technique.
3. Complétez `private/operation_input.json`.
4. Relancez les commandes de génération.

Un dossier avec des `blocking_points` ouverts ne doit jamais être envoyé à un obligé, un délégataire, un mandataire ou au PNCEE.

## 7. Si l'IA signale un risque PNCEE `severity: high`

Un risque PNCEE `high` correspond à une cause possible de rejet direct ou à une non-conformité importante.
Exemples : opération non éligible, seuil réglementaire non respecté, pièce obligatoire absente, formule de calcul impossible à justifier.

Avant tout envoi :

1. corrigez la donnée ou récupérez la pièce justificative ;
2. relancez le contrôle ;
3. faites valider le point par le responsable technique ou par l'acteur CEE qui porte le dossier.

## 8. Fiches supportées en contrôle complet

Les fiches suivantes disposent d'un contrôle complet dans le dépôt :

| Code | Intitulé |
| --- | --- |
| BAR-TH-179 | Pompe à chaleur collective air/eau résidentielle. |
| BAR-TH-171 | Pompe à chaleur air/eau résidentielle collective. |
| BAR-TH-168 | Dispositif solaire thermique. |
| BAT-TH-116 | Système de gestion technique du bâtiment (GTB). |
| BAT-TH-162 | Système géothermique tertiaire. |
| BAT-TH-163 | Pompe à chaleur collective air/eau tertiaire. |

Pour les autres fiches, le dossier peut être généré en mode brouillon générique.
Il doit être relu et validé par un thermicien, un responsable technique ou un acteur CEE avant tout envoi.

## 9. Sécurité des données

Le dossier `private/` est ignoré par git.
Les dossiers `outputs/`, `clients/` et `dossiers/` sont aussi prévus pour rester locaux.

Ne commitez jamais :

- données client réelles ;
- devis réels ;
- factures réelles ;
- attestations signées ;
- photos de chantier ;
- logos, signatures ou documents privés ;
- exports de dossiers CEE réels.

Le dépôt public doit contenir les règles, les modèles, les exemples fictifs et les scripts, jamais vos dossiers clients.

## 10. Utiliser ce repo avec son IA

Vous pouvez utiliser ChatGPT, Claude ou une autre IA pour vous aider à remplir, contrôler et expliquer un dossier.
Donnez-lui le contexte du dépôt, le code fiche et le contenu de votre fichier d'opération.

Prompt type à copier-coller :

> "Tu es un expert CEE. J'ai le repo fiches-cee cloné en local. Le code fiche est BAR-TH-179. Voici les données de mon opération : [coller le contenu de private/operation_input.json]. Génère le dossier complet et liste les points bloquants éventuels."

L'IA ne doit pas inventer une valeur réglementaire.
Si une donnée manque, elle doit vous poser une question ou marquer le point comme bloquant.
