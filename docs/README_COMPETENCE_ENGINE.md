# CEE Competence Engine

Le `competence_engine/` transforme les retours metier et les textes sources en competences reutilisables par une IA.

L'objectif est d'eviter qu'un agent reparte de zero a chaque dossier. Pour chaque tache complexe, il peut lire une competence dediee :

- generer ou controler un devis ;
- generer ou controler une facture ;
- produire une note de dimensionnement ;
- produire un DPT ;
- appliquer une matrice de controle PNCEE ;
- appliquer une methode technique propre a une famille de fiches.

## Structure

```text
competence_engine/
  schemas/
    competence.schema.json

  common/
    controle_pncee.json
    dpt_cee.json
    devis_cee.json
    facture_cee.json

  technical/
    audit_nf_en_16247.json
    building_heat_losses.json
    cvc_cost_estimation.json
    ecs_dimensioning.json
    gtb_bacs_method.json
    note_dimensionnement_chauffage.json
    pac_hydraulic_integration.json

  index.json
```

## Regle de preuve

Chaque competence doit separer :

- `official` / `legal_text` : source officielle ou texte juridique ;
- `ministry_guidance` : questions-reponses ou guide ministeriel ;
- `operator_practice` : pratique d'operateur ou retour terrain ;
- `secondary_analysis` : analyse non officielle.

Une pratique d'operateur peut guider un brouillon, mais ne doit jamais etre presentee comme obligation reglementaire sans source officielle.

Un corpus prive local peut alimenter une competence, mais il ne doit pas etre copie dans le depot. La bonne pratique est de distiller uniquement les champs, controles, risques et methodes generiques, puis de marquer la source comme `secondary_analysis`. Voir `external_knowledge/README.md`.

## Statuts

- `draft_from_user_research` : structure utile, mais issue d'une synthese utilisateur ou IA a consolider.
- `needs_official_review` : contenu a verifier contre les textes officiels avant usage strict.
- `validated` : contenu controle contre les sources officielles du depot ou de Legifrance.

## Utilisation par une IA

Pour une operation, l'agent doit lire dans cet ordre :

1. `competence_engine/index.json`
2. la competence commune necessaire, par exemple `competence_engine/common/devis_cee.json`
3. `data/curated/{CODE}.json` ou `data/json/{CODE}.json`
4. `rules/{CODE}.rules.json` si disponible

En mode strict, toute valeur absente ou non sourcee doit produire une question bloquante ou un champ `[A COMPLETER]`.

## Outils MCP

Le serveur MCP expose maintenant les competences directement :

- `list_competences(category, status, applies_to)` : inventaire filtrable des competences ;
- `get_competence(competence_id)` : contenu complet d'une competence ;
- `find_competences(code, task)` : selection des competences pertinentes pour une fiche et/ou une tache.

Ces outils servent a eviter qu'un agent lise tout le depot. Il peut d'abord trouver les competences utiles, puis charger uniquement les fichiers necessaires.

Le moteur dossier consomme aussi ces competences via `scripts/dossier_validators.py`.
Il expose cote MCP les outils stricts `validate_quote`, `validate_invoice`,
`validate_dimensioning_note`, `validate_dpt`, `run_control_matrix` et
`validate_dossier_cee`. Dans `dossier_agent.py`, le meme moteur est appele en
mode `advisory` par defaut ; le mode `strict` bloque les champs critiques
manquants et alimente les questions bloquantes.

## Calculs rules structurés

Le moteur `compute_kwh_cumac` utilise les `rules/*.rules.json` quand une table de calcul exploitable existe. Cette couche couvre maintenant les calculateurs structurés suivants :

- `BAR-TH-168` : montant par m2 de capteurs selon zone et usage ;
- `BAR-TH-171` : montant de base selon type de logement et Etas, facteur surface, facteur zone ;
- `BAR-TH-179` : table PAC collective existante, avec facteur R ;
- `BAT-TH-116` : GTB, somme des montants par usage, facteur zone, surface geree ;
- `BAT-TH-162` / `BAT-TH-163` : montants PAC tertiaire selon puissance, Etas/COP, zone, usage le cas echeant, facteur secteur et surface.

Si une variable critique manque, le moteur refuse de calculer et retourne `needs_human_review: true`.

## Competences communes disponibles

`competence_engine/common/devis_cee.json`

- champs requis d'un devis ;
- exigences CEE liees a la date d'engagement ;
- coherence avec cadre contribution, AH et facture ;
- controle RGE si requis par la fiche ;
- risques de rejet PNCEE lies au devis.

`competence_engine/common/facture_cee.json`

- mentions obligatoires de facture ;
- role de preuve de realisation CEE ;
- date d'achevement et delai de depot ;
- coherence avec devis, AH, cadre contribution et annexes techniques ;
- champs techniques a charger depuis la fiche ;
- risques de rejet PNCEE lies a la facture.

`competence_engine/common/dpt_cee.json`

- clarification : DPT est un usage metier, pas un terme reglementaire officiel ;
- structure dossier technique + dossier de preuves pre-depot ;
- separation operations standardisees / specifiques / programmes ;
- mapping des preuves vers les champs critiques ;
- controle annexe 6, chronologie, calculs et risques PNCEE ;
- archivage encode a 9 ans selon l'article R.222-4 du Code de l'energie.

`competence_engine/common/controle_pncee.json`

- typologie des controles PNCEE/COFRAC ;
- matrice de risques pre-depot high/medium/low ;
- chronologie RAI avec tolerance PP/copro preservee ;
- controles RGE, AH, facture, annexe 6, non-cumul, technique et precarite ;
- signaux de fraude orientes revue humaine ;
- archivage encode a 9 ans selon l'article R.222-4.

`competence_engine/technical/note_dimensionnement_chauffage.json`

- obligation de note selon la fiche ;
- perimetre chauffe, Tbase et deperditions ;
- methode simplifiee d'estimation marquee a valider ;
- preparation d'un calcul detaille a faire valider par professionnel ;
- controle puissance generateur / besoins ;
- facteur R BAR-TH-179 ;
- risques de rejet lies a l'absence de note ou aux incoherences techniques.

`competence_engine/technical/pac_hydraulic_integration.json`

- puissance PAC disponible a Tbase, et non simple puissance catalogue ;
- compatibilite emetteurs / regime d'eau / application temperature ;
- inertie hydraulique et volume tampon estime ;
- bivalence et appoint ;
- risques de cycles courts, performance degradee ou donnees fabricant absentes.

`competence_engine/technical/building_heat_losses.json`

- collecte des surfaces, valeurs R/U/lambda et temperatures ;
- calculs R = e/lambda, U = 1/somme R, Q = U x A x DeltaT ;
- distinction R vs U pour les controles CEE isolation ;
- statut des valeurs : confirme, estime, a valider ;
- renvoi vers validation professionnelle pour tout calcul opposable.

`competence_engine/technical/ecs_dimensioning.json`

- profils de puisage ECS ;
- choix instantane / accumulation / semi-accumulation ;
- volume equivalent 60 C, puissance echangeur et volume de stockage ;
- pertes de boucle ECS ;
- risques sanitaires type legionelle et besoin de post-chauffage pour systemes basse temperature.

`competence_engine/technical/gtb_bacs_method.json`

- preuve de classe GTB/BACS ;
- fonctions controlees et liste de points ;
- distinction supervision simple vs regulation automatique ;
- commissionnement, captures IHM, DOE et coherences devis/facture ;
- usage dedie BAT-TH-116 au lieu d'une note de dimensionnement chauffage.

`competence_engine/technical/audit_nf_en_16247.json`

- contact preliminaire, demarrage, collecte, terrain, analyse, rapport ;
- perimetre, donnees energetiques, reference et qualite des donnees ;
- separation mesure / calcul / simulation / estimation ;
- lien avec DPT et operations specifiques CEE ;
- interdiction d'inventer economies, couts ou TRB.

`competence_engine/technical/cvc_cost_estimation.json`

- chiffrage indicatif CVC par ratios ou BPU ;
- perimetre inclus/exclus, quantites et date de valeur ;
- alerte sur travaux induits et base de prix obsolete ;
- prix toujours marques `estimated` tant qu'ils ne viennent pas d'un devis ;
- validation par consultation, idealement trois entreprises.
