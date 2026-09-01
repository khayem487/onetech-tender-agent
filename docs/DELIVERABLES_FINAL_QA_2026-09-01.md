# Contrôle final des livrables — 1er septembre 2026

## Verdict

Les livrables finaux sont cohérents, ouvrables et prêts à être transmis au tuteur entreprise.

La version publiée est construite sur la narration et les diagrammes de la version Claude, après audit factuel et visuel. Les éléments utiles de l’autre version ont uniquement servi de comparaison. Sa copie exacte reste archivée localement hors dépôt.

## Fichiers contrôlés

| Fichier | Contrôle | Résultat |
|---|---|---|
| `RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx` | ouverture et export Microsoft Word | réussi |
| `RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf` | format A4, pagination, rendu page par page | 34 pages, aucune page blanche |
| `PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx` | ouverture et export Microsoft PowerPoint | 16 diapositives, notes 16/16 |
| `PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf` | format 16:9, rendu slide par slide | 16 pages, aucun débordement visible |

## Corrections factuelles

- retrait du volume total non vérifié d’annonces HAICOP ;
- suppression de la durée hebdomadaire non confirmée ;
- distinction entre 62 tests locaux et 5 tests d’intégration ;
- remplacement des formulations absolues sur les doublons par le résultat mesuré de la campagne de validation ;
- suppression des tailles et compteurs de sauvegarde non nécessaires au récit ;
- description du modèle local uniquement comme benchmark expérimental encadré ;
- conclusion recentrée sur les apports livrés à One Tech ;
- aucune mention de fonctionnalités absentes dans le rapport ou la soutenance.

## Contrôle visuel

- thème bleu marine cohérent sur les 16 diapositives ;
- quatre diagrammes grand format créés pour l’architecture, la traçabilité, le pipeline quotidien et l’analyse Go/No-Go ;
- sources PlantUML Claude conservées et éditables ;
- rapport sans page blanche et sommaire vérifié après la pagination finale ;
- page de résultats alignée avec le snapshot validé.

## Validation technique

Exécution locale du 1er septembre 2026 :

```text
62 tests locaux réussis
5 tests d’intégration désélectionnés lorsque Docker est arrêté
```

Snapshot full-stack documenté du projet :

```text
62 tests locaux + 5 tests d’intégration = 67 tests Python
6 scripts SQL réussis
5/5 outils MCP validés
Mailpit, Gmail et Telegram validés
```

## Sécurité

- aucun token Telegram, jeton OpenClaw ou secret OAuth dans les livrables ;
- mots de passe locaux retirés du README courant ;
- valeurs d’authentification documentées via `.env` et `.env.example` ;
- scan du contenu texte courant : aucune valeur locale connue détectée ;
- les anciens mots de passe ayant existé dans l’historique Git doivent être renouvelés avant d’accorder l’accès au dépôt à un tiers.

## Empreintes SHA-256

```text
RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.docx
B2FEBB705F1AD15B6B4168D81ED79F55ABD4DDDE60385CF58720811ABE434710

RAPPORT_STAGE_KHAYEM_BEN_GHORBEL.pdf
ECA608F4C81A9ADB6FBCFFF8E350729BD283C012016B3424F8919B5EC7862516

PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pptx
E373F9D9A5C4DA5C473306E508E122972463B7694E2322AD285C4EE114C21EEA

PRESENTATION_SOUTENANCE_KHAYEM_BEN_GHORBEL.pdf
10D5C22F64D4C529840ACDF4A829C0B04860B643A8F6A01CEAEE42145178D722
```

## Git

Le remplacement doit être effectué par un commit normal, sans réécriture de l’historique ni force-push. Les quatre brouillons locaux non suivis restent exclus du commit.
