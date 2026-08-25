# OneTech Tender Agent

Projet de stage :

> Développement d'un système IA agentique pour la gestion des appels d'offres publics

Le flux de bout en bout collecte les données publiques HAICOP, les normalise,
les stocke dans PostgreSQL, télécharge les documents publics et fournit leur
contexte complet à OpenClaw pour une fiche Go/No-Go traçable.

## Architecture actuelle

```text
n8n (08:00 Europe/Paris, jours ouvrés)
        -> ao-worker authentifié
        -> OpenClaw entreprise
        -> package Python onetech_ao
        -> API et pages publiques HAICOP
        -> PostgreSQL 16
        -> téléchargement + SHA-256
        -> extraction PDF/DOCX + OCR + conversion DOC
        -> analyse Go/No-Go traçable
        -> digest Mailpit + Gmail

OpenClaw / Claude / client MCP
        -> serveur MCP onetech-tender (5 outils)
        -> mêmes données et fonctions PostgreSQL
```

Le collecteur ne contourne aucune authentification TUNEPS. Il conserve le
payload HAICOP original dans PostgreSQL et utilise des UPSERT pour empêcher
les doublons.

## État du projet

Au 25 août 2026, le pipeline local est opérationnel et reproductible :

- 100 appels d'offres publics et 152 documents stockés sans doublon ;
- 152/152 fichiers téléchargés, hashés et extraits dans PostgreSQL ;
- formats traités : 41 PDF, 35 DOC, 74 DOCX, 1 PNG et 1 JPEG ;
- OCR Tesseract réel validé sur les documents scannés ;
- conversion contrôlée des anciens DOC par LibreOffice validée ;
- analyse et scoring conservés séparément des faits officiels ;
- digest n8n quotidien actif, avec Mailpit local et Gmail multi-destinataires ;
- registre de diffusion idempotent par canal et destinataire ;
- serveur MCP enregistré et testé avec cinq outils ;
- `phi4-mini` installé dans Ollama et sélectionnable dans l'OpenClaw entreprise ;
- démarrage Windows automatique et watchdog toutes les cinq minutes ;
- sauvegarde complète avec checksums et restauration PostgreSQL testée en base isolée ;
- 67 tests Python et 6 tests SQL réussis.

Telegram est implémenté mais reste volontairement désactivé tant qu'un bot
OneTech distinct du bot personnel et l'identifiant négatif du groupe ne sont
pas configurés. Odoo est volontairement hors périmètre.

## Accès local aux services

| Service | Adresse | Identité/configuration |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | base `onetech_ao`, utilisateur `onetech` |
| pgAdmin | <http://localhost:5050> | administration graphique PostgreSQL |
| n8n | <http://localhost:5678> | orchestration du digest quotidien |
| Mailpit | <http://localhost:8025> | boîte email locale de test |
| ao-worker | réseau Docker interne, port `8080` | exécution contrôlée du pipeline Python |
| Gateway OpenClaw entreprise | `127.0.0.1:18790` | configuration dans `C:\Users\khaye\.openclaw-company\openclaw.json` |
| Ollama | `127.0.0.1:11434` | modèle local `phi4-mini:latest` |
| MCP `onetech-tender` | stdio local | cinq outils de collecte, lecture, analyse et digest |

### Identifiants locaux pgAdmin et PostgreSQL

Ces identifiants sont ceux de l'environnement de développement local actuel.
Les services sont liés à `127.0.0.1` et ne sont pas exposés directement sur le
réseau. Ils doivent être remplacés avant tout déploiement partagé ou public.

Connexion à l'interface pgAdmin :

```text
URL      : http://localhost:5050
Email    : admin@onetech.com
Password : OneTech_Admin#2026!9pG
```

Connexion de pgAdmin au serveur PostgreSQL :

```text
Nom du serveur       : OneTech PostgreSQL
Host depuis Windows  : 127.0.0.1
Host depuis Docker   : postgres
Port                 : 5432
Maintenance database : onetech_ao
Username             : onetech
Password             : OneTech_AO#2026_Postgres!7qM
```

Le premier mot de passe ouvre l'interface pgAdmin. Le second authentifie
pgAdmin, Python ou `psql` auprès du serveur PostgreSQL. Ce sont deux comptes
différents.

Connexion à l'interface n8n :

```text
URL      : http://localhost:5678
Email    : admin@onetech.com
Password : OneTech_n8n#2026!9n8
Rôle     : global:owner
```

Ce compte est enregistré dans le volume persistant `onetech_n8n_data`. La
variable `N8N_ENCRYPTION_KEY` n'est pas son mot de passe : elle sert à chiffrer
les credentials techniques conservés par n8n.

Mailpit ne demande aucun compte : son interface est accessible localement sur
`http://localhost:8025`, et son serveur SMTP local écoute sur
`127.0.0.1:1025` sans utilisateur ni mot de passe.

### Configuration locale et autres secrets

La source de configuration locale reste :

```text
C:\Users\khaye\.openclaw-company\workspace\.env
```

Pour les consulter localement dans PowerShell :

```powershell
Get-Content C:\Users\khaye\.openclaw-company\workspace\.env
```

Le fichier `.env` et `pgadmin/pgpass` sont ignorés par Git. Les autres secrets,
notamment `AUTOMATION_API_TOKEN`, `N8N_ENCRYPTION_KEY`, les identifiants Gmail,
Telegram et le token du gateway OpenClaw, ne doivent pas être ajoutés au README
ou aux commits. Utiliser `.env.example` pour documenter les variables attendues.

## Installation locale

Prérequis : Docker Desktop et Python 3.11 ou plus récent.

Le démarrage recommandé, à la racine du workspace entreprise :

```powershell
.\scripts\start-onetech-stack.ps1 -StartGateway -StartOllama
```

Pour une installation manuelle :

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
docker compose exec -T ao-worker python -m onetech_ao.cli process-documents --limit 50
```

Pour ne traiter qu'un dossier précis :

```powershell
docker compose exec -T ao-worker python -m onetech_ao.cli process-documents `
  --tender-id Tender-103283 --limit 50
```

Collecter puis traiter les documents dans la même commande :

```powershell
docker compose exec -T ao-worker python -m onetech_ao.cli collect --limit 20 --with-details --process-documents
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

Un avis lisible sans cahier des charges reste une analyse `partielle`. Une
analyse partielle ne peut plus enregistrer un `GO` définitif : elle doit rester
`A_DISCUTER` ou `NO_GO` avec des scores cohérents. Les textes des AO sont
toujours considérés comme des données non fiables à analyser, jamais comme des
instructions à exécuter.

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

La version PostgreSQL de la skill `analyse-ao` est appliquée et active depuis
`skills/analyse-ao/SKILL.md`. Une nouvelle session de l'interface OpenClaw
entreprise l'a validée en langage naturel sur `Tender-103307` : deux documents
sur deux lus, fiche en neuf sections, analyse PostgreSQL ID 53 et replay
anti-doublon réutilisant le même ID.

## Automatisation quotidienne

Le pipeline quotidien est maintenant en place :

```text
n8n (jours ouvrés, 08:00 Europe/Paris)
        -> ao-worker authentifié
        -> gateway OpenClaw entreprise
        -> collecte HAICOP + PostgreSQL + documents + analyse-ao
        -> digest Markdown persistant
        -> registre anti-doublon de diffusion
        -> Mailpit local par défaut, puis Gmail/Telegram sur opt-in explicite
```

Services supplémentaires :

| Service | Adresse | Usage |
| --- | --- | --- |
| n8n | <http://localhost:5678> | orchestration et déclenchement manuel/planifié |
| Mailpit | <http://localhost:8025> | boîte email locale de test, sans envoi Internet |
| ao-worker | réseau Docker interne, port `8080` | passerelle limitée entre n8n et OpenClaw |

Avant une exécution, le gateway entreprise doit être lancé sur `127.0.0.1:18790` :

```powershell
C:\Users\khaye\.openclaw-company\start-company-gateway.cmd
```

Pour importer une première fois le workflow n8n, l'activer et redémarrer
seulement n8n si nécessaire :

```powershell
.\scripts\activate-daily-automation.ps1
```

Le script est idempotent : il ne crée pas un second workflow s'il existe déjà.
Le workflow planifié reste dans la base persistante de n8n ; le fichier JSON
monté dans `automation/n8n/workflows/` est sa définition versionnée et ne
s'importe pas automatiquement.

Pour un test visuel, ouvrir n8n, sélectionner `OneTech AO - Daily Digest`, puis
utiliser **Execute workflow** depuis le déclencheur manuel. Vérifier le digest
dans `data/digests/`, les journaux dans `executions_quotidiennes`, le message de
secours dans Mailpit et le message réel dans Gmail. Le mode local validé est :

```text
AUTOMATION_DELIVERY_ARGS=--mailpit --email
```

Gmail est actif via le compte OAuth défini par `GOG_ACCOUNT`. Les destinataires
sont une liste séparée par des virgules dans `DIGEST_EMAIL_TO`. Chaque adresse
possède sa propre preuve d'envoi et sa propre protection anti-doublon dans
PostgreSQL. L'envoi réel et le retry idempotent ont été validés le
17 août 2026 : une relance retourne `deja_envoyee` sans créer de second message.
Mailpit reste activé comme preuve locale et canal de secours. Telegram est
implémenté mais reste désactivé par défaut. Son activation exige explicitement
`TELEGRAM_ENABLED=true`, un token de bot OneTech distinct du bot personnel et
un `TELEGRAM_CHAT_ID` négatif correspondant à un groupe. Le script de démarrage
et le script d'activation manuelle refusent une configuration privée ou
partagée et maintiennent alors le workflow Telegram inactif. Ne jamais ajouter
le jeton OAuth ou un autre secret au dépôt.

## Serveur MCP et modèle local Phi

Le serveur MCP `onetech-tender` expose exactement :

```text
collect_tenders
list_open_tenders
get_tender
analyze_tender
generate_digest
```

`analyze_tender` reste honnête et borné : il lit une analyse persistée ou
prépare un contexte factuel ; il ne prétend pas avoir enregistré une nouvelle
décision. Les réponses sont déterministes, limitées en taille et expurgent les
secrets des erreurs internes.

Le modèle `ollama/phi4-mini:latest` est autorisé dans l'OpenClaw entreprise. Il
fonctionne localement sur CPU et sert uniquement de second avis expérimental :
le benchmark a correctement rejeté deux AO hors périmètre, mais il reste lent
et peut inventer certaines justifications. Le modèle OpenAI reste le modèle de
production pour l'analyse quotidienne.

Le tri initial respecte le profil OneTech : une AO doit atteindre le seuil
`minimum_relevance_score` (actuellement `6`) et les achats matériels sans
composante numérique explicite sont pénalisés. Le digest peut donc signaler
qu'aucune opportunité pertinente n'est disponible, plutôt que forcer un faux
positif hors périmètre IT.

Les secrets d'automatisation `AUTOMATION_API_TOKEN`, `N8N_ENCRYPTION_KEY` et
`OPENCLAW_GATEWAY_TOKEN` existent seulement dans `.env` ou la configuration
locale du gateway ; ils ne doivent jamais être affichés ni commités.

## Tests

```powershell
.\scripts\test-database.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -m 'not integration and not network'
.\.venv\Scripts\python.exe -m pytest -m integration
```

Le snapshot final exécute 67 tests Python et 6 scripts SQL. Les tests
d'intégration vérifient les UPSERT, l'idempotence, l'automatisation, Telegram et
le protocole MCP, puis suppriment leurs données factices. Le contrôle `status`
doit signaler zéro doublon, zéro payload brut vide et 0 document restant.

## Dépannage

- Gateway entreprise indisponible : lancer
  `C:\Users\khaye\.openclaw-company\start-company-gateway.cmd`, puis vérifier
  que `127.0.0.1:18790` écoute avant de lancer le digest.
- Worker indisponible : vérifier `docker compose ps`, puis ouvrir
  `http://localhost:8025` uniquement pour Mailpit ; le worker est interne et
  son contrôle `/health` se fait depuis Docker.
- Workflow n8n absent ou inactif : lancer
  `.\scripts\activate-daily-automation.ps1`, puis vérifier le workflow dans
  n8n. Le JSON monté seul ne suffit pas.
- Aucun email visible pendant le test : contrôler Mailpit à
  `http://localhost:8025`; le mode par défaut n'envoie rien sur Gmail.
- PostgreSQL indisponible : lancer `docker compose up -d`, attendre l'état
  `healthy`, puis réessayer `status`.
- Tables absentes : lancer `.\scripts\apply-database.ps1`. Les migrations sont
  idempotentes.
- Module Python introuvable : réinstaller le projet avec
  `.\.venv\Scripts\python.exe -m pip install -e '.[dev]'`.
- Erreur HAICOP temporaire : conserver la ligne `collectes_haicop` en échec et
  relancer plus tard ; ne pas utiliser un endpoint privé en contournement.
- Cahier des charges absent : il peut nécessiter une session TUNEPS autorisée.
- OCR indisponible : vérifier `tesseract --version` et `pdftoppm -v` dans
  `onetech-ao-worker`, puis reconstruire l'image.
- Conversion DOC indisponible : vérifier `libreoffice --headless --version`
  dans `onetech-ao-worker`, puis relancer avec `--retry-errors`.
- Contrôle global : lancer
  `.\scripts\healthcheck-onetech-stack.ps1 -RequireGateway -RequireOllama -RequireWorkflows -RequireMcp`.

Voir [`database/README.md`](database/README.md) pour le schéma,
[`DOCKER_SETUP.md`](DOCKER_SETUP.md) pour Docker,
[`docs/OPERATIONS.md`](docs/OPERATIONS.md) pour les sauvegardes et la
supervision, et [`HISTORY.md`](HISTORY.md) pour l'historique du projet.

## Etat actuel et suites

Le flux complet est prêt pour une démonstration locale : collecte, stockage,
documents, OCR/DOC, analyse, digest Gmail, orchestration n8n, MCP, modèle Phi de
comparaison, sauvegarde/restauration et supervision. Le profil OneTech marqué
`VALIDATED_V1` reste la source de scoring.

Le seul branchement externe restant est l'association d'un bot Telegram
OneTech dédié au groupe déjà créé. Odoo n'est pas réalisé, conformément au
périmètre décidé.
