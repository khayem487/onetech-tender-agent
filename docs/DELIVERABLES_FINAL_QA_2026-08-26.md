# Contrôle final des livrables — 26 août 2026

## Périmètre contrôlé

- rapport source Markdown ;
- rapport Word éditable ;
- rapport HTML imprimable ;
- rapport PDF A4 ;
- présentation PowerPoint éditable ;
- présentation PDF ;
- notes orateur ;
- cinq visuels HTML/PNG ;
- README et scripts de génération/export.

## Résultats

| Contrôle | Résultat |
|---|---:|
| Pages du rapport PDF | 32 |
| Diapositives | 16 |
| Diapositives avec notes orateur | 16 / 16 |
| Volume des notes | 1 599 mots |
| Durée estimée | 16 à 18 minutes avec la démonstration |
| Visuels intégrés au rapport | 5 |
| Tests Python | 67 / 67 réussis |
| Tests PostgreSQL | 6 / 6 réussis |

La présentation suit le plan communiqué par CY Tech : entreprise, mission,
outils utilisés, solutions réalisées, compétences techniques et soft skills.

## Contrôle visuel

Le rapport et la présentation ont été rendus en images puis inspectés sous forme
de planches de contact. Les corrections ont notamment porté sur :

- la suppression des blocs négatifs ou sans rapport avec le travail livré ;
- l’équilibre des cartes, métriques et espacements ;
- deux chevauchements détectés sur les diapositives entreprise et conclusion ;
- l’ajout d’une architecture simplifiée, d’un pipeline documentaire, d’une vue
  de traçabilité, d’une vue multicanale et d’un tableau de résultats ;
- la suppression du Mermaid brut et des marqueurs Markdown visibles ;
- la table des matières Word, les numéros de page et les notes orateur.

Aucune page blanche ni diapositive vide n’a été détectée.

## Contrôle de contenu

Le rapport et la présentation se concentrent sur les capacités effectivement
réalisées et validées. Les scans PDF/DOCX/PPTX n’ont trouvé aucun bloc négatif
sur des tâches écartées, aucune mention de fonctionnalité non réalisée et aucun
placeholder administratif.

Le snapshot présenté reste cohérent dans tous les formats :

- 100 appels d’offres centralisés ;
- 152 documents sur 152 présents, hashés et extraits ;
- aucun doublon détecté ;
- 67 tests Python et 6 tests SQL réussis ;
- 5 outils MCP opérationnels ;
- diffusion Mailpit, Gmail et Telegram validée.

## Reproductibilité

Les livrables sont générés à partir de deux sources Markdown finales par :

~~~powershell
.\.venv\Scripts\python.exe .\scripts\build-livrables.py
.\scripts\export-livrables-office.ps1
~~~

Le premier script produit DOCX, HTML, PPTX, notes et visuels. Le second imprime
le rapport HTML en PDF avec Chrome et exporte le diaporama depuis PowerPoint.
Les fichiers temporaires sont créés séparément puis remplacent les PDF finaux
uniquement après un export réussi.

## Sécurité avant publication

- dépôt GitHub confirmé privé ;
- fichier .env ignoré ;
- aucun token Telegram, Gmail, OpenAI ou GitHub détecté dans les livrables ;
- fichiers temporaires Office ignorés ;
- aucun brouillon obsolète inclus dans le commit final ;
- les mots de passe de démonstration documentés dans le README doivent être
  renouvelés avant tout partage du dépôt avec un tiers.
