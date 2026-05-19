# External Knowledge

Ce dossier documente comment raccorder un corpus prive local au toolkit sans le publier.

Regle principale : ne jamais committer les documents sources prives. Le depot public ne doit contenir que des competences distillees, des schemas, des tests et des exemples anonymises.

## Usage recommande

1. Garder le corpus source hors du depot.
2. Declarer son emplacement via une variable d'environnement locale, par exemple `CEE_EXTERNAL_RAG_ROOT`.
3. Extraire uniquement des competences generiques dans `competence_engine/`.
4. Marquer les sources comme `secondary_analysis` quand elles viennent d'un corpus prive.
5. Exiger une source officielle ou une validation professionnelle pour tout point reglementaire, contractuel ou technique opposable.

## Ce qui peut entrer dans le depot

- Une methode generique.
- Une liste de champs a collecter.
- Une regle de non-hallucination.
- Une alerte de coherence.
- Un exemple de configuration anonymise.

## Ce qui ne doit pas entrer dans le depot

- Chemins absolus locaux.
- Noms internes de clients, societes ou projets.
- Documents bruts du corpus prive.
- Prix terrain presentes comme contractuels.
- Valeurs reglementaires non verifiees contre une source officielle.

Voir `external_knowledge/examples/local_corpus.example.json` pour un exemple de configuration safe.
