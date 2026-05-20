# CEE Dossier Agent

Objectif : permettre a ChatGPT 5.5 de monter un pack CEE pre-depot a partir des
informations client et des documents fournis par l'utilisateur, sans utiliser de
SaaS CRM.

Le depot public reste une base reglementaire. Les donnees client reelles ne
doivent jamais etre commitees dans ce depot.

## Principe V1

La V1 couvre uniquement `BAR-TH-179`.

Flux attendu :

1. L'utilisateur transmet a ChatGPT les informations client en langage naturel.
2. ChatGPT transforme les informations en `client_operation.json`.
3. ChatGPT lance ou reproduit la logique de `scripts/dossier_agent.py`.
4. L'agent produit un statut : `pret_predepot`, `incomplet_questions`, `a_risque` ou `non_eligible`.
5. Si une donnee critique manque, l'agent pose une question precise.

## Regle stricte anti-hallucination

- Ne jamais inventer une date, une puissance, une zone climatique, une valeur Etas, une qualification, une reference materiel ou une piece documentaire.
- Si l'information manque, mettre `unknown`, `null` ou une question bloquante.
- Un dossier ne peut pas etre `pret_predepot` si une question bloquante existe.
- Toute conclusion critique doit citer la fiche officielle ou le JSON derive.

## Pack pre-depot genere

Le script peut generer localement :

- `dossier_predepot.json`
- `dossier_predepot.md`
- `calcul_kwh_cumac.json`
- `checklist_pieces.json`
- `questions_manquantes.md`
- `risques_pncee.md`
- `sources_reglementaires.md`

Exemple :

```bash
python scripts/dossier_agent.py examples/dossier_agent/bar_th_179_complete.json --output dossiers_local/demo_bar_th_179
```

`dossiers_local/` est ignore par Git.

## Moteur dossier unifie

Le dossier pivot est decrit par `schemas/dossier_cee.schema.json`. Il accepte
les blocs usuels `beneficiary`, `client`, `site`, `operation`, `quote`,
`invoice`, `documents`, `calculation`, `technical`, `building`, `climate`,
`generator`, `boiler_room` et `dpt`.

Les validateurs deterministes vivent dans `scripts/dossier_validators.py` :

- `validate_quote` controle le devis et la date d'engagement.
- `validate_invoice` controle la facture comme preuve de realisation.
- `validate_dimensioning_note` controle la note quand la fiche la rend explicite.
- `validate_dpt` controle le dossier technique/preuves interne.
- `run_control_matrix` consolide les risques PNCEE.
- `validate_dossier_cee` execute l'ensemble.

`dossier_agent.py` appelle ce moteur en mode `advisory` par defaut pour enrichir
les dossiers sans casser les anciens statuts. Pour bloquer reellement un dossier
incomplet, passer `validation_mode: "strict"` dans l'operation d'entree.

Les memes fonctions sont exposees par le MCP : `validate_quote`,
`validate_invoice`, `validate_dimensioning_note`, `validate_dpt`,
`run_control_matrix` et `validate_dossier_cee`.

## Donnees BAR-TH-179 exigees

Pour calculer et controler un dossier BAR-TH-179, l'agent doit obtenir au minimum :

- batiment residentiel collectif existant ;
- date d'engagement ;
- usage PAC : chauffage ou chauffage + ECS ;
- type PAC air/eau ;
- systeme de chauffage collectif ;
- puissance thermique nominale PAC Prated a -10 deg C ;
- puissance utile de chaufferie apres travaux ;
- confirmation que les equipements de secours sont exclus ;
- Etas et application basse / moyenne-haute temperature ;
- zone climatique H1/H2/H3 ;
- nombre d'appartements chauffes par la PAC ;
- absence de cumul interdit avec BAR-TH-169 ;
- signe de qualite professionnel ;
- etude prealable de dimensionnement signee, datee et remise ;
- preuve de realisation ;
- decision de qualification ou certification ;
- document fabricant ou equivalent ;
- attestation sur l'honneur ;
- devis/commande et facture.

## Limite volontaire

Le script ne depose rien sur EMMY et ne remplace pas le compte officiel du
demandeur. Il prepare un dossier pre-depot pour controle humain et transmission
par l'acteur habilite.
