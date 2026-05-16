# Email pieces manquantes

Objet: {{ mail.subject }}

Bonjour,

Dans le cadre du dossier CEE {{ operation.cee_code }} pour le site {{ site.address }}, {{ site.postal_code }} {{ site.city }}, les elements suivants restent a transmettre ou a valider :

{{ documents.missing_markdown }}

Points de vigilance :

{{ compliance.risks_markdown }}

Merci,

{{ mail.sender_name }}

{{ company.name }}
