# Rapport de stage — version finale

> **Version de référence pour l’entreprise et CY Tech**
>
> Dernière validation : 1er septembre 2026

## Fichiers à utiliser

- [Rapport PDF](./RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf) — version de lecture et d’envoi, 34 pages A4.
- [Rapport Word](./RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx) — version éditable, ouvrable dans Microsoft Word.
- [Évaluation de stage](./ANNEXE_EVALUATION_STAGE_A_FAIRE_REMPLIR_PAR_MAKRAM.pdf) — document séparé à faire compléter par le tuteur entreprise.

Le fichier Word est la source éditable canonique. Le PDF a été exporté depuis ce même fichier avec Microsoft Word.

## Angle retenu

Le rapport présente uniquement le travail livré :

- collecte des données publiques HAICOP ;
- persistance PostgreSQL idempotente ;
- téléchargement, empreintes SHA-256, extraction et OCR multilingue ;
- analyse Go/No-Go structurée et traçable ;
- orchestration n8n et worker authentifié ;
- diffusion Mailpit, Gmail et Telegram ;
- cinq outils MCP bornés ;
- tests, sauvegarde et restauration vérifiée.

La narration suit le principe : **le modèle propose, le code vérifie, PostgreSQL conserve la preuve et l’humain décide**.

## Snapshot présenté

| Indicateur | Résultat validé |
|---|---:|
| Appels d’offres centralisés | 100 |
| Documents présents, hachés et extraits | 152 / 152 |
| Tests Python | 62 locaux + 5 d’intégration = 67 |
| Scripts SQL | 6 / 6 |
| Outils MCP | 5 / 5 |
| Canaux validés | Mailpit, Gmail, Telegram |

Les formulations absolues ont été évitées : le rapport indique qu’aucun doublon n’a été observé pendant la campagne de validation et décrit les contraintes techniques qui protègent les rejouements.

## Diagrammes

Les sources PlantUML de la version Claude et les diagrammes finaux grand format sont conservés dans [diagrammes_uml](./diagrammes_uml/).
