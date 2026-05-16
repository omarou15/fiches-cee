# Note technique / dimensionnement - {{ operation.cee_code }}

## Identification

- Dossier: {{ operation.case_id }}
- Client: {{ client.name }}
- Site: {{ site.address }}, {{ site.postal_code }} {{ site.city }}
- Entreprise: {{ company.legal_name }}
- Fiche: {{ operation.cee_code }}
- Intitule fiche: {{ fiche.title }}

## Donnees operation

- Description: {{ operation.description }}
- Date d'engagement: {{ operation.engagement_date }}
- Surface concernee: {{ site.heated_surface_m2 }} m2
- Zone climatique: {{ site.climate_zone }}
- Type de batiment: {{ site.building_type }}

## Donnees techniques

- Usage: {{ technical.usage }}
- Equipement / systeme: {{ technical.equipment_description }}
- Marque: {{ technical.brand }}
- Reference: {{ technical.reference }}
- Performance: {{ technical.performance_value }}
- Commentaires techniques: {{ technical.notes }}

## Exigences techniques extraites de la fiche

{{ fiche.technical_requirements_markdown }}

## Conclusion

Cette note est un brouillon generique. Les valeurs critiques doivent etre confirmees par un professionnel qualifie et rattachees aux justificatifs avant signature.
