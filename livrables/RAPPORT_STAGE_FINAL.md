# Rapport de stage — version finale

## Développement d’un système IA agentique pour la gestion des appels d’offres publics

**Étudiant :** Khayem Ben Ghorbel

**Formation :** CY Tech — Cycle ingénieur Informatique ING1/GI

**Organisme d’accueil :** One Tech Business Solutions — One Tech Group

**Encadrant entreprise :** Makram Ben Hamed

**Période :** 26 juin – 26 août 2026

Le rapport a été reconstruit intégralement à partir du code, des migrations, des workflows, des tests et du handoff technique du dépôt. Les versions de référence sont :

- [RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf](./RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf) — version de lecture et d’impression, 35 pages A4 ;
- [RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx](./RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx) — version Word éditable.

## Résumé

OneTech Tender Agent est un MVP d’IA agentique pour la gestion des appels d’offres publics. Il collecte des consultations publiques depuis HAICOP, normalise les faits dans PostgreSQL, télécharge les pièces sous contraintes, extrait leur texte par des méthodes natives ou par OCR, puis prépare un contexte traçable pour une analyse Go / No-Go en neuf sections. Une grille explicite de quatre critères sur vingt-cinq points structure la recommandation. Des validations déterministes contrôlent les scores, la cohérence de la décision, la complétude et l’empreinte du contexte.

L’exécution quotidienne s’appuie sur n8n, un worker Python et un registre de diffusion idempotent vers Mailpit, Gmail et Telegram. Un serveur MCP expose cinq opérations bornées à l’agent. Le résultat reste une aide à la décision : la validation humaine demeure obligatoire.

## État vérifié présenté dans le rapport

- 100 appels d’offres collectés ;
- 152 pièces documentaires présentes, hachées et extraites ;
- corpus : 41 PDF, 74 DOCX, 35 DOC, 1 PNG et 1 JPEG ;
- 5 outils MCP exposés ;
- 62 tests locaux réussis sur 62, hors intégration et réseau ;
- référence full-stack documentée : 67 tests Python et 6 tests SQL ;
- deux cas de démonstration traçables : `Tender-103283` à 24/100 et `Tender-103307` à 36/100, tous deux `NO_GO` ;
- rejeu sans duplication des consultations, documents, analyses et livraisons.

## Structure du rapport

Le document couvre le contexte du stage, l’état de l’art, les spécifications, la méthode, l’architecture, le modèle de données, la collecte, le pipeline documentaire et OCR, l’analyse Go / No-Go, l’automatisation, les séquences, MCP, les résultats, la sécurité, la démonstration, les compétences acquises et la conclusion. Il contient aussi une bibliographie, un scénario de démonstration de trois minutes et une checklist de soutenance.

## Diagrammes

Les figures sont intégrées dans le rapport et fournies séparément dans [diagrammes_finaux](./diagrammes_finaux/) :

1. chronologie du projet ;
2. diagramme de cas d’utilisation ;
3. architecture logique et déploiement ;
4. modèle de données et chaîne de traçabilité ;
5. pipeline de téléchargement, détection, extraction et OCR ;
6. matrice Go / No-Go ;
7. diagramme de séquence de l’exécution quotidienne ;
8. diagramme de séquence de l’interaction Telegram ;
9. architecture MCP ;
10. résultats de validation ;
11. contrôles de sécurité et de qualité ;
12. scénarios de démonstration.

## Positionnement

Le livrable est présenté comme un **MVP opérationnel, validé et démontrable**. Il ne revendique ni mise en production, ni gain métier chiffré, ni précision statistique non mesurée. Les pièces et recommandations restent soumises à une vérification humaine.
