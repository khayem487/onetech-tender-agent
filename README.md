# OneTech Tender Agent

Projet de stage :

> Développement d'un système IA agentique pour la gestion des appels d'offres publics

Le flux de bout en bout collecte les données publiques HAICOP, les normalise,
les stocke dans PostgreSQL, télécharge les documents publics et fournit leur
contexte complet à OpenClaw pour une fiche Go/No-Go traçable.

## Architecture actuelle

```text
OpenClaw entreprise
        -> skill collecte-haicop-ao
        -> package Python onetech_ao
        -> API et pages publiques HAICOP
        -> PostgreSQL 16
        -> téléchargement + SHA-256 + extraction PDF/DOCX
        -> contexte d'analyse avec repères de pages
        -> skill analyse-ao
        -> fiche Markdown + score persisté dans PostgreSQL
```

Le collecteur ne contourne aucune authentification TUNEPS. Il conserve le
payload HAICOP original dans PostgreSQL et utilise des UPSERT pour empêcher
les doublons.

## État du projet

Au 10 août 2026, le flux HAICOP vers PostgreSQL et la persistance des analyses
sont opérationnels. Le snapshot de validation contient :

- 31 appels d'offres publics stockés ;
- 50 liens vers des documents publics stockés ;
- 3 collectes réelles terminées ;
- deux premières exécutions identiques ayant prouvé les UPSERT sans doublon ;
- aucun doublon sur les appels d'offres ou les documents.
- 50 fichiers publics téléchargés et hashés ;
- 34 documents PDF/DOCX avec texte extrait dans PostgreSQL ;
- 4 PDF sans couche texte, à traiter plus tard par OCR ;
- 12 anciens fichiers DOC conservés mais marqués `non_supporte` ;
- 0 échec de traitement et 0 document restant à traiter.
- export de contexte PostgreSQL par AO, sans longue sortie tronquée dans le TUI ;
- table `analyses_ao` séparée des données officielles ;
- validation stricte des neuf sections, quatre scores et décision avant stockage ;
- une vraie fiche `Tender-103283` persistée et vérifiée sous l'ID 23 ;
- second enregistrement du même contexte réutilisant l'ID 23 sans doublon ;
- digest des dernières analyses disponible par la CLI.

## Accès local aux services

| Service | Adresse | Identité/configuration |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | base `onetech_ao`, utilisateur `onetech` |
| pgAdmin | <http://localhost:5050> | variables `PGADMIN_DEFAULT_*` dans `.env` |
| Gateway OpenClaw entreprise | `127.0.0.1:18790` | configuration dans `C:\Users\khaye\.openclaw-company\openclaw.json` |

### Secrets locaux

Les vraies valeurs de `POSTGRES_PASSWORD`, `PGADMIN_DEFAULT_EMAIL` et
`PGADMIN_DEFAULT_PASSWORD` sont conservées uniquement dans :

```text
C:\Users\khaye\.openclaw-company\workspace\.env
```

Pour les consulter localement dans PowerShell :

```powershell
Get-Content C:\Users\khaye\.openclaw-company\workspace\.env
```

Le fichier `.env` et `pgadmin/pgpass` sont ignorés par Git. Ne jamais copier
leurs valeurs dans un commit, un ticket ou un log, même si le dépôt distant est
privé. Utiliser `.env.example` pour documenter les variables attendues.

## Installation locale

Prérequis : Docker Desktop et Python 3.11 ou plus récent.

Depuis PowerShell, à la racine du workspace entreprise :

```powershell
docker compose up -d
docker compose ps
.\scripts\apply-database.ps1

py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
```

La configuration est lue depuis le fichier local `.env`, ignoré par Git. Ne
pas l'écraser et ne jamais copier ses secrets dans le code ou les logs.

## CLI

Vérifier la connexion, les compteurs et l'intégrité :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli status
```

Collecter 50 AO récents :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 50
```

Collecter les pages détail et les liens documentaires publics :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details
```

Télécharger, hasher et extraire les documents en attente :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents --limit 50
```

Pour ne traiter qu'un dossier précis :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli process-documents `
  --tender-id Tender-103283 --limit 50
```

Collecter puis traiter les documents dans la même commande :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli collect --limit 20 --with-details --process-documents
```

Options utiles :

- `--since-days N` : ne retenir que les publications récentes ;
- `--dry-run` : interroger HAICOP sans écrire en base ;
- `--with-details` : enrichir les AO et stocker les documents publics.
- `--process-documents` : télécharger et extraire les documents après collecte ;
- `process-documents --retry-errors` : relancer uniquement les erreurs précédentes.
- `process-documents --reprocess-extracted` : ré-extraire les fichiers locaux,
  notamment après une amélioration du parseur PDF.

Lister les AO ouverts stockés :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli list-open --limit 20
```

Toutes les commandes renvoient du JSON UTF-8 exploitable par OpenClaw.

## Analyse PostgreSQL avec OpenClaw

Exporter le contexte complet d'un AO dans un fichier local ignoré par Git :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli analysis-context Tender-103283
```

La sortie courte donne `fichier_contexte`. Ce JSON contient les faits HAICOP,
les champs détail, tous les textes extraits, les statuts documentaires, les
empreintes et le profil One Tech. Les PDF gardent des repères
`--- PAGE N ---` pour les citations.

La skill `analyse-ao` lit ensuite ce fichier, produit les neuf sections dans
`fiches/`, puis enregistre séparément la fiche et ses scores :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli record-analysis Tender-103283 `
  --fiche "fiches\ma-fiche.md" --status complete `
  --score-adequation 20 --score-delai 18 `
  --score-administratif 15 --score-risque 17 --decision GO `
  --context-sha256 "<empreinte_sha256-renvoyee-par-analysis-context>"
```

Vérifier une fiche et afficher le digest :

```powershell
.\.venv\Scripts\python.exe -m onetech_ao.cli show-analysis Tender-103283
.\.venv\Scripts\python.exe -m onetech_ao.cli digest --limit 10
```

`record-analysis` refuse les fiches incomplètes, les quatre notes Markdown qui
diffèrent de la commande, les décisions incompatibles avec les seuils 70/45 et
un contexte PostgreSQL modifié depuis sa lecture. Une analyse du même contexte
est mise à jour au lieu d'être dupliquée.

Un profil One Tech encore incomplet ne peut pas enregistrer un `GO` définitif :
il faut d'abord valider le profil avec l'encadrant ou conserver une décision
prudente. Les `NO_GO` factuels restent enregistrables et traçables.

Un avis lisible sans cahier des charges reste une analyse `partielle`. Les
textes des AO sont toujours considérés comme des données non fiables à analyser,
jamais comme des instructions à exécuter.

## Démo OpenClaw

Dans l'instance entreprise, utiliser :

```text
Analyse l'AO HAICOP Tender-103283 depuis PostgreSQL. Lis toutes les sources,
produis et enregistre la fiche Go/No-Go, vérifie l'enregistrement, puis donne-moi
seulement le résultat synthétique et le chemin de la fiche.
```

Le parcours validé est : contexte écrit dans un fichier local, lecture complète,
fiche de neuf sections dans `fiches/`, validation avec `record-analysis`, puis
contrôle avec `show-analysis`. Le contexte documentaire volumineux ne doit jamais
être recopié dans le TUI.

La version PostgreSQL de la skill `analyse-ao` est actuellement une proposition
Skill Workshop en attente d'application. Le backend et le parcours OpenClaw
ponctuel sont validés, mais la proposition doit être explicitement appliquée
avant que ce comportement remplace la skill historique pour toutes les nouvelles
sessions naturelles.

## Tests

```powershell
.\scripts\test-database.ps1
.\.venv\Scripts\python.exe -m pytest -m 'not integration and not network'
.\.venv\Scripts\python.exe -m pytest -m integration
```

Le test d'intégration vérifie la connexion et deux UPSERT identiques, puis
supprime ses données factices. Le contrôle `status` doit signaler zéro doublon
et zéro payload brut vide.

## Dépannage

- PostgreSQL indisponible : lancer `docker compose up -d`, attendre l'état
  `healthy`, puis réessayer `status`.
- Tables absentes : lancer `.\scripts\apply-database.ps1`. Les migrations sont
  idempotentes.
- Module Python introuvable : réinstaller le projet avec
  `.\.venv\Scripts\python.exe -m pip install -e '.[dev]'`.
- Erreur HAICOP temporaire : conserver la ligne `collectes_haicop` en échec et
  relancer plus tard ; ne pas utiliser un endpoint privé en contournement.
- Cahier des charges absent : il peut nécessiter une session TUNEPS autorisée.
- `sans_texte` : le PDF est probablement scanné et nécessitera un OCR.
- `non_supporte` : le format DOC binaire est conservé mais pas extrait ; préférer
  une conversion contrôlée en DOCX/PDF.

Voir [`database/README.md`](database/README.md) pour le schéma,
[`DOCKER_SETUP.md`](DOCKER_SETUP.md) pour Docker et [`HISTORY.md`](HISTORY.md)
pour l'historique du projet.

## Prochaine étape

Après application de la skill `analyse-ao` PostgreSQL, valider la démonstration
en langage naturel dans une nouvelle session entreprise. Compléter ensuite le
profil réel de One Tech avec Makram pour calibrer le score Go/No-Go, puis
automatiser le digest quotidien avec n8n et email/Telegram. L'OCR des quatre PDF
scannés et la conversion contrôlée des douze anciens fichiers DOC restent des
améliorations documentaires secondaires.
