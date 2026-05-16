# Exemples anonymises - CEE Dossier Agent

Ces fichiers servent uniquement de cas de test et de demonstration.
Ils ne doivent contenir aucune donnee client reelle.

La V1 couvre volontairement `BAR-TH-179` :

- `bar_th_179_complete.json` : dossier complet et calculable.
- `bar_th_179_incomplete.json` : dossier incomplet, l'agent doit poser des questions.
- `bar_th_179_ecs_only_non_eligible.json` : operation non eligible car PAC ECS seule.

Generation locale d'un pack pre-depot :

```bash
python scripts/dossier_agent.py examples/dossier_agent/bar_th_179_complete.json --output dossiers_local/demo_bar_th_179
```

Le dossier `dossiers_local/` est ignore par Git pour eviter tout stockage de donnees client dans le depot public.
