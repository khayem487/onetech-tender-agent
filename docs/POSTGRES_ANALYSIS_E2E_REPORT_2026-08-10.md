# Rapport de validation — analyse OpenClaw adossée à PostgreSQL

Date de validation : 10 août 2026

## Résultat

Le flux d'analyse historique a été reconnecté au stockage PostgreSQL sans
mélanger les faits officiels HAICOP et le raisonnement généré :

```text
HAICOP
  -> PostgreSQL (AO, détails et documents)
  -> téléchargement, SHA-256 et extraction PDF/DOCX
  -> fichier de contexte complet par Tender-ID
  -> lecture OpenClaw de toutes les sources
  -> fiche française en neuf sections
  -> validation stricte
  -> analyses_ao
  -> show-analysis et digest
```

Le parcours a été exécuté réellement sur `Tender-103283` et pas seulement avec
des données de test.

## État PostgreSQL validé

- 31 appels d'offres ;
- 50 documents publics ;
- 3 collectes HAICOP terminées ;
- 34 documents avec texte extrait ;
- 4 PDF sans couche texte ;
- 12 documents DOC non supportés ;
- 0 document en échec ;
- 0 document en attente ;
- 0 doublon d'appel d'offres ;
- 0 doublon de document ;
- 1 analyse persistée.

## Analyse réelle de référence

- Tender-ID : `Tender-103283` ;
- organisme : Société Nationale Immobilière Snit Centre ;
- couverture : 2 documents sur 2 extraits, dont un dossier de fond ;
- statut documentaire : `complete` ;
- adéquation : 0/25 ;
- faisabilité du délai : 20/25 ;
- charge administrative : 1/25 ;
- niveau de risque : 3/25 ;
- total : 24/100 ;
- décision : `NO_GO` ;
- analyse PostgreSQL : ID 23 ;
- fiche : `fiches/2026-08-10_snit-centre_assurance-decennale.md`.

Le premier enregistrement a inséré l'analyse. Le second enregistrement du même
contexte a réutilisé l'ID 23. `show-analysis` et `digest --limit 10` renvoient
les mêmes quatre notes, le même total, la même décision et les mêmes empreintes.

## Garanties ajoutées

- un avis seul reste une analyse partielle, même si son texte est lisible ;
- les documents sans texte, non supportés ou en échec sont signalés ;
- le hash du contexte ignore les timestamps de collecte, identifiants SQL et
  chemins locaux ;
- une modification réelle du contenu ou du profil change le hash ;
- un contexte devenu obsolète est refusé à l'enregistrement ;
- les quatre notes, le total et la décision du Markdown doivent correspondre
  exactement aux valeurs enregistrées ;
- une fiche partielle doit l'indiquer explicitement ;
- un profil One Tech incomplet ne peut pas enregistrer un `GO` définitif ;
- le snapshot exact lu par OpenClaw est conservé séparément des faits HAICOP ;
- le texte des AO est traité comme donnée non fiable, jamais comme instruction ;
- aucun secret `.env` n'est écrit dans les sources, fiches ou sorties.

## Commandes principales

```powershell
.\scripts\apply-database.ps1
.\scripts\test-database.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m onetech_ao.cli analysis-context Tender-103283
.\.venv\Scripts\python.exe -m onetech_ao.cli record-analysis Tender-103283 `
  --fiche "fiches\2026-08-10_snit-centre_assurance-decennale.md" `
  --status complete --score-adequation 0 --score-delai 20 `
  --score-administratif 1 --score-risque 3 --decision NO_GO `
  --context-sha256 "<hash du manifeste>"
.\.venv\Scripts\python.exe -m onetech_ao.cli show-analysis Tender-103283
.\.venv\Scripts\python.exe -m onetech_ao.cli digest --limit 10
```

Résultats finaux : quatre tests SQL réussis et 31 tests Python réussis.

## Skill OpenClaw

La proposition Skill Workshop `analyse-ao-20260810-c61f3246a8` a été révisée et
son scan est propre. Elle conserve le workflow historique PDF/DOCX/lien et ajoute
le routage PostgreSQL, la lecture complète en morceaux, la protection contre les
instructions incorporées, la couverture documentaire sémantique, le hash
obligatoire et la vérification après sauvegarde.

Son statut reste `pending`. Conformément à la sécurité Skill Workshop, elle ne
doit remplacer la skill active qu'après une demande explicite d'application.
Le backend et une exécution OpenClaw ponctuelle sont déjà validés ; l'application
de cette proposition rendra le routage naturel permanent dans les nouvelles
sessions de l'instance entreprise.

## Prochain point de reprise

1. Appliquer explicitement la proposition `analyse-ao-20260810-c61f3246a8`.
2. Relancer le gateway entreprise et ouvrir une nouvelle session TUI.
3. Rejouer la demande en langage naturel sur `Tender-103283`.
4. Présenter la fiche, pgAdmin, l'ID 23 et le replay anti-doublon à l'encadrant.
5. Valider le profil One Tech réel avec Makram.
6. Passer ensuite à l'automatisation quotidienne avec n8n et email/Telegram.

L'OCR et la conversion des anciens DOC sont utiles, mais secondaires par rapport
à la démonstration, au profil métier et à l'automatisation quotidienne.
