# Rule Engine

Le dossier `rules/` contient les regles metier generiques par fiche.

La V1 contient :

```text
rules/BAR-TH-179.rules.json
```

Les regles pointent vers les JSON officiels derives dans `data/json/`.
Elles ne remplacent pas les PDF officiels : pour un arbitrage critique, revenir
au PDF source liste dans la fiche.

Principe :

- une regle ne doit pas inventer de donnee ;
- un champ absent devient `missing` ou `blocking` ;
- une valeur estimee doit porter `needs_human_validation: true`.
