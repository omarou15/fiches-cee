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
    note_dimensionnement_chauffage.json

  index.json
```

## Regle de preuve

Chaque competence doit separer :

- `official` / `legal_text` : source officielle ou texte juridique ;
- `ministry_guidance` : questions-reponses ou guide ministeriel ;
- `operator_practice` : pratique d'operateur ou retour terrain ;
- `secondary_analysis` : analyse non officielle.

Une pratique d'operateur peut guider un brouillon, mais ne doit jamais etre presentee comme obligation reglementaire sans source officielle.

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
