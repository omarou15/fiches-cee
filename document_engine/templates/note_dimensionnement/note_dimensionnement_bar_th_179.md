# Note de dimensionnement - {{ operation.cee_code }}

## Identification

- Dossier: {{ operation.case_id }}
- Client: {{ client.name }}
- Site: {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Entreprise: {{ company.legal_name }}
- Date d'engagement: {{ operation.engagement_date }}

## Donnees de base

- Surface chauffee: {{ site.heated_surface_m2 }} m2
- Emetteurs: {{ site.emitters }}
- Temperature de base: {{ site.base_temperature_c }} deg C
- Temperature depart reseau: {{ technical.flow_temperature_c }} deg C
- Temperature interieure de consigne: {{ technical.indoor_setpoint_c }} deg C
- Deperditions a Tbase: {{ technical.heat_losses_kw_at_tbase }} kW

## Pompe a chaleur

- Marque: {{ technical.pac_brand }}
- Reference: {{ technical.pac_reference }}
- Puissance Prated a -10 deg C: {{ technical.pac_power_kw_prated_minus_10 }} kW
- Etas: {{ technical.etas_percent }} %
- Application temperature: {{ technical.application_temperature }}
- Taux de couverture annuel chauffage: {{ technical.annual_heating_coverage_percent }} %

## Chaufferie apres travaux

- Puissance utile chaufferie apres travaux: {{ technical.chaufferie_useful_power_after_works_kw }} kW
- Equipements de secours exclus: {{ technical.backup_equipment_excluded }}
- Facteur R retenu: {{ technical.r_factor }}

## Conclusion

La presente note est un brouillon technique. Toute valeur estimee doit etre validee par un professionnel qualifie avant signature.
